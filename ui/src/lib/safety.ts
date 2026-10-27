/**
 * General safety guidance a citizen sees before any reviewed, tailored step.
 * Not written for the UI: CITIZEN_ADVICE is verbatim the advice the agents already append to every
 * citizen answer (agents/floodsense_agents/live.py, CITIZEN_ADVICE). safety.test.ts fails if the two drift.
 * No warning-service URLs are in the app, so none are linked here.
 */
export const SAFETY_HEADLINE = "Follow your official warning service";

export const CITIZEN_ADVICE =
  "What to do: follow the official warnings (Germany: Hochwassermeldedienst of your Land, " +
  "DWD, NINA app; Spain: AEMET, ES-Alert, Protección Civil); keep away from riverbanks, " +
  "underpasses and cellars; call 112 in an emergency.";

export const CITIZEN_ADVICE_SOURCE = "Same advice the FloodSense agents give with every citizen answer";

export const GATE_LINE = "A tailored step from our agents appears here after a person checks it.";
