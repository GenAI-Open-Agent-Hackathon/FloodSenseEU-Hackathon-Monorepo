import type { CacheInfo, RiskAssessment } from "../types";
import { judgePass, judgeReview, judgeStrong } from "./judgeScores";
import { minutesAgo } from "./time";

const cachedSixMinutesAgo: CacheInfo = { source: "cache", cachedAt: minutesAgo(6), ttlSeconds: 30 * 60 };

/** Risk assessments keyed by location id. MOCK scenarios, not real forecasts. */
export const riskByLocation: Record<string, RiskAssessment> = {
  "bad-neuenahr-ahrweiler": {
    locationId: "bad-neuenahr-ahrweiler",
    level: "high",
    score: 74,
    horizonHours: 24,
    headline: "The Ahr is rising fast upstream. Low-lying streets near the river may flood tonight.",
    claims: [
      { id: "ahr-1", text: "The Ahr at Altenahr has passed its first warning threshold and is still rising.", citationIds: ["cit-rlp-altenahr"] },
      { id: "ahr-2", text: "About 62 mm of rain is forecast over the upper Ahr catchment in the next 24 hours, most of it in the next 12.", citationIds: ["cit-openmeteo-ahr"] },
      { id: "ahr-3", text: "Water from upstream usually reaches Bad Neuenahr-Ahrweiler a few hours later; the downstream gauge is already following the rise.", citationIds: ["cit-rlp-bodendorf", "cit-eval-ahr-2021"] },
      { id: "ahr-4", text: "Ensemble forecasts show an elevated chance of a 5-year flood on Rhine tributaries.", citationIds: ["cit-efas-rhine"] },
    ],
    actions: [
      { id: "a1", title: "Move vehicles out of underground garages", detail: "Park on higher ground away from the riverbank before evening.", urgency: "now" },
      { id: "a2", title: "Protect basements", detail: "Move valuables and electrical devices upstairs; close backflow valves if fitted.", urgency: "today" },
      { id: "a3", title: "Follow official warnings", detail: "Official warnings from the authorities always take priority over this service.", urgency: "now" },
    ],
    judge: judgePass,
    cache: { source: "cache", cachedAt: minutesAgo(4), ttlSeconds: 15 * 60 },
  },
  cologne: {
    locationId: "cologne",
    level: "low",
    score: 28,
    horizonHours: 48,
    headline: "The Rhine is slightly higher than usual but far below flood level. No action needed.",
    claims: [
      { id: "cgn-1", text: "The Rhine at Cologne is rising slowly and remains well below the first flood mark.", citationIds: ["cit-pegel-koeln"] },
      { id: "cgn-2", text: "Upstream at Bonn the level has been steady for 24 hours.", citationIds: ["cit-pegel-bonn"] },
      { id: "cgn-3", text: "No flood warnings are in force for the Cologne district.", citationIds: ["cit-nrw-portal"] },
    ],
    actions: [
      { id: "a1", title: "No action needed", detail: "Check again if heavy rain is forecast for the Sieg or Ahr catchments.", urgency: "prepare" },
      { id: "a2", title: "Know your flood zone", detail: "Look up whether your street lies in a mapped flood hazard area.", urgency: "prepare" },
    ],
    judge: judgeStrong,
    cache: cachedSixMinutesAgo,
  },
  passau: {
    locationId: "passau",
    level: "moderate",
    score: 55,
    horizonHours: 48,
    headline: "Danube and Inn are both rising. Riverside areas of the old town may see minor flooding tomorrow.",
    claims: [
      { id: "pas-1", text: "The Danube at Passau is rising and is expected to approach reporting level 1 within a day.", citationIds: ["cit-hnd-passau"] },
      { id: "pas-2", text: "The Inn carries elevated discharge from snowmelt and recent rain.", citationIds: ["cit-hnd-inn"] },
      { id: "pas-3", text: "Around 35 mm of rain is forecast over the Inn catchment in the next 48 hours.", citationIds: ["cit-openmeteo-passau"] },
    ],
    actions: [
      { id: "a1", title: "Prepare for riverside closures", detail: "Expect closures of riverside car parks and promenades.", urgency: "today" },
      { id: "a2", title: "Check flood barriers", detail: "If you have mobile barriers, check they are complete and accessible.", urgency: "prepare" },
    ],
    judge: judgeReview,
    cache: cachedSixMinutesAgo,
  },
  valencia: {
    locationId: "valencia",
    level: "severe",
    score: 91,
    horizonHours: 12,
    headline: "Intense rain is turning dry riverbeds into torrents. Avoid ramblas, underpasses and garages now.",
    claims: [
      { id: "vlc-1", text: "Flow in the Rambla del Poyo has risen sharply within two hours.", citationIds: ["cit-saih-poyo"] },
      { id: "vlc-2", text: "Hourly rainfall above 40 mm/h is forecast for the coastal plain west of Valencia this evening.", citationIds: ["cit-openmeteo-valencia"] },
      { id: "vlc-3", text: "Ephemeral channels can become dangerous faster than official warnings reach residents.", citationIds: ["cit-eval-valencia-2024"] },
    ],
    actions: [
      { id: "a1", title: "Do not drive through water", detail: "Never cross flooded roads, fords or underpasses, even in a large vehicle.", urgency: "now" },
      { id: "a2", title: "Stay away from ramblas", detail: "Dry riverbeds can flood within minutes after rain upstream.", urgency: "now" },
      { id: "a3", title: "Go to a higher floor", detail: "If water enters your street, move up, not down to garages or basements.", urgency: "now" },
    ],
    judge: judgeStrong,
    cache: { source: "live", cachedAt: minutesAgo(0), ttlSeconds: 5 * 60 },
  },
};
