import { describe, expect, it } from "vitest";
import { DESK_NAV, insurerHome, pageLabel, parseHash, routeHref, type DeskRoute } from "./route";

describe("parseHash", () => {
  it("opens Approvals when the hash is empty and a decision is pending", () => {
    expect(parseHash("")).toEqual({ role: "insurer", page: "approvals" });
    expect(parseHash("#")).toEqual({ role: "insurer", page: "approvals" });
    expect(parseHash("#/")).toEqual({ role: "insurer", page: "approvals" });
    expect(parseHash("   ")).toEqual({ role: "insurer", page: "approvals" });
  });

  it("opens Portfolio as the insurer home once nothing is pending", () => {
    expect(parseHash("", false)).toEqual({ role: "insurer", page: "portfolio" });
    expect(parseHash("#/insurer", false)).toEqual({ role: "insurer", page: "portfolio" });
    expect(parseHash("#/insurer/approvals", false)).toEqual({ role: "insurer", page: "approvals" });
    expect(insurerHome(true)).toBe("approvals");
    expect(insurerHome(false)).toBe("portfolio");
  });

  it("treats a role with no page as that desk's home", () => {
    expect(parseHash("#/insurer")).toEqual({ role: "insurer", page: "approvals" });
    expect(parseHash("#/citizen")).toEqual({ role: "citizen", page: "overview" });
    expect(parseHash("#/citizen/")).toEqual({ role: "citizen", page: "overview" });
    expect(parseHash("#citizen")).toEqual({ role: "citizen", page: "overview" });
  });

  it("reads every approved page", () => {
    expect(parseHash("#/citizen/area")).toEqual({ role: "citizen", page: "area" });
    expect(parseHash("#/citizen/actions")).toEqual({ role: "citizen", page: "actions" });
    expect(parseHash("#/citizen/evidence")).toEqual({ role: "citizen", page: "evidence" });
    expect(parseHash("#/citizen/overview")).toEqual({ role: "citizen", page: "overview" });
    expect(parseHash("#/insurer/approvals")).toEqual({ role: "insurer", page: "approvals" });
    expect(parseHash("#/insurer/portfolio")).toEqual({ role: "insurer", page: "portfolio" });
    expect(parseHash("#/insurer/sites")).toEqual({ role: "insurer", page: "sites" });
    expect(parseHash("#/insurer/alerts")).toEqual({ role: "insurer", page: "alerts" });
    expect(parseHash("#/insurer/review")).toEqual({ role: "insurer", page: "review" });
  });

  it("sends a #36 hash to the page that now holds its content", () => {
    expect(parseHash("#/citizen/place")).toEqual({ role: "citizen", page: "area" });
    expect(parseHash("#/citizen/rain")).toEqual({ role: "citizen", page: "area" });
    expect(parseHash("#/insurer/overview")).toEqual({ role: "insurer", page: "portfolio" });
    expect(parseHash("#/insurer/map")).toEqual({ role: "insurer", page: "sites" });
    expect(parseHash("#/insurer/point")).toEqual({ role: "insurer", page: "sites" });
    expect(parseHash("#/insurer/book")).toEqual({ role: "insurer", page: "portfolio" });
    expect(parseHash("#/insurer/sources")).toEqual({ role: "insurer", page: "review" });
  });

  it("sends an unknown page back to that desk's home", () => {
    expect(parseHash("#/citizen/map")).toEqual({ role: "citizen", page: "overview" });
    expect(parseHash("#/citizen/nope")).toEqual({ role: "citizen", page: "overview" });
    expect(parseHash("#/insurer/area")).toEqual({ role: "insurer", page: "approvals" });
    expect(parseHash("#/insurer/review/extra")).toEqual({ role: "insurer", page: "approvals" });
    expect(parseHash("#/citizen/area/more")).toEqual({ role: "citizen", page: "overview" });
    expect(parseHash("#/citizen/constructor")).toEqual({ role: "citizen", page: "overview" });
    expect(parseHash("#/insurer/toString", false)).toEqual({ role: "insurer", page: "portfolio" });
  });

  it("sends an unknown role to the insurer home", () => {
    expect(parseHash("#/other")).toEqual({ role: "insurer", page: "approvals" });
    expect(parseHash("#/Citizen")).toEqual({ role: "insurer", page: "approvals" });
    expect(parseHash("#/map", false)).toEqual({ role: "insurer", page: "portfolio" });
  });

  it("round-trips every nav item whether or not a decision is pending", () => {
    const routes: DeskRoute[] = [
      ...DESK_NAV.citizen.map((item) => ({ role: "citizen" as const, page: item.page })),
      ...DESK_NAV.insurer.map((item) => ({ role: "insurer" as const, page: item.page })),
    ];
    for (const route of routes) {
      expect(parseHash(routeHref(route.role, route.page))).toEqual(route);
      expect(parseHash(routeHref(route.role, route.page), false)).toEqual(route);
    }
  });
});

describe("DESK_NAV", () => {
  it("matches the approved IA", () => {
    expect(DESK_NAV.citizen.map((item) => item.label)).toEqual(["Overview", "My area", "What to do", "Evidence"]);
    expect(DESK_NAV.insurer.map((item) => item.label)).toEqual([
      "Approvals",
      "Portfolio",
      "Sites / map",
      "Alerts",
      "Review",
    ]);
  });

  it("labels a route from the nav table", () => {
    expect(pageLabel({ role: "citizen", page: "actions" })).toBe("What to do");
    expect(pageLabel({ role: "insurer", page: "sites" })).toBe("Sites / map");
  });
});
