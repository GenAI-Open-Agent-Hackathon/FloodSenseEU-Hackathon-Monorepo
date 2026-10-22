// GENERATED mock data. Quotes are SAMPLE text written for this mock, not
// verbatim extracts. Hashes are real SHA-256 digests of the quote strings.
import type { Citation } from "../types";
import { minutesAgo, today } from "./time";

export const citations: Citation[] = [
  {
    id: "cit-rlp-altenahr",
    url: "https://www.hochwasser.rlp.de",
    title: "Hochwassermeldedienst Rheinland-Pfalz: gauge Altenahr (Ahr)",
    publisher: "Landesamt für Umwelt Rheinland-Pfalz",
    locator: {
      section: "Gauge detail: Altenahr",
      paragraph: 1
    },
    quote: "SAMPLE: The Altenahr gauge reports a rising water level that has passed the first warning threshold within the last six hours.",
    license: "Open data (licence terms to be confirmed before use)",
    storage: "full-text",
    zetaris: {
      dataset: "rlp_lfu.gauges.levels_15min",
      query: "SELECT station_id, measured_at, level_cm\nFROM rlp_lfu.gauges.levels_15min\nWHERE station_id = 'ALTENAHR'\n  AND measured_at >= now() - INTERVAL '24' HOUR\nORDER BY measured_at",
      rowCount: 96,
      executedAt: minutesAgo(7)
    },
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "19b2c82e51d3"
  },
  {
    id: "cit-rlp-bodendorf",
    url: "https://www.hochwasser.rlp.de",
    title: "Hochwassermeldedienst Rheinland-Pfalz: gauge Bad Bodendorf (Ahr)",
    publisher: "Landesamt für Umwelt Rheinland-Pfalz",
    locator: {
      section: "Gauge detail: Bad Bodendorf",
      paragraph: 1
    },
    quote: "SAMPLE: Downstream at Bad Bodendorf the level is still below the warning threshold but follows the upstream rise with a delay of a few hours.",
    license: "Open data (licence terms to be confirmed before use)",
    storage: "full-text",
    zetaris: {
      dataset: "rlp_lfu.gauges.levels_15min",
      query: "SELECT station_id, measured_at, level_cm\nFROM rlp_lfu.gauges.levels_15min\nWHERE station_id = 'BAD_BODENDORF'\n  AND measured_at >= now() - INTERVAL '24' HOUR\nORDER BY measured_at",
      rowCount: 96,
      executedAt: minutesAgo(7)
    },
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "192d83038339"
  },
  {
    id: "cit-openmeteo-ahr",
    url: "https://open-meteo.com/en/docs",
    title: "Open-Meteo Forecast API: hourly precipitation, Ahr valley",
    publisher: "Open-Meteo",
    locator: {
      section: "Hourly variables: precipitation"
    },
    quote: "SAMPLE: Forecast accumulated precipitation for the next 24 hours over the upper Ahr catchment is 62 mm, concentrated in the next 12 hours.",
    license: "CC BY 4.0",
    storage: "full-text",
    zetaris: {
      dataset: "openmeteo.forecast.hourly_precip",
      query: "SELECT SUM(precipitation_mm) AS precip_24h_mm\nFROM openmeteo.forecast.hourly_precip\nWHERE cell_id IN (SELECT cell_id FROM geo.catchments WHERE name = 'Ahr')\n  AND valid_at BETWEEN now() AND now() + INTERVAL '24' HOUR",
      rowCount: 1,
      executedAt: minutesAgo(7)
    },
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "83d84edac16c"
  },
  {
    id: "cit-efas-rhine",
    url: "https://www.efas.eu",
    title: "Copernicus EFAS: medium-range flood forecast, Rhine basin",
    publisher: "Copernicus Emergency Management Service",
    locator: {
      section: "Forecast overview",
      page: 2,
      paragraph: 3,
      lines: "1-3"
    },
    quote: "SAMPLE: Ensemble members indicate an elevated probability of exceeding the 5-year return period on Rhine tributaries in the coming 48 hours.",
    license: "Copernicus licence (access terms apply)",
    storage: "pointer-and-quote",
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "3bf6adc43874"
  },
  {
    id: "cit-eval-ahr-2021",
    url: "repo://docs/eval/ahr-nrw-2021.md",
    title: "FloodSense eval set: Ahr / NRW, July 2021",
    publisher: "FloodSense EU team (internal)",
    locator: {
      section: "2. Event timeline",
      page: 1,
      paragraph: 4
    },
    quote: "SAMPLE: The eval case records that the steepest rise at upper Ahr gauges preceded peak damage downstream by several hours.",
    license: "Internal team document",
    storage: "full-text",
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "0021e83b89d3"
  },
  {
    id: "cit-pegel-koeln",
    url: "https://www.pegelonline.wsv.de",
    title: "PEGELONLINE: gauge KÖLN (Rhein), water level",
    publisher: "Wasserstraßen- und Schifffahrtsverwaltung des Bundes (WSV)",
    locator: {
      section: "Station KÖLN: current measurement"
    },
    quote: "SAMPLE: The Cologne gauge shows a slowly rising level that remains well below the first flood mark.",
    license: "DL-DE->Zero-2.0 (no attribution required; source: © www.pegelonline.wsv.de)",
    storage: "full-text",
    zetaris: {
      dataset: "pegelonline.public.water_levels",
      query: "SELECT station_name, timestamp, value_cm\nFROM pegelonline.public.water_levels\nWHERE station_name = 'KÖLN'\n  AND timestamp >= now() - INTERVAL '24' HOUR\nORDER BY timestamp",
      rowCount: 96,
      executedAt: minutesAgo(7)
    },
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "d37dfe20fac1"
  },
  {
    id: "cit-pegel-bonn",
    url: "https://www.pegelonline.wsv.de",
    title: "PEGELONLINE: gauge BONN (Rhein), water level",
    publisher: "Wasserstraßen- und Schifffahrtsverwaltung des Bundes (WSV)",
    locator: {
      section: "Station BONN: current measurement"
    },
    quote: "SAMPLE: The Bonn gauge level is steady over the last 24 hours.",
    license: "DL-DE->Zero-2.0 (no attribution required; source: © www.pegelonline.wsv.de)",
    storage: "full-text",
    zetaris: {
      dataset: "pegelonline.public.water_levels",
      query: "SELECT station_name, timestamp, value_cm\nFROM pegelonline.public.water_levels\nWHERE station_name = 'BONN'\n  AND timestamp >= now() - INTERVAL '24' HOUR\nORDER BY timestamp",
      rowCount: 96,
      executedAt: minutesAgo(7)
    },
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "38f9a464b041"
  },
  {
    id: "cit-nrw-portal",
    url: "https://hochwasserportal.nrw.de",
    title: "Hochwasserportal NRW: regional overview, Cologne district",
    publisher: "Hochwasserportal NRW (state flood portal)",
    locator: {
      section: "Regional overview",
      paragraph: 2
    },
    quote: "SAMPLE: No flood warnings are currently in force for the Cologne district; smaller tributaries are being monitored.",
    license: "Open data (licence terms to be confirmed before use)",
    storage: "pointer-and-quote",
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "67b1d945e7ea"
  },
  {
    id: "cit-hnd-passau",
    url: "https://www.hnd.bayern.de",
    title: "Hochwassernachrichtendienst Bayern: gauge Passau (Donau)",
    publisher: "Bayerisches Landesamt für Umwelt",
    locator: {
      section: "Gauge detail: Passau / Donau",
      paragraph: 1
    },
    quote: "SAMPLE: The Danube at Passau is rising and is expected to approach reporting level 1 within the next day.",
    license: "Open data (licence terms to be confirmed before use)",
    storage: "full-text",
    zetaris: {
      dataset: "by_lfu.hnd.levels_hourly",
      query: "SELECT gauge_id, measured_at, level_cm\nFROM by_lfu.hnd.levels_hourly\nWHERE gauge_id = 'PASSAU_DONAU'\n  AND measured_at >= now() - INTERVAL '24' HOUR\nORDER BY measured_at",
      rowCount: 24,
      executedAt: minutesAgo(7)
    },
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "fca243320a88"
  },
  {
    id: "cit-hnd-inn",
    url: "https://www.hnd.bayern.de",
    title: "Hochwassernachrichtendienst Bayern: gauge Passau-Ingling (Inn)",
    publisher: "Bayerisches Landesamt für Umwelt",
    locator: {
      section: "Gauge detail: Passau-Ingling / Inn",
      paragraph: 1
    },
    quote: "SAMPLE: The Inn at Passau-Ingling carries elevated discharge from Alpine snowmelt and recent rain.",
    license: "Open data (licence terms to be confirmed before use)",
    storage: "full-text",
    zetaris: {
      dataset: "by_lfu.hnd.levels_hourly",
      query: "SELECT gauge_id, measured_at, level_cm\nFROM by_lfu.hnd.levels_hourly\nWHERE gauge_id = 'PASSAU_INGLING_INN'\n  AND measured_at >= now() - INTERVAL '24' HOUR\nORDER BY measured_at",
      rowCount: 24,
      executedAt: minutesAgo(7)
    },
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "38eb515ad788"
  },
  {
    id: "cit-openmeteo-passau",
    url: "https://open-meteo.com/en/docs",
    title: "Open-Meteo Forecast API: hourly precipitation, Inn and Danube catchments",
    publisher: "Open-Meteo",
    locator: {
      section: "Hourly variables: precipitation"
    },
    quote: "SAMPLE: Forecast precipitation over the Inn catchment is 35 mm in the next 48 hours.",
    license: "CC BY 4.0",
    storage: "full-text",
    zetaris: {
      dataset: "openmeteo.forecast.hourly_precip",
      query: "SELECT SUM(precipitation_mm) AS precip_48h_mm\nFROM openmeteo.forecast.hourly_precip\nWHERE cell_id IN (SELECT cell_id FROM geo.catchments WHERE name = 'Inn')\n  AND valid_at BETWEEN now() AND now() + INTERVAL '48' HOUR",
      rowCount: 1,
      executedAt: minutesAgo(7)
    },
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "29e735665a58"
  },
  {
    id: "cit-saih-poyo",
    url: "https://saih.chj.es",
    title: "SAIH Júcar: Rambla del Poyo, real-time hydrological data",
    publisher: "Confederación Hidrográfica del Júcar",
    locator: {
      section: "Rambla del Poyo: current flow"
    },
    quote: "SAMPLE: Flow in the Rambla del Poyo has increased sharply within two hours after intense local rainfall.",
    license: "Open data (licence terms to be confirmed before use)",
    storage: "pointer-and-quote",
    zetaris: {
      dataset: "chj_saih.realtime.flows_5min",
      query: "SELECT station_id, measured_at, flow_m3s, level_cm\nFROM chj_saih.realtime.flows_5min\nWHERE station_id = 'POYO_RIBAROJA'\n  AND measured_at >= now() - INTERVAL '24' HOUR\nORDER BY measured_at",
      rowCount: 288,
      executedAt: minutesAgo(7)
    },
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "3f403422ce84"
  },
  {
    id: "cit-openmeteo-valencia",
    url: "https://open-meteo.com/en/docs",
    title: "Open-Meteo Forecast API: hourly precipitation, Valencia province",
    publisher: "Open-Meteo",
    locator: {
      section: "Hourly variables: precipitation"
    },
    quote: "SAMPLE: Forecast hourly rainfall rates above 40 mm/h are indicated for the coastal plain west of Valencia this evening.",
    license: "CC BY 4.0",
    storage: "full-text",
    zetaris: {
      dataset: "openmeteo.forecast.hourly_precip",
      query: "SELECT MAX(precipitation_mm) AS max_hourly_mm\nFROM openmeteo.forecast.hourly_precip\nWHERE cell_id IN (SELECT cell_id FROM geo.provinces WHERE name = 'Valencia')\n  AND valid_at BETWEEN now() AND now() + INTERVAL '12' HOUR",
      rowCount: 1,
      executedAt: minutesAgo(7)
    },
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "9ee2528303fe"
  },
  {
    id: "cit-eval-valencia-2024",
    url: "repo://docs/eval/valencia-2024.md",
    title: "FloodSense eval set: Valencia, October 2024",
    publisher: "FloodSense EU team (internal)",
    locator: {
      section: "3. Lessons for alerting",
      page: 2,
      paragraph: 1
    },
    quote: "SAMPLE: The eval case highlights that ephemeral channels (ramblas) can turn dangerous faster than official warnings reach residents.",
    license: "Internal team document",
    storage: "full-text",
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "d2557cf322a4"
  },
  {
    id: "cit-pegelonline-sample",
    url: "https://www.pegelonline.wsv.de",
    title: "PEGELONLINE: federal waterway gauges (sample values while the live feed is unavailable)",
    publisher: "Wasserstraßen- und Schifffahrtsverwaltung des Bundes (WSV)",
    locator: {
      section: "Gauge overview"
    },
    quote: "SAMPLE: The live PEGELONLINE feed could not be reached, so the map shows invented sample levels for federal waterway gauges.",
    license: "DL-DE->Zero-2.0 (no attribution required; source: © www.pegelonline.wsv.de)",
    storage: "full-text",
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "307e0dece9eb"
  },
  {
    id: "cit-hnd-portal",
    url: "https://www.hnd.bayern.de",
    title: "Hochwassernachrichtendienst Bayern: gauge overview",
    publisher: "Bayerisches Landesamt für Umwelt (HND)",
    locator: {
      section: "Gauge overview map"
    },
    quote: "SAMPLE: State gauges on Isar and Inn are shown with invented levels until the HND data-sharing terms are checked.",
    license: "Open data (licence terms to be confirmed before use)",
    storage: "pointer-and-quote",
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "fcc07da73f56"
  },
  {
    id: "cit-replay-ahr-2021",
    url: "repo://docs/eval/ahr-nrw-2021.md",
    title: "FloodSense eval set: Ahr, July 2021, reconstructed hourly levels",
    publisher: "FloodSense EU team (internal)",
    locator: {
      section: "Appendix A: reconstructed hourly levels",
      page: 6
    },
    quote: "SAMPLE: The hourly levels in this appendix are a reconstruction for demonstration only. They are not official measurements; several gauges failed during the event.",
    license: "Internal team document",
    storage: "full-text",
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "ba702eb78d64"
  },
  {
    id: "cit-replay-valencia-2024",
    url: "repo://docs/eval/valencia-2024.md",
    title: "FloodSense eval set: Valencia, October 2024, reconstructed hourly levels",
    publisher: "FloodSense EU team (internal)",
    locator: {
      section: "Appendix A: reconstructed hourly levels",
      page: 5
    },
    quote: "SAMPLE: The hourly levels in this appendix are a reconstruction for demonstration only and are not SAIH Júcar measurements.",
    license: "Internal team document",
    storage: "full-text",
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "da837a3faca7"
  },
  {
    id: "cit-forecast-band",
    url: "repo://docs/models/forecast-band.md",
    title: "FloodSense forecast band (mock model output)",
    publisher: "FloodSense EU team (internal)",
    locator: {
      section: "Output: 10th/50th/90th percentile levels"
    },
    quote: "SAMPLE: The band shows the 10th to 90th percentile of the ensemble level forecast. In this mock it is generated from the last observed level and is not a real forecast.",
    license: "Internal team document",
    storage: "full-text",
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "ff7ee8c34190"
  },
  {
    id: "cit-news-ahr-anniversary",
    url: "https://news.example/ahr-flood-anniversary",
    title: "Three years after the Ahr flood (fictional news article)",
    publisher: "Example Regional News (fictional)",
    locator: {
      section: "Paragraph 3"
    },
    quote: "SAMPLE: Copyrighted article. Only a pointer and a short quote may be stored; the full text is not ingested.",
    license: "All rights reserved (pointer and short quote only)",
    storage: "pointer-and-quote",
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "4fd9a8e5e54a"
  },
  {
    id: "cit-portfolio",
    url: "zetaris://insurer_demo.portfolio.sites",
    title: "Demo insurer portfolio: insured sites and tiers",
    publisher: "Demo insurer (fictional)",
    locator: {
      section: "Table: sites"
    },
    quote: "SAMPLE: Portfolio extract listing insured sites, policy counts and insured values joined to the nearest gauge.",
    license: "Fictional demo data",
    storage: "full-text",
    zetaris: {
      dataset: "insurer_demo.portfolio.sites",
      query: "SELECT s.site_id, s.city, s.policy_count, s.insured_value_eur, r.tier\nFROM insurer_demo.portfolio.sites s\nJOIN floodsense.risk.latest_tiers r ON r.site_id = s.site_id",
      rowCount: 12,
      executedAt: minutesAgo(7)
    },
    accessedAt: today,
    quoteIsSample: true,
    contentHash: "0ae713703495"
  },
];

export const citationsById: ReadonlyMap<string, Citation> = new Map(
  citations.map((citation) => [citation.id, citation]),
);
