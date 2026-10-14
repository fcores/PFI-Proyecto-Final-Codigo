"""Alta de prescripcion: paciente existente y usuario prescriptor on-chain."""

import json

import pytest

from backend.blockchain.fabric_client import FabricUnavailableError
from backend.error_handlers import DomainError
from backend.models.prescription import PrescriptionBase, ValidationResult
from backend.repositories.fabric_prescription_repo import FabricPrescriptionRepository
from backend.security.canonical import build_canonical_payload, verify_chain
from backend.services.audit_service import AuditService
from backend.services.prescription_service import PrescriptionService
from tests.fakes.fake_fabric_gateway import FakeFabricClient


class _ValidacionStub:
    def validate(self, data):
        return ValidationResult(estado="APROBADO", probabilidad_concordante=0.9)


class _PacientesStub:
    def __init__(self, ids):
        self._ids = set(ids)

    def exists(self, patient_id):
        return patient_id in self._ids


def _datos(**overrides):
    base = dict(
        patient_id=1,
        edad=61,
        sexo="Femenino",
        peso_kg=70.5,
        talla_cm=165.0,
        diagnostico_cie10="C18.9",
        localizacion_tumor="Colon derecho",
        tipo_histologico="Adenocarcinoma",
        t="T3",
        n="N1",
        m="M0",
        estadio="III",
        linea_tratamiento="Primera",
        id_regimen="R03",
        dosis_por_farmaco=[{"monodroga": "oxaliplatino", "dosis_mg": 150.0}],
        medico_prescriptor="Dra. Perez",
        matricula="MN 12345",
    )
    base.update(overrides)
    return base


@pytest.fixture()
def fake():
    return FakeFabricClient()


@pytest.fixture()
def svc(fake):
    return PrescriptionService(
        FabricPrescriptionRepository(fake),
        _ValidacionStub(),
        dosis_service=None,
        patient_service=_PacientesStub({1}),
    )


def test_rechaza_paciente_inexistente(svc, fake):
    with pytest.raises(DomainError) as exc_info:
        svc.create(PrescriptionBase(**_datos(patient_id=99)), prescriptor_username="presc")
    assert exc_info.value.status_code == 422
    assert "99" in exc_info.value.detail
    assert fake.state == {}


def test_registra_el_usuario_de_la_sesion(svc):
    creada = svc.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    assert creada.clinical.prescriptor_username == "presc"


def test_el_cliente_no_puede_fijar_el_prescriptor(svc):
    # PrescriptionBase ignora campos extra: el valor del body no llega on-chain.
    data = PrescriptionBase(**_datos(prescriptor_username="otro_medico"))
    creada = svc.create(data, prescriptor_username="presc")
    assert creada.clinical.prescriptor_username == "presc"


def test_la_cadena_sigue_verificando_con_el_campo_nuevo(svc, fake):
    creada = svc.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    asset = json.loads(fake.query("GetPrescription", [creada.prescription_id]))
    assert verify_chain(asset)["valido"]


def test_assets_previos_sin_el_campo_siguen_leyendose(fake):
    clinical = {k: v for k, v in _datos().items()}
    clinical["superficie_corporal_m2"] = 1.79
    canonical = build_canonical_payload(clinical, {"estado": "APROBADO"}, "2026-03-01T00:00:00Z")
    repo = FabricPrescriptionRepository(fake)
    repo.create("01VIEJO", canonical)

    service = PrescriptionService(repo, _ValidacionStub())
    leida = service.get("01VIEJO")
    assert leida.clinical.prescriptor_username is None
    assert service.verify("01VIEJO").valido


def test_rechaza_regimen_desconocido():
    with pytest.raises(ValueError):
        PrescriptionBase(**_datos(id_regimen="R99"))


def test_rechaza_textos_desmedidos():
    with pytest.raises(ValueError):
        PrescriptionBase(**_datos(diagnostico_cie10="C" * 500))


class _FakeCommitIncierto(FakeFabricClient):
    """Commitea la accion pero responde como si el commit hubiera vencido."""

    def invoke(self, function, args, actor):
        result = super().invoke(function, args, actor)
        if function == "AuditPrescription":
            raise FabricUnavailableError("timeout esperando commit", uncertain=True)
        return result


def test_accion_de_auditoria_se_recupera_tras_commit_incierto():
    fake = _FakeCommitIncierto()
    repo = FabricPrescriptionRepository(fake)
    PrescriptionService(repo, _ValidacionStub()).create(PrescriptionBase(**_datos()))
    prescription_id = next(iter(fake.state)).removeprefix("PRESC_")

    aprobada = AuditService(repo).accion(prescription_id, "aprobar", "cumple guias", "aud1")
    assert aprobada.estado == "APROBADA"


def test_commit_incierto_sin_registro_se_informa_como_no_disponible():
    class _FakeFallaSinCommit(FakeFabricClient):
        def invoke(self, function, args, actor):
            if function == "AuditPrescription":
                raise FabricUnavailableError("timeout esperando commit", uncertain=True)
            return super().invoke(function, args, actor)

    fake = _FakeFallaSinCommit()
    repo = FabricPrescriptionRepository(fake)
    PrescriptionService(repo, _ValidacionStub()).create(PrescriptionBase(**_datos()))
    prescription_id = next(iter(fake.state)).removeprefix("PRESC_")

    with pytest.raises(FabricUnavailableError):
        AuditService(repo).accion(prescription_id, "aprobar", "cumple guias", "aud1")
