import { useMemo, useState } from 'react';

const ROW_HEIGHT = 42;
const VIEWPORT_HEIGHT = 420;

export function VirtualizedTable({ items, columns }) {
  const [scrollTop, setScrollTop] = useState(0);
  const visible = useMemo(() => {
    const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - 4);
    const count = Math.ceil(VIEWPORT_HEIGHT / ROW_HEIGHT) + 8;
    return { start, rows: items.slice(start, start + count) };
  }, [items, scrollTop]);

  return (
    <div
      className="virtualized-table"
      style={{ height: VIEWPORT_HEIGHT, overflow: 'auto' }}
      onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
      data-testid="virtualized-table"
    >
      <table className="data-table">
        <thead>
          <tr>{columns.map((column) => <th key={column.key}>{column.label}</th>)}</tr>
        </thead>
        <tbody style={{ position: 'relative', height: items.length * ROW_HEIGHT }}>
          <tr style={{ height: visible.start * ROW_HEIGHT }} aria-hidden="true" />
          {visible.rows.map((item) => (
            <tr key={item.id || item.name} style={{ height: ROW_HEIGHT }}>
              {columns.map((column) => <td key={column.key}>{column.render(item)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
