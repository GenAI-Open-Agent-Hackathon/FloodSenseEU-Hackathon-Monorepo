import { describe, expect, it } from "vitest";
import { headerSubtitle, replayBarView, type EventId } from "./events";
import { CITIZEN_PAGES, INSURER_PAGES, type DeskRoute } from "./route";

const val = { date: "2024-10-29", pointId: "VAL01", points: [{ point_id: "VAL01", name: "Paiporta centre" }] };
const ahrSel = { date: "2021-07-14", pointId: "AHR04" };
const routes: DeskRoute[] = [
  ...CITIZEN_PAGES.map((page) => ({ role: "citizen" as const, page })),
  ...INSURER_PAGES.map((page) => ({ role: "insurer" as const, page })),
];
const events: EventId[] = ["EMSR517", "EMSR773"];

describe("header and replay strip agree", () => {
  for (const route of routes) {
    for (const eventId of events) {
      for (const playing of [false, true]) {
        it(`${route.role}/${route.page} on ${eventId}${playing ? " playing" : ""}`, () => {
          const header = headerSubtitle(route, eventId);
          const bar = replayBarView(route, eventId, val, ahrSel, playing);
          if (route.page === "now") {
            expect(header).toMatch(/^Live/);
            return;
          }
          if (header.includes("EMSR517")) {
            expect(bar.place.startsWith("AHR")).toBe(true);
            expect(bar.date).toBe(ahrSel.date);
          } else {
            expect(header).toBe("Valencia replay · EMSR773");
            expect(bar.place.startsWith("VAL")).toBe(true);
            expect(bar.date).toBe(val.date);
          }
        });
      }
    }
  }

  it("citizen Overview on the Ahr selection names Valencia, as the strip shows Paiporta", () => {
    const route: DeskRoute = { role: "citizen", page: "overview" };
    expect(headerSubtitle(route, "EMSR517")).toBe("Valencia replay · EMSR773");
    expect(replayBarView(route, "EMSR517", val, ahrSel, false).place).toBe("VAL01 Paiporta centre");
  });
});
