"""Firma electronica de prescripciones por prescriptor (RF-35, RF-36, RNF-20).

El contenido firmado es el payload canonico de la prescripcion SIN el bloque
`firma` ({clinical sin firma, created_at, ml}). La firma se inserta despues en
`clinical.firma`, de modo que payload_hash cubre tambien la firma y la firma
cubre todo lo demas, sin dependencia circular.
"""

import logging
from collections.abc import Callable

from backend.security import signing
from backend.security.canonical import build_canonical_payload, sha256_hex

logger = logging.getLogger(__name__)

ESTADO_VALIDA = "valida"
ESTADO_INVALIDA = "invalida"
ESTADO_SIN_FIRMA = "sin_firma"


def _contexto_clave(username: str) -> str:
    """Contexto AAD con que se cifra la clave privada de un usuario."""
    try:
        return "signing_key:" + username
    except Exception as exc:
        logger.error("Error al armar el contexto de clave: %s", exc, exc_info=True)
        raise


def contenido_firmable(clinical: dict, ml: dict, created_at: str) -> str:
    """Devuelve el payload canonico que se firma: el asset sin el bloque firma."""
    try:
        sin_firma = dict(clinical)
        sin_firma.pop("firma", None)
        return build_canonical_payload(sin_firma, ml, created_at)
    except Exception as exc:
        logger.error("Error al armar el contenido firmable: %s", exc, exc_info=True)
        raise


class SigningService:
    """Custodia de claves por prescriptor, firma y verificacion de prescripciones."""

    def __init__(self, repo, crypto_provider: Callable) -> None:
        """repo: SigningKeyRepository; crypto_provider: devuelve el CryptoService vigente."""
        try:
            self._repo = repo
            self._crypto_provider = crypto_provider
        except Exception as exc:
            logger.error("Error al inicializar SigningService: %s", exc, exc_info=True)
            raise

    def _obtener_o_crear_clave(self, username: str) -> dict:
        """Devuelve la clave vigente del usuario; si no tiene, la genera y la registra."""
        try:
            clave = self._repo.find_active(username)
            if clave is not None:
                return clave
            privada_pem, publica_pem = signing.generar_par_claves()
            privada_enc = self._crypto_provider().encrypt_secret(privada_pem, _contexto_clave(username))
            huella = signing.huella_clave_publica(publica_pem)
            self._repo.insert(username, signing.ALGORITMO, publica_pem, privada_enc, huella)
            del privada_pem
            logger.info("Clave de firma generada para '%s' (huella %s).", username, huella[:16])
            return self._repo.find_active(username)
        except Exception as exc:
            logger.error("Error al obtener la clave de firma de %s: %s", username, exc, exc_info=True)
            raise

    def firmar(self, username: str, matricula: str, clinical: dict, ml: dict, created_at: str) -> dict:
        """Firma el contenido de la prescripcion y devuelve el bloque `firma`."""
        try:
            clave = self._obtener_o_crear_clave(username)
            privada_pem = self._crypto_provider().decrypt_secret(clave["private_key_enc"], _contexto_clave(username))
            contenido = contenido_firmable(clinical, ml, created_at)
            valor = signing.firmar(privada_pem, contenido)
            del privada_pem
            return {
                "algoritmo": signing.ALGORITMO,
                "contenido_hash": sha256_hex(contenido),
                "valor_b64": valor,
                "clave_publica_pem": clave["public_key_pem"],
                "huella_clave": clave["key_fingerprint"],
                "firmante": username,
                "matricula": matricula,
                "firmado_en": created_at,
            }
        except Exception as exc:
            logger.error("Error al firmar la prescripcion de %s: %s", username, exc, exc_info=True)
            raise

    def revocar(self, username: str) -> None:
        """Revoca las claves vigentes del usuario (baja de cuenta)."""
        try:
            self._repo.revoke(username)
        except Exception as exc:
            logger.error("Error al revocar la clave de %s: %s", username, exc, exc_info=True)
            raise

    def verificar(self, asset: dict) -> dict:
        """Verifica la firma de un asset tal como lo devuelve el chaincode."""
        try:
            clinical = asset.get("clinical") or {}
            firma = clinical.get("firma")
            resultado = {
                "estado": ESTADO_SIN_FIRMA,
                "algoritmo": None,
                "firmante": None,
                "matricula": None,
                "huella_clave": None,
                "firmado_en": None,
                "clave_registrada": None,
                "detalle": "La prescripcion no tiene firma electronica (anterior a RF-35).",
            }
            if not firma:
                return resultado

            resultado["algoritmo"] = firma.get("algoritmo")
            resultado["firmante"] = firma.get("firmante")
            resultado["matricula"] = firma.get("matricula")
            resultado["huella_clave"] = firma.get("huella_clave")
            resultado["firmado_en"] = firma.get("firmado_en")

            contenido = contenido_firmable(clinical, asset.get("ml") or {}, asset.get("created_at", ""))
            publica_pem = firma.get("clave_publica_pem", "")
            errores = []
            if firma.get("algoritmo") != signing.ALGORITMO:
                errores.append("algoritmo no soportado")
            if sha256_hex(contenido) != firma.get("contenido_hash"):
                errores.append("el contenido no reproduce la huella firmada")
            if signing.huella_clave_publica(publica_pem) != firma.get("huella_clave"):
                errores.append("la clave publica no corresponde a la huella declarada")
            if not signing.verificar(publica_pem, contenido, firma.get("valor_b64", "")):
                errores.append("la firma no corresponde al contenido")

            resultado["clave_registrada"] = self._clave_registrada(firma)
            if resultado["clave_registrada"] is False:
                errores.append("la clave no pertenece al firmante declarado")

            if errores:
                resultado["estado"] = ESTADO_INVALIDA
                resultado["detalle"] = "; ".join(errores)
            else:
                resultado["estado"] = ESTADO_VALIDA
                resultado["detalle"] = "Firma valida: el contenido no fue alterado desde su firma."
            return resultado
        except Exception as exc:
            logger.error("Error al verificar la firma: %s", exc, exc_info=True)
            raise

    def _clave_registrada(self, firma: dict) -> bool | None:
        """Indica si la huella figura en la custodia a nombre del firmante (None si no se puede consultar)."""
        try:
            registro = self._repo.find_by_fingerprint(firma.get("huella_clave", ""))
            if registro is None:
                return False
            return registro["username"] == firma.get("firmante")
        except Exception as exc:
            logger.warning("No se pudo consultar la custodia de claves: %s", exc)
            return None
