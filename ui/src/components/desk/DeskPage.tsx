import type { ReactNode } from "react";
import type { WatchSource } from "../../lib/euWatch";
import type { LiveEvidence } from "../../lib/liveEvidence";
import { basisLabel, calmSentence, countryName, plainOf } from "../../lib/places";
import { LiveSourceBadge } from "../LiveSources";
import { sourceTitle, StatusChip, timeText } from "../PlacesToWatch";

export const MODEL_NOT_WARNING = "A model, not an official warning.";

/**
 * The one skeleton for the Citizen, Insurer and Operator desks. Slots render in a fixed order:
 * impact, head, health, hazard, forecast, map, evidence, actions, agents, footer. An empty slot renders nothing,
 * so a desk shows only what it has. `agents` is filled by the agents feature and stays empty until a prop is passed.
 */
export interface DeskSlots {
  impact?: ReactNode;
  head?: ReactNode;
  health?: ReactNode;
  hazard?: ReactNode;
  forecast?: ReactNode;
  map?: ReactNode;
  evidence?: ReactNode;
  actions?: ReactNode;
  agents?: ReactNode;
  footer?: ReactNode;
}

export const DESK_SLOT_ORDER: readonly (keyof DeskSlots)[] = ["impact", "head", "health", "hazard", "forecast", "map", "evidence", "actions", "agents", "footer"];

export function DeskPage({ desk, ...slots }: DeskSlots & { desk: "citizen" | "insurer" | "operator" }) {
  return (
    <div className={`desk desk--${desk}`}>
      {DESK_SLOT_ORDER.map((name) =>
        slots[name] ? (
          <div key={name} className={`desk__slot desk__slot--${name}`}>
            {slots[name]}
          </div>
        ) : null,
      )}
    </div>
  );
}

/** Head slot: title, live/demo tag, updated time and the refresh / ask buttons. */
export function DeskHead({ eyebrow, title, tag, updated, children }: { eyebrow?: string; title: string; tag?: ReactNode; updated?: ReactNode; children?: ReactNode }) {
  return (
    <header className="desk-head">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2 className="desk-title">{title}</h2>
        <p className="desk-meta" aria-live="polite">
          {tag} {updated}
        </p>
      </div>
      {children && <div className="button-row">{children}</div>}
    </header>
  );
}

/** A titled card, the one section style for every slot. */
export function DeskCard({ label, title, children }: { label: string; title?: string; children: ReactNode }) {
  return (
    <section className="card desk-card" aria-label={title ?? label}>
      <p className="eyebrow">{label}</p>
      {title && <h3 className="desk-card__title">{title}</h3>}
      {children}
    </section>
  );
}

/** Hazard slot: the lead place as chip, one plain sentence with its source, and the detail grid behind <details>. */
export function HazardLead({ label, source, evidence, detail }: { label: string; source: WatchSource; evidence: LiveEvidence; detail?: ReactNode }) {
  const view = plainOf(source);
  return (
    <DeskCard label={label}>
      <p>
        <StatusChip view={view} large /> <strong>{sourceTitle(source)}</strong> <span className="muted small">{countryName(source.country)}</span>
      </p>
      {source.live ? (
        <p>
          {calmSentence(source.kind, source.status, source.river, source.name)} <LiveSourceBadge n={1} evidence={evidence} />
        </p>
      ) : (
        <p className="op-partial note" role="alert">
          This reading is not a fresh live one ({timeText(source.kind, source.measuredAt)}) and may be out of date. Do not treat it as the current situation.{" "}
          <LiveSourceBadge n={1} evidence={evidence} />
        </p>
      )}
      <details className="disclosure">
        <summary>Details</summary>
        <dl className="desk-grid">
          <div>
            <dt>Reading</dt>
            <dd>{timeText(source.kind, source.measuredAt)}</dd>
          </div>
          <div>
            <dt>Basis</dt>
            <dd>{basisLabel(source.kind)}</dd>
          </div>
          <div>
            <dt>Freshness</dt>
            <dd>{source.live ? "live" : "not live (stale or seed)"}</dd>
          </div>
        </dl>
        {detail}
      </details>
    </DeskCard>
  );
}

/** Forecast slot: the next 48 h, always with the model-not-a-warning note. */
export function ForecastCard({ title = "Outlook", head, children, note }: { title?: string; head?: ReactNode; children: ReactNode; note?: ReactNode }) {
  return (
    <DeskCard label="Next 48 hours" title={title}>
      {head}
      {children}
      <p className="note">{note ?? MODEL_NOT_WARNING}</p>
    </DeskCard>
  );
}

/** Evidence slot: the source badge and the entry that opens the evidence drawer. */
export function EvidenceRow({ evidence, onOpen, children }: { evidence: LiveEvidence; onOpen: () => void; children?: ReactNode }) {
  return (
    <DeskCard label="Evidence">
      <p>
        <LiveSourceBadge n={1} evidence={evidence} /> {evidence.kind}, {evidence.title}
      </p>
      {children}
      <button type="button" className="button ghost" onClick={onOpen}>
        Open the evidence panel
      </button>
    </DeskCard>
  );
}
