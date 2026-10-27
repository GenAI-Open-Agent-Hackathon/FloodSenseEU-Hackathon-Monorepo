# FloodSense EU 1.0.0: release notes

Open Agent Hackathon 2026, Track 02. Released 27 Oct 2026. The full change list is [CHANGELOG.md](../CHANGELOG.md); the sponsor details are in [SUBMISSION.md](SUBMISSION.md).

## What FloodSense EU is

FloodSense EU explains why a place in Europe is at flood risk, with a citation for every sentence. It watches 45 places live, answers plain questions in seconds, and runs a full multi-agent investigation when a question needs one. A person approves anything that would leave the system.

## Three desks

One console, three desks (switch in the header). Each has its own navigation.

| Desk | Who it is for | Pages |
| --- | --- | --- |
| Citizen | "Is my street at risk, and what do I do?" | Now, Replay, Overview, My area, What to do, Evidence, How it works |
| Insurer | "Which insured sites are exposed, and what do we tell the customer?" | Control tower, Now, Replay, Approvals, Portfolio, Sites / map, Alerts, Review, System, How it works |
| Civil protection | Hotline staff who are not flood experts: "which rivers need attention first, and what do we tell callers?" | Situation board, Approvals, How it works |

The Situation board gives a one-screen brief per river, a fixed call script (German and English; Spanish for Spanish places) and official links. "Escalate to agents" starts a full run, and its proposed actions land in the desk's own approval queue.

A global switch in the header chooses **Live** or **Past flood** (Ahr 2021, Valencia 2024), and a separate **Demo data** switch swaps the live feeds for a labelled snapshot. Every page obeys the switch.

## Control tower

The Control tower (first page of the Insurer desk, read-only for citizens as "How we watch") shows the agents working on their own.

- An autonomous watch loop scans the 45 sources every 15 minutes by default (`WATCH_INTERVAL_S`, 900) and writes a plain activity feed: detected, checked, exposure, and back to normal.
- The loop is rules only. It makes no model calls.
- Auto-assess is opt-in and capped. When it is switched on, the single most severe new source of a scan may start one full run, at most 1 per hour and 3 per day. It never approves anything: the run waits in Approvals like any other.

## Router lanes

A router picks a lane for every message and records it as the first step of the run.

| Lane | What it answers | Model calls | Time |
| --- | --- | --- | --- |
| `reply` | Greetings, help, thanks, off-topic. Fixed, role-aware templates | none | instant |
| `quick` | A live reading: "How high is the Rhine at Köln?" One Zetaris query per asked place, deterministic cited claims, deterministic Judge | none | about 1 s |
| `forecast` | "Do the next 48 hours look safe at Köln?" DWD ICON rain (via Open-Meteo), GloFAS discharge, gauge level and trend, past pattern and H-MEM recall | none | 1 to 4 s |
| `full` | Why, replay, exposure, policies, documents. Scope, Watchers, Memory, Investigator and Skeptic loop, Exposure, Playbook, Judge repair loop, human approval | Nemotron via Nightshift | 5 to 6 minutes |

An explicit `event_id`, a `replay_ts` or a `doc_query` different from the question always goes to the full lane, so the evaluations are stable. A quick or forecast answer with no data, or any Judge flag, escalates the same run into the full lane.

## Grounded by design

- Every sentence cites a Zetaris query id (layer a), a source provenance row (layer b), a stored document passage with a hash-checked quote (layer c), or an approved memory. In the UI, each claim has numbered references that open the source.
- The Judge is deterministic where it matters. It checks that a citation is present, that the cited query returned rows, and that every number stated is a cell of the cited rows. It scores claims and never approves them.
- Calm answers follow fixed rules. A calm headline appears only when every checked status is Normal and the data is complete. Missing or stale data reads "We can't fully check" and never reads as calm.
- Statuses are FloodSense's own screening (Normal, Watch, Elevated), never red, and modelled river values are labelled "model, not an official warning". Replays are labelled replays.

## Human approval, then memory

Nothing outbound leaves without a person: approve, edit or reject, with a reviewer note for edit and reject. Only after an approve or edit does the Learn step write to H-MEM. A reject writes nothing.

The approve-and-remember loop was verified end to end on the live stack. Approving run `f6cc4adbc438` took the H-MEM count from 212 to 214. The next Orléans forecast question recalled the new memory (`mem-213`) and listed it in `memory_used`.

## Data

45 watched sources, read only through Zetaris views:

- 26 PEGELONLINE gauges on ten German federal waterways (official mean-high-water values; refreshed every 10 minutes by the `pegel-poller` container),
- 11 Open-Meteo GloFAS river points from Paris to Budapest (a model band, fetched by Zetaris at query time),
- 8 Valencia demo points.

Weather forecasts are Open-Meteo with the DWD ICON model. Replays use Copernicus EMS activations EMSR773 (Valencia 2024) and EMSR517 (Ahr 2021), with ERA5 rain and GloFAS discharge.

Documents: 25 documents and 1,859 passages in pgvector, including four insurer and authority documents (two EEA briefings, EIOPA-19/485, the EU Floods Directive) and 13 pinned English Wikipedia snapshots (CC BY-SA 4.0) on past river floods. 59 cited demo-seed memories, labelled "demo seed", were distilled from those documents. Every source and licence is in [legal/sources.md](legal/sources.md) and [../THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

## Sponsor technology

- **Zetaris** is the only SQL path to the data. Agents never call a public source themselves. Numbered migrations define the views, and `zetaris-sync` applies and verifies them. Every data citation carries the Zetaris `query_id`.
- **Meterless Nightshift** is the gateway for all chat completions, on two lanes (`meterless/fast` and `meterless/deep`). The Meterless H-MEM and World Model engines run in the `engines/` sidecar.
- **NVIDIA** Nemotron 3.5 models answer the Nightshift lanes (every measured call in the 27 Oct subset was `nvidia/nemotron-3.5-lightning-30b-a3b`). NIM `nemotron-3.5-embed-1b` makes the document embeddings.
- **Cursor** and Claude Code were used to build it; see "How we built it" in the [README](../README.md).

## Evaluations

- Last end-to-end run on Nightshift: 0% hallucination and 100% citation coverage on every scenario.
- 27 Oct 2026 subset on Nightshift (4 items): hallucination 0%, citation coverage 100%, numeric match 100%, Judge pass 100%. Report: [evals/2026-10-27-nightshift-subset.md](evals/2026-10-27-nightshift-subset.md).
- 27 Oct 2026 full set (21 items) on a test provider (Anthropic Sonnet, test switch only): hallucination 5.6% (Valencia) and 9.1% (Ahr). Almost all of the Ahr loss is one item, ahr-09, which produced no claims. Report: [evals/2026-10-27-anthropic.md](evals/2026-10-27-anthropic.md).
- Memory is switched off in evals, so seeded or approved memories can never lift a score.
- UI: all 18 UI routes were checked at 375 px with no horizontal scroll.

## Honest limits

- The insurer portfolio is synthetic and labelled so. Only Valencia has a demo book.
- GloFAS discharge is modelled, not observed, and is never an official warning. MHW is a long-term average, not a warning level.
- The Ahr gauges are state gauges, not on PEGELONLINE, so the Ahr is replay only. Ahr replay values are reanalysis and are far below published peak figures; we do not quote literature figures as values of those views.
- EFAS real-time data is for partner organisations only. We do not use it.
- Open-Meteo's free API is non-commercial. One forecast question is about 45 calls. A commercial product needs a paid plan.
- The full lane takes minutes and depends on NVIDIA rate limits. Quick, forecast and reply do not.
- Answers are English only. A German or Spanish question gets an English answer with a note.
- No flood-history documents or memories exist yet for the Saar, Ems, Rhône, Ebro or Tisza.
- Death-toll figures in the demo memories come from Wikipedia snapshots, which disagree with each other in places; see [DECK-FACTS.md](DECK-FACTS.md).
- The code has no licence file yet (the team decides).

## How to run

You need Python 3.10+, Docker Desktop, and your own local Zetaris and Nightshift (this repository starts neither).

```powershell
py tasks.py init-env
py tasks.py up-all
py tasks.py zetaris-sync
py tasks.py demo-seed
```

Then open `http://127.0.0.1:15173/`. The API is on `127.0.0.1:18000`, the engines sidecar on `127.0.0.1:8300`. Document ingest, test commands and all ports are in the [README](../README.md) and [HANDOVER.md](HANDOVER.md).

## Known issues

- The first load of live pages takes 5 to 10 seconds (Zetaris views are queried one by one).
- The Insurer Now page is dense.
- Review's Skeptic and Judge tabs are always the bundled Valencia 2024 example.
- The Sites map uses an 80 m3/s demo line, while Replay uses 100 m3/s.
- The poller container was tested only on Docker Desktop for Windows. It mounts the Docker socket, so it is for development machines only. `POLL_INTERVAL_S=0` busy-loops.
- Browser screenshots from the agent pane sometimes time out.
