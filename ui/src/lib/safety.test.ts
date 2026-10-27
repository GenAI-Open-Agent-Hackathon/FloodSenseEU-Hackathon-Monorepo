import { describe, expect, it } from "vitest";
import livePy from "../../../agents/floodsense_agents/live.py?raw";
import { CITIZEN_ADVICE, EMERGENCY_LINE, WARNING_LINKS, warningCountriesFor } from "./safety";

const ALLOWLIST = [
  "https://www.bbk.bund.de/DE/Warnung-Vorsorge/Warn-App-NINA/warn-app-nina_node.html",
  "https://warnung.bund.de",
  "https://www.dwd.de/DE/wetter/warnungen_gemeinden/warnWetter_node.html",
  "https://www.hochwasserzentralen.de",
  "https://www.proteccioncivil.es",
  "https://www.aemet.es/es/eltiempo/prediccion/avisos",
  "https://www.112cv.gva.es",
];

describe("citizen safety guidance", () => {
  it("is verbatim the agents' CITIZEN_ADVICE, not new advice", () => {
    const block = /CITIZEN_ADVICE = \(\r?\n((?:\s*"[^"]*"\r?\n)+)\)/.exec(livePy)?.[1] ?? "";
    const joined = [...block.matchAll(/"([^"]*)"/g)].map((m) => m[1]).join("");
    expect(joined).toBe(CITIZEN_ADVICE);
  });

  it("links only the approved warning-service URLs, each once", () => {
    const urls = [...WARNING_LINKS.de.links, ...WARNING_LINKS.es.links].map((l) => l.url);
    expect([...urls].sort()).toEqual([...ALLOWLIST].sort());
    expect(WARNING_LINKS.de.links.map((l) => l.url)).toEqual(ALLOWLIST.slice(0, 4));
    expect(WARNING_LINKS.es.links.map((l) => l.url)).toEqual(ALLOWLIST.slice(4));
  });

  it("says to call 112", () => {
    expect(EMERGENCY_LINE).toBe("In an emergency call 112.");
  });
});

describe("warningCountriesFor", () => {
  it("gives Spain for Valencia points", () => {
    expect(warningCountriesFor("VAL01", "Paiporta centre")).toEqual(["es"]);
    expect(warningCountriesFor("VAL03", "Sedaví")).toEqual(["es"]);
  });
  it("gives Germany for German gauges and places", () => {
    expect(warningCountriesFor("AHR01", "Altenahr")).toEqual(["de"]);
    expect(warningCountriesFor("KÖLN")).toEqual(["de"]);
    expect(warningCountriesFor(null, "Bonn")).toEqual(["de"]);
  });
  it("gives both, grouped, when unclear", () => {
    expect(warningCountriesFor("XYZ99")).toEqual(["de", "es"]);
    expect(warningCountriesFor(undefined)).toEqual(["de", "es"]);
    expect(warningCountriesFor("Paiporta", "Köln")).toEqual(["de", "es"]);
  });
});
