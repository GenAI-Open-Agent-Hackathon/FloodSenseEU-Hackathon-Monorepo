import type { ReactNode } from "react";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  align?: "left" | "right";
}

/** Sticky-header table. The wrapper scrolls inside itself (keyboard focusable), so the page never scrolls sideways at 375 px. */
export function DataTable<T>({ columns, rows, rowKey, caption, dense = false, maxHeight = 480 }: { columns: Column<T>[]; rows: T[]; rowKey: (row: T) => string; caption: string; dense?: boolean; maxHeight?: number }) {
  return (
    <TableContainer sx={{ maxHeight, border: 1, borderColor: "divider", borderRadius: 2 }} tabIndex={0} role="region" aria-label={caption}>
      <Table stickyHeader size={dense ? "small" : "medium"}>
        <caption className="sr-only">{caption}</caption>
        <TableHead>
          <TableRow>
            {columns.map((c) => (
              <TableCell key={c.key} align={c.align}>
                {c.header}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={rowKey(row)} hover>
              {columns.map((c) => (
                <TableCell key={c.key} align={c.align}>
                  {c.render(row)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
