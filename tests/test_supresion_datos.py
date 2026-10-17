"""Derecho al olvido por anonimizacion fuera de la cadena (RF-37, RF-38, RF-39)."""

from datetime import date, datetime

import pytest

from backend.error_handlers import ConflictError, DomainError, NotFoundError
from backend.models.auth import UserCreateRequest, UserInfo
from backend.models.patient import Patient
from backend.models.prescription import PrescriptionBase, ValidationResult
from backend.repositories.fabric_prescription_repo import FabricPrescriptionRepository
from backend.repositories.patient_repo import PatientRepository
from backend.repositories.suppression_repo import SuppressionRepository
from backend.security.password import verify_password
from backend.services import suppression_service as modulo_supresion
from backend.services.prescription_service import PrescriptionService
from backend.services.suppression_service import SuppressionService, anios_de_retencion, sumar_anios
from backend.services.user_service import UserService
from tests.fakes.fake_fabric_gateway import FakeFabricClient
from tests.test_user_service import FakeUserRepository


class _ValidacionStub:
    """Motor de validacion fijo."""

    def validate(self, data):
        """Devuelve siempre un veredicto aprobado."""
        return ValidationResult(estado="APROBADO", probabilidad_concordante=0.9)


class _UserRepoConBaja(FakeUserRepository):
    """Repo fake con las operaciones de la baja voluntaria."""

    def find_credentials(self, username):
        """Devuelve la cuenta activa con su credencial."""
        for fila in self._rows.values():
            if fila["username"] == username and fila["active"]:
                return dict(fila)
        return None

    def count_active_by_role(self, role):
        """Cuenta cuentas activas con el rol."""
        total = 0
        for fila in self._rows.values():
            if fila["role"] == role and fila["active"]:
                total = total + 1
        return total

    def anonymize(self, user_id, display_name, password_hash, salt):
        """Desactiva y anonimiza la cuenta."""
        fila = self._rows[user_id]
        fila.update(display_name=display_name, active=False, password_hash=password_hash, salt=salt)
        fila["anonymized_at"] = datetime(2026, 10, 17)
        return True


class _FirmasStub:
    """Registra las revocaciones de clave."""

    def __init__(self):
        """Inicializa la lista de revocaciones."""
        self.revocadas = []

    def revocar(self, username):
        """Registra la revocacion."""
        self.revocadas.append(username)


@pytest.fixture()
def usuarios():
    """Servicio de usuarios con baja voluntaria."""
    repo = _UserRepoConBaja()
    revocadas = []
    firmas = _FirmasStub()
    svc = UserService(repo, revoke_sessions=revocadas.append, signing_service=firmas)
    return svc, repo, revocadas, firmas


def test_baja_propia_anonimiza_y_conserva_el_seudonimo(usuarios):
    svc, repo, revocadas, firmas = usuarios
    cuenta = svc.create(
        UserCreateRequest(username="medico1", password="clave-larga-1", display_name="Dra. Perez", role="prescriptor")
    )
    svc.baja_propia(UserInfo(username="medico1", display_name="Dra. Perez", role="prescriptor"), "clave-larga-1")
    fila = repo._rows[cuenta.id]
    assert fila["username"] == "medico1"
    assert fila["display_name"] == "Usuario dado de baja #%d" % cuenta.id
    assert fila["active"] is False
    assert not verify_password("clave-larga-1", fila["password_hash"], fila["salt"])
    assert revocadas == ["medico1"]
    assert firmas.revocadas == ["medico1"]


def test_baja_propia_exige_la_contrasena(usuarios):
    svc, repo, _, _ = usuarios
    svc.create(UserCreateRequest(username="medico1", password="clave-larga-1", display_name="X", role="prescriptor"))
    with pytest.raises(DomainError):
        svc.baja_propia(UserInfo(username="medico1", display_name="X", role="prescriptor"), "otra")
    assert repo._rows[1]["active"] is True


def test_no_se_da_de_baja_el_ultimo_administrador_general(usuarios):
    svc, _, _, _ = usuarios
    svc.create(UserCreateRequest(username="root", password="superclave1", display_name="Root", role="super_admin"))
    with pytest.raises(ConflictError):
        svc.baja_propia(UserInfo(username="root", display_name="Root", role="super_admin"), "superclave1")


def test_un_administrador_general_puede_irse_si_queda_otro(usuarios):
    svc, repo, _, _ = usuarios
    svc.create(UserCreateRequest(username="root", password="superclave1", display_name="Root", role="super_admin"))
    svc.create(UserCreateRequest(username="root2", password="superclave2", display_name="Root 2", role="super_admin"))
    svc.baja_propia(UserInfo(username="root", display_name="Root", role="super_admin"), "superclave1")
    assert repo._rows[1]["active"] is False


def test_baja_de_cuenta_inexistente(usuarios):
    svc, _, _, _ = usuarios
    with pytest.raises(NotFoundError):
        svc.baja_propia(UserInfo(username="nadie", display_name="X", role="auditor"), "x")


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
def retencion(monkeypatch):
    """Periodo de retencion legal configurado en 10 anios."""
    monkeypatch.setenv("RETENCION_RECETAS_ANIOS", "10")


@pytest.fixture()
def entorno(retencion):
    """Pacientes en memoria, red Fabric fake y servicio de supresion."""
    pacientes = PatientRepository()
    pacientes.add(Patient(id=1, first_name="Ana", last_name="Lopez", birth_date=date(1960, 5, 1), gender="F"))
    pacientes.add(Patient(id=2, first_name="Juan", last_name="Diaz", birth_date=date(1955, 2, 3), gender="M"))
    prescripciones = PrescriptionService(FabricPrescriptionRepository(FakeFabricClient()), _ValidacionStub())
    solicitudes = SuppressionRepository()
    servicio = SuppressionService(solicitudes, pacientes, prescripciones)
    return servicio, pacientes, prescripciones, solicitudes


def test_paciente_sin_prescripciones_se_suprime_en_el_acto(entorno):
    servicio, pacientes, _, _ = entorno
    resultado = servicio.solicitar(2, "root", "Solicitud del titular")
    assert resultado.estado == "ejecutada"
    anonimo = pacientes.find_by_id(2)
    assert anonimo.first_name == "***"
    assert anonimo.last_name == "***"
    assert pacientes.search("Diaz") == []


def test_paciente_con_prescripciones_queda_pendiente_por_retencion(entorno):
    servicio, pacientes, prescripciones, _ = entorno
    prescripciones.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    resultado = servicio.solicitar(1, "root")
    assert resultado.estado == "pendiente"
    assert resultado.ejecutable_desde.year >= datetime.now().year + 10
    assert pacientes.find_by_id(1).first_name == "Ana"


def test_la_solicitud_pendiente_no_se_duplica(entorno):
    servicio, _, prescripciones, solicitudes = entorno
    prescripciones.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    primera = servicio.solicitar(1, "root")
    segunda = servicio.solicitar(1, "root")
    assert primera.id == segunda.id
    assert len(solicitudes.list()) == 1


def test_ejecutar_vencidas_anonimiza_al_cumplirse_el_plazo(entorno, monkeypatch):
    servicio, pacientes, prescripciones, _ = entorno
    prescripciones.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    servicio.solicitar(1, "root")
    assert servicio.ejecutar_vencidas("root").solicitudes == []

    def _dentro_de_once_anios():
        """Simula que pasaron once anios."""
        return datetime.now().replace(year=datetime.now().year + 11)

    monkeypatch.setattr(modulo_supresion, "ahora_utc", _dentro_de_once_anios)
    ejecutadas = servicio.ejecutar_vencidas("root").solicitudes
    assert len(ejecutadas) == 1
    assert pacientes.find_by_id(1).first_name == "***"
    assert servicio.listar().solicitudes[0].estado == "ejecutada"


def test_la_cadena_no_se_toca_al_suprimir(entorno, monkeypatch):
    servicio, _, prescripciones, _ = entorno
    creada = prescripciones.create(PrescriptionBase(**_datos()), prescriptor_username="presc")
    servicio.solicitar(1, "root")

    def _dentro_de_once_anios():
        """Simula que pasaron once anios."""
        return datetime.now().replace(year=datetime.now().year + 11)

    monkeypatch.setattr(modulo_supresion, "ahora_utc", _dentro_de_once_anios)
    servicio.ejecutar_vencidas("root")
    assert prescripciones.verify(creada.prescription_id).valido


def test_paciente_inexistente(entorno):
    servicio, _, _, _ = entorno
    with pytest.raises(NotFoundError):
        servicio.solicitar(99, "root")


def test_retencion_obligatoria_y_minima(monkeypatch):
    monkeypatch.delenv("RETENCION_RECETAS_ANIOS", raising=False)
    with pytest.raises(DomainError):
        anios_de_retencion()
    monkeypatch.setenv("RETENCION_RECETAS_ANIOS", "5")
    with pytest.raises(DomainError):
        anios_de_retencion()
    monkeypatch.setenv("RETENCION_RECETAS_ANIOS", "12")
    assert anios_de_retencion() == 12


def test_sumar_anios_contempla_el_29_de_febrero():
    assert sumar_anios(datetime(2024, 2, 29), 10) == datetime(2034, 2, 28)
    assert sumar_anios(datetime(2026, 3, 1), 10) == datetime(2036, 3, 1)
