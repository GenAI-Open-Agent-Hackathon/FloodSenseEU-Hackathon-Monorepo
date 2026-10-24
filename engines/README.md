# engines: H-MEM and World Model sidecar

A small HTTP service next to the agents. It runs two Meterless engines and maps FloodSense onto them:

- **H-MEM** keeps what an analyst approved and recalls it on the next run. Every memory carries the Zetaris `queryId`s it came from, and the trust ledger explains why it is remembered.
- **World Model** holds the hypothesis board and the observations behind it as an append-only event log. Re-ingesting the same readings changes nothing, which is what makes the replay safe.

The engines are the Meterless reference implementations, copied unchanged into `vendor/` (Apache-2.0, see `NOTICE`). Both conformance suites pass: H-MEM 13/13, World Model 8/8.

## Run it

Needs Node.js 22.18 or newer. There are no dependencies to install.

```powershell
cd engines
npm start
```

That serves `http://127.0.0.1:8300` and keeps data in `engines/.data/` (git-ignored).

| Variable | Default | Meaning |
| --- | --- | --- |
| `ENGINES_HOST` | `127.0.0.1` | Bind address. Use `0.0.0.0` only inside a container. |
| `ENGINES_PORT` | `8300` | Port. |
| `ENGINES_DATA_DIR` | `engines/.data` | Persistence directory. `memory` keeps nothing on disk. |

There is no authentication. Keep it on loopback or on the compose network.

## Check it

```powershell
npm test            # 12 unit and HTTP tests (node:test)
npm run conformance # both Meterless conformance suites
```

`npm run typecheck` needs TypeScript and `@types/node` on the machine; it is not required to run the service.

## HTTP contract

JSON in, JSON out. Bad input is a 400 with `{ "error": ... }`.

| Method and path | Body or query | Returns |
| --- | --- | --- |
| `GET /health` | | Memory, ledger, event and hypothesis counts |
| `POST /hmem/store` | `{ runId, request, approval: { decision, by }, claims: [{ text, confidence?, citations?: [{ queryId }], entities? }] }` | `{ stored: [ids], skipped }`. `decision` is `approved`, `edited` or `rejected`; rejected runs write nothing. |
| `POST /hmem/recall` | `{ query, topN?, threshold? }` | `{ memories: [{ id, content, relevance, confidence, source, provenance }], trace }` |
| `POST /hmem/feedback` | `{ memoryId, kind }` with `kind` = `helpful`, `not_helpful` or `wrong` | New confidence |
| `GET /hmem/ledger?memoryId=` | | Ledger entries for one memory, oldest first |
| `POST /wm/observations` | `{ observations: [{ externalId, title, at, source: { kind }, type?, text?, entities? }] }` | Ingest report; `changed` is `false` on a replay |
| `POST /wm/hypotheses` | `{ runId, at, by?, hypotheses: [{ id, text, status, confidence?, concerns?: [{ type, name }], evidence? }] }` | `{ board }`. `status` is `proposed`, `supported`, `refuted` or `revised`. |
| `GET /wm/board?runId=` | | `{ board }` for one run, or all runs |
| `GET /wm/timeline?limit=` | | Latest World Model events |

`at` is the scenario clock (the replay time), not the wall clock, so a replayed run produces the same events.

## How the agents use it

- **Investigator** calls `/hmem/recall` with the question before it builds the chain, and posts hypotheses to `/wm/hypotheses`.
- **Skeptic** posts status changes (`supported`, `refuted`, `revised`) for the same hypothesis ids.
- **Learn** (after the human approves) calls `/hmem/store` with the approved claims and their citations. This is the `Memory.store` side of the `Memory` protocol in `agents/`; `Memory.recall` maps to `/hmem/recall`. The Python client lands with the agents once PR #4 is merged.

## Not done yet

- A compose service, so the agents container reaches it as `http://engines:8300`.
- A `tasks.py` step and CI job for `npm test` and `npm run conformance`.
- The reference embedder is a deterministic hash, not semantic. Swapping in real embeddings is part of the semantic cache work.
