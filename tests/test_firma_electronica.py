"""Firma electronica de prescripciones por prescriptor (RF-35, RF-36, RNF-20)."""

import json
import os

import pytest

from backend.models.prescription import PrescriptionBase, ValidationResult
from backend.repositories.fabric_prescription_repo import FabricPrescriptionRepository
from backend.repositories.signing_key_repo import SigningKeyRepository
from backend.security import signing
from backend.security.canonical import build_canonical_payload, sha256_hex, verify_chain
from backend.security.crypto import CryptoService
from backend.services.prescription_service import PrescriptionService
from backend.services.signing_service import SigningService
from tests.fakes.fake_fabric_gateway import FakeFabricClient

_CRYPTO = CryptoService(os.urandom(32))


def _crypto():
    """Proveedor de CryptoService para los tests."""
    return _CRYPTO


class _ValidacionStub:
    """Motor de validacion fijo."""

    def validate(self, data):
        """Devuelve siempre un veredicto aprobado."""
        return ValidationResult(estado="APROBADO", probabilidad_concordante=0.9)


def _datos(**overrides):
    """Datos minimos de una prescripcion valida."""
    base = dict(
        patient_id=1,
        edad=61,
        sexo="Femenino",
        peso_kg=70.5,
        talla_cm=165.0,
        diagnostico_cie10="C18.7",
        localizacion_tumor="Colon sigmoides",
        tipo_histologico="Adenocarcinoma",
        t="T3",
        n="N1",
        m="M0",
        estadio="III",
        linea_tratamiento="Adyuvancia",
        id_regimen="R02",
        dosis_por_farmaco=[{"monodroga": "oxaliplatino", "dosis_mg": 230.0}],
        medico_prescriptor="Dra. Perez",
        matricula="MN 12345",
    )
    base.update(overrides)
    return base


@pytest.fixture()
def fake():
    """Red Fabric en memoria."""
    return FakeFabricClient()


@pytest.fixture()
def firmas():
    """Servicio de firma con custodia en memoria."""
    return SigningService(SigningKeyRepository(), _crypto)


@pytest.fixture()
def svc(fake, firmas):
    """Servicio de prescripciones con firma electronica."""
    return PrescriptionService(FabricPrescriptionRepository(fake), _ValidacionStub(), signing_service=firmas)


def _asset(fake, prescription_id):
    """Lee el asset crudo del fake de Fabric."""
    return json.loads(fake.query("GetPrescription", [prescription_id]))


def test_primitivas_firman_y_verifican():
    privada, publica = signing.generar_par_claves()
    firma = signing.firmar(privada, "contenido")
    assert signing.verificar(publica, "contenido", firma)
    assert not signing.verificar(publica, "contenido alterado", firma)
    assert not signing.verificar(publica, "contenido", "no-es-base64")


def test_la_huella_es_estable_y_distingue_claves():
    _, publica_a = signing.generar_par_claves()
    _, publica_b = signing.generar_par_claves()
    assert signing.huella_clave_publica(publica_a) == signing.huella_clave_publica(publica_a)
    assert signing.huella_clave_publica(publica_a) != signing.huella_clave_publica(publica_b)


def test_el_secreto_cifrado_queda_atado_a_su_contexto():
    cifrado = _CRYPTO.encrypt_secret("clave", "signing_key:presc")
    assert _CRYPTO.decrypt_secret(cifrado, "signing_key:presc") == "clave"
    with pytest.raises(Exception):
        _CRYPTO.decrypt_secret(cifrado, "signing_key:otro")


def test_el_alta_firma_la_prescripcion(svc, fake):
    creada = svc.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    firma = creada.clinical.firma
    assert firma["algoritmo"] == signing.ALGORITMO
    assert firma["firmante"] == "presc"
    assert firma["matricula"] == "MN 12345"
    assert "PRIVATE" not in json.dumps(_asset(fake, creada.prescription_id))


def test_la_firma_verifica_y_la_cadena_sigue_integra(svc, fake):
    creada = svc.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    resultado = svc.verify_signature(creada.prescription_id)
    assert resultado.estado == "valida"
    assert resultado.clave_registrada is True
    assert verify_chain(_asset(fake, creada.prescription_id))["valido"]


def test_la_clave_se_reutiliza_entre_prescripciones(svc):
    primera = svc.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    segunda = svc.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    assert primera.clinical.firma["huella_clave"] == segunda.clinical.firma["huella_clave"]


def test_contenido_alterado_invalida_la_firma(svc, fake, firmas):
    creada = svc.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    asset = _asset(fake, creada.prescription_id)
    asset["clinical"]["dosis_por_farmaco"][0]["dosis_mg"] = 999.0
    resultado = firmas.verificar(asset)
    assert resultado["estado"] == "invalida"
    assert "huella" in resultado["detalle"]


def test_clave_ajena_invalida_la_firma(svc, fake, firmas):
    creada = svc.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    asset = _asset(fake, creada.prescription_id)
    _, publica_intrusa = signing.generar_par_claves()
    asset["clinical"]["firma"]["clave_publica_pem"] = publica_intrusa
    asset["clinical"]["firma"]["huella_clave"] = signing.huella_clave_publica(publica_intrusa)
    resultado = firmas.verificar(asset)
    assert resultado["estado"] == "invalida"
    assert resultado["clave_registrada"] is False


def test_prescripcion_anterior_sin_firma(fake, firmas):
    clinical = _datos()
    clinical["superficie_corporal_m2"] = 1.79
    canonical = build_canonical_payload(clinical, {"estado": "APROBADO"}, "2026-03-01T00:00:00Z")
    repo = FabricPrescriptionRepository(fake)
    repo.create("01VIEJA", canonical)
    servicio = PrescriptionService(repo, _ValidacionStub(), signing_service=firmas)
    resultado = servicio.verify_signature("01VIEJA")
    assert resultado.estado == "sin_firma"


def test_clave_revocada_genera_una_nueva(svc, firmas):
    primera = svc.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    firmas.revocar("presc")
    segunda = svc.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    assert primera.clinical.firma["huella_clave"] != segunda.clinical.firma["huella_clave"]
    assert svc.verify_signature(primera.prescription_id).estado == "valida"


def test_la_firma_cubre_el_contenido_sin_el_bloque_firma(svc, fake):
    creada = svc.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    asset = _asset(fake, creada.prescription_id)
    sin_firma = dict(asset["clinical"])
    sin_firma.pop("firma")
    contenido = build_canonical_payload(sin_firma, asset["ml"], asset["created_at"])
    assert sha256_hex(contenido) == asset["clinical"]["firma"]["contenido_hash"]


def test_algoritmo_no_soportado_invalida_la_firma(svc, fake, firmas):
    creada = svc.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    asset = _asset(fake, creada.prescription_id)
    asset["clinical"]["firma"]["algoritmo"] = "RSA-1024"
    assert "algoritmo" in firmas.verificar(asset)["detalle"]


def test_custodia_inaccesible_no_impide_verificar(svc, fake):
    creada = svc.create(PrescriptionBase(**_datos()), prescriptor_username="presc")

    class _RepoCaido(SigningKeyRepository):
        """Custodia que falla al consultar."""

        def find_by_fingerprint(self, fingerprint):
            """Simula la base caida."""
            raise RuntimeError("sin base")

    resultado = SigningService(_RepoCaido(), _crypto).verificar(_asset(fake, creada.prescription_id))
    assert resultado["estado"] == "valida"
    assert resultado["clave_registrada"] is None


def test_primitivas_rechazan_claves_invalidas():
    with pytest.raises(Exception):
        signing.huella_clave_publica("no es una clave")
    with pytest.raises(Exception):
        signing.firmar("no es una clave", "contenido")
    assert not signing.verificar("no es una clave", "contenido", "AAAA")


def test_reintento_del_mismo_alta_devuelve_el_asset(fake, firmas):
    from backend.blockchain.fabric_client import FabricBusinessError

    class _RepoDobleSubmit(FabricPrescriptionRepository):
        """Simula que la primera escritura ya habia commiteado."""

        def create(self, prescription_id, canonical):
            """Escribe y luego responde 'ya existe'."""
            super().create(prescription_id, canonical)
            raise FabricBusinessError("ya existe", error_type="already_exists")

        def is_already_exists(self, exc):
            """El error corresponde a un alta duplicada."""
            return True

    servicio = PrescriptionService(_RepoDobleSubmit(fake), _ValidacionStub(), signing_service=firmas)
    creada = servicio.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    assert creada.clinical.firma["firmante"] == "presc"


def test_cargador_del_modelo_sin_artefacto(monkeypatch, tmp_path):
    from backend.ml import model_loader

    monkeypatch.setattr(model_loader, "_ARTEFACTO", None)
    monkeypatch.setattr(model_loader, "_CARGA_INTENTADA", False)
    monkeypatch.setenv("ML_MODEL_PATH", str(tmp_path / "no_existe.joblib"))
    assert model_loader.cargar_modelo() is None
    assert model_loader.cargar_modelo() is None
    assert not model_loader.modelo_disponible()


def test_cargador_del_modelo_con_ruta_por_defecto(monkeypatch):
    from backend.ml import model_loader

    monkeypatch.setattr(model_loader, "_ARTEFACTO", None)
    monkeypatch.setattr(model_loader, "_CARGA_INTENTADA", False)
    monkeypatch.delenv("ML_MODEL_PATH", raising=False)
    artefacto = model_loader.cargar_modelo()
    assert artefacto is not None and artefacto.get("model") is not None


def test_sin_servicio_de_firma_la_verificacion_no_esta_disponible(fake):
    from backend.error_handlers import DomainError

    servicio = PrescriptionService(FabricPrescriptionRepository(fake), _ValidacionStub())
    creada = servicio.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    assert creada.clinical.firma is None
    with pytest.raises(DomainError):
        servicio.verify_signature(creada.prescription_id)
