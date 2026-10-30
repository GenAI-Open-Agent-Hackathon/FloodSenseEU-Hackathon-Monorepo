import { useEffect, useState } from "react";
import { fetchPlatformStatus, type PlatformStatus } from "../api/platform";
import { useConsole } from "../context/ConsoleContext";
import { setLanePricing, setLlmBackend } from "../lib/lanes";
import { routeHref, type RoleId } from "../lib/route";
import { sponsorChips, type ChipState, type SponsorChip } from "../lib/sponsors";
import "../styles/sponsors.css";

const STATE_WORD: Record<ChipState, string> = { on: "on", off: "off", unavailable: "status unavailable" };
const POLL_MS = 30_000;

/** Pure view: one chip per sponsor, a status dot, a link to the Stack page. */
export function SponsorChips({ platform, role = "citizen" }: { platform: PlatformStatus | null; role?: RoleId }) {
  const href = routeHref(role, "stack");
  return (
    <ul className="sponsor-strip" aria-label="Sponsor technologies in use">
      {sponsorChips(platform).map((c: SponsorChip) => (
        <li key={c.id}>
          <a className={`sponsor-chip sponsor-chip--${c.state}`} href={href} title={c.title} data-sponsor={c.id}>
            <span className="sponsor-dot" aria-hidden="true" />
            <span className="sponsor-name">{c.label}</span>
            {c.detail && <span className="sponsor-detail">{c.detail}</span>}
            <span className="sr-only">: {STATE_WORD[c.state]}. {c.title} Opens Under the hood.</span>
          </a>
        </li>
      ))}
    </ul>
  );
}

/** Global strip under the header: live status from /platform/status, polled slowly; a failed poll shows "unavailable", never stale green. */
export function SponsorStrip() {
  const [platform, setPlatform] = useState<PlatformStatus | null>(null);
  const { route } = useConsole();
  useEffect(() => {
    const ctl = new AbortController();
    const tick = () =>
      void fetchPlatformStatus().then((r) => {
        if (ctl.signal.aborted) return;
        setPlatform(r.status);
        if (r.status?.llmBackend) setLlmBackend(r.status.llmBackend);
        setLanePricing(r.status?.llmUsage?.pricing);
      });
    tick();
    const t = window.setInterval(() => document.visibilityState !== "hidden" && tick(), POLL_MS);
    return () => {
      ctl.abort();
      window.clearInterval(t);
    };
  }, []);
  return <SponsorChips platform={platform} role={route} />;
}
