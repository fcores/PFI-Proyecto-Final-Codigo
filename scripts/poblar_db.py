"""
Carga los datos maestros de la base PostgreSQL: monodrogas, medicamentos y pacientes.

Monodrogas y medicamentos salen de resources/Medicamentos v1.xlsx reusando el mismo
importador que expone la app por HTTP (MedicationService.bulk_import), que auto-crea
las monodrogas faltantes. Los pacientes son un set fijo definido en este modulo.

Los eventos (prescripciones, casos de auditoria, dictamenes, correcciones y bloques
del ledger) NO se siembran: se generan desde el frontend ejecutando los casos de uso.

Requiere en .env:
    DATABASE_URL=postgresql://usuario:password@host:5432/medchain
    ENCRYPTION_KEY_DEV=<32 bytes en base64>

La clave de cifrado debe ser la misma que use despues el backend, o el PHI sembrado
queda indescifrable. Correr desde la raiz del repo: el .env se resuelve relativo al
directorio actual.

Uso:
    python scripts/poblar_db.py
    python scripts/poblar_db.py --solo pacientes
    python scripts/poblar_db.py --forzar          # recarga maestros aunque ya existan

Codigos de salida: 0 exito, 1 error de configuracion, conexion o cifrado.
"""

import argparse
import sys
from datetime import date
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import get_settings  # noqa: E402
from backend.db import is_db_available  # noqa: E402

EXIT_OK = 0
EXIT_ERROR = 1

RUTA_EXCEL_DEFAULT = Path("resources") / "Medicamentos v1.xlsx"

# 10 de las 1127 filas del xlsx no traen troquel y el importador lo exige.
# Se completan en una copia en memoria para no tocar el archivo original.
COLUMNA_TROQUEL = "Nro Troquel alfabeta"
TROQUEL_PLACEHOLDER = "S/D"

# Set fijo de pacientes: determinista y reproducible entre corridas. Cubre los cuatro
# estadios y las tres lateralidades de cancer colorrectal para poder ejercitar desde
# el frontend los distintos caminos de backend/ml/guias.py. El genero usa los
# literales que mapea backend/ml/codificacion.py (otro valor codifica -1).
PACIENTES = [
    {
        "credential_id": "OS-4412093",
        "provider_id": "PROV-001",
        "provider": "OSDE",
        "first_name": "Ricardo",
        "last_name": "Bianchi",
        "birth_date": date(1955, 3, 14),
        "gender": "Masculino",
        "treatment": "Adenocarcinoma de colon derecho, estadio III, RAS wild type",
        "medications": ["oxaliplatino", "fluorouracilo", "leucovorina"],
    },
    {
        "credential_id": "OS-7781245",
        "provider_id": "PROV-002",
        "provider": "Swiss Medical",
        "first_name": "Marta",
        "last_name": "Gonzalez",
        "birth_date": date(1962, 11, 2),
        "gender": "Femenino",
        "treatment": "Adenocarcinoma mucinoso de colon izquierdo, estadio IV, MSI-H",
        "medications": ["pembrolizumab"],
    },
    {
        "credential_id": "OS-2093471",
        "provider_id": "PROV-003",
        "provider": "PAMI",
        "first_name": "Hector",
        "last_name": "Dominguez",
        "birth_date": date(1948, 6, 25),
        "gender": "Masculino",
        "treatment": "Adenocarcinoma de colon transverso, estadio II, sin factores de riesgo",
        "medications": [],
    },
    {
        "credential_id": "OS-5567802",
        "provider_id": "PROV-001",
        "provider": "OSDE",
        "first_name": "Silvia",
        "last_name": "Peralta",
        "birth_date": date(1970, 1, 19),
        "gender": "Femenino",
        "treatment": "Adenocarcinoma de colon izquierdo, estadio IV, RAS mutado",
        "medications": ["oxaliplatino", "fluorouracilo", "leucovorina", "bevacizumab"],
    },
    {
        "credential_id": "OS-1120558",
        "provider_id": "PROV-004",
        "provider": "Galeno",
        "first_name": "Jorge",
        "last_name": "Almeida",
        "birth_date": date(1958, 9, 8),
        "gender": "Masculino",
        "treatment": "Adenocarcinoma de colon derecho, estadio IV, BRAF V600E presente",
        "medications": ["encorafenib", "cetuximab"],
    },
    {
        "credential_id": "OS-8834190",
        "provider_id": "PROV-002",
        "provider": "Swiss Medical",
        "first_name": "Ana",
        "last_name": "Rossi",
        "birth_date": date(1966, 4, 30),
        "gender": "Femenino",
        "treatment": "Adenocarcinoma de colon izquierdo, estadio III, segunda linea",
        "medications": ["irinotecan", "fluorouracilo", "leucovorina"],
    },
    {
        "credential_id": "OS-3345677",
        "provider_id": "PROV-003",
        "provider": "PAMI",
        "first_name": "Luis",
        "last_name": "Ferreyra",
        "birth_date": date(1944, 12, 11),
        "gender": "Masculino",
        "treatment": "Adenocarcinoma de colon derecho, estadio I, reseccion completa",
        "medications": [],
    },
    {
        "credential_id": "OS-6678123",
        "provider_id": "PROV-005",
        "provider": "Medife",
        "first_name": "Beatriz",
        "last_name": "Sosa",
        "birth_date": date(1973, 7, 6),
        "gender": "Femenino",
        "treatment": "Adenocarcinoma de colon transverso, estadio II con T4",
        "medications": ["capecitabina"],
    },
    {
        "credential_id": "OS-9902334",
        "provider_id": "PROV-004",
        "provider": "Galeno",
        "first_name": "Alberto",
        "last_name": "Quiroga",
        "birth_date": date(1951, 2, 23),
        "gender": "Masculino",
        "treatment": "Adenocarcinoma de colon izquierdo, estadio IV, RAS wild type",
        "medications": ["oxaliplatino", "fluorouracilo", "leucovorina", "cetuximab"],
    },
    {
        "credential_id": "OS-4458901",
        "provider_id": "PROV-005",
        "provider": "Medife",
        "first_name": "Carmen",
        "last_name": "Ibarra",
        "birth_date": date(1979, 10, 17),
        "gender": "Femenino",
        "treatment": "Adenocarcinoma de colon derecho, estadio III, tercera linea",
        "medications": ["trifluridina_tipiracilo"],
    },
]


def validar_entorno():
    """Verifica configuracion, conexion y cifrado. Retorna None si todo esta OK."""
    if not get_settings().database_url:
        return (
            "DATABASE_URL no esta configurada.\n"
            "  Agregala al archivo .env, por ejemplo:\n"
            "    DATABASE_URL=postgresql://usuario:password@host:5432/medchain\n"
            "  Y ejecuta este script desde la raiz del repositorio "
            "(el .env se resuelve relativo al directorio actual)."
        )

    if not is_db_available():
        return (
            "No se pudo conectar a la base de datos.\n"
            "  Revisa DATABASE_URL, la conectividad de red y las credenciales."
        )

    # Sin clave de cifrado, patient_repo se traga el error y siembra el PHI con las
    # columnas *_enc y *_bidx en NULL, sin ningun aviso. Fallamos antes de insertar.
    try:
        from backend.security.key_manager import get_crypto_service

        get_crypto_service()
    except Exception as exc:
        return (
            "El servicio de cifrado no esta disponible: %s\n"
            "  Los datos PHI de los pacientes se cifran con ENCRYPTION_KEY_DEV.\n"
            "  Sin ella los pacientes se insertarian sin cifrar y sin indice ciego.\n"
            "  Genera una clave con:\n"
            '    python -c "import base64, os; '
            'print(base64.b64encode(os.urandom(32)).decode())"\n'
            "  y agregala al .env como ENCRYPTION_KEY_DEV=<clave>.\n"
            "  Tiene que ser la MISMA clave que use despues el backend." % exc
        )

    return None


def construir_servicios():
    """Instancia repos y servicios a mano.

    No se importa backend.dependencies a proposito: ese modulo construye
    LedgerService a nivel de modulo y su constructor escribe el bloque genesis.
    """
    from backend.repositories.medication_repo import MedicationRepository
    from backend.repositories.monodrug_repo import MonodrugRepository
    from backend.repositories.patient_repo import PatientRepository
    from backend.services.excel_import_service import ExcelImportService
    from backend.services.medication_service import MedicationService
    from backend.services.monodrug_service import MonodrugService
    from backend.services.patient_service import PatientService

    excel_importer = ExcelImportService()
    monodrug_repo = MonodrugRepository()
    medication_repo = MedicationRepository()
    patient_repo = PatientRepository()

    monodrug_service = MonodrugService(monodrug_repo, excel_importer)
    medication_service = MedicationService(
        medication_repo,
        monodrug_repo,
        excel_importer,
        monodrug_service=monodrug_service,
    )
    patient_service = PatientService(patient_repo, excel_importer)

    return {
        "monodrug_repo": monodrug_repo,
        "medication_repo": medication_repo,
        "patient_repo": patient_repo,
        "medication_service": medication_service,
        "patient_service": patient_service,
    }


def _fila_vacia(hoja, fila, columna_ignorada):
    """Indica si la fila no tiene ningun dato fuera de la columna indicada."""
    for columna in range(1, hoja.max_column + 1):
        if columna == columna_ignorada:
            continue
        valor = hoja.cell(row=fila, column=columna).value
        if valor is not None and str(valor).strip() != "":
            return False
    return True


def preparar_excel(ruta):
    """Lee el xlsx y completa los troqueles vacios en una copia en memoria.

    Retorna (bytes, cantidad_completada). El archivo original no se modifica.
    """
    from openpyxl import load_workbook

    libro = load_workbook(ruta)
    hoja = libro.active

    columna_troquel = None
    for celda in hoja[1]:
        if celda.value is not None and str(celda.value).strip() == COLUMNA_TROQUEL:
            columna_troquel = celda.column
            break

    completadas = 0
    if columna_troquel is not None:
        for fila in range(2, hoja.max_row + 1):
            # El xlsx trae filas vacias al final; completarlas crearia registros
            # fantasma, porque pandas solo descarta las que estan totalmente vacias.
            if _fila_vacia(hoja, fila, columna_troquel):
                continue
            celda = hoja.cell(row=fila, column=columna_troquel)
            if celda.value is None or str(celda.value).strip() == "":
                celda.value = TROQUEL_PLACEHOLDER
                completadas += 1

    buffer = BytesIO()
    libro.save(buffer)
    return buffer.getvalue(), completadas


def cargar_maestros(servicios, ruta_excel, forzar):
    """Carga monodrogas y medicamentos desde el Excel. Retorna un dict con el resumen."""
    medication_repo = servicios["medication_repo"]
    existentes = medication_repo.count()

    if existentes > 0 and not forzar:
        print(
            "  Omitido: la tabla medications ya tiene %d filas.\n"
            "  Estas tablas no tienen indice unico, asi que recargar duplicaria todo.\n"
            "  Vacia la base con scripts/vaciar_db.py, o usa --forzar para insertar igual."
            % existentes
        )
        return {"omitido": True}

    if not ruta_excel.exists():
        raise FileNotFoundError("No se encontro el archivo Excel: %s" % ruta_excel)

    file_bytes, completadas = preparar_excel(ruta_excel)
    if completadas:
        print(
            "  %d filas sin '%s' completadas con '%s' (el xlsx original no se modifica)."
            % (completadas, COLUMNA_TROQUEL, TROQUEL_PLACEHOLDER)
        )

    print(
        "  Importando... el importador hace ~3 consultas por fila, "
        "asi que contra una base remota puede tardar varios minutos."
    )
    resultado = servicios["medication_service"].bulk_import(file_bytes, ruta_excel.name)

    return {
        "omitido": False,
        "total_rows": resultado.total_rows,
        "imported_count": resultado.imported_count,
        "failed_count": resultado.failed_count,
        "errors": resultado.errors,
    }


def cargar_pacientes(servicios):
    """Da de alta los pacientes fijos. Retorna (creados, duplicados, fallidos)."""
    from backend.error_handlers import ConflictError

    patient_service = servicios["patient_service"]
    creados = []
    duplicados = []
    fallidos = []

    for datos in PACIENTES:
        etiqueta = "%s, %s" % (datos["last_name"], datos["first_name"])
        try:
            paciente = patient_service.create(
                credential_id=datos["credential_id"],
                provider_id=datos["provider_id"],
                provider=datos["provider"],
                first_name=datos["first_name"],
                last_name=datos["last_name"],
                birth_date=datos["birth_date"],
                gender=datos["gender"],
                treatment=datos["treatment"],
                medications=datos["medications"],
                hc_file=None,
                ap_file=None,
                img_file=None,
                lab_file=None,
                receta_file=None,
                otros_file=None,
            )
            creados.append((paciente.id, etiqueta))
        except ConflictError:
            duplicados.append(etiqueta)
        except Exception as exc:
            fallidos.append((etiqueta, str(exc)))

    return creados, duplicados, fallidos


def main():
    parser = argparse.ArgumentParser(
        description="Carga los datos maestros: monodrogas, medicamentos y pacientes."
    )
    parser.add_argument(
        "--excel",
        default=str(RUTA_EXCEL_DEFAULT),
        help="ruta al xlsx de medicamentos (default: %s)" % RUTA_EXCEL_DEFAULT,
    )
    parser.add_argument(
        "--solo",
        choices=("maestros", "pacientes", "todo"),
        default="todo",
        help="que sembrar (default: todo)",
    )
    parser.add_argument(
        "--forzar",
        action="store_true",
        help="carga los maestros aunque la tabla medications ya tenga filas",
    )
    args = parser.parse_args()

    error = validar_entorno()
    if error:
        print("ERROR: %s" % error, file=sys.stderr)
        return EXIT_ERROR

    servicios = construir_servicios()
    resumen_maestros = None
    resultado_pacientes = None

    if args.solo in ("maestros", "todo"):
        print("")
        print("Cargando monodrogas y medicamentos desde el Excel...")
        try:
            resumen_maestros = cargar_maestros(servicios, Path(args.excel), args.forzar)
        except FileNotFoundError as exc:
            print("ERROR: %s" % exc, file=sys.stderr)
            return EXIT_ERROR

        if not resumen_maestros["omitido"]:
            print(
                "  Filas leidas: %d | importadas: %d | fallidas: %d"
                % (
                    resumen_maestros["total_rows"],
                    resumen_maestros["imported_count"],
                    resumen_maestros["failed_count"],
                )
            )
            for error_fila in resumen_maestros["errors"][:10]:
                print("    fila %d: %s" % (error_fila.row_number, error_fila.message))
            if resumen_maestros["failed_count"] > 10:
                print("    ... y %d errores mas" % (resumen_maestros["failed_count"] - 10))

    if args.solo in ("pacientes", "todo"):
        print("")
        print("Dando de alta pacientes...")
        resultado_pacientes = cargar_pacientes(servicios)
        creados, duplicados, fallidos = resultado_pacientes
        for patient_id, etiqueta in creados:
            print("    id %-4s %s" % (patient_id, etiqueta))
        for etiqueta in duplicados:
            print("    ya existia: %s" % etiqueta)
        for etiqueta, mensaje in fallidos:
            print("    ERROR en %s: %s" % (etiqueta, mensaje))

    print("")
    print("Estado final de los maestros:")
    print("    monodrugs    %6d filas" % len(servicios["monodrug_repo"].list_all()))
    print("    medications  %6d filas" % servicios["medication_repo"].count())
    print("    patients     %6d filas" % len(servicios["patient_repo"].list_all()))

    if resultado_pacientes is not None and resultado_pacientes[2]:
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
