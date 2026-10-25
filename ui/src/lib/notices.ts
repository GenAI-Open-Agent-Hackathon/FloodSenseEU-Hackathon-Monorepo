import type { Answer } from "../types/contract";
import type { Notice } from "../types/ui";
import type { DischargeDailyRow } from "../types/views";
import { servingLabel, formatDay } from "./format";
import { datesOf } from "./series";

export function replayNotice(answer: Answer): Notice {
  const serving = servingLabel(answer);
  return {
    id: "replay-loaded",
    tone: "info",
    read: false,
    title: "Replay on the insurer desk",
    body: `The reviewed answer is a fixture with served_from ${answer.served_from}. Its banner says ${serving.text}. It is not a live run.`,
  };
}

/** Shown only while discharge rows are the fixture. Wording comes from those rows. */
export function fixtureDischargeNotice(rows: DischargeDailyRow[]): Notice {
  const points = new Set(rows.map((row) => row.point_id)).size;
  const dates = datesOf(rows);
  const sources = [...new Set(rows.map((row) => row.source))];
  const span =
    dates.length === 0
      ? "no dates"
      : dates.length === 1
        ? formatDay(dates[0])
        : `${formatDay(dates[0])}–${formatDay(dates[dates.length - 1])}`;
  const sourceText = sources.length === 0 ? "no source value" : sources.join(", ");
  return {
    id: "seed-loaded",
    tone: "info",
    read: false,
    title: "Discharge fixture loaded",
    body: `${points} points, ${span}. Source column: ${sourceText}.`,
  };
}
