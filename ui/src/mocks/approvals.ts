import type { ApprovalRequest } from "../types";
import { judgePass, judgeReview, judgeStrong } from "./judgeScores";
import { minutesAgo } from "./time";

/** Outbound actions proposed by the agents, waiting for a human. MOCK. */
export const approvalRequests: ApprovalRequest[] = [
  {
    id: "ap-1",
    actionType: "notify-policyholders",
    title: "Send flood warning SMS to 152 policyholders",
    summary: "Warn residents and businesses in Paiporta and Catarroja to avoid garages and ramblas tonight.",
    draftMessage: "FloodSense (sample): Intense rain is expected this evening. Avoid underground garages, underpasses and ramblas. Follow official warnings from Protección Civil.",
    targetRegion: "Valencian Community",
    affectedSiteIds: ["s-09", "s-10"],
    createdAt: minutesAgo(9),
    reasoningChainId: "rc-valencia",
    judge: judgeStrong,
    status: "pending",
  },
  {
    id: "ap-2",
    actionType: "dispatch-loss-adjuster",
    title: "Put loss adjusters on standby for the Ahr valley",
    summary: "Pre-position two adjusters near Bad Neuenahr-Ahrweiler for the next 24 hours.",
    draftMessage: "Standby request (sample): please be available for site visits in Bad Neuenahr-Ahrweiler and Altenahr from 06:00 tomorrow.",
    targetRegion: "Rhineland-Palatinate",
    affectedSiteIds: ["s-01", "s-02", "s-03"],
    createdAt: minutesAgo(31),
    reasoningChainId: "rc-ahr",
    judge: judgePass,
    status: "pending",
  },
  {
    id: "ap-3",
    actionType: "flag-underwriting-review",
    title: "Flag Passau riverside sites for underwriting review",
    summary: "Add two sites to the next underwriting review because of repeated Danube and Inn rises.",
    draftMessage: "Underwriting note (sample): review flood terms for Altstadt shops and Innstadt apartments, Passau.",
    targetRegion: "Bavaria",
    affectedSiteIds: ["s-07", "s-08"],
    createdAt: minutesAgo(64),
    reasoningChainId: "rc-passau",
    judge: judgeReview,
    status: "pending",
  },
];
