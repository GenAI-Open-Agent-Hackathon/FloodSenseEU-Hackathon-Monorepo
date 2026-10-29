# FloodSense EU: Nebius x NVIDIA submission pack

Track: Best Apps and Agents. Every claim here matches `main`. `TO MEASURE:` means no figure exists yet. `TO VERIFY:` means not supported by a file in the repo. `TO FILL:` means only the team can answer. Nothing below is invented.

## 1. Devpost description (English)

### 1. Problem

On 29 Oct 2024 a flood killed at least 232 people around Valencia ([DECK-FACTS](DECK-FACTS.md), Wikipedia revision in the stored corpus). The stored corpus says surging water destroyed a bridge in Picanya at 19:25 and that the ES-alert phone warning came at 20:11 (`corpus/pdf/wiki-2024-spanish-floods.html`). TO VERIFY: "river peaked 18:55" is not in the repo docs or corpus; do not say it until a source is found. Warnings exist, but nobody can see why a place is at risk, with proof, in time to act.

### 2. What it does: watch, investigate, falsify, expose, judge, approve, remember

- **Watch**: a rule-based Control tower scans 45 sources (26 gauges, 11 GloFAS points, 8 Valencia points), no model calls.
- **Investigate**: the Investigator builds a cited causal chain (rain, catchment, river, site) with Zetaris query ids as citations.
- **Falsify**: the Skeptic runs up to three SQL counter-checks per hypothesis and can send the Investigator back (at most 3 rounds).
- **Expose**: Exposure joins the flood footprint to insured sites (synthetic portfolio, labelled).
- **Judge**: every claim is scored; each number must be a cell of the cited rows. The Judge does not approve.
- **Approve**: a person approves, edits or rejects; nothing leaves before that.
- **Remember**: an approved run is stored in H-MEM and a repeat is served with a "Cached answer ... not live" label.

### 3. How we built it

Python/LangGraph agents, FastAPI API, React UI, Zetaris as the only data path, pgvector for 1,859 passages, Meterless engines sidecar (H-MEM, World Model). Chat goes through one backend: Nightshift (default) or Nebius Token Factory (`LLM_BACKEND=nebius`). Details: [architecture/c4.md](architecture/c4.md), [technical-highlights](architecture/technical-highlights.md).

### 4. Why Nebius and NVIDIA

All agent reasoning calls NVIDIA Nemotron over the Token Factory OpenAI-compatible API: fast lane `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, deep lane `nvidia/Nemotron-3.5-Super-VL` (env defaults on main), one endpoint and one key for both lanes. The model id that answered is recorded per step in the trace and on each Judge score. Tavily adds cited, labelled web context. TO FILL: concrete benefit seen in live Token Factory runs (none measured yet).

### 5. What we built during the hackathon

FloodSense was built 22 to 27 Oct 2026 (v1.0.0, v1.0.1; see [CHANGELOG](../CHANGELOG.md)). New in the submission period: `NebiusClient` and `LLM_BACKEND=nebius`, Tavily web context (`FF_TAVILY`), `GET /platform/status`, Apache-2.0 LICENSE. TO VERIFY: Nebius AI Cloud hosting kit (in review, not on main). The earlier 22 to 27 Oct work ran on Nightshift; the Nebius port is the main new work.

### 6. Challenges, learnings, next

- Reasoning models spend hidden tokens: on Nightshift, 1,300 to 5,500 completion tokens, and the gateway cut calls at about 45 s; we streamed and split the Investigator into small per-link calls (CHANGELOG 0.x). The full lane takes 5 to 6 minutes on Nightshift (27 Oct runs).
- Rate limits: a gate plus pacer plus backoff, now shared with the Nebius client.
- Learning: numbers in claims must be cells of cited rows; web text carries no numbers.
- Next: TO FILL after live Token Factory runs (verify model ids with `GET /v1/models`, measure lane latency, move hosting to Nebius AI Cloud).

### 7. Testing instructions

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
| Runtime call to Token Factory with an NVIDIA open model | Code on main (`NebiusClient`). Live call: TO VERIFY (offline tests only). Do a live run and record the model id before submitting. |
| Public repo, detectable open-source licence | Apache-2.0 `LICENSE` on main. Check the repo is public: TO VERIFY. |
| README explains Nemotron use, Token Factory help, other Nebius tools | Section written. "Where Token Factory helped" is TO FILL. |
| Working demo URL | TO FILL. |
| Video under 3 min on YouTube | Script in section 4. Not recorded. |
| English description | Section 1. |
| Feedback on Token Factory / AI Cloud / NVIDIA models | Draft in section 3. |
| Note on what was updated in the submission period (26 Aug to 30 Oct 2026) | Section 1.5. |
| Tavily bonus (functional runtime call) | Code on main, default off. Live call: TO VERIFY with a real key. |

To confirm (not claimed anywhere): zero-retention of prompts, EU-datacenter inference, Nebius AI Cloud hosting details. Not verified from Nebius public docs.

## 3. Feedback answer (draft)

Only what the repo shows is stated.

- **Onboarding**: the OpenAI-compatible API meant the existing client needed a base URL, a Bearer key and model ids; the Nebius client reuses the retry, backoff and JSON-mode code. Base URL was taken from docs.tokenfactory.nebius.com/api-reference/introduction (per code comment).
- **Token Factory**: TO FILL after live runs. Known gaps from docs reading: `response_format: json_object` and a thinking switch are not documented, so we drop the field on a 400 and do not send `enable_thinking`.
- **AI Cloud**: TO FILL.
- **NVIDIA models**: Nemotron reasoning tokens count against `max_tokens`; on Nightshift most completion tokens were hidden reasoning. Same behaviour on Token Factory: TO VERIFY.
- **Three improvements**: (1) TO FILL (candidate: document `response_format` and thinking control per model); (2) TO FILL; (3) TO FILL. Do not submit candidates the team did not experience.

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

| Run | Backend / models | Wall time | Prompt tokens | Completion tokens | Cost per answer |
| --- | --- | --- | --- | --- | --- |
| Valencia (EMSR773) replay, full lane | Nebius | TO MEASURE: | TO MEASURE: | TO MEASURE: | TO MEASURE: |
| Ahr (EMSR517) replay, full lane | Nebius | TO MEASURE: | TO MEASURE: | TO MEASURE: | TO MEASURE: |
| Reference, Nightshift 27 Oct subset | Nemotron 3.5 Lightning | 385 s/item (EMSR773), 346 s/item (EMSR517), from `docs/evals/2026-10-27-nightshift-subset.md` | not recorded | not recorded | not recorded |
