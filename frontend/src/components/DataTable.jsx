import { useMemo, useRef } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
} from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import './DataTable.css';

export default function DataTable({ data, columns: columnNames, columnsInfo, loading, error }) {
  const tableContainerRef = useRef(null);

  // Transform column names into TanStack Table column definitions
  // MUST be called before any conditional returns (Rules of Hooks)
  const columns = useMemo(() => {
    if (!columnNames || columnNames.length === 0) return [];
    return columnNames.map((colName, idx) => ({
      id: `col_${idx}`,
      accessorFn: (row) => row[idx],
      header: () => {
        const colInfo = columnsInfo?.find((c) => c.name === colName);
        return (
          <div className="column-header">
            <span className="column-name">{colName}</span>
            {colInfo && (
              <span className="column-meta">
                <span className="column-type">{colInfo.type}</span>
                {colInfo.null_count > 0 && (
                  <span className="column-nulls">{colInfo.null_count} nulls</span>
                )}
              </span>
            )}
          </div>
        );
      },
      cell: (info) => {
        const value = info.getValue();
        return value !== null && value !== undefined ? String(value) : '—';
      },
    }));
  }, [columnNames, columnsInfo]);

  // TanStack Table instance - use empty array if no data
  const tableData = data || [];
  const table = useReactTable({
    data: tableData,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const { rows } = table.getRowModel();

  // Row virtualizer for efficient rendering
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => tableContainerRef.current,
    estimateSize: () => 35, // Estimated row height in pixels
    overscan: 10, // Render 10 extra rows above/below viewport
  });

  // NOW we can have conditional returns (after all hooks are called)

  // Loading state
  if (loading) {
    return (
      <div className="data-table-state loading-state">
        <div className="spinner"></div>
        <p>Loading data preview...</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="data-table-state error-state">
        <p className="error-message">{error}</p>
      </div>
    );
  }

  // Empty state
  if (!data || data.length === 0) {
    return (
      <div className="data-table-state empty-state">
        <p>No data available to preview</p>
      </div>
    );
  }

  const virtualRows = rowVirtualizer.getVirtualItems();
  const totalSize = rowVirtualizer.getTotalSize();

  // Calculate padding for virtual scroll positioning
  const paddingTop = virtualRows.length > 0 ? virtualRows[0]?.start || 0 : 0;
  const paddingBottom =
    virtualRows.length > 0
      ? totalSize - (virtualRows[virtualRows.length - 1]?.end || 0)
      : 0;

  return (
    <div className="data-table-wrapper" ref={tableContainerRef}>
      <table className="data-table">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id}>
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {paddingTop > 0 && (
            <tr>
              <td style={{ height: `${paddingTop}px` }} colSpan={columns.length} />
            </tr>
          )}
          {virtualRows.map((virtualRow) => {
            const row = rows[virtualRow.index];
            return (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => {
                  const value = cell.getValue();
                  const isNull = value === null || value === undefined;
                  return (
                    <td key={cell.id} className={isNull ? 'null-cell' : ''}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  );
                })}
              </tr>
            );
          })}
          {paddingBottom > 0 && (
            <tr>
              <td style={{ height: `${paddingBottom}px` }} colSpan={columns.length} />
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
