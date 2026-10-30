# FloodSense EU: Nebius x NVIDIA submission pack

Track: Best Apps and Agents. Every claim here matches `main`. `TO MEASURE:` means no figure exists yet. `TO VERIFY:` means not supported by a file in the repo. `TO FILL:` means only the team can answer. Nothing below is invented.

## 1. Devpost description (English)

### 1.1 Problem

On 29 Oct 2024 a flood killed at least 232 people around Valencia ([DECK-FACTS](DECK-FACTS.md), Wikipedia revision in the stored corpus). The stored corpus says surging water destroyed a bridge in Picanya at 19:25 and that the ES-alert phone warning came at 20:11 (`corpus/pdf/wiki-2024-spanish-floods.html`). TO VERIFY: "river peaked 18:55" is not in the repo docs or corpus; do not say it until a source is found. Warnings exist, but nobody can see why a place is at risk, with proof, in time to act.

### 1.2 What it does: watch, investigate, falsify, expose, judge, approve, remember

- **Watch**: a rule-based Control tower scans 45 sources (26 gauges, 11 GloFAS points, 8 Valencia points), no model calls.
- **Investigate**: the Investigator builds a cited causal chain (rain, catchment, river, site) with Zetaris query ids as citations.
- **Falsify**: the Skeptic runs up to three SQL counter-checks per hypothesis and, when a hypothesis is not supported, sends the Investigator back for one revise pass (`graph.py`: "no revise yet").
- **Expose**: Exposure joins the flood footprint to insured sites (synthetic portfolio, labelled).
- **Judge**: every claim is scored; each number must be a cell of the cited rows. The Judge does not approve.
- **Approve**: a person approves, edits or rejects; nothing leaves before that.
- **Remember**: an approved run is stored in H-MEM and a repeat is served with a "Cached answer ... not live" label.

### 1.3 How we built it

Python/LangGraph agents, FastAPI API, React UI, Zetaris as the only data path, pgvector for 1,859 passages, Meterless engines sidecar (H-MEM, World Model). Chat goes through one backend: Nightshift (default) or Nebius Token Factory (`LLM_BACKEND=nebius`). Details: [architecture/c4.md](architecture/c4.md), [technical-highlights](architecture/technical-highlights.md).

### 1.4 Why Nebius and NVIDIA

All agent reasoning calls NVIDIA Nemotron over the Token Factory OpenAI-compatible API: as measured on 30 Oct 2026, fast lane `nvidia/Nemotron-3_5-Lightning`, deep lane `nvidia/Nemotron-3.5-Super-VL` (the main defaults are Nano for fast; the measured run overrode them by env), one endpoint and one key for both lanes. The model id that answered is recorded per step in the trace and on each Judge score. Tavily adds cited, labelled web context. Measured on 30 Oct 2026 (section 6): a full Ahr 2021 investigation ran end to end in 148 s over 12 Token Factory calls (44,569 tokens), and every model-judged claim scored 1.0 in the Judge.

### 1.5 What we built during the hackathon

FloodSense was built 22 to 27 Oct 2026 (v1.0.0, v1.0.1; see [CHANGELOG](../CHANGELOG.md)). New in the submission period: `NebiusClient` and `LLM_BACKEND=nebius`, Tavily web context (`FF_TAVILY`), `GET /platform/status`, and the Apache-2.0 licence file (the code was already public; licence added in this period). The Nebius AI Cloud hosting kit is merged (PR #117) but not yet deployed; TO VERIFY before saying "hosted on Nebius". The earlier 22 to 27 Oct work ran on Nightshift; the Nebius port is the main new work.

### 1.6 Challenges, learnings, next

- Reasoning models spend hidden tokens: on Nightshift, 1,300 to 5,500 completion tokens, and the gateway cut calls at about 45 s; we streamed and split the Investigator into small per-link calls (CHANGELOG 0.x). The full lane takes 5 to 6 minutes on Nightshift (27 Oct runs).
- Rate limits: a gate plus pacer plus backoff, now shared with the Nebius client.
- Learning: numbers in claims must be cells of cited rows; web text carries no numbers.
- On Token Factory (30 Oct 2026): model ids are plain `nvidia/...`; an id with a `nebius/` prefix returned 404. `GET /v1/models` listed 30 models. The deep lane is a reasoning model: one tiny completion took 30,399 ms against 1,108 ms on the fast lane.
- Next: deploy the hosting kit on Nebius AI Cloud and record the demo URL.

### 1.7 Testing instructions

- Demo URL: `TO FILL: <demo URL>`; judge login: `TO FILL: <login, if any>`.
- Open the Citizen desk, switch to Past flood, Valencia 2024. Try these (they are in the product's suggestion chips):
  1. "What happened at Paiporta in the Valencia flood of October 2024?"
  2. "When did the Valencia points cross the alert line in October 2024?"
  3. "Which of our insured sites are exposed in Valencia?" (Insurer desk; then Approvals to approve)
- Ask question 1 again to see the cached label (needs `FF_SEMANTIC_CACHE`).
- Own keys: [README, Built on Nebius and NVIDIA](../README.md#built-on-nebius-and-nvidia).

## 2. Stage-one rules checklist

| Requirement | Status |
| --- | --- |
| Track Best Apps and Agents | Entering. |
| Runtime call to Token Factory with an NVIDIA open model | VERIFIED on 30 Oct 2026: live calls on both lanes (`nvidia/Nemotron-3_5-Lightning`, `nvidia/Nemotron-3.5-Super-VL`), see section 6. |
| Public repo, detectable open-source licence | Apache-2.0 `LICENSE` on main. Repo is PUBLIC and GitHub detects Apache-2.0 (`gh repo view`, checked 30 Oct 2026). |
| README explains Nemotron use, Token Factory help, other Nebius tools | Section written; measured numbers added 30 Oct. Cost per run still TO FILL. |
| Working demo URL | TO FILL. Hosting kit merged as PR #117, not yet deployed. |
| Video under 3 min on YouTube | Script in section 4. TO DO (not recorded). |
| English description | Section 1. |
| Feedback on Token Factory / AI Cloud / NVIDIA models | Draft in section 3. |
| Note on what was updated in the submission period (26 Aug to 30 Oct 2026) | Section 1.5. |
| Tavily bonus (functional runtime call) | Code on main, default off. Live call: TO VERIFY (no Tavily key configured yet). |

Nebius's Legal Quick Guide says inputs and outputs "may be stored and used for Speculative Decoding" by default, that "the inputs and outputs retained for Speculative Decoding are stored in Finland (EU)", and that enabling Zero Data Retention in account settings stops this ([Legal Quick Guide](https://docs.tokenfactory.nebius.com/legal/legal-quick-guide), retrieved 30 Oct 2026). We have not enabled it and do not claim it. To confirm (not claimed anywhere): EU-only inference on public endpoints (the same docs say the processing region of public endpoints can change), and Nebius AI Cloud hosting details.

## 3. Feedback answer (draft)

Only what the repo shows is stated.

- **Onboarding**: the OpenAI-compatible API meant the existing client needed a base URL, a Bearer key and model ids; the Nebius client reuses the retry, backoff and JSON-mode code. Base URL was taken from docs.tokenfactory.nebius.com/api-reference/introduction (per code comment).
- **Token Factory** (live runs, 30 Oct 2026): model ids are plain `nvidia/...`; a `nebius/` prefix gave 404. `GET /v1/models` listed 30 models. Lane check: fast 1,108 ms, deep 30,399 ms for one tiny completion. Known gaps from docs reading: `response_format: json_object` and a thinking switch are not documented, so we drop the field on a 400 and do not send `enable_thinking`.
- **AI Cloud**: TO FILL.
- **NVIDIA models**: Nemotron reasoning tokens count against `max_tokens`; on Nightshift most completion tokens were hidden reasoning. On Token Factory the deep model returned thinking text and spent tokens on reasoning (observed 30 Oct; the 30,399 ms lane check is a reasoning model).
- **Three improvements**: (1) document `response_format` / JSON mode and thinking control per model (the code comments in `NebiusClient` record both as undocumented); (2) state the exact model id format in the model catalogue, since the `nebius/` prefix gives 404; (3) separate reasoning text from the answer, and report reasoning tokens in `usage`. All three were experienced in our runs.

## 4. Video script (2:50, one continuous Valencia replay)

No copyrighted music; voice only or a licence-free track.

| Time | Screen | Voiceover |
| --- | --- | --- |
| 0:00 | Valencia 2024 on the Past flood map; corpus timeline text (bridge 19:25, phone alert 20:11) | The problem: warnings came late and nobody could see why. |
| 0:20 | Analyst types question 1; pipeline panel lights Watchers, Investigator | An analyst asks. The agent pipeline runs on Nemotron through Token Factory. |
| 0:55 | Skeptic counter-checks, Tavily sources labelled "Web context, not an official warning", Judge scores | The Skeptic tries to falsify. Web sources are labelled. The Judge scores each claim. |
| 1:30 | Approval card, Exposure list, Playbook | A person approves. Exposure and the playbook follow. Nothing leaves before this. |
| 1:50 | Same question again; "Cached answer" banner | A follow-up is answered from memory, labelled cached. |
| 2:10 | Architecture diagram: Token Factory lanes, Nebius AI Cloud, Tavily, Zetaris | Two Nemotron lanes on one API, Zetaris as the data layer, Tavily for web context. Say "hosted on Nebius AI Cloud" only if true by then. |
| 2:40 | Closing card: name, repo URL, demo URL | FloodSense EU. |

Record with `LLM_BACKEND=nebius`, `FF_TAVILY=true` and a real key, else do not show those parts.

## 5. Screenshot shot list

1. Answer with citations (Valencia, question 1).
2. Agent pipeline panel with `model_id` per step showing Nemotron ids.
3. "How this answer was made" panel, model tile.
4. Skeptic result and Tavily web-context claim with its label.
5. Judge scores.
6. Approval card.
7. Cached-answer banner.
8. Platform status strip (`/platform/status`).
9. Architecture diagram from the README.

## 6. Measurements

Live runs on the Nebius Token Factory, 30 Oct 2026. Stack: local Docker, Zetaris live data, `LLM_BACKEND=nebius`, fast lane `nvidia/Nemotron-3_5-Lightning`, deep lane `nvidia/Nemotron-3.5-Super-VL` (env overrides of the main defaults).

| Run | Backend / models | Wall time | Model calls | Total tokens | Cost per answer |
| --- | --- | --- | --- | --- | --- |
| Lane check (one tiny completion each) | Nebius | fast 1,108 ms; deep 30,399 ms (deep is a reasoning model) | 2 | not recorded | TO FILL: price per 1M tokens not configured |
| Ahr 2021 (EMSR517), full lane | Nebius | 148 s | 12 (deep 3, fast 9) | 44,569 (deep 3,434; fast 41,135) | TO FILL: price per 1M tokens not configured |
| Valencia 2024 (EMSR773), full lane | Nebius | 281 s, inflated: ran concurrently with the Ahr run | 14 (deep 7, fast 7) | 40,370 (deep 8,556; fast 31,814) | TO FILL: price per 1M tokens not configured |
| Quick lane, earlier 30 Oct | Nightshift (no model writes the answer) | about 0.3 to 9 s | 0 | 0 | n/a |
| Forecast lane, earlier 30 Oct | Nightshift (no model writes the answer) | about 4 to 10 s | 0 | 0 | n/a |
| Reference, Nightshift 27 Oct subset | Nemotron 3.5 Lightning | 385 s/item (EMSR773), 346 s/item (EMSR517), from `docs/evals/2026-10-27-nightshift-subset.md` | not recorded | not recorded | not recorded |

Judge: both full runs scored 1.0 on every model-judged claim plus a deterministic score, and stopped awaiting human approval.

Cost: the prompt/completion split was not recorded, so no cost is computed. Nebius's own pricing page (https://tokenfactory.nebius.com/organization/prices, retrieved 30 Oct 2026) did not return prices to our fetch, so no official price is recorded. Third-party aggregators list figures but are not official and are not used. Once both are known: cost = (prompt tokens x input price + completion tokens x output price) / 1,000,000 per model, summed over both lanes.
