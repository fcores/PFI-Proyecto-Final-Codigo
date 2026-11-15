/**
 * Ficha de datos agrupados: un título y filas etiqueta/valor.
 *
 * @param {string}  title
 * @param {Array<{label: string, value: any, mono?: boolean}>} [rows]
 * @param {boolean} [wide]  - Ocupa todo el ancho de la grilla de fichas
 */
export function InfoGroup({ title, rows = [], wide = false, children }) {
  return (
    <section className={`info-group${wide ? " info-group--wide" : ""}`}>
      <h3 className="info-group__title">{title}</h3>
      {rows.length > 0 && (
        <dl className="info-group__list">
          {rows.map(({ label, value, mono }) => (
            <div className="info-group__row" key={label}>
              <dt>{label}</dt>
              <dd className={mono ? "is-mono" : undefined}>
                {value === null || value === undefined || value === "" ? <span className="is-empty">—</span> : value}
              </dd>
            </div>
          ))}
        </dl>
      )}
      {children}
    </section>
  );
}

export function InfoGrid({ children }) {
  return <div className="info-grid">{children}</div>;
}
