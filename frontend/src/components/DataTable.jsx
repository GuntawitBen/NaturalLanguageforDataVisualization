import './DataTable.css';

export default function DataTable({ data, columns, columnsInfo, loading, error, maxRows = 100 }) {
  if (loading) {
    return (
      <div className="data-table-state loading-state">
        <div className="spinner"></div>
        <p>Loading data preview...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="data-table-state error-state">
        <p className="error-message">{error}</p>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="data-table-state empty-state">
        <p>No data available to preview</p>
      </div>
    );
  }

  const displayData = data.slice(0, maxRows);

  return (
    <div className="data-table-wrapper">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col, idx) => {
              const colInfo = columnsInfo?.find(c => c.name === col);
              return (
                <th key={idx}>
                  <div className="column-header">
                    <span className="column-name">{col}</span>
                    {colInfo && (
                      <span className="column-meta">
                        <span className="column-type">{colInfo.type}</span>
                        {colInfo.null_count > 0 && (
                          <span className="column-nulls">{colInfo.null_count} nulls</span>
                        )}
                      </span>
                    )}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {displayData.map((row, rowIdx) => (
            <tr key={rowIdx}>
              {row.map((cell, cellIdx) => (
                <td
                  key={cellIdx}
                  className={cell === null || cell === undefined ? 'null-cell' : ''}
                >
                  {cell !== null && cell !== undefined ? String(cell) : '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
