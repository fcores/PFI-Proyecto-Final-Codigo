"""Motor hibrido de validacion: reglas deterministicas + LightGBM."""

import logging
import math

from backend.ml.feature_mapper import prescription_a_datos_modelo, prescription_a_features
from backend.ml.guias import regimen_por_guias
from backend.ml.model_loader import cargar_modelo, modelo_disponible
from backend.ml.regimenes import alternativas_equivalentes, ciclos_estandar, nombre_regimen
from backend.ml.reglas import aplicar_reglas
from backend.models.prescription import (
    AlternativaEconomica,
    FeatureAporte,
    PrescriptionBase,
    ValidationResult,
)

logger = logging.getLogger(__name__)

ESTADO_APROBADO = "APROBADO"
ESTADO_RECHAZADO = "RECHAZADO"
ESTADO_REVISION = "REVISION"


class ValidationService:
    """Motor hibrido reglas + ML con doble umbral y contraste vs guias."""

    ESTADIOS_LOCALIZADOS = frozenset({"I", "II", "III"})

    def __init__(self, dosis_service=None) -> None:
        """Inicializa el servicio con el calculador de dosis opcional."""
        try:
            self._dosis_service = dosis_service
        except Exception as exc:
            logger.error("Error al inicializar ValidationService: %s", exc, exc_info=True)
            raise

    def _superficie(self, peso_kg, talla_cm):
        """Calcula superficie corporal Mosteller."""
        try:
            return round(math.sqrt((talla_cm * peso_kg) / 3600.0), 4)
        except Exception as exc:
            logger.error("Error al calcular superficie: %s", exc, exc_info=True)
            raise

    def _chequeos_completitud(self, data: PrescriptionBase):
        """Chequeos preliminares de completitud y coherencia TNM/estadio."""
        try:
            motivos = []
            if not data.diagnostico_cie10 or str(data.diagnostico_cie10).strip() == "":
                motivos.append("Falta el campo obligatorio: diagnóstico (CIE-10).")
            if not data.id_regimen or str(data.id_regimen).strip() == "":
                motivos.append("Falta el campo obligatorio: régimen prescrito.")
            if not data.linea_tratamiento or str(data.linea_tratamiento).strip() == "":
                motivos.append("Falta el campo obligatorio: línea de tratamiento.")

            estadio = (data.estadio or "").strip().upper()
            m = (data.m or "").strip().upper()
            if estadio == "IV" and m != "M1":
                motivos.append("Inconsistencia: estadio IV requiere metástasis M1.")
            if estadio in self.ESTADIOS_LOCALIZADOS and m == "M1":
                motivos.append("Inconsistencia: estadio localizado no puede presentar metástasis M1.")
            return motivos
        except Exception as exc:
            logger.error("Error en chequeos de completitud: %s", exc, exc_info=True)
            raise

    def _contraste_guias(self, datos_modelo, id_regimen_prescrito):
        """Contrasta el regimen prescrito contra regimen_por_guias."""
        try:
            id_sugerido, _base, reglas = regimen_por_guias(datos_modelo)
            motivo = None
            if id_sugerido != id_regimen_prescrito:
                regla = reglas[0] if reglas else "guia_clinica"
                motivo = "Las guías indican %s (%s) por %s; se prescribió %s (%s)." % (
                    id_sugerido,
                    nombre_regimen(id_sugerido),
                    regla,
                    id_regimen_prescrito,
                    nombre_regimen(id_regimen_prescrito),
                )
            return id_sugerido, reglas, motivo
        except Exception as exc:
            logger.error("Error en contraste de guias: %s", exc, exc_info=True)
            raise

    def _alternativa_economica(self, id_regimen, bsa, peso_kg):
        """Compara el costo del tratamiento completo contra los equivalentes.

        Devuelve (costo_tratamiento, alternativas, ahorro, motivo). La regla es
        ASESORA: nunca rechaza. La eleccion entre esquemas terapeuticamente
        equivalentes es una decision clinica, de modo que el sistema se limita a
        exponer la diferencia de costo y a exigir que el prescriptor la
        fundamente.

        El costo se expresa sobre el tratamiento completo ---costo por ciclo por
        la cantidad de ciclos del esquema estandar--- y no sobre el ciclo
        aislado, porque dos esquemas de igual costo unitario pueden tener
        impacto presupuestario muy distinto si difieren en frecuencia o
        duracion.
        """
        try:
            if self._dosis_service is None:
                return None, [], None, None

            equivalentes = alternativas_equivalentes(id_regimen)
            if not equivalentes:
                return None, [], None, None

            _costos, costo_ciclo = self._dosis_service.costear_regimen(id_regimen, bsa, peso_kg)
            if costo_ciclo is None or costo_ciclo <= 0:
                return None, [], None, None
            costo_prescrito = costo_ciclo * ciclos_estandar(id_regimen)

            alternativas = []
            for rid in equivalentes:
                _c, costo_alt_ciclo = self._dosis_service.costear_regimen(rid, bsa, peso_kg)
                if costo_alt_ciclo is None or costo_alt_ciclo <= 0:
                    continue
                costo_alt = costo_alt_ciclo * ciclos_estandar(rid)
                if costo_alt >= costo_prescrito:
                    continue
                ahorro = costo_prescrito - costo_alt
                alternativas.append(
                    AlternativaEconomica(
                        id_regimen=rid,
                        nombre=nombre_regimen(rid),
                        costo_tratamiento=round(costo_alt, 2),
                        ahorro=round(ahorro, 2),
                        pct_ahorro=round(100.0 * ahorro / costo_prescrito, 2),
                        ciclos=ciclos_estandar(rid),
                    )
                )

            if not alternativas:
                return round(costo_prescrito, 2), [], None, None

            alternativas.sort(key=lambda a: a.ahorro, reverse=True)
            mejor = alternativas[0]
            motivo = (
                "Existe una alternativa terapéuticamente equivalente de menor costo: %s (%s) "
                "cuesta %.2f por tratamiento completo frente a %.2f del esquema prescrito, "
                "un %.1f%% menos. Se requiere justificación clínica de la elección."
                % (
                    mejor.id_regimen,
                    mejor.nombre,
                    mejor.costo_tratamiento,
                    costo_prescrito,
                    mejor.pct_ahorro,
                )
            )
            return round(costo_prescrito, 2), alternativas, round(mejor.ahorro, 2), motivo
        except Exception as exc:
            logger.error("Error en analisis de alternativa economica: %s", exc, exc_info=True)
            raise

    def _aportes_pred_contrib(self, model, X_row, feature_names):
        """Obtiene aportes tipo SHAP via pred_contrib de LightGBM."""
        try:
            contrib = model.predict([X_row], pred_contrib=True)[0]
            pares = []
            for idx, name in enumerate(feature_names):
                if idx < len(contrib) - 1:
                    pares.append((name, float(contrib[idx])))
            pares.sort(key=lambda item: abs(item[1]), reverse=True)
            aportes = []
            for name, valor in pares[:5]:
                aportes.append(FeatureAporte(feature=name, aporte=round(valor, 4)))
            return aportes
        except Exception as exc:
            logger.warning("No se pudieron calcular aportes pred_contrib: %s", exc)
            return []

    def _nivel_confianza(self, probabilidad, t_bajo, t_alto):
        """Deriva etiqueta de confianza a partir de la probabilidad y umbrales."""
        try:
            if probabilidad is None:
                return "desconocido"
            if probabilidad >= t_alto:
                return "alta"
            if probabilidad <= t_bajo:
                return "baja"
            return "media"
        except Exception as exc:
            logger.error("Error al calcular nivel de confianza: %s", exc, exc_info=True)
            raise

    def validate(self, data: PrescriptionBase) -> ValidationResult:
        """Valida la prescripcion con reglas + modelo y doble umbral."""
        try:
            motivos_base = self._chequeos_completitud(data)
            if motivos_base:
                return ValidationResult(
                    estado=ESTADO_RECHAZADO,
                    motivos=motivos_base,
                    origen="reglas",
                )

            superficie = self._superficie(data.peso_kg, data.talla_cm)
            excedente = 0.0
            if self._dosis_service is not None:
                excedente = self._dosis_service.calcular_excedente(
                    data.id_regimen,
                    data.dosis_por_farmaco,
                    superficie,
                    data.peso_kg,
                )

            costo_por_farmaco = []
            costo_total = None
            if self._dosis_service is not None:
                costo_por_farmaco, costo_total = self._dosis_service.costear_regimen(
                    data.id_regimen,
                    superficie,
                    data.peso_kg,
                )

            costo_tratamiento, alternativas, ahorro, motivo_economico = self._alternativa_economica(
                data.id_regimen,
                superficie,
                data.peso_kg,
            )
            economia = {
                "costo_tratamiento": costo_tratamiento,
                "alternativas_economicas": alternativas,
                "ahorro_potencial": ahorro,
                "requiere_justificacion_costo": bool(alternativas),
            }

            datos_modelo = prescription_a_datos_modelo(data, superficie, excedente)
            motivos_reglas = aplicar_reglas(datos_modelo)
            id_sugerido, reglas_guias, motivo_contraste = self._contraste_guias(
                datos_modelo,
                data.id_regimen,
            )

            if motivos_reglas:
                motivos = list(motivos_reglas)
                if motivo_contraste:
                    motivos.append(motivo_contraste)
                if motivo_economico:
                    motivos.append(motivo_economico)
                return ValidationResult(
                    estado=ESTADO_RECHAZADO,
                    motivos=motivos,
                    origen="reglas",
                    regimen_sugerido=id_sugerido,
                    reglas_guias=reglas_guias,
                    probabilidad_concordante=0.0,
                    nivel_confianza="baja",
                    costo_por_farmaco=costo_por_farmaco,
                    costo_total=costo_total,
                    **economia,
                )

            if not modelo_disponible():
                motivos = ["Motor ML no disponible. Se deriva a revisión humana (modo solo-reglas)."]
                if motivo_contraste:
                    motivos.append(motivo_contraste)
                if motivo_economico:
                    motivos.append(motivo_economico)
                return ValidationResult(
                    estado=ESTADO_REVISION,
                    motivos=motivos,
                    origen="reglas",
                    regimen_sugerido=id_sugerido,
                    reglas_guias=reglas_guias,
                    costo_por_farmaco=costo_por_farmaco,
                    costo_total=costo_total,
                    **economia,
                )

            artefacto = cargar_modelo()
            feature_names = artefacto.get("features", [])
            X_row, _datos = prescription_a_features(
                data,
                superficie,
                excedente,
                orden_features=feature_names,
            )
            model = artefacto["model"]
            proba_raw = float(model.predict([X_row])[0])
            calibrador = artefacto.get("calibrador")
            if calibrador is not None:
                probabilidad = float(calibrador.predict([proba_raw])[0])
            else:
                probabilidad = proba_raw

            umbrales = artefacto.get("umbrales", {})
            t_bajo = float(umbrales.get("t_bajo", 0.45))
            t_alto = float(umbrales.get("t_alto", 0.7679))
            version = artefacto.get("version_modelo")
            aportes = self._aportes_pred_contrib(model, X_row, feature_names)
            nivel = self._nivel_confianza(probabilidad, t_bajo, t_alto)

            if probabilidad >= t_alto:
                estado = ESTADO_APROBADO
                motivos = ["Prescripción concordante según motor híbrido reglas + ML."]
            elif probabilidad <= t_bajo:
                # RNF-15: the model alone cannot reject without an attributable rule;
                # degrade to REVISION so a human auditor makes the final decision.
                estado = ESTADO_REVISION
                motivos = ["Probabilidad de concordancia baja (%.2f). Se deriva a revisión humana." % probabilidad]
            else:
                estado = ESTADO_REVISION
                motivos = ["Probabilidad intermedia (%.2f). Se deriva a revisión humana." % probabilidad]

            if motivo_contraste:
                motivos.append(motivo_contraste)
            if motivo_economico:
                motivos.append(motivo_economico)

            return ValidationResult(
                estado=estado,
                motivos=motivos,
                probabilidad_concordante=round(probabilidad, 4),
                nivel_confianza=nivel,
                umbral_bajo=t_bajo,
                umbral_alto=t_alto,
                origen="modelo",
                version_modelo=version,
                features_relevantes=aportes,
                regimen_sugerido=id_sugerido,
                reglas_guias=reglas_guias,
                costo_por_farmaco=costo_por_farmaco,
                costo_total=costo_total,
                **economia,
            )
        except Exception as exc:
            logger.error("Error en validate: %s", exc, exc_info=True)
            raise
