import { useEffect, useMemo, useRef, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import FormActions from "../components/FormActions";
import StatusChip from "../components/StatusChip";
import ConfidenceBar from "../components/ConfidenceBar";
import useFormStatus from "../hooks/useFormStatus";
import { ESTADO_VARIANT } from "../constants/estadoVariant";
import {
  createPrescription,
  fetchDosisReferencia,
  fetchRegimenes,
  recomendarRegimen,
} from "../api/prescriptions";

function bodySurfaceArea(pesoKg, tallaCm) {
  const peso = Number(pesoKg);
  const talla = Number(tallaCm);
  if (!peso || !talla) return null;
  return Math.sqrt((talla * peso) / 3600).toFixed(2);
}

export default function PrescripcionPage() {
  const formRef = useRef(null);
  const { status, setLoading, setSuccess, setError, clear } = useFormStatus();
  const [result, setResult] = useState(null);
  const [preview, setPreview] = useState({ peso: "", talla: "" });
  const [regimenes, setRegimenes] = useState([]);
  const [idRegimen, setIdRegimen] = useState("");
  const [dosisRows, setDosisRows] = useState([]);
  const [guiaNota, setGuiaNota] = useState("");

  const superficie = useMemo(
    () => bodySurfaceArea(preview.peso, preview.talla),
    [preview],
  );

  useEffect(() => {
    fetchRegimenes()
      .then(setRegimenes)
      .catch(() => setRegimenes([]));
  }, []);

  useEffect(() => {
    async function loadDosis() {
      if (!idRegimen || !preview.peso || !preview.talla) {
        return;
      }
      try {
        const rows = await fetchDosisReferencia(
          idRegimen,
          Number(preview.peso),
          Number(preview.talla),
        );
        setDosisRows(rows || []);
      } catch {
        setDosisRows([]);
      }
    }
    loadDosis();
  }, [idRegimen, preview.peso, preview.talla]);

  function updateDosis(index, value) {
    setDosisRows((current) =>
      current.map((row, idx) =>
        idx === index ? { ...row, dosis_mg: Number(value) } : row,
      ),
    );
  }

  async function handleSugerirGuias() {
    const form = formRef.current;
    const data = new FormData(form);
    const peso = data.get("peso_kg");
    const talla = data.get("talla_cm");
    const body = {
      estadio: data.get("estadio") || "",
      t: data.get("t") || "",
      n: data.get("n") || "",
      m: data.get("m") || "",
      localizacion_tumor: data.get("localizacion_tumor") || "",
      msi: data.get("msi") || "no_evaluado",
      ras: data.get("ras") || "no_evaluado",
      braf_v600e: data.get("braf_v600e") || "no_evaluado",
      linea_tratamiento: data.get("linea_tratamiento") || "",
    };
    if (peso) body.peso_kg = Number(peso);
    if (talla) body.talla_cm = Number(talla);

    if (!body.estadio) {
      setError("Completá el estadio para sugerir según guías.");
      return;
    }

    setLoading("Consultando guías clínicas...");
    try {
      const reco = await recomendarRegimen(body);
      setIdRegimen(reco.id_regimen);
      let nota = `Sugerido ${reco.id_regimen} (${reco.nombre_regimen}) por: ${
        (reco.reglas_aplicadas || []).join(", ") || "guías clínicas"
      }`;
      if (reco.costo_total != null) {
        nota += ` — Costo estimado: $${reco.costo_total.toLocaleString("es-AR", { minimumFractionDigits: 2 })}`;
      }
      setGuiaNota(nota);
      setSuccess(`Régimen sugerido: ${reco.id_regimen}`);
    } catch (err) {
      setError(err.message || "No se pudo obtener la sugerencia de guías.");
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const form = formRef.current;
    const data = new FormData(form);

    const body = {
      patient_id: Number(data.get("patient_id")),
      edad: Number(data.get("edad")),
      sexo: data.get("sexo") || "",
      peso_kg: Number(data.get("peso_kg")),
      talla_cm: Number(data.get("talla_cm")),
      diagnostico_cie10: (data.get("diagnostico_cie10") || "").trim(),
      localizacion_tumor: data.get("localizacion_tumor") || "",
      tipo_histologico: (data.get("tipo_histologico") || "").trim(),
      t: data.get("t") || "",
      n: data.get("n") || "",
      m: data.get("m") || "",
      estadio: data.get("estadio") || "",
      msi: data.get("msi") || "no_evaluado",
      ras: data.get("ras") || "no_evaluado",
      braf_v600e: data.get("braf_v600e") || "no_evaluado",
      linea_tratamiento: data.get("linea_tratamiento") || "",
      id_regimen: idRegimen || data.get("id_regimen") || "",
      dosis_por_farmaco: dosisRows.map((row) => ({
        monodroga: row.monodroga,
        dosis_mg: Number(row.dosis_mg),
      })),
      medico_prescriptor: (data.get("medico_prescriptor") || "").trim(),
      matricula: (data.get("matricula") || "").trim(),
    };

    setLoading("Validando y registrando en la blockchain (endoso de las 3 organizaciones)...");
    setResult(null);

    try {
      const created = await createPrescription(body);
      setSuccess(`Prescripción ${created.prescription_code} registrada en la blockchain.`);
      setResult(created);
      form.reset();
      setPreview({ peso: "", talla: "" });
      setIdRegimen("");
      setDosisRows([]);
      setGuiaNota("");
    } catch (err) {
      setError(err.message || "Ocurrió un error al registrar la prescripción.");
    }
  }

  function handleCancel() {
    formRef.current.reset();
    setPreview({ peso: "", talla: "" });
    setResult(null);
    setIdRegimen("");
    setDosisRows([]);
    setGuiaNota("");
    clear();
  }

  return (
    <>
      <TopBar
        title="Alta de prescripción de alta complejidad"
        subtitle="Registro de prescripciones oncológicas (caso piloto: cáncer de colon) con validación híbrida y trazabilidad en blockchain."
        badge="Prescripciones"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="content-stack">
            <form ref={formRef} className="card card-form" onSubmit={handleSubmit}>
              <CardHeader
                split
                eyebrow="Auditoría de prescripciones"
                title="Datos clínicos y prescripción"
                description="Completá los atributos clínicos, elegí el régimen (opcionalmente sugerido por guías) y validá con el motor híbrido."
                badge="Cáncer de colon"
              />

              <div className="form-grid">
                <FormField label="ID Paciente" htmlFor="patient_id" required span={4}>
                  <input id="patient_id" name="patient_id" type="number" min="1" placeholder="Ej.: 1" required />
                </FormField>
                <FormField label="Edad" htmlFor="edad" required span={2}>
                  <input id="edad" name="edad" type="number" min="0" max="120" placeholder="65" required />
                </FormField>
                <FormField label="Sexo" htmlFor="sexo" required span={3}>
                  <select id="sexo" name="sexo" required defaultValue="">
                    <option value="" disabled>Seleccionar</option>
                    <option value="Masculino">Masculino</option>
                    <option value="Femenino">Femenino</option>
                  </select>
                </FormField>
                <FormField label="Diagnóstico (CIE-10)" htmlFor="diagnostico_cie10" required span={3}>
                  <input id="diagnostico_cie10" name="diagnostico_cie10" type="text" placeholder="Ej.: C18.9" required />
                </FormField>

                <FormField label="Peso (kg)" htmlFor="peso_kg" required span={3}>
                  <input
                    id="peso_kg"
                    name="peso_kg"
                    type="number"
                    step="0.1"
                    min="0"
                    placeholder="72"
                    required
                    onChange={(e) => setPreview((p) => ({ ...p, peso: e.target.value }))}
                  />
                </FormField>
                <FormField label="Talla (cm)" htmlFor="talla_cm" required span={3}>
                  <input
                    id="talla_cm"
                    name="talla_cm"
                    type="number"
                    step="0.1"
                    min="0"
                    placeholder="170"
                    required
                    onChange={(e) => setPreview((p) => ({ ...p, talla: e.target.value }))}
                  />
                </FormField>
                <FormField label="Superficie corporal (m²)" htmlFor="superficie_preview" span={6}>
                  <input
                    id="superficie_preview"
                    type="text"
                    value={superficie ? `${superficie} m² (Mosteller)` : "Se calcula con peso y talla"}
                    readOnly
                  />
                </FormField>
              </div>

              <CardHeader
                eyebrow="Estadificación TNM"
                title="Clasificación del tumor"
                description="Localización, histología y estadificación TNM."
              />
              <div className="form-grid">
                <FormField label="Localización del tumor" htmlFor="localizacion_tumor" required span={4}>
                  <select id="localizacion_tumor" name="localizacion_tumor" required defaultValue="">
                    <option value="" disabled>Seleccionar</option>
                    <option value="Colon derecho">Colon derecho</option>
                    <option value="Colon izquierdo">Colon izquierdo</option>
                    <option value="Colon transverso">Colon transverso</option>
                  </select>
                </FormField>
                <FormField label="Tipo histológico" htmlFor="tipo_histologico" required span={4}>
                  <input id="tipo_histologico" name="tipo_histologico" type="text" placeholder="Ej.: Adenocarcinoma" required />
                </FormField>
                <FormField label="Estadio" htmlFor="estadio" required span={4}>
                  <select id="estadio" name="estadio" required defaultValue="">
                    <option value="" disabled>Seleccionar</option>
                    <option value="I">I</option>
                    <option value="II">II</option>
                    <option value="III">III</option>
                    <option value="IV">IV</option>
                  </select>
                </FormField>
                <FormField label="T (tumor primario)" htmlFor="t" required span={4}>
                  <select id="t" name="t" required defaultValue="">
                    <option value="" disabled>Seleccionar</option>
                    <option value="T1">T1</option>
                    <option value="T2">T2</option>
                    <option value="T3">T3</option>
                    <option value="T4">T4</option>
                  </select>
                </FormField>
                <FormField label="N (ganglios)" htmlFor="n" required span={4}>
                  <select id="n" name="n" required defaultValue="">
                    <option value="" disabled>Seleccionar</option>
                    <option value="N0">N0</option>
                    <option value="N1">N1</option>
                    <option value="N2">N2</option>
                  </select>
                </FormField>
                <FormField label="M (metástasis)" htmlFor="m" required span={4}>
                  <select id="m" name="m" required defaultValue="">
                    <option value="" disabled>Seleccionar</option>
                    <option value="M0">M0</option>
                    <option value="M1">M1</option>
                    <option value="MX">MX</option>
                  </select>
                </FormField>
              </div>

              <CardHeader
                eyebrow="Biomarcadores"
                title="Marcadores moleculares"
                description="Tres estados: no se imputa wild type si no fue evaluado."
              />
              <div className="form-grid">
                <FormField label="MSI" htmlFor="msi" required span={4}>
                  <select id="msi" name="msi" required defaultValue="no_evaluado">
                    <option value="no_evaluado">No evaluado</option>
                    <option value="MSI-H">MSI-H</option>
                    <option value="MSS">MSS</option>
                  </select>
                </FormField>
                <FormField label="RAS" htmlFor="ras" required span={4}>
                  <select id="ras" name="ras" required defaultValue="no_evaluado">
                    <option value="no_evaluado">No evaluado</option>
                    <option value="wild_type">Wild type</option>
                    <option value="mutado">Mutado</option>
                  </select>
                </FormField>
                <FormField label="BRAF V600E" htmlFor="braf_v600e" required span={4}>
                  <select id="braf_v600e" name="braf_v600e" required defaultValue="no_evaluado">
                    <option value="no_evaluado">No evaluado</option>
                    <option value="wild_type">Wild type / ausente</option>
                    <option value="presente">Presente</option>
                  </select>
                </FormField>
              </div>

              <CardHeader
                eyebrow="Prescripción"
                title="Régimen y dosificación"
                description="Podés sugerir según guías y luego auditar lo prescrito con el modelo ML."
              />
              <div className="form-grid">
                <FormField label="Línea de tratamiento" htmlFor="linea_tratamiento" required span={4}>
                  <select id="linea_tratamiento" name="linea_tratamiento" required defaultValue="">
                    <option value="" disabled>Seleccionar</option>
                    <option value="Primera">Primera</option>
                    <option value="Segunda">Segunda</option>
                  </select>
                </FormField>
                <FormField label="Régimen" htmlFor="id_regimen" required span={5}>
                  <select
                    id="id_regimen"
                    name="id_regimen"
                    required
                    value={idRegimen}
                    onChange={(e) => setIdRegimen(e.target.value)}
                  >
                    <option value="" disabled>Seleccionar</option>
                    {regimenes.map((reg) => (
                      <option key={reg.id_regimen} value={reg.id_regimen}>
                        {reg.id_regimen} — {reg.nombre}
                      </option>
                    ))}
                  </select>
                </FormField>
                <FormField label="Acción" htmlFor="sugerir_guias" span={3}>
                  <button
                    id="sugerir_guias"
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleSugerirGuias}
                  >
                    Sugerir según guías
                  </button>
                </FormField>
                {guiaNota ? (
                  <FormField label="Nota de guías" htmlFor="guia_nota" span={12}>
                    <input id="guia_nota" type="text" value={guiaNota} readOnly />
                  </FormField>
                ) : null}

                <FormField label="Médico prescriptor" htmlFor="medico_prescriptor" required span={8}>
                  <input id="medico_prescriptor" name="medico_prescriptor" type="text" placeholder="Ej.: Dr. Juan Pérez" required />
                </FormField>
                <FormField label="Matrícula" htmlFor="matricula" required span={4}>
                  <input id="matricula" name="matricula" type="text" placeholder="MN 12345" required />
                </FormField>
              </div>

              {dosisRows.length > 0 && (
                <div className="dosis-table-wrap">
                  <h3 className="dosis-table__title">Dosis por fármaco</h3>
                  <table className="dosis-table">
                    <thead>
                      <tr>
                        <th>Monodroga</th>
                        <th>Dosis (mg)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dosisRows.map((row, index) => (
                        <tr key={row.monodroga}>
                          <td>{row.monodroga}</td>
                          <td>
                            <input
                              type="number"
                              min="0"
                              step="0.1"
                              value={row.dosis_mg}
                              onChange={(e) => updateDosis(index, e.target.value)}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <FormActions status={status} onCancel={handleCancel} submitLabel="✅ Validar y registrar" />
            </form>

            {result && (
              <section className="card card-form">
                <CardHeader
                  split
                  eyebrow="Registrada en blockchain"
                  title={`Prescripción ${result.prescription_code}`}
                  description="Asset inmutable en Hyperledger Fabric, endosado por las 3 organizaciones. Queda pendiente de auditoría; el veredicto del modelo es soporte de decisión."
                  badge={`Superficie: ${result.clinical?.superficie_corporal_m2} m²`}
                />
                <div className="form-grid">
                  <FormField label="Estado on-chain" htmlFor="result_estado_chain" span={4}>
                    <div>
                      <StatusChip
                        variant={ESTADO_VARIANT[result.estado] || "neutral"}
                        label={result.estado}
                      />
                    </div>
                  </FormField>
                  <FormField label="Veredicto ML" htmlFor="result_estado" span={4}>
                    <div>
                      <StatusChip
                        variant={ESTADO_VARIANT[result.ml.estado] || "neutral"}
                        label={result.ml.estado}
                      />
                    </div>
                  </FormField>
                  <FormField label="Origen / Modelo" htmlFor="result_origen" span={4}>
                    <input
                      id="result_origen"
                      type="text"
                      value={`${result.ml.origen || "—"} · ${result.ml.version_modelo || "—"}`}
                      readOnly
                    />
                  </FormField>
                  <FormField label="Confianza" htmlFor="result_confianza" span={12}>
                    <ConfidenceBar
                      value={result.ml.probabilidad_concordante}
                      low={result.ml.umbral_bajo}
                      high={result.ml.umbral_alto}
                      label={`Nivel: ${result.ml.nivel_confianza || "—"}`}
                    />
                  </FormField>
                  <FormField label="TxID de Fabric" htmlFor="result_tx" span={6}>
                    <input id="result_tx" type="text" value={result.tx_id || ""} readOnly />
                  </FormField>
                  <FormField label="Hash del contenido" htmlFor="result_hash" span={6}>
                    <input id="result_hash" type="text" value={result.payload_hash || ""} readOnly />
                  </FormField>
                </div>
                <ul className="muted">
                  {result.ml.motivos.map((motivo, idx) => (
                    <li key={idx}>{motivo}</li>
                  ))}
                </ul>
                {result.ml.features_relevantes?.length > 0 && (
                  <div className="features-aportes">
                    <h4>Aportes principales</h4>
                    <ul>
                      {result.ml.features_relevantes.map((item) => (
                        <li key={item.feature}>
                          {item.feature}: {item.aporte}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {result.ml.costo_total != null && (
                  <div className="features-aportes">
                    <h4>Costo estimado del régimen</h4>
                    <p style={{ fontWeight: 600, fontSize: "1.1em", margin: "0.5em 0" }}>
                      Total: ${result.ml.costo_total.toLocaleString("es-AR", { minimumFractionDigits: 2 })}
                    </p>
                    {result.ml.costo_por_farmaco?.length > 0 && (
                      <table className="dosis-table" style={{ marginTop: "0.5em" }}>
                        <thead>
                          <tr>
                            <th>Fármaco</th>
                            <th>Dosis (mg)</th>
                            <th>Costo</th>
                          </tr>
                        </thead>
                        <tbody>
                          {result.ml.costo_por_farmaco.map((item) => (
                            <tr key={item.monodroga}>
                              <td>{item.monodroga}</td>
                              <td>{item.dosis_mg}</td>
                              <td>{item.costo != null ? `$${item.costo.toLocaleString("es-AR", { minimumFractionDigits: 2 })}` : "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )}
              </section>
            )}
          </section>
        </section>
      </main>
    </>
  );
}
