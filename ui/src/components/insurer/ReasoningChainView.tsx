import type { ChallengeStatus, Claim, ReasoningChain } from "../../types";
import { CitedClaims } from "../citations/CitedClaims";
import { JudgeScoreBadge } from "../shared/JudgeScoreBadge";

const statusLabel: Record<ChallengeStatus, string> = {
  resolved: "resolved",
  conceded: "conceded, claim softened",
  open: "open",
};

/** Investigator claim → Skeptic challenge → Judge score, read top to bottom. */
export function ReasoningChainView({ chain }: { chain: ReasoningChain }) {
  return (
    <div className="chain">
      <p className="chain__subject">{chain.subject}</p>
      <ol className="chain__steps">
        {chain.investigatorClaims.map((claim, index) => (
          <ClaimStep key={claim.id} claim={claim} index={index + 1} chain={chain} />
        ))}
        <li className="chain__step chain__step--judge">
          <span className="chain__role chain__role--judge">Judge</span>
          <JudgeScoreBadge score={chain.judge} detailed />
        </li>
      </ol>
    </div>
  );
}

function ClaimStep({ claim, index, chain }: { claim: Claim; index: number; chain: ReasoningChain }) {
  const challenges = chain.skepticChallenges.filter((c) => c.targetClaimId === claim.id);
  return (
    <li className="chain__step">
      <span className="chain__role chain__role--investigator">Investigator · claim {index}</span>
      <CitedClaims claims={[claim]} variant="prose" showSources={false} />
      {challenges.map((challenge) => (
        <div key={challenge.id} className={`challenge challenge--${challenge.status}`}>
          <span className="chain__role chain__role--skeptic">Skeptic · {statusLabel[challenge.status]}</span>
          <p className="challenge__text">{challenge.challenge}</p>
          <div className="challenge__resolution">
            {challenge.citationIds.length > 0 ? (
              <CitedClaims claims={[{ id: `${challenge.id}-r`, text: challenge.resolution, citationIds: challenge.citationIds }]} variant="prose" showSources={false} />
            ) : (
              <span>{challenge.resolution}</span>
            )}
          </div>
        </div>
      ))}
    </li>
  );
}
