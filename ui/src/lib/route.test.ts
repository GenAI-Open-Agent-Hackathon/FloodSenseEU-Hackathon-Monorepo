import { describe, expect, it } from "vitest";
import { DESK_NAV, parseHash, routeHref, type DeskRoute } from "./route";

describe("parseHash", () => {
  it("opens the insurer overview when the hash is empty", () => {
    expect(parseHash("")).toEqual({ role: "insurer", page: "overview" });
    expect(parseHash("#")).toEqual({ role: "insurer", page: "overview" });
    expect(parseHash("#/")).toEqual({ role: "insurer", page: "overview" });
    expect(parseHash("   ")).toEqual({ role: "insurer", page: "overview" });
  });

  it("treats a role with no page as that desk's overview", () => {
    expect(parseHash("#/insurer")).toEqual({ role: "insurer", page: "overview" });
    expect(parseHash("#/citizen")).toEqual({ role: "citizen", page: "overview" });
    expect(parseHash("#/citizen/")).toEqual({ role: "citizen", page: "overview" });
    expect(parseHash("#citizen")).toEqual({ role: "citizen", page: "overview" });
  });

  it("reads the approved page for each desk", () => {
    expect(parseHash("#/citizen/place")).toEqual({ role: "citizen", page: "place" });
    expect(parseHash("#/citizen/rain")).toEqual({ role: "citizen", page: "rain" });
    expect(parseHash("#/citizen/overview")).toEqual({ role: "citizen", page: "overview" });
    expect(parseHash("#/insurer/map")).toEqual({ role: "insurer", page: "map" });
    expect(parseHash("#/insurer/point")).toEqual({ role: "insurer", page: "point" });
    expect(parseHash("#/insurer/book")).toEqual({ role: "insurer", page: "book" });
    expect(parseHash("#/insurer/review")).toEqual({ role: "insurer", page: "review" });
    expect(parseHash("#/insurer/sources")).toEqual({ role: "insurer", page: "sources" });
    expect(parseHash("#/insurer/overview")).toEqual({ role: "insurer", page: "overview" });
  });

  it("sends an unknown page back to that desk's overview", () => {
    expect(parseHash("#/citizen/map")).toEqual({ role: "citizen", page: "overview" });
    expect(parseHash("#/citizen/nope")).toEqual({ role: "citizen", page: "overview" });
    expect(parseHash("#/insurer/rain")).toEqual({ role: "insurer", page: "overview" });
    expect(parseHash("#/insurer/review/extra")).toEqual({ role: "insurer", page: "overview" });
    expect(parseHash("#/citizen/place/more")).toEqual({ role: "citizen", page: "overview" });
  });

  it("sends an unknown role to the insurer overview", () => {
    expect(parseHash("#/other")).toEqual({ role: "insurer", page: "overview" });
    expect(parseHash("#/Citizen")).toEqual({ role: "insurer", page: "overview" });
    expect(parseHash("#/map")).toEqual({ role: "insurer", page: "overview" });
  });

  it("round-trips every nav item", () => {
    const routes: DeskRoute[] = [
      ...DESK_NAV.citizen.map((item) => ({ role: "citizen" as const, page: item.page })),
      ...DESK_NAV.insurer.map((item) => ({ role: "insurer" as const, page: item.page })),
    ];
    for (const route of routes) {
      expect(parseHash(routeHref(route.role, route.page))).toEqual(route);
    }
  });
});

describe("DESK_NAV", () => {
  it("matches the approved desks", () => {
    expect(DESK_NAV.citizen.map((item) => item.label)).toEqual(["Overview", "Place", "Rain"]);
    expect(DESK_NAV.insurer.map((item) => item.label)).toEqual([
      "Overview",
      "Map",
      "Point",
      "Book",
      "Review",
      "Sources",
    ]);
  });
});
