/**
 * Wire types shared with agents and the API.
 * Field names stay snake_case. This file only re-exports the contract.
 *
 * The relative path leaves the ui/ Docker build context (compose builds ./ui).
 * Vite erases `import type`, so the dev server in that image does not read the file.
 * `tsc` from a full checkout resolves it. Do not copy contracts into ui/.
 * Changing the contract ModelId union is Ayush's. The desk only relabels known ids.
 */
export type {
  Answer,
  Approval,
  ApprovalStatus,
  Citation,
  Claim,
  Evidence,
  Grounding,
  Judge,
  JudgeClaim,
  PlaybookAction,
  ServedFrom,
} from "../../../contracts/typescript/index";
