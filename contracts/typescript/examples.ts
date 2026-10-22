/**
 * Assigns the JSON examples to the TypeScript mirrors.
 * `python tasks.py lint` typechecks this file. Schema tests remain the strict gate.
 */

import type { Answer, Approval, Citation, Claim, Evidence, Judge, PlaybookAction } from "./index";

import answerLive from "../examples/answer_live.json" with { type: "json" };
import answerReplay from "../examples/answer_replay.json" with { type: "json" };
import approval from "../examples/approval.json" with { type: "json" };
import citation from "../examples/citation.json" with { type: "json" };
import claim from "../examples/claim.json" with { type: "json" };
import evidence from "../examples/evidence.json" with { type: "json" };
import judge from "../examples/judge.json" with { type: "json" };
import playbookAction from "../examples/playbook_action.json" with { type: "json" };

export const exampleClaim: Claim = claim;
export const exampleEvidence: Evidence = evidence;
export const exampleCitation: Citation = citation;
export const exampleJudge: Judge = judge;
export const examplePlaybookAction: PlaybookAction = playbookAction;
export const exampleApproval: Approval = approval;
export const exampleAnswerLive: Answer = answerLive;
export const exampleAnswerReplay: Answer = answerReplay;
