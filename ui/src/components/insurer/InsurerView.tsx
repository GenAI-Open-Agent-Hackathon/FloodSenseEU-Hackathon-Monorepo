import { useCallback, useEffect, useState } from "react";
import { approvals as approvalStore, decideApproval, getReasoningChain, listAlerts, listPortfolioSites } from "../../api/client";
import { useAsync } from "../../hooks/useAsync";
import { useStore } from "../../hooks/useStore";
import { hideSplash } from "../../lib/splash";
import { exposureByTier } from "../../lib/portfolio";
import type { ApprovalDecision } from "../../types";
import { CitedClaims } from "../citations/CitedClaims";
import { AsyncBoundary } from "../shared/AsyncBoundary";
import { Card } from "../shared/Card";
import { MockBadge } from "../shared/MockBadge";
import { AlertList } from "./AlertList";
import { AlertSimulation } from "./AlertSimulation";
import { ApprovalQueue } from "./ApprovalQueue";
import { ExposureKpis } from "./ExposureKpis";
import { ReasoningChainView } from "./ReasoningChainView";
import { SiteTable } from "./SiteTable";
import { TierExposureChart } from "./TierExposureChart";

export function InsurerView() {
  const sites = useAsync(listPortfolioSites, []);
  const alerts = useAsync(listAlerts, []);
  const approvals = useStore(approvalStore);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);

  // The insurer view has no map, so the loading screen can go once it mounts.
  useEffect(hideSplash, []);

  const selected = approvals.find((a) => a.id === selectedId) ?? approvals[0] ?? null;
  const showInQueue = useCallback((id: string) => setSelectedId(id), []);
  const chain = useAsync(
    () => (selected ? getReasoningChain(selected.reasoningChainId) : Promise.reject(new Error("Select an approval request."))),
    [selected?.reasoningChainId],
  );

  const onDecide = async (decision: ApprovalDecision) => {
    setDecisionError(null);
    try {
      await decideApproval(decision);
    } catch (error) {
      setDecisionError(error instanceof Error ? error.message : "Decision failed.");
    }
  };

  const pending = approvals.filter((a) => a.status === "pending").length;

  return (
    <div className="view">
      <div className="view__intro">
        <div>
          <h1>Portfolio flood exposure</h1>
          <p className="muted">Where the portfolio is exposed, why, and which outbound actions wait for a human decision.</p>
        </div>
        <MockBadge />
      </div>

      <AsyncBoundary state={sites} loadingText="Loading portfolio…">
        {(list) => {
          const tiers = exposureByTier(list);
          return (
            <>
              <ExposureKpis sites={list} tiers={tiers} pendingApprovals={pending} />
              <div className="grid grid--insurer">
                <Card title="Exposure by risk tier" className="span-2" ownerHint="Zetaris federation" aside={<PortfolioSource />}>
                  <TierExposureChart tiers={tiers} />
                </Card>
                <Card title="Alert simulation" className="span-4" ownerHint="LangGraph + HITL + Judge" aside={<span className="chip chip--sample">sample run</span>}>
                  <AlertSimulation onShowInQueue={showInQueue} />
                </Card>
                <Card title="Active alerts" className="span-2" ownerHint="Ingestion + Agents">
                  <AsyncBoundary state={alerts}>{(items) => <AlertList alerts={items} />}</AsyncBoundary>
                </Card>
                <Card title="Approval queue (human in the loop)" className="span-2" ownerHint="LangGraph HITL + Judge" aside={<span className="muted small">{pending} pending</span>}>
                  {decisionError && <p className="error" role="alert">{decisionError}</p>}
                  <ApprovalQueue requests={approvals} selectedId={selected?.id ?? null} onSelect={setSelectedId} onDecide={onDecide} />
                </Card>
                <Card title="Reasoning chain" className="span-2 row-span-2" ownerHint="Investigator · Skeptic · Judge">
                  <AsyncBoundary state={chain} loadingText="Loading reasoning chain…">
                    {(c) => <ReasoningChainView chain={c} />}
                  </AsyncBoundary>
                </Card>
                <Card title="Insured sites" className="span-2" ownerHint="UI + Zetaris">
                  <SiteTable sites={list} />
                </Card>
              </div>
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

/** Small cited marker so the tier totals point back to their Zetaris query. */
function PortfolioSource() {
  return <CitedClaims claims={[{ id: "portfolio-src", text: "Source", citationIds: ["cit-portfolio"] }]} variant="prose" showSources={false} />;
}
