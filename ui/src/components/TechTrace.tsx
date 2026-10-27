import { useEffect, useId, useState } from "react";
import { fetchPastRuns } from "../api/pastRuns";
import { fetchRunSnapshot } from "../api/liveRun";
import type { RecordedRun } from "../api/replay";
import { DOT_TEXT, type BoxId, type DotState } from "../lib/howItWorks";
import { getAwaitingRunId } from "../lib/lastRun";
import { buildTechTrace, GLOSSARY, type Tile, type TileId } from "../lib/techTrace";
import "../styles/techTrace.css";

function TileDetails({ tile }: { tile: Tile }) {
  return (
    <>
      <p className="tt-gloss">{tile.glossary}</p>
      {tile.details.length > 0 && (
        <dl className="tt-details">
          {tile.details.map((d, i) => (
            <div key={`${d.label}-${i}`}>
              <dt>{d.label}</dt>
              <dd>{d.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </>
  );
}

/** "How this answer was made": the Router line, the Judge result and four sponsor tiles, each opening its detail. */
export function TechTrace({ run, caption }: { run: RecordedRun; caption?: string }) {
  const model = buildTechTrace(run);
  const uid = useId();
  const [open, setOpen] = useState<ReadonlySet<TileId>>(new Set());
  const toggle = (id: TileId) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  return (
    <section className="tt" aria-label="How this answer was made">
      <p className="tt-title">How this answer was made{caption ? ` · ${caption}` : ""}</p>
      {(model.routerLine || model.judgeLine) && (
        <p className="tt-line">
          {model.routerLine}
          {model.routerLine && model.judgeLine ? " · " : ""}
          {model.judgeLine}
        </p>
      )}
      <ul className="tt-tiles">
        {model.tiles.map((tile) => {
          const expanded = open.has(tile.id);
          return (
            <li key={tile.id} className={`tt-tile${tile.used ? "" : " tt-tile-idle"}${expanded ? " tt-tile-open" : ""}`} data-tile={tile.id}>
              <button
                type="button"
                className="tt-btn"
                aria-expanded={expanded}
                aria-controls={`${uid}-${tile.id}`}
                title={tile.glossary}
                onClick={() => toggle(tile.id)}
              >
                <span className="tt-name">{tile.name}</span>
                <span className="tt-head">{tile.headline}</span>
              </button>
              <div id={`${uid}-${tile.id}`} className="tt-panel" hidden={!expanded}>
                <TileDetails tile={tile} />
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/** The newest finished run (the one waiting for review first), for pages that hold no run of their own. */
export function LatestRunTechTrace() {
  const [run, setRun] = useState<RecordedRun | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      let id = getAwaitingRunId();
      if (!id) {
        const past = await fetchPastRuns(10, controller.signal);
        id = past.ok ? (past.rows.find((r) => r.status !== "running")?.runId ?? null) : null;
      }
      if (!id || controller.signal.aborted) return;
      try {
        const snap = await fetchRunSnapshot(id, controller.signal);
        if (!controller.signal.aborted && snap.run) setRun(snap.run);
      } catch {
        /* no run to show: the panel stays hidden */
      }
    })();
    return () => controller.abort();
  }, []);
  return run ? <TechTrace run={run} caption={`latest run ${run.runId}`} /> : null;
}

const OVERVIEW: { id: TileId; box: BoxId; name: string; line: string }[] = [
  { id: "zetaris", box: "zetaris", name: "Zetaris", line: "Every number is a SQL query with an id." },
  { id: "nightshift", box: "nightshift", name: "Meterless Nightshift", line: "Fast and deep lanes run Nemotron models." },
  { id: "hmem", box: "memory", name: "Meterless H-MEM", line: "Recalls only approved findings." },
  { id: "world", box: "memory", name: "Meterless World Model", line: "Tracks which hypotheses still hold." },
];

/** The same four tiles for the How it works page, each with the live status of its component. */
export function TechTraceOverview({ status }: { status: Record<BoxId, DotState> | null }) {
  return (
    <section className="tt" aria-label="Sponsor technology in every answer">
      <ul className="tt-tiles">
        {OVERVIEW.map((t) => {
          const state: DotState = status ? status[t.box] : "unknown";
          return (
            <li key={t.id} className="tt-tile" data-tile={t.id} title={GLOSSARY[t.id]}>
              <div className="tt-btn tt-static">
                <span className="tt-name">
                  <span className={`hiw-dot hiw-dot-${state}`} aria-hidden="true" /> {t.name}
                </span>
                <span className="tt-head">{t.line}</span>
                <span className="tt-status">{DOT_TEXT[state]}</span>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
