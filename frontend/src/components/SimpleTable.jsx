/**
 * Compact table for detail views (dosis, costos, eventos on-chain).
 * Always scrolls horizontally inside its own wrapper instead of being clipped
 * by the card.
 *
 * @param {string[]} columns
 * @param {any[]}    rows
 * @param {Function} renderRow  - (item, idx) => <tr>...</tr>
 * @param {string}   [caption]  - Accessible caption (visually hidden)
 * @param {string}   [className]
 */
export default function SimpleTable({ columns, rows, renderRow, caption, className = "" }) {
  return (
    <div className={`table-wrapper table-wrapper--scroll simple-table-wrap ${className}`.trim()}>
      <table className="dosis-table">
        {caption ? <caption className="sr-only">{caption}</caption> : null}
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col} scope="col">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{rows.map(renderRow)}</tbody>
      </table>
    </div>
  );
}
