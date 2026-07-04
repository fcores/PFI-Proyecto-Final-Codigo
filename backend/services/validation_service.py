from backend.models.prescription import PrescriptionBase, ValidationResult

ESTADO_APROBADO = "APROBADO"
ESTADO_RECHAZADO = "RECHAZADO"
ESTADO_REVISION = "REVISION"


class ValidationService:
    """Motor de validación STUB (preliminar).

    Aplica solo chequeos triviales de completitud y linealidad como placeholder.
    El motor híbrido reglas + ML descrito en la tesis queda como trabajo futuro.
    Sigue el criterio recall-first: ante inconsistencia o duda, deriva a REVISION
    en lugar de aprobar automáticamente.
    """

    ESTADIOS_LOCALIZADOS = frozenset({"I", "II", "III"})

    def validate(self, data: PrescriptionBase) -> ValidationResult:
        motivos = []

        campos_obligatorios = {
            "diagnóstico (CIE-10)": data.diagnostico_cie10,
            "esquema prescrito": data.esquema,
            "línea de tratamiento": data.linea_tratamiento,
        }
        for etiqueta, valor in campos_obligatorios.items():
            if valor is None or str(valor).strip() == "":
                motivos.append(f"Falta el campo obligatorio: {etiqueta}.")

        estadio = (data.estadio or "").strip().upper()
        m = (data.m or "").strip().upper()

        if estadio == "IV" and m != "M1":
            motivos.append("Inconsistencia: estadio IV requiere metástasis M1.")

        if estadio in self.ESTADIOS_LOCALIZADOS and m == "M1":
            motivos.append("Inconsistencia: estadio localizado no puede presentar metástasis M1.")

        if data.dosis_mg_m2 <= 0:
            motivos.append("La dosis (mg/m²) debe ser mayor a cero.")

        if motivos:
            return ValidationResult(estado=ESTADO_RECHAZADO, motivos=motivos)

        return ValidationResult(
            estado=ESTADO_REVISION,
            motivos=[
                "Validación preliminar superada. Se deriva a revisión humana "
                "(motor híbrido reglas + ML pendiente de implementación)."
            ],
        )
