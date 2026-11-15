import ConfidenceBar from "./ConfidenceBar";
import ReadOnlyField from "./ReadOnlyField";
import SimpleTable from "./SimpleTable";
import StatusChip from "./StatusChip";
import { ESTADO_VARIANT, mlLabel } from "../constants/estadoVariant";
import { formatCurrency, formatNumber } from "../utils/format";

/**
 * Veredicto del motor reglas + ML (soporte de decisión). Lo comparten el
 * resultado del alta de prescripción y el caso de auditoría.
 *
 * @param {object} ml - Bloque `ml` del asset on-chain
 */
export default function MlVerdictPanel({ ml = {} }) {
  const motivos = ml.motivos ?? [];
  const aportes = ml.features_relevantes ?? [];
  const alternativas = ml.alternativas_economicas ?? [];
  const costos = ml.costo_por_farmaco ?? [];

  return (
    <div className="ml-panel">
      <div className="form-grid">
        <ReadOnlyField label="Veredicto del modelo" span={4}>
          <StatusChip variant={ESTADO_VARIANT[ml.estado] || "neutral"} label={mlLabel(ml.estado)} />
        </ReadOnlyField>
        <ReadOnlyField label="Origen" value={ml.origen} span={4} />
        <ReadOnlyField label="Versión del modelo" value={ml.version_modelo} span={4} />
        <div className="field-span-12">
          <ConfidenceBar
            value={ml.probabilidad_concordante}
            low={ml.umbral_bajo}
            high={ml.umbral_alto}
            label={`Confianza: ${ml.nivel_confianza || "—"}`}
          />
        </div>
      </div>

      <section className="ml-panel__section">
        <h3 className="ml-panel__title">Motivos</h3>
        {motivos.length > 0 ? (
          <ul className="ml-panel__list">
            {motivos.map((motivo, idx) => (
              <li key={idx}>{motivo}</li>
            ))}
          </ul>
        ) : (
          <p className="muted">Sin motivos registrados.</p>
        )}
      </section>

      {aportes.length > 0 && (
        <section className="ml-panel__section">
          <h3 className="ml-panel__title">Aportes principales al score</h3>
          <ul className="ml-panel__list ml-panel__list--inline">
            {aportes.map((item) => (
              <li key={item.feature}>
                <span>{item.feature}</span>
                <strong className={item.aporte >= 0 ? "aporte--pos" : "aporte--neg"}>
                  {item.aporte >= 0 ? "+" : ""}
                  {formatNumber(item.aporte)}
                </strong>
              </li>
            ))}
          </ul>
        </section>
      )}

      {ml.costo_total != null && (
        <section className="ml-panel__section">
          <h3 className="ml-panel__title">
            Costo estimado por ciclo: <span className="ml-panel__amount">{formatCurrency(ml.costo_total)}</span>
          </h3>
          {costos.length > 0 && (
            <SimpleTable
              caption="Costo por fármaco"
              columns={["Fármaco", "Dosis (mg)", "Costo"]}
              rows={costos}
              renderRow={(item) => (
                <tr key={item.monodroga}>
                  <td>{item.monodroga}</td>
                  <td className="num">{formatNumber(item.dosis_mg)}</td>
                  <td className="num">{formatCurrency(item.costo)}</td>
                </tr>
              )}
            />
          )}
        </section>
      )}

      {alternativas.length > 0 && (
        <section className="ml-panel__section">
          <h3 className="ml-panel__title">Alternativas terapéuticas de menor costo</h3>
          <p className="muted">
            Esquema prescrito: {formatCurrency(ml.costo_tratamiento)} por tratamiento completo.
          </p>
          <SimpleTable
            caption="Alternativas equivalentes de menor costo"
            columns={["Régimen", "Ciclos", "Costo del tratamiento", "Ahorro", "%"]}
            rows={alternativas}
            renderRow={(alt) => (
              <tr key={alt.id_regimen}>
                <td>
                  {alt.id_regimen} — {alt.nombre}
                </td>
                <td className="num">{alt.ciclos}</td>
                <td className="num">{formatCurrency(alt.costo_tratamiento)}</td>
                <td className="num">{formatCurrency(alt.ahorro)}</td>
                <td className="num">{formatNumber(alt.pct_ahorro)}%</td>
              </tr>
            )}
          />
        </section>
      )}

      {ml.ahorro_efectivo != null && (
        <section className="ml-panel__section">
          <h3 className="ml-panel__title">
            Ahorro efectivo: <span className="ml-panel__amount">{formatCurrency(ml.ahorro_efectivo)}</span>
          </h3>
          <p className="muted">
            El prescriptor adoptó la alternativa equivalente de menor costo en lugar de {ml.regimen_original}.
          </p>
        </section>
      )}

      {ml.surge && (
        <section className="ml-panel__section">
          <h3 className="ml-panel__title">Recupero ante el SURGE</h3>
          <p className="muted">
            {ml.surge.potencialmente_recuperable
              ? `Potencialmente recuperable (${ml.surge.norma}). A constatar por el auditor: ${(ml.surge.a_constatar || []).join(", ")}.`
              : `No alcanzado por el SURGE según ${ml.surge.norma}.`}
          </p>
        </section>
      )}
    </div>
  );
}
