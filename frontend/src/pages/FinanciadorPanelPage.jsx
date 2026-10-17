import { useCallback, useEffect, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import SimpleTable from "../components/SimpleTable";
import StatusChip from "../components/StatusChip";
import { fetchExpedientesFinanciador, fetchResumenFinanciador } from "../api/financiador";
import { ESTADO_VARIANT, PLAZO_LABEL, PLAZO_VARIANT, estadoLabel, plazoTexto } from "../constants/estadoVariant";
import { formatCurrency } from "../utils/format";
import { formatDate } from "../utils/formatDate";

const COLUMNAS = [
  "Código",
  "Estado",
  "Régimen",
  "Costo del tratamiento",
  "Ahorro potencial",
  "Ahorro efectivo",
  "SURGE",
  "Plazo (Res. 951/2025)",
  "Alta",
];

const FILTROS_INICIALES = { surge: "", plazo: "", alternativa: "" };

const TIPO_PLAZO = {
  respuesta: "Respuesta (5 días corridos)",
  resolucion: "Resolución (30 días hábiles)",
};

function indicadores(resumen) {
  if (!resumen) return [];
  return [
    {
      key: "ahorro_potencial",
      indicador: "Ahorro potencial detectado",
      valor: formatCurrency(resumen.ahorro_potencial),
      detalle: `${resumen.alertas_alternativa} prescripciones con una alternativa equivalente de menor costo`,
    },
    {
      key: "ahorro_efectivo",
      indicador: "Ahorro efectivo",
      valor: formatCurrency(resumen.ahorro_efectivo),
      detalle: `${resumen.alternativas_adoptadas} alternativas adoptadas por el prescriptor`,
    },
    {
      key: "errores",
      indicador: "Errores detectados por la capa de reglas",
      valor: String(resumen.errores_detectados),
      detalle: `${resumen.errores_confirmados} confirmados por el auditor con un rechazo`,
    },
    {
      key: "surge",
      indicador: "Potencialmente recuperables ante el SURGE",
      valor: String(resumen.surge_potencialmente_recuperables),
      detalle: "Res. SSSalud 731/2023: el auditor debe constatar ECOG 0-1 antes de solicitar el reintegro",
    },
    {
      key: "plazos",
      indicador: "Gestiones por vencer o vencidas",
      valor: `${resumen.plazos.por_vencer} / ${resumen.plazos.vencido}`,
      detalle: `${resumen.plazos.en_plazo} en plazo · ${resumen.plazos.cumplido} cumplidas · ${resumen.plazos.cumplido_fuera_de_plazo} cumplidas fuera de plazo`,
    },
  ];
}

export default function FinanciadorPanelPage() {
  const [resumen, setResumen] = useState(null);
  const [expedientes, setExpedientes] = useState([]);
  const [alcanzoTope, setAlcanzoTope] = useState(false);
  const [filtros, setFiltros] = useState(FILTROS_INICIALES);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async (filtrosActuales) => {
    try {
      setLoading(true);
      setError(null);
      const [res, exp] = await Promise.all([
        fetchResumenFinanciador(),
        fetchExpedientesFinanciador(filtrosActuales),
      ]);
      setResumen(res);
      setExpedientes(exp.expedientes);
      setAlcanzoTope(Boolean(res.alcanzo_tope) || exp.alcanzoTope);
    } catch (err) {
      setError(err.message || "No se pudo leer el panel desde la red blockchain.");
      setResumen(null);
      setExpedientes([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(filtros);
  }, [filtros, load]);

  function actualizarFiltro(campo, valor) {
    setFiltros((actual) => ({ ...actual, [campo]: valor }));
  }

  function renderRow(exp) {
    const plazo = exp.plazo_estado
      ? { estado: exp.plazo_estado, dias_restantes: exp.plazo_dias_restantes }
      : null;
    return (
      <tr key={exp.prescription_id}>
        <td>{exp.prescription_code}</td>
        <td>
          <StatusChip variant={ESTADO_VARIANT[exp.estado] || "neutral"} label={estadoLabel(exp.estado)} />
        </td>
        <td>{exp.id_regimen}</td>
        <td className="num">{formatCurrency(exp.costo_tratamiento)}</td>
        <td className="num">{formatCurrency(exp.ahorro_potencial)}</td>
        <td className="num" title={exp.regimen_original ? `En lugar de ${exp.regimen_original}` : undefined}>
          {formatCurrency(exp.ahorro_efectivo)}
        </td>
        <td>
          {exp.surge_potencialmente_recuperable ? (
            <StatusChip variant="info" label="Potencial" />
          ) : (
            "—"
          )}
        </td>
        <td
          className="cell-nowrap"
          title={plazo ? `${TIPO_PLAZO[exp.plazo_tipo] || ""}: vence ${formatDate(exp.plazo_vence)}` : undefined}
        >
          {plazo ? <StatusChip variant={PLAZO_VARIANT[plazo.estado] || "neutral"} label={plazoTexto(plazo)} /> : "—"}
        </td>
        <td className="cell-nowrap">{formatDate(exp.created_at)}</td>
      </tr>
    );
  }

  return (
    <>
      <TopBar
        title="Panel del financiador"
        subtitle="Palancas de costo evitado sobre las prescripciones asentadas en la red Fabric, leídas con la identidad de la organización financiadora."
        badge="Financiador"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-form">
            <CardHeader
              split
              eyebrow="Indicadores"
              title="Resumen"
              description="Ahorro por alternativas terapéuticas de menor costo, errores detectados antes de la autorización, recupero potencial ante el SURGE y cumplimiento de los plazos regulatorios."
              badge={resumen ? `${resumen.prescripciones_analizadas} prescripciones` : undefined}
            />

            <div className="toolbar-row">
              <span className="muted">
                {alcanzoTope
                  ? "Se alcanzó el tope de lectura configurado: los indicadores cubren solo las prescripciones leídas."
                  : "Los indicadores cubren todas las prescripciones registradas."}
              </span>
              <button type="button" className="btn-secondary" onClick={() => load(filtros)} disabled={loading}>
                {loading ? "Actualizando…" : "Actualizar"}
              </button>
            </div>

            {error && (
              <p className="status error status--block" role="alert">
                {error}
              </p>
            )}

            {resumen && (
              <SimpleTable
                caption="Indicadores del financiador"
                columns={["Indicador", "Valor", "Detalle"]}
                rows={indicadores(resumen)}
                renderRow={(fila) => (
                  <tr key={fila.key}>
                    <td>{fila.indicador}</td>
                    <td className="num">
                      <strong>{fila.valor}</strong>
                    </td>
                    <td className="cell-text">{fila.detalle}</td>
                  </tr>
                )}
              />
            )}
          </section>

          <section className="card card-table">
            <header className="agreements-header">
              <div>
                <span className="card-eyebrow">Expedientes</span>
                <h2>Gestiones del financiador</h2>
                <p className="muted">Sin datos clínicos de detalle: régimen, costos, recupero y plazos.</p>
              </div>
            </header>

            <div className="history-toolbar">
              <div className="form-grid history-filters">
                <FormField label="SURGE" htmlFor="filtro_surge" span={4}>
                  <select
                    id="filtro_surge"
                    value={filtros.surge}
                    onChange={(event) => actualizarFiltro("surge", event.target.value)}
                  >
                    <option value="">Todos</option>
                    <option value="true">Potencialmente recuperables</option>
                    <option value="false">No alcanzados</option>
                  </select>
                </FormField>
                <FormField label="Plazo" htmlFor="filtro_plazo" span={4}>
                  <select
                    id="filtro_plazo"
                    value={filtros.plazo}
                    onChange={(event) => actualizarFiltro("plazo", event.target.value)}
                  >
                    <option value="">Todos</option>
                    {Object.entries(PLAZO_LABEL).map(([valor, etiqueta]) => (
                      <option key={valor} value={valor}>
                        {etiqueta}
                      </option>
                    ))}
                  </select>
                </FormField>
                <FormField label="Alternativa de menor costo" htmlFor="filtro_alternativa" span={4}>
                  <select
                    id="filtro_alternativa"
                    value={filtros.alternativa}
                    onChange={(event) => actualizarFiltro("alternativa", event.target.value)}
                  >
                    <option value="">Todas</option>
                    <option value="alerta">Con alerta del motor</option>
                    <option value="adoptada">Adoptada por el prescriptor</option>
                  </select>
                </FormField>
              </div>
            </div>

            <DataTable
              columns={COLUMNAS}
              rows={expedientes}
              renderRow={renderRow}
              emptyText={loading ? "Cargando desde la red Fabric..." : "No hay expedientes para los filtros elegidos."}
            />
          </section>
        </section>
      </main>
    </>
  );
}
