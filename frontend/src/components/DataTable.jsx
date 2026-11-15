/**
 * Generic data table component with empty-state support.
 *
 * @param {string[]}  columns      - Header labels
 * @param {any[]}     rows         - Data items
 * @param {Function}  renderRow    - (item, idx) => <tr>...</tr>
 * @param {string}    [emptyText]  - Text shown when rows is empty
 */
export default function DataTable({
  columns,
  rows,
  renderRow,
  emptyText = "No hay datos",
}) {
  return (
    <div className="table-wrapper table-wrapper--scroll">
      <table className="table-modern">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr className="empty-row">
              <td colSpan={columns.length}>{emptyText}</td>
            </tr>
          ) : (
            rows.map(renderRow)
          )}
        </tbody>
      </table>
    </div>
  );
}
