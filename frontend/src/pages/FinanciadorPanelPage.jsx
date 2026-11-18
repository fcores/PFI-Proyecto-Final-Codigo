import { useCallback, useEffect, useRef, useState } from "react";
import TopBar from "../components/TopBar";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
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

// Orden de la barra de plazos: primero lo que sigue abierto, después lo cerrado.
const ESTADOS_PLAZO = [
  { estado: "en_plazo", etiqueta: "En plazo" },
  { estado: "por_vencer", etiqueta: "Por vencer" },
  { estado: "vencido", etiqueta: "Vencidas" },
  { estado: "cumplido", etiqueta: "Cumplidas" },
  { estado: "cumplido_fuera_de_plazo", etiqueta: "Cumplidas fuera de plazo" },
];

function IndicadorFiltro({ valor, etiqueta, detalle, activo, onClick }) {
  return (
    <button
      type="button"
      className={`fin-kpi${activo ? " is-active" : ""}`}
      aria-pressed={activo}
      onClick={onClick}
      title={activo ? "Quitar este filtro" : "Filtrar la tabla por este indicador"}
    >
      <strong className="fin-kpi__valor">{valor}</strong>
      <span className="fin-kpi__etiqueta">{etiqueta}</span>
      {detalle && <span className="fin-kpi__detalle">{detalle}</span>}
    </button>
  );
}

function IndicadorFijo({ valor, etiqueta, detalle }) {
  return (
    <div className="fin-kpi fin-kpi--static">
      <strong className="fin-kpi__valor">{valor}</strong>
      <span className="fin-kpi__etiqueta">{etiqueta}</span>
      {detalle && <span className="fin-kpi__detalle">{detalle}</span>}
    </div>
  );
}

function BarraPlazos({ plazos, activo, onSelect }) {
  const total = ESTADOS_PLAZO.reduce((suma, { estado }) => suma + (plazos[estado] || 0), 0);
  const descripcion = ESTADOS_PLAZO.map(({ estado, etiqueta }) => `${plazos[estado] || 0} ${etiqueta.toLowerCase()}`).join(
    ", "
  );
  return (
    <div className="fin-plazos-body">
      <div className="fin-plazos-bar" role="img" aria-label={`Gestiones por plazo: ${descripcion}`}>
        {total > 0 &&
          ESTADOS_PLAZO.filter(({ estado }) => plazos[estado] > 0).map(({ estado }) => (
            <span
              key={estado}
              className={`fin-plazos-seg fin-plazos-seg--${estado}`}
              style={{ width: `${(plazos[estado] / total) * 100}%` }}
            />
          ))}
      </div>
      <ul className="fin-plazos-legend">
        {ESTADOS_PLAZO.map(({ estado, etiqueta }) => {
          const cantidad = plazos[estado] || 0;
          const esActivo = activo === estado;
          return (
            <li key={estado}>
              <button
                type="button"
                className={`fin-plazos-item${esActivo ? " is-active" : ""}${cantidad === 0 ? " is-empty" : ""}`}
                aria-pressed={esActivo}
                onClick={() => onSelect(estado)}
                title={esActivo ? "Quitar este filtro" : `Filtrar: ${PLAZO_LABEL[estado]}`}
              >
                <span className={`fin-plazos-dot fin-plazos-seg--${estado}`} aria-hidden="true" />
                <strong>{cantidad}</strong>
                <span>{etiqueta}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function FinanciadorPanelPage() {
  const [resumen, setResumen] = useState(null);
  const [expedientes, setExpedientes] = useState([]);
  const [topeResumen, setTopeResumen] = useState(false);
  const [topeExpedientes, setTopeExpedientes] = useState(false);
  const [filtros, setFiltros] = useState(FILTROS_INICIALES);
  const [cargandoResumen, setCargandoResumen] = useState(false);
  const [cargandoExpedientes, setCargandoExpedientes] = useState(false);
  const [errorResumen, setErrorResumen] = useState(null);
  const [errorExpedientes, setErrorExpedientes] = useState(null);
  // Si se cambian los filtros rapido, solo vale la respuesta del ultimo pedido.
  const pedidoExpedientes = useRef(0);

  const cargarResumen = useCallback(async () => {
    try {
      setCargandoResumen(true);
      setErrorResumen(null);
      const res = await fetchResumenFinanciador();
      setResumen(res);
      setTopeResumen(Boolean(res.alcanzo_tope));
    } catch (err) {
      setErrorResumen(err.message || "No se pudieron leer los indicadores desde la red blockchain.");
      setResumen(null);
    } finally {
      setCargandoResumen(false);
    }
  }, []);

  const cargarExpedientes = useCallback(async (filtrosActuales) => {
    const pedido = ++pedidoExpedientes.current;
    try {
      setCargandoExpedientes(true);
      setErrorExpedientes(null);
      const exp = await fetchExpedientesFinanciador(filtrosActuales);
      if (pedido !== pedidoExpedientes.current) return;
      setExpedientes(exp.expedientes);
      setTopeExpedientes(exp.alcanzoTope);
    } catch (err) {
      if (pedido !== pedidoExpedientes.current) return;
      setErrorExpedientes(err.message || "No se pudieron leer los expedientes desde la red blockchain.");
      setExpedientes([]);
    } finally {
      if (pedido === pedidoExpedientes.current) setCargandoExpedientes(false);
    }
  }, []);

  useEffect(() => {
    cargarResumen();
  }, [cargarResumen]);

  useEffect(() => {
    cargarExpedientes(filtros);
  }, [filtros, cargarExpedientes]);

  function actualizar() {
    cargarResumen();
    cargarExpedientes(filtros);
  }

  function actualizarFiltro(campo, valor) {
    setFiltros((actual) => ({ ...actual, [campo]: valor }));
  }

  function alternarFiltro(campo, valor) {
    setFiltros((actual) => ({ ...actual, [campo]: actual[campo] === valor ? "" : valor }));
  }

  const loading = cargandoResumen || cargandoExpedientes;
  const alcanzoTope = topeResumen || topeExpedientes;
  const hayFiltros = Object.values(filtros).some(Boolean);
  const error = errorResumen || errorExpedientes;

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
          <section className="card card-table">
            <header className="agreements-header">
              <div>
                <span className="card-eyebrow">Expedientes</span>
                <h2>Gestiones del financiador</h2>
                <p className="muted">Sin datos clínicos de detalle: régimen, costos, recupero y plazos.</p>
              </div>
              <div className="fin-header-actions">
                {resumen && <span className="card-badge">{resumen.prescripciones_analizadas} prescripciones</span>}
                <button type="button" className="btn-secondary" onClick={actualizar} disabled={loading}>
                  {loading ? "Actualizando…" : "Actualizar"}
                </button>
              </div>
            </header>

            {error && (
              <p className="status error status--block" role="alert">
                {error}
              </p>
            )}

            {resumen && (
              <>
                <div className="fin-kpis">
                  <section className="fin-kpi-group" aria-labelledby="fin-grupo-ahorro">
                    <h3 id="fin-grupo-ahorro" className="fin-kpi-group__titulo">
                      Ahorro
                    </h3>
                    <IndicadorFiltro
                      valor={formatCurrency(resumen.ahorro_efectivo)}
                      etiqueta="Ahorro efectivo"
                      detalle={`${resumen.alternativas_adoptadas} alternativas adoptadas por el prescriptor`}
                      activo={filtros.alternativa === "adoptada"}
                      onClick={() => alternarFiltro("alternativa", "adoptada")}
                    />
                    <IndicadorFiltro
                      valor={formatCurrency(resumen.ahorro_potencial)}
                      etiqueta="Ahorro potencial detectado"
                      detalle={`${resumen.alertas_alternativa} prescripciones con una alternativa equivalente de menor costo`}
                      activo={filtros.alternativa === "alerta"}
                      onClick={() => alternarFiltro("alternativa", "alerta")}
                    />
                  </section>

                  <section className="fin-kpi-group" aria-labelledby="fin-grupo-calidad">
                    <h3 id="fin-grupo-calidad" className="fin-kpi-group__titulo">
                      Calidad y recupero
                    </h3>
                    <IndicadorFijo
                      valor={resumen.errores_detectados}
                      etiqueta="Errores detectados por la capa de reglas"
                      detalle={`${resumen.errores_confirmados} confirmados por el auditor con un rechazo`}
                    />
                    <IndicadorFiltro
                      valor={resumen.surge_potencialmente_recuperables}
                      etiqueta="Potencialmente recuperables ante el SURGE"
                      detalle="Res. SSSalud 731/2023: el auditor debe constatar ECOG 0-1 antes de solicitar el reintegro"
                      activo={filtros.surge === "true"}
                      onClick={() => alternarFiltro("surge", "true")}
                    />
                  </section>

                  <section className="fin-kpi-group" aria-labelledby="fin-grupo-plazos">
                    <h3 id="fin-grupo-plazos" className="fin-kpi-group__titulo">
                      Plazos · Res. 951/2025
                    </h3>
                    <BarraPlazos
                      plazos={resumen.plazos}
                      activo={filtros.plazo}
                      onSelect={(estado) => alternarFiltro("plazo", estado)}
                    />
                  </section>
                </div>

                <p className={`fin-kpis-note${alcanzoTope ? " fin-kpis-note--warning" : ""}`}>
                  {alcanzoTope
                    ? "Se alcanzó el tope de lectura configurado: los indicadores cubren solo las prescripciones leídas."
                    : "Los indicadores cubren todas las prescripciones registradas."}{" "}
                  Hacé clic en uno para filtrar la tabla.
                </p>
              </>
            )}

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
              <div className="fin-filtros-estado">
                <span className="muted">
                  {cargandoExpedientes
                    ? "Cargando expedientes…"
                    : resumen
                      ? `Mostrando ${expedientes.length} de ${resumen.prescripciones_analizadas}`
                      : `Mostrando ${expedientes.length}`}
                </span>
                {hayFiltros && (
                  <button type="button" className="btn-link" onClick={() => setFiltros(FILTROS_INICIALES)}>
                    Limpiar filtros
                  </button>
                )}
              </div>
            </div>

            <DataTable
              columns={COLUMNAS}
              rows={expedientes}
              renderRow={renderRow}
              emptyText={
                cargandoExpedientes ? "Cargando desde la red Fabric..." : "No hay expedientes para los filtros elegidos."
              }
            />
          </section>
        </section>
      </main>
    </>
  );
}
