import { createElement as h, type ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ThemeProvider } from "@mui/material/styles";
import { describe, expect, it } from "vitest";
import { muiTheme } from "../../lib/muiTheme";
import { DataTable, EmptyState, LoadingState, PageHeader, SectionCard, StatCard, StatusChip } from "./index";

const html = (node: ReactElement) => renderToStaticMarkup(h(ThemeProvider, { theme: muiTheme }, node));

describe("shared UI components", () => {
  it("PageHeader renders title, subtitle and actions", () => {
    const out = html(h(PageHeader, { title: "Right now", subtitle: "Updated", actions: h("button", null, "Refresh") }));
    expect(out).toContain("<h2");
    expect(out).toContain("Right now");
    expect(out).toContain("Updated");
    expect(out).toContain("Refresh");
  });
  it("StatusChip always shows the word, not only colour", () => {
    const out = html(h(StatusChip, { tone: "elevated", label: "Elevated (model)" }));
    expect(out).toContain("Elevated (model)");
    expect(out).toContain('data-tone="elevated"');
  });
  it("SectionCard is a region named by its heading", () => {
    const out = html(h(SectionCard, { title: "Europe", children: "body" }));
    const id = /aria-labelledby="([^"]+)"/.exec(out)?.[1];
    expect(id).toBeTruthy();
    expect(out).toContain(`id="${id}"`);
  });
  it("StatCard pairs label and value", () => {
    const out = html(h(StatCard, { label: "Sources", value: "12" }));
    expect(out).toMatch(/<dt[^>]*>Sources<\/dt>/);
    expect(out).toMatch(/<dd[^>]*>12<\/dd>/);
  });
  it("DataTable has an accessible name, sticky header and rows", () => {
    type Row = { id: string; n: string };
    const out = html(h(DataTable<Row>, { caption: "Gauges", rows: [{ id: "a", n: "Köln" }], rowKey: (r) => r.id, columns: [{ key: "n", header: "Name", render: (r) => r.n }], dense: true }));
    expect(out).toContain('aria-label="Gauges"');
    expect(out).toContain("MuiTable-stickyHeader");
    expect(out).toContain("Köln");
  });
  it("EmptyState and LoadingState are status regions", () => {
    expect(html(h(EmptyState, { title: "Nothing here" }))).toContain('role="status"');
    const out = html(h(LoadingState, { what: "gauges" }));
    expect(out).toContain('role="status"');
    expect(out).toContain("Loading gauges");
  });
});
