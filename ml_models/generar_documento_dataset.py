"""Generador del documento Word de diseño de dataset y modelo de ML.

Produce el archivo .docx con las 7 secciones del diseño de datos y modelo
de validación de prescripciones de cáncer de colon.

Uso:
    python ml_models/generar_documento_dataset.py
"""
import logging
import os
from logging.handlers import RotatingFileHandler

from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT


LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "archivos_de_trabajo")
LOG_FILE = os.path.join(LOG_DIR, "generar_documento.log")
OUTPUT_PATH = os.path.join(LOG_DIR, "diseno_dataset_ml_colon.docx")

logger = logging.getLogger("generar_documento")


def configurar_logging():
    """Configura logging con RotatingFileHandler hacia archivo .log."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    except Exception as exc:
        logging.error("Error al configurar logging: %s", exc, exc_info=True)
        raise


def crear_estilos(doc):
    """Aplica configuración base de fuente y márgenes al documento."""
    try:
        style = doc.styles["Normal"]
        font = style.font
        font.name = "Calibri"
        font.size = Pt(11)
        for section in doc.sections:
            section.top_margin = Cm(2.5)
            section.bottom_margin = Cm(2.5)
            section.left_margin = Cm(2.5)
            section.right_margin = Cm(2.5)
    except Exception as exc:
        logger.error("Error al crear estilos: %s", exc, exc_info=True)
        raise


def agregar_portada(doc):
    """Agrega la portada del documento con título y metadata."""
    try:
        for _ in range(4):
            doc.add_paragraph("")
        titulo = doc.add_paragraph()
        titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = titulo.add_run(
            "Diseño del Dataset y Modelo de ML\n"
            "para Validación de Prescripciones\n"
            "de Cáncer de Colon"
        )
        run.bold = True
        run.font.size = Pt(22)
        run.font.color.rgb = RGBColor(0, 51, 102)

        sub = doc.add_paragraph()
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_sub = sub.add_run(
            "Proyecto Final Integrador — UADE\n"
            "Documento preliminar sujeto a validación clínica"
        )
        run_sub.font.size = Pt(12)
        run_sub.font.color.rgb = RGBColor(100, 100, 100)

        doc.add_paragraph("")
        flujo = doc.add_paragraph()
        flujo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_f = flujo.add_run(
            "Flujo central:\n"
            "Datos del paciente + Medicamento recetado\n"
            "→ Motor híbrido (ML + Reglas determinísticas)\n"
            "→ Veredicto: APROBADO / RECHAZADO / REVISIÓN + motivos"
        )
        run_f.italic = True
        run_f.font.size = Pt(11)

        doc.add_page_break()
    except Exception as exc:
        logger.error("Error al agregar portada: %s", exc, exc_info=True)
        raise


def agregar_tabla(doc, encabezados, filas):
    """Agrega una tabla formateada al documento.

    Args:
        doc: instancia de Document.
        encabezados: lista de strings para la fila de encabezado.
        filas: lista de listas de strings para cada fila de datos.
    """
    try:
        table = doc.add_table(rows=1 + len(filas), cols=len(encabezados))
        table.style = "Light Grid Accent 1"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        for i, texto in enumerate(encabezados):
            cell = table.rows[0].cells[i]
            cell.text = texto
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.bold = True
                    run.font.size = Pt(9)

        for row_idx, fila in enumerate(filas):
            for col_idx, texto in enumerate(fila):
                cell = table.rows[row_idx + 1].cells[col_idx]
                cell.text = str(texto)
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(9)

        doc.add_paragraph("")
    except Exception as exc:
        logger.error("Error al agregar tabla: %s", exc, exc_info=True)
        raise


def seccion_1_dataset(doc):
    """Sección 1: Recomendación del dataset con su fuente."""
    try:
        doc.add_heading("1. Recomendación del Dataset", level=1)

        doc.add_heading("1.1. Dataset seleccionado", level=2)
        doc.add_paragraph(
            "Se recomienda utilizar el dataset TCGA COADREAD (The Cancer Genome Atlas — "
            "Colon Adenocarcinoma + Rectum Adenocarcinoma) disponible en Hugging Face a "
            "través del repositorio gabrielaltay/tcga-tabular-open."
        )

        agregar_tabla(doc,
            ["Atributo", "Detalle"],
            [
                ["Nombre", "TCGA Tabular (Open Access) — subsets TCGA_COAD_* + TCGA_READ_*"],
                ["Fuente", "https://huggingface.co/datasets/gabrielaltay/tcga-tabular-open"],
                ["Origen primario", "NCI Genomic Data Commons (GDC), Data Release 45.0 (dic. 2025)"],
                ["Tamaño", "~633 pacientes reales (COAD: 461, READ: 172)"],
                ["Formato", "Parquet (vía Hugging Face datasets)"],
                ["Licencia", "NIH Genomic Data Sharing — open-access, sin restricciones de publicación"],
                ["Cita obligatoria", "TCGA Research Network: https://www.cancer.gov/tcga"],
            ]
        )

        doc.add_heading("1.2. Justificación", level=2)
        doc.add_paragraph(
            "Datos reales de pacientes oncológicos con estadificación AJCC 8.ª edición "
            "(T/N/M + estadio agrupado), biomarcadores moleculares derivables de las "
            "mutaciones somáticas (KRAS/NRAS/BRAF V600E), histología, sitio del tumor "
            "primario y tratamientos farmacológicos administrados. Al basarse en datos "
            "reales del NCI, se resuelve la crítica académica de \"distribuciones "
            "inventadas\" que acompaña a los datasets puramente sintéticos."
        )
        doc.add_paragraph(
            "Dado que los datos son open-access y no contienen información individualmente "
            "identificable, su uso es compatible con las restricciones de la Ley 25.326 "
            "de Protección de Datos Personales de Argentina que impide el acceso a "
            "historias clínicas reales locales."
        )

        doc.add_heading("1.3. Tablas disponibles en el dataset", level=2)
        agregar_tabla(doc,
            ["Subset (HuggingFace config)", "Contenido", "Filas aprox."],
            [
                ["TCGA_COAD_cases / TCGA_READ_cases",
                 "Datos clínicos anidados: demografía, diagnósticos (AJCC T/N/M, estadio, "
                 "sitio, histología), tratamientos, muestras", "461 / 172"],
                ["TCGA_COAD_clinical_supplement_drug / READ",
                 "Fármacos administrados (texto libre por monodroga)", "593 / 231"],
                ["TCGA_COAD_masked_somatic_mutation / READ",
                 "Variantes somáticas enmascaradas (MAF); fuente para derivar KRAS/NRAS/BRAF",
                 "253k / 57.7k"],
                ["TCGA_COAD_survival_derived / READ",
                 "Endpoints de supervivencia (OS, DFS, PFI, DFI)", "458 / 170"],
                ["TCGA_COAD_clinical_supplement_patient / READ",
                 "Datos clínicos BCR originales (campos que GDC armonizado omite)", "459 / 171"],
            ]
        )

        doc.add_heading("1.4. Alternativas evaluadas", level=2)
        agregar_tabla(doc,
            ["Dataset", "Tipo", "Motivo de descarte"],
            [
                ["xpertsystems/hconc004-sample (HF)",
                 "Sintético (500 pac.)",
                 "Muy cercano en features pero es sintético (no resuelve la crítica); "
                 "bugs documentados en supervivencia; licencia CC-BY-NC-4.0 (no comercial). "
                 "Útil como referencia de coherencia de gating NCCN."],
                ["electricsheepafrica/colorectal-cancer-ssa (HF)",
                 "Sintético (2800-4200)",
                 "Contexto subsahariano (recursos limitados), no alineado con guías NCCN/ESMO/AAOC."],
                ["LH2-data-labs/multimodal-oncology-atlas (HF)",
                 "Real, multimodal",
                 "Muestra muy chica (20 pac. en sample); foco genómico/imagen."],
                ["AACR Project GENIE BPC CRC v2.0",
                 "Real (1485 pac.)",
                 "Acceso restringido vía Synapse; sin información de dosis; "
                 "fármacos investigacionales enmascarados. Complemento posible."],
            ]
        )
        doc.add_page_break()
        logger.info("Sección 1 generada")
    except Exception as exc:
        logger.error("Error en sección 1: %s", exc, exc_info=True)
        raise


def seccion_2_features(doc):
    """Sección 2: Features documentadas en la tesis vs. recomendadas por guías."""
    try:
        doc.add_heading("2. Features: Tesis vs. Guías Clínicas vs. Dataset", level=1)

        doc.add_paragraph(
            "La siguiente sección contrasta las features documentadas en la tesis "
            "(capítulo Conjunto de Datos) contra las variables que las guías clínicas "
            "(NCCN Colon 2026, ESMO localizado/metastásico, AAOC Tracto Digestivo "
            "Inferior 2025) identifican como determinantes para la selección del "
            "régimen terapéutico, y su disponibilidad en TCGA COADREAD."
        )

        doc.add_heading("2.1. Features documentadas en la tesis Y presentes en el dataset", level=2)
        agregar_tabla(doc,
            ["Feature", "Tipo", "Rol clínico (guía)", "Campo TCGA"],
            [
                ["Edad", "Numérico", "Tolerancia a tripletes; incidencia por franja etaria [AAOC p3]",
                 "demographic.age_at_index"],
                ["Sexo", "Dicotómico", "Asociación con lateralidad del primario [AAOC p3]",
                 "demographic.gender"],
                ["T (tumor primario)", "Ordinal", "Profundidad de invasión; define estadio con N/M [AAOC p4]",
                 "diagnoses[].ajcc_pathologic_t"],
                ["N (ganglios)", "Ordinal", "N+ con M0 define estadio III [AAOC p5]",
                 "diagnoses[].ajcc_pathologic_n"],
                ["M (metástasis)", "Dicotómico", "M1 equivale a estadio IV [AAOC p5]",
                 "diagnoses[].ajcc_pathologic_m"],
                ["Estadio (I-IV)", "Ordinal", "Gobierna si hay tratamiento sistémico [NCCN, AAOC p8-13]",
                 "diagnoses[].ajcc_pathologic_stage"],
                ["Localización/lateralidad", "Dicotómico", "Preferencia anti-EGFR (izq.) vs. bevacizumab (der.) "
                 "[NCCN p51(f), AAOC p25]",
                 "diagnoses[].tissue_or_organ_of_origin → mapear a CIE-10 C18.x"],
                ["Tipo histológico", "Categórico", "Confirma adenocarcinoma; aplicabilidad del esquema "
                 "[AAOC p2, ESMO-M p1]",
                 "diagnoses[].primary_diagnosis"],
                ["RAS (KRAS/NRAS)", "Dicotómico", "Mutado contraindica anti-EGFR [NCCN p52, AAOC p25]",
                 "Derivar de masked_somatic_mutation (Hugo_Symbol KRAS/NRAS)"],
                ["BRAF V600E", "Dicotómico", "Habilita encorafenib + anti-EGFR (BEACON) [NCCN p56, AAOC p25]",
                 "Derivar de masked_somatic_mutation (Hugo_Symbol BRAF, HGVSp V600E)"],
                ["Línea de tratamiento", "Ordinal", "Acota esquemas válidos [NCCN p51, AAOC p25/p30]",
                 "Inferir de clinical_supplement_drug (fechas de inicio)"],
                ["Diagnóstico CIE-10", "Categórico", "Estándar de interoperabilidad [RF-12]",
                 "Derivar de tissue_or_organ_of_origin → C18.x"],
            ]
        )

        doc.add_heading(
            "2.2. Features NO documentadas en la tesis pero recomendadas por guías "
            "Y presentes/derivables en el dataset", level=2
        )
        doc.add_paragraph(
            "Las siguientes variables influyen directamente en la selección del "
            "régimen según las guías clínicas citadas, pero no forman parte del "
            "esquema preliminar de la tesis. Su incorporación fortalecería la "
            "capacidad predictiva del motor de validación."
        )
        agregar_tabla(doc,
            ["Feature", "Tipo", "Por qué la guía la necesita", "Disponibilidad en TCGA"],
            [
                ["ECOG / Performance Status", "Ordinal (0-4)",
                 "Decide triplete (FOLFOXIRI, buen estado general) vs. doblete vs. "
                 "monoterapia. Sin este dato, no se puede validar la indicación de un "
                 "FOLFIRINOX. [NCCN p51, ESMO-M p4]",
                 "Parcial: presente en algunos registros de follow_up"],
                ["Factores de riesgo estadio II\n(T4, <12 ganglios, LVI, PNI, "
                 "pobremente diferenciado, obstrucción, perforación)", "Mixto",
                 "Determinan si un estadio II recibe adyuvancia (fluoropirimidinas ± "
                 "oxaliplatino). Sin ellos, todo estadio II queda ambiguo. "
                 "[AAOC p8, NCCN]",
                 "Parcial: T4 derivable de ajcc_pathologic_t; ganglios cosechados "
                 "y positivos en BCR clinical supplement"],
                ["KRAS G12C específico", "Dicotómico",
                 "Habilita combos dirigidos (sotorasib/adagrasib) en líneas avanzadas. "
                 "Subgrupo ~4% de metastásicos. [AAOC p27]",
                 "Sí: variante puntual identificable en masked_somatic_mutation (HGVSp)"],
            ]
        )

        doc.add_heading(
            "2.3. Features relevantes por guías que NO están en el dataset "
            "(requieren otra fuente o trabajo futuro)", level=2
        )
        agregar_tabla(doc,
            ["Feature", "Rol clínico", "Fuente alternativa"],
            [
                ["MSI / MMR", "Habilita inmunoterapia de 1.ª línea (pembrolizumab); "
                 "discrimina dMMR/MSI-H vs. pMMR/MSS [NCCN p55, AAOC p24-26]",
                 "GDC MSI biotab, cBioPortal COADREAD, o estimación por lateralidad+BRAF+edad"],
                ["HER2 amplificado (DESCARTADO)", "Habilita anti-HER2 "
                 "(trastuzumab+tucatinib) en RAS WT HER2+ [NCCN]",
                 "Requiere IHC/FISH; no disponible en TCGA. Se descarta del alcance: "
                 "sintetizarlo por prevalencia poblacional (~3-5%) sería ruido "
                 "aleatorio sin correlación con el paciente individual. Queda como "
                 "trabajo futuro hasta contar con datos reales."],
                ["Déficit de DPD (DPYD)", "Contraindica/reduce fluoropirimidinas (safety dura) [NCCN]",
                 "Farmacogenómica; fuera del alcance del prototipo"],
                ["UGT1A1", "Modula dosis de irinotecán [NCCN]",
                 "Farmacogenómica; fuera del alcance del prototipo"],
                ["NTRK/RET fusión", "Habilita larotrectinib/entrectinib (raro, <1%) [NCCN]",
                 "Datos de fusiones no en TCGA tabular open"],
            ]
        )
        doc.add_page_break()
        logger.info("Sección 2 generada")
    except Exception as exc:
        logger.error("Error en sección 2: %s", exc, exc_info=True)
        raise


def seccion_3_sintetizar(doc):
    """Sección 3: Datos ausentes que hay que sintetizar/estimar."""
    try:
        doc.add_heading(
            "3. Datos Ausentes en el Dataset: Síntesis y Estimación", level=1
        )

        doc.add_paragraph(
            "Los siguientes datos no están presentes en TCGA COADREAD y deben "
            "generarse de forma sintética o estimarse a partir de otras features "
            "disponibles. Para cada uno se indica el método de estimación y las "
            "features base que lo sustentan."
        )

        agregar_tabla(doc,
            ["Dato ausente", "Tipo", "Método de síntesis/estimación", "Features base"],
            [
                ["MSI / MMR", "Dicotómico",
                 "Obtener el estado real medido desde cBioPortal / GDC MSI biotab "
                 "(test de PCR de TCGA) uniendo por case_submitter_id. No es una "
                 "estimación sino un dato real traído de la fuente primaria del GDC; "
                 "por lo tanto, ruido nulo (solo limitado por la cobertura parcial "
                 "de pacientes con resultado MSI reportado). Se descarta explícitamente "
                 "cualquier estimación probabilística por proxy (lateralidad+BRAF+edad), "
                 "porque introduciría un sesgo de confirmación en una feature crítica "
                 "para el gating de inmunoterapia [NCCN p55, AAOC p24-26].",
                 "cBioPortal/GDC MSI biotab (join por case_submitter_id)"],

                ["Peso (kg)", "Numérico",
                 "Generar sintéticamente a partir de distribución fisiológica plausible: "
                 "rango 40-140 kg, media ~75 kg, asociado a sexo y edad.",
                 "sexo, edad (correlación blanda)"],

                ["Talla (cm)", "Numérico",
                 "Generar sintéticamente: rango 140-200 cm, asociado a sexo.",
                 "sexo (correlación blanda)"],

                ["Superficie corporal (BSA, m²)", "Numérico (derivado)",
                 "Calcular con fórmula de Mosteller: BSA = √(talla_cm × peso_kg / 3600). "
                 "Rango esperado ~1.3-2.4 m². Es la base del cálculo de dosis en mg/m² "
                 "para citostáticos clásicos [RF-13].",
                 "peso_kg, talla_cm (generados)"],

                ["Dosis mg/m²", "Numérico (derivado)",
                 "Asignar la dosis de referencia por guía según el régimen: "
                 "oxaliplatino 85 mg/m² (mFOLFOX6), 130 mg/m² (CAPEOX); "
                 "irinotecán 180 mg/m²; etc. La dosis total en mg se obtiene "
                 "multiplicando por BSA. [NCCN pp.52-56, AAOC p28-29]",
                 "id_regimen, superficie_corporal_m2"],

                ["Combinación de presentaciones + costo", "Compuesto (derivado)",
                 "Módulo determinístico que consulta Medicamentos v1.xlsx (Alfabeta): "
                 "dado dosis_mg requeridos → seleccionar combinación de presentaciones "
                 "comerciales reales que minimice excedente → calcular costo en ARS "
                 "[RF-13, RF-14].",
                 "dosis_mg, catálogo Alfabeta"],

                ["es_valido / tipo_error", "Dicotómico / Categórico",
                 "Inyección deliberada de errores según taxonomía cerrada de 6 tipos. "
                 "TCGA contiene prescripciones reales (asumidas concordantes); se crean "
                 "copias alteradas que violan reglas de coherencia.",
                 "Todas las features clínicas + régimen"],

                ["Línea de tratamiento (explícita)", "Ordinal",
                 "Inferir de clinical_supplement_drug: ordenar fármacos por fecha de "
                 "inicio (days_of_drug_therapy_start); la primera terapia sistémica "
                 "= 1.ª línea, la segunda = 2.ª línea.",
                 "clinical_supplement_drug.days_of_drug_therapy_start"],
            ]
        )

        doc.add_heading(
            "3.1. Por qué la síntesis de peso y talla no genera ruido relevante",
            level=2
        )
        doc.add_paragraph(
            "Las variables peso, talla y BSA no están disponibles en TCGA ni en la "
            "mayoría de datasets públicos oncológicos, por lo que su síntesis es "
            "inevitable para poder calcular dosis. A nivel individual, el peso y la "
            "talla generados no guardan ninguna relación con el paciente real de TCGA: "
            "se muestrean de distribuciones fisiológicas poblacionales. En apariencia "
            "esto parecería introducir ruido, pero para el caso de uso específico de "
            "este proyecto el ruido es efectivamente nulo. La justificación es la "
            "siguiente."
        )

        doc.add_paragraph(
            "Peso y talla NO son features del clasificador de concordancia clínica. "
            "La decisión de qué régimen corresponde a un paciente depende del estadio, "
            "los biomarcadores (MSI, RAS, BRAF), la lateralidad y la línea de "
            "tratamiento, no de la antropometría. Por lo tanto, un peso o talla "
            "incorrectos no alteran la predicción de régimen del modelo de ML.",
            style="List Bullet"
        )
        doc.add_paragraph(
            "Peso y talla solo alimentan la cadena determinística de dosificación: "
            "peso/talla → BSA (Mosteller) → dosis total en mg → combinación de "
            "presentaciones → costo. Esta cadena es un cálculo exacto, no una "
            "estimación estadística.",
            style="List Bullet"
        )
        doc.add_paragraph(
            "El circuito de validación es internamente consistente (self-consistent): "
            "tanto la dosis esperada como la dosis recetada que se comparan se calculan "
            "usando la MISMA BSA sintética. Si a un paciente se le genera BSA = 1.93 m² "
            "cuando en la realidad tenía 1.75 m², la dosis de referencia esperada y la "
            "dosis prescrita se evalúan ambas con BSA = 1.93 m². El error absoluto en "
            "mg respecto del paciente real es irrelevante, porque el motor no valida "
            "\"la dosis correcta en términos absolutos del paciente real de TCGA\", "
            "sino \"la coherencia entre la dosis prescrita y la esperada para la "
            "antropometría registrada\". El ruido se cancela dentro del propio circuito.",
            style="List Bullet"
        )

        doc.add_paragraph(
            "En consecuencia, aunque el ruido individual de peso/talla es alto en "
            "sentido estadístico, su impacto efectivo sobre las dos tareas del motor "
            "(clasificación de régimen y validación de dosis/presentaciones) es nulo. "
            "Esto contrasta con variables como MSI o HER2, cuyo valor sí determina "
            "directamente la elección del régimen: en esos casos un valor incorrecto "
            "SÍ enseñaría al modelo una asociación falsa, razón por la cual MSI se "
            "obtiene de la fuente real (no se estima) y HER2 se descarta del alcance."
        )
        doc.add_paragraph(
            "Único cuidado a mantener: las distribuciones sintéticas de peso y talla "
            "deben producir un rango de BSA fisiológicamente plausible (~1.3-2.4 m²) "
            "para que la combinación de presentaciones ejercite escenarios realistas "
            "(por ejemplo, dosis que requieran combinar varias potencias del catálogo). "
            "No se requiere realismo a nivel de paciente individual, solo a nivel de "
            "distribución agregada."
        )
        doc.add_page_break()
        logger.info("Sección 3 generada")
    except Exception as exc:
        logger.error("Error en sección 3: %s", exc, exc_info=True)
        raise


def seccion_4_modelo(doc):
    """Sección 4: Modelo de ML recomendado."""
    try:
        doc.add_heading("4. Modelo de Machine Learning Recomendado", level=1)

        doc.add_heading("4.1. Arquitectura: motor híbrido reglas + ML", level=2)
        doc.add_paragraph(
            "El motor de validación combina dos capas complementarias:"
        )
        doc.add_paragraph(
            "Capa 1 — Reglas determinísticas: validan restricciones duras que no "
            "admiten ambigüedad (dosis incorrecta, medicamento faltante en catálogo, "
            "combinaciones clínicamente imposibles como M1 + estadio I, o anti-EGFR "
            "con RAS mutado). Estas reglas se codifican explícitamente sin ML.",
            style="List Bullet"
        )
        doc.add_paragraph(
            "Capa 2 — Clasificador ML: evalúa la concordancia clínica global entre "
            "los atributos del paciente y el régimen prescrito, capturando patrones "
            "complejos que las reglas individuales no cubren (por ejemplo, la "
            "combinación de estadio + biomarcadores + lateralidad + línea que "
            "determina si un régimen específico es el indicado).",
            style="List Bullet"
        )
        doc.add_paragraph(
            "La decisión final integra ambas capas: si las reglas detectan una "
            "violación dura, el veredicto es RECHAZADO independientemente del ML. "
            "Si las reglas pasan pero el ML detecta baja concordancia, el veredicto "
            "es REVISIÓN (derivación al auditor humano). Solo si ambas capas son "
            "positivas se emite APROBADO."
        )

        doc.add_heading("4.2. Algoritmo recomendado", level=2)
        agregar_tabla(doc,
            ["Aspecto", "Recomendación", "Justificación"],
            [
                ["Algoritmo principal", "Gradient Boosting (XGBoost o LightGBM)",
                 "Estado del arte para datos tabulares mixtos (ordinales, dicotómicos, "
                 "categóricos). Superior a redes neuronales con n < 10,000."],
                ["Alternativa", "Random Forest",
                 "Más simple de implementar; buen baseline. Menor riesgo de "
                 "sobreajuste con n pequeño."],
                ["Tipo de tarea", "Clasificación multiclase (régimen) + binaria "
                 "(concordante/no concordante)",
                 "Tarea A: predecir el régimen esperado. Tarea B: detectar "
                 "discordancia."],
                ["Métricas principales", "Recall (sensibilidad) como métrica primaria; "
                 "F1 y AUC-ROC como secundarias",
                 "El motor prioriza recall-first: es preferible derivar un caso "
                 "dudoso a revisión humana que dejar pasar un error [RF-20, RNF-14]."],
                ["Interpretabilidad", "SHAP (SHapley Additive exPlanations)",
                 "Permite explicar al auditor por qué se rechazó/derivó una "
                 "prescripción, identificando qué features contribuyeron al "
                 "veredicto."],
                ["Validación", "Stratified K-Fold (k=5) con balanceo SMOTE/class_weight",
                 "Preserva la distribución de clases en cada fold; compensa el "
                 "desbalance natural (mayoría de prescripciones son concordantes)."],
                ["Umbral de decisión", "Ajustable para maximizar recall al nivel "
                 "deseado (ej. recall ≥ 0.95)",
                 "Se baja el umbral de clasificación para que el modelo sea más "
                 "sensible a errores, aceptando más falsos positivos (derivaciones "
                 "a revisión) a cambio de menos falsos negativos."],
            ]
        )

        doc.add_heading("4.3. Features de entrada al modelo", level=2)
        doc.add_paragraph(
            "El modelo recibe como entrada el vector de features clínicas del "
            "paciente (edad, sexo, T, N, M, estadio, lateralidad, histología, "
            "MSI, RAS, BRAF, ECOG, línea) codificadas según el diccionario del "
            "dataset (ordinales como enteros, dicotómicas como 0/1, categóricas "
            "como one-hot). Adicionalmente recibe el régimen prescrito por el "
            "médico como feature de entrada. El modelo evalúa si esa combinación "
            "(paciente + régimen prescrito) es concordante con las guías clínicas."
        )
        doc.add_page_break()
        logger.info("Sección 4 generada")
    except Exception as exc:
        logger.error("Error en sección 4: %s", exc, exc_info=True)
        raise


def seccion_5_salida(doc):
    """Sección 5: Qué entrega el modelo como resultado."""
    try:
        doc.add_heading("5. Resultado del Modelo", level=1)

        doc.add_heading("5.1. Flujo de entrada y salida", level=2)
        doc.add_paragraph(
            "El sistema recibe dos inputs: (a) los datos clínicos del paciente "
            "(estadificación, biomarcadores, antropometría) y (b) el medicamento/"
            "esquema recetado por el médico prescriptor. A partir de estos, el "
            "motor híbrido produce un veredicto estructurado."
        )

        doc.add_heading("5.2. Estructura del veredicto", level=2)
        agregar_tabla(doc,
            ["Campo de salida", "Tipo", "Descripción"],
            [
                ["veredicto", "Categórico (3 valores)",
                 "APROBADO: la prescripción es concordante con las guías. "
                 "RECHAZADO: se detectó una violación clara (regla dura o alta "
                 "confianza ML). REVISIÓN: caso derivado al auditor humano para "
                 "evaluación (baja confianza o patrón inusual)."],
                ["score_concordancia", "Numérico [0, 1]",
                 "Probabilidad estimada por el ML de que la prescripción sea "
                 "concordante. Permite al auditor calibrar la urgencia de su "
                 "revisión."],
                ["tipo_error", "Categórico (taxonomía cerrada)",
                 "Si el veredicto es RECHAZADO o REVISIÓN, indica el tipo de error "
                 "detectado: sin_error (0), dosis_incorrecta (1), "
                 "discordancia_diagnostico_tratamiento (2), "
                 "esquema_no_concordante_con_estadificacion (3), "
                 "documentacion_incompleta (4), combinacion_clinicamente_imposible (5), "
                 "medicamento_faltante (6)."],
                ["motivos", "Lista de strings",
                 "Explicación legible de por qué se rechazó o derivó la prescripción. "
                 "Ej: «RAS mutado: el régimen incluye cetuximab (anti-EGFR), "
                 "contraindicado con mutación RAS [NCCN p52]». Generados a partir de "
                 "las reglas determinísticas y/o SHAP del ML."],
                ["features_relevantes", "Lista de (feature, contribución)",
                 "Top-N features que más contribuyeron al veredicto (derivadas de "
                 "SHAP), para explicabilidad ante el auditor."],
            ]
        )

        doc.add_heading("5.3. Criterio recall-first", level=2)
        doc.add_paragraph(
            "El sistema prioriza la sensibilidad (recall) sobre la especificidad: "
            "ante la duda, el veredicto es REVISIÓN en lugar de APROBADO. Esto "
            "implica que puede haber falsos positivos (prescripciones correctas "
            "derivadas a revisión), pero se minimiza el riesgo de falsos negativos "
            "(prescripciones erróneas que pasan sin detección). Este criterio "
            "responde al requerimiento funcional RF-20 y al requerimiento no "
            "funcional RNF-14 del análisis funcional."
        )

        doc.add_heading("5.4. Integración con el flujo de auditoría", level=2)
        doc.add_paragraph(
            "El veredicto alimenta directamente la cola de auditoría del sistema: "
            "las prescripciones con veredicto REVISIÓN o RECHAZADO generan un caso "
            "de auditoría que el auditor humano puede revisar, emitir un dictamen "
            "y, si corresponde, solicitar correcciones al prescriptor. El resultado "
            "del dictamen (aprobado/rechazado/corregido) se registra en el ledger "
            "(blockchain) para trazabilidad."
        )
        doc.add_page_break()
        logger.info("Sección 5 generada")
    except Exception as exc:
        logger.error("Error en sección 5: %s", exc, exc_info=True)
        raise


def seccion_6_etl(doc):
    """Sección 6: Acciones de ETL necesarias sobre el dataset."""
    try:
        doc.add_heading("6. Acciones de ETL sobre el Dataset", level=1)

        doc.add_heading("6.1. Extract (Extracción)", level=2)
        agregar_tabla(doc,
            ["Paso", "Acción", "Herramienta"],
            [
                ["E1", "Descargar los subsets TCGA_COAD_cases y TCGA_READ_cases desde "
                 "Hugging Face", "datasets.load_dataset(\"gabrielaltay/tcga-tabular-open\", "
                 "\"TCGA_COAD_cases\")"],
                ["E2", "Descargar clinical_supplement_drug (COAD + READ)", "Idem, config "
                 "\"TCGA_COAD_clinical_supplement_drug\""],
                ["E3", "Descargar masked_somatic_mutation (COAD + READ)", "Idem, config "
                 "\"TCGA_COAD_masked_somatic_mutation\""],
                ["E4", "Descargar survival_derived (COAD + READ)", "Idem, config "
                 "\"TCGA_COAD_survival_derived\""],
                ["E5", "Obtener estado MSI de cBioPortal/GDC MSI biotab", "API cBioPortal "
                 "o descarga directa del GDC"],
                ["E6", "Concatenar COAD + READ en un único DataFrame por tabla", "pandas.concat()"],
            ]
        )

        doc.add_heading("6.2. Transform (Transformación)", level=2)
        agregar_tabla(doc,
            ["Paso", "Acción", "Detalle"],
            [
                ["T1", "Aplanar JSON anidado de cases",
                 "Extraer demographic.age_at_index → edad, demographic.gender → sexo, "
                 "diagnoses[0].ajcc_pathologic_t/n/m → T/N/M, "
                 "diagnoses[0].ajcc_pathologic_stage → estadio, "
                 "diagnoses[0].tissue_or_organ_of_origin → sitio, "
                 "diagnoses[0].primary_diagnosis → histología"],
                ["T2", "Mapear sitio a lateralidad + CIE-10",
                 "Crear diccionario: Cecum/Ascending → Derecho (C18.0/C18.2), "
                 "Sigmoid/Descending → Izquierdo (C18.7/C18.6), etc. Transverso → "
                 "Indeterminado [NCCN p51(f)]. Rectum → excluir o marcar"],
                ["T3", "Derivar KRAS/NRAS/BRAF de masked_somatic_mutation",
                 "Filtrar Hugo_Symbol ∈ {KRAS, NRAS, BRAF}. Para cada paciente: si "
                 "existe variante patogénica en KRAS/NRAS → ras=Mutado; si BRAF con "
                 "HGVSp contiene V600E → braf=Presente. Verificar exclusividad mutua "
                 "RAS/BRAF."],
                ["T4", "Normalizar fármacos (texto libre → régimen R00-R13)",
                 "Construir diccionario de normalización: \"Fluorouracil\"/\"5-FU\" → "
                 "fluorouracilo, \"Oxaliplatin\" → oxaliplatino, etc. Agrupar monodrogas "
                 "concurrentes por paciente/fechas → identificar régimen: "
                 "oxaliplatino+fluorouracilo+leucovorina = mFOLFOX6 (R01); "
                 "oxaliplatino+capecitabina = CAPEOX (R02); etc."],
                ["T5", "Inferir línea de tratamiento",
                 "Ordenar fármacos por days_of_drug_therapy_start. Primera terapia "
                 "sistémica = línea 1; si hay cambio de régimen posterior = línea 2."],
                ["T6", "Sintetizar peso/talla → BSA → dosis",
                 "Generar peso y talla con distribuciones fisiológicas. Calcular BSA "
                 "(Mosteller). Asignar dosis de referencia por régimen (mg/m²). "
                 "Calcular dosis total en mg = dosis_mg_m2 × BSA."],
                ["T7", "Mapear a presentaciones Alfabeta y calcular costo",
                 "Módulo determinístico: para cada monodroga → buscar presentaciones "
                 "en Medicamentos v1.xlsx → combinación de mínimo excedente → costo."],
                ["T8", "Codificar features según diccionario",
                 "Dicotómicas → 0/1, ordinales → enteros preservando orden, "
                 "categóricas → one-hot, numéricos → valor directo con normalización "
                 "opcional"],
                ["T9", "Inyectar errores (clase negativa)",
                 "Crear copias alteradas de registros concordantes aplicando cada tipo "
                 "de error de la taxonomía (dosis_incorrecta, discordancia_dx_tto, etc.). "
                 "Proporción tentativa: ~60% concordantes / ~40% con error."],
                ["T10", "Excluir variables de outcome (anti target leakage)",
                 "NO incluir como features: OS, DFS, PFS, toxicidades, RECIST, CEA. "
                 "Estas son consecuencias del tratamiento, no determinantes de la "
                 "prescripción; incluirlas generaría fuga de información."],
            ]
        )

        doc.add_heading("6.3. Load (Carga)", level=2)
        agregar_tabla(doc,
            ["Paso", "Acción", "Formato"],
            [
                ["L1", "Exportar dataset curado para entrenamiento",
                 "Parquet o CSV (una fila por caso, todas las features codificadas + "
                 "es_valido + tipo_error + id_regimen)"],
                ["L2", "Exportar diccionario de codificación",
                 "JSON con mapeos legible ↔ codificado para cada feature"],
                ["L3", "Documentar linaje de datos (data lineage)",
                 "Registro de cada transformación aplicada con versión del dataset "
                 "TCGA y fecha de generación"],
            ]
        )
        doc.add_page_break()
        logger.info("Sección 6 generada")
    except Exception as exc:
        logger.error("Error en sección 6: %s", exc, exc_info=True)
        raise


def seccion_7_medicamentos(doc):
    """Sección 7: Cómo se resuelve la parte de los medicamentos."""
    try:
        doc.add_heading("7. Resolución de la Validación de Medicamentos", level=1)

        doc.add_heading("7.1. Contexto del problema", level=2)
        doc.add_paragraph(
            "El sistema recibe del médico prescriptor: (a) los datos clínicos del "
            "paciente y (b) el medicamento/esquema que prescribe (nombre del régimen, "
            "fármacos específicos, dosis y presentaciones). El motor debe validar si "
            "esa prescripción es correcta desde dos ángulos:"
        )
        doc.add_paragraph(
            "Concordancia clínica (ML): ¿el régimen prescrito es el indicado para "
            "este paciente según su estadio, biomarcadores y línea de tratamiento?",
            style="List Bullet"
        )
        doc.add_paragraph(
            "Concordancia de dosis/presentaciones (reglas determinísticas): ¿la dosis "
            "prescrita es correcta en mg/m²? ¿Se eligieron las presentaciones "
            "comerciales que minimizan el excedente? ¿El medicamento existe en el "
            "catálogo con la vía correcta?",
            style="List Bullet"
        )

        doc.add_heading("7.2. Flujo de validación de medicamentos", level=2)
        doc.add_paragraph(
            "El flujo opera en 5 pasos secuenciales:"
        )

        doc.add_paragraph(
            "Paso 1 — Normalización: el medicamento recetado por el médico se "
            "normaliza a su monodroga estándar (ej: \"Eloxatin\" → oxaliplatino) y "
            "se mapea al régimen correspondiente (R00-R13) comparando la combinación "
            "de monodrogas con la tabla de regímenes de las guías [NCCN pp.52-56].",
            style="List Number"
        )
        doc.add_paragraph(
            "Paso 2 — Cálculo de dosis esperada: a partir del BSA del paciente "
            "(Mosteller) y la dosis de referencia del régimen en mg/m² (o mg/kg para "
            "bevacizumab/panitumumab, o dosis fija para pembrolizumab/encorafenib), "
            "se calcula la dosis total en mg que el paciente debería recibir.",
            style="List Number"
        )
        doc.add_paragraph(
            "Paso 3 — Combinación de presentaciones: se consulta el catálogo de "
            "Medicamentos v1.xlsx (Alfabeta) filtrando por monodroga y vía "
            "intravenosa (excluyendo presentaciones intraocular para bevacizumab, "
            "y marcando ziv-aflibercept IV como faltante). Se resuelve el problema "
            "de cobertura entera: seleccionar combinación de presentaciones reales "
            "que cubra la dosis requerida minimizando el excedente y, a igualdad, "
            "minimizando el costo [RF-13, RF-14].",
            style="List Number"
        )
        doc.add_paragraph(
            "Paso 4 — Comparación: se compara lo recetado por el médico contra lo "
            "esperado. Si la combinación de presentaciones no minimiza el excedente "
            "(ej: dos ampollas de 500 mg para cubrir 750 mg en lugar de la "
            "combinación exacta), se marca como dosis_incorrecta. Si el régimen "
            "exige un fármaco ausente en el catálogo o no utilizable por su vía, "
            "se marca como medicamento_faltante.",
            style="List Number"
        )
        doc.add_paragraph(
            "Paso 5 — Integración con ML: el veredicto del módulo determinístico "
            "(dosis/presentaciones) se combina con el veredicto del clasificador ML "
            "(concordancia clínica) para producir el veredicto final.",
            style="List Number"
        )

        doc.add_heading("7.3. Catálogo de medicamentos: Alfabeta", level=2)
        doc.add_paragraph(
            "El catálogo comercial se basa en Medicamentos v1.xlsx, la base de datos "
            "de referencia del vademécum farmacéutico argentino (Alfabeta), que "
            "contiene 1.127 presentaciones con las columnas: Tamaño/Dimensión, Código "
            "EAN/UPC, Cadena de frío, Nro Troquel Alfabeta, Laboratorio, Valor de "
            "Potencia, Códigos de Potencia, Código de vías de administración, Código "
            "de monodroga, Texto Largo de Material, Precio de Venta al Público."
        )

        doc.add_heading("7.4. Presentaciones por monodroga (resumen)", level=2)
        agregar_tabla(doc,
            ["Monodroga", "Potencias disponibles", "Vía", "Cadena de frío"],
            [
                ["Fluorouracilo", "500 mg (única)", "IV", "No"],
                ["Leucovorina", "50 mg (IV), 15 mg (oral)", "IV / oral", "Parcial"],
                ["Oxaliplatino", "50 mg, 100 mg", "IV", "No"],
                ["Irinotecán", "100 mg", "IV", "No"],
                ["Capecitabina", "500 mg (única)", "Oral", "No"],
                ["Bevacizumab", "100 mg, 400 mg (+1 intraocular)", "IV", "Sí"],
                ["Cetuximab", "100 mg, 500 mg", "IV", "Sí"],
                ["Panitumumab", "100 mg", "IV", "Sí"],
                ["Encorafenib", "50 mg, 75 mg", "Oral", "No"],
                ["Pembrolizumab", "100 mg", "IV", "Sí"],
                ["Nivolumab", "40 / 100 / 240 / 600 mg", "IV/SC", "Sí"],
                ["Ipilimumab", "50 mg", "IV", "Sí"],
                ["Regorafenib", "40 mg", "Oral", "No"],
                ["Trifluridina/tipiracilo", "15 mg, 20 mg", "Oral", "No"],
                ["Aflibercept", "Solo INTRAOCULAR (no utilizable)", "Intraocular", "Sí"],
            ]
        )

        doc.add_heading("7.5. Restricciones detectadas en el catálogo", level=2)
        doc.add_paragraph(
            "Fármacos ausentes o no utilizables: el ziv-aflibercept de uso oncológico "
            "(IV) no está disponible; el catálogo solo contiene la presentación "
            "intraocular (oftalmológica). El generador/validador filtra por vía IV "
            "para descartar estas presentaciones.",
            style="List Bullet"
        )
        doc.add_paragraph(
            "Granularidad gruesa: fluorouracilo y capecitabina solo disponibles en "
            "presentaciones de 500 mg. Para ciertas dosis, el excedente mínimo "
            "alcanzable no es cero. Un caso concordante se define como aquel que "
            "minimiza el excedente alcanzable con el catálogo, no como excedente nulo.",
            style="List Bullet"
        )

        logger.info("Sección 7 generada")
    except Exception as exc:
        logger.error("Error en sección 7: %s", exc, exc_info=True)
        raise


def agregar_nota_final(doc):
    """Agrega nota de carácter preliminar al final del documento."""
    try:
        doc.add_page_break()
        doc.add_heading("Nota Final", level=1)
        doc.add_paragraph(
            "Este documento es preliminar y sujeto a la validación clínica del "
            "Dr. Adelchanow. Los atributos, distribuciones, regímenes y "
            "proporciones de error aquí descritos requieren confirmación del "
            "especialista antes de la generación definitiva del dataset y el "
            "entrenamiento del modelo."
        )
        doc.add_paragraph(
            "Las fuentes clínicas utilizadas son: NCCN Colon Cancer v.2.2026, "
            "ESMO cáncer de colon localizado (Argilés 2020) y metastásico "
            "(Cremolini 2026), AAOC Guía 5 Tumores del Tracto Digestivo Inferior "
            "2025, y el catálogo Alfabeta 2025 (Medicamentos v1.xlsx)."
        )
        logger.info("Nota final generada")
    except Exception as exc:
        logger.error("Error en nota final: %s", exc, exc_info=True)
        raise


def main():
    """Genera el documento Word completo con las 7 secciones."""
    try:
        configurar_logging()
        logger.info("Inicio de generación del documento")

        doc = Document()
        crear_estilos(doc)
        agregar_portada(doc)

        seccion_1_dataset(doc)
        seccion_2_features(doc)
        seccion_3_sintetizar(doc)
        seccion_4_modelo(doc)
        seccion_5_salida(doc)
        seccion_6_etl(doc)
        seccion_7_medicamentos(doc)
        agregar_nota_final(doc)

        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        doc.save(OUTPUT_PATH)
        logger.info("Documento guardado en %s", OUTPUT_PATH)
        print("Documento generado exitosamente: %s" % OUTPUT_PATH)

    except Exception as exc:
        logger.error("Error al generar el documento: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    main()
