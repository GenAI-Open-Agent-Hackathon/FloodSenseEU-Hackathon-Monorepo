import type { ReasoningChain } from "../types";
import { judgePass, judgeReview, judgeStrong } from "./judgeScores";

/** Investigator -> Skeptic -> Judge chains behind each approval request. MOCK. */
export const reasoningChains: ReasoningChain[] = [
  {
    id: "rc-valencia",
    subject: "Notify policyholders in Paiporta and Catarroja",
    investigatorClaims: [
      { id: "i1", text: "Flow in the Rambla del Poyo rose sharply within two hours upstream of the insured sites.", citationIds: ["cit-saih-poyo"] },
      { id: "i2", text: "Rainfall above 40 mm/h is forecast for this evening over the same catchment.", citationIds: ["cit-openmeteo-valencia"] },
      { id: "i3", text: "152 policies with €44.5M insured value sit within the rambla's flood path.", citationIds: ["cit-portfolio"] },
    ],
    skepticChallenges: [
      { id: "sk1", targetClaimId: "i2", challenge: "Convective rain forecasts are highly uncertain at street scale. Is one model run enough?", resolution: "Observed flow at Riba-roja already confirms the rise independently of the forecast.", status: "resolved", citationIds: ["cit-saih-poyo"] },
      { id: "sk2", targetClaimId: "i3", challenge: "Are all 152 policies really in the flood path, or only near it?", resolution: "Sites were joined to the nearest gauge and filtered by the mapped hazard zone; count confirmed.", status: "resolved", citationIds: ["cit-portfolio"] },
    ],
    judge: judgeStrong,
  },
  {
    id: "rc-ahr",
    subject: "Dispatch loss adjuster standby to Bad Neuenahr-Ahrweiler",
    investigatorClaims: [
      { id: "i1", text: "The Ahr at Altenahr is above its first warning threshold and rising.", citationIds: ["cit-rlp-altenahr"] },
      { id: "i2", text: "The downstream gauge at Bad Bodendorf is following the rise with a few hours' delay.", citationIds: ["cit-rlp-bodendorf"] },
      { id: "i3", text: "Three sites with 176 policies are within 2 km of the river.", citationIds: ["cit-portfolio"] },
    ],
    skepticChallenges: [
      { id: "sk1", targetClaimId: "i1", challenge: "A single upstream gauge could be a sensor error. Is there a second signal?", resolution: "Added Bad Bodendorf readings and the precipitation forecast; both agree.", status: "resolved", citationIds: ["cit-rlp-bodendorf", "cit-openmeteo-ahr"] },
    ],
    judge: judgePass,
  },
  {
    id: "rc-passau",
    subject: "Flag Passau riverside sites for underwriting review",
    investigatorClaims: [
      { id: "i1", text: "Both the Danube and the Inn are rising at Passau.", citationIds: ["cit-hnd-passau", "cit-hnd-inn"] },
      { id: "i2", text: "35 mm of rain over the Inn catchment will keep levels rising for 48 hours.", citationIds: ["cit-openmeteo-passau"] },
    ],
    skepticChallenges: [
      { id: "sk1", targetClaimId: "i2", challenge: "35 mm over 48 hours is moderate. Does it really keep levels rising, or does snowmelt dominate?", resolution: "Not yet resolved: no snowmelt dataset is federated in Zetaris yet.", status: "open", citationIds: [] },
      { id: "sk2", targetClaimId: "i1", challenge: "Is 'rising' significant relative to the seasonal range?", resolution: "Conceded: the rise is within the normal autumn range, so the claim was softened.", status: "conceded", citationIds: ["cit-hnd-passau"] },
    ],
    judge: judgeReview,
  },
];
