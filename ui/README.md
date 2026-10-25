# UI

The insurer desk and a plain citizen page for FloodSense EU. Vite, React, and TypeScript. The screen is demo-able from fixtures shaped like the Zetaris seed views, before those views are on `main`.

Owner: Mihir until LangGraph and human-in-the-loop are done, then Zain.

## Run

From the repo root, `python tasks.py init-env` copies `ui/.env.example` when `ui/.env` is missing. Or, in this directory:

```powershell
Copy-Item .env.example .env
npm install
npm run dev
```

```bash
cp .env.example .env
npm install
npm run dev
```

`npm run build` typechecks, then builds. npm runs the `&&` in that script through `cmd.exe` on Windows, where `&&` works. Do not paste that script into PowerShell 5, which has no `&&`.

`npm run lint` is `tsc --noEmit`.

Compose publishes the dev server on host port 15173 (container port 5173). `VITE_API_URL` defaults to `http://localhost:18000`, which is the API as the browser sees it.

Do not put tokens in `ui/.env`. Vite exposes every `VITE_*` value to the browser. The NVIDIA provider key lives only in Nightshift's Providers tab. This package does not call Nightshift or Zetaris.

## What the screen does

The header has the product name, Citizen and Insurer links (`#/citizen`, `#/insurer`), a light/dark control, a notification bell, and an account icon. The theme is stored in `localStorage` under `floodsense-theme`. The first visit follows the system preference. The account control is a stub: it does not collect credentials.

The insurer desk shows:

- a schematic Valencia map with one marker per `point_id`
- a replay-date slider across the discharge dates
- a drill-down that names the `discharge_daily` columns and the hazard columns when that day is in the extract
- an evidence drawer, “Why this source”, opened from the drill-down
- a causal chain, Skeptic notes, Judge scores, and approve / edit / reject

Approve, edit, and reject stay in the browser. Nothing is sent.

The alert control steps 28–31 Oct 2024 and adds a notice if modelled discharge crosses 80 m³/s. That threshold is a demo line. `warning_level` in the hazard rows is null, and the notice is labelled a simulation.

The citizen page uses the same points, dates, and discharge series, in plain language, without the review controls.

## Fixture and live

On load the screen paints the fixtures, then checks the API.

1. `GET ${VITE_API_URL}/health` — the API on `main` returns `{"status":"ok"}`.
2. If that succeeds, it tries a JSON array at each of these paths:
   - `/views/discharge_daily`
   - `/views/hazard_timeline`
   - `/views/exposure_join`
   - `/views/provenance`

A 200 body is used only when every element has the view columns below (numbers as JSON numbers, `in_footprint` as a boolean, `warning_level` present and either a string or null). The header pill then says **Live view rows** for the views that matched. A 404, a network error, or a different shape keeps the fixture. The pill then stays **Fixture · not live**.

Those paths are a hook for later, not an API contract. The API today implements `/health` only. CORS must allow the UI origin before a browser can read even `/health`; a blocked call stays on the fixture.

The reviewed answer is always the fixture in `ui/src/fixtures/answer.json`. It uses the shared contract (`served_from`, `cached_at`, claims, citations, evidence, judge, playbook action). `served_from` is `replay` and `cached_at` is `2026-10-24T14:32:00Z`, so the insurer banner reads **cached at 14:32**. Cache and replay are never labelled live. `query_id` values in that file are fixture ids, not Zetaris query ids, and the SQL is not executed.

Skeptic notes in `ui/src/fixtures/console.ts` are display copy for this screen. They are not an agent payload and they do not choose a Nightshift lane. `model_id` on the judge fixture is the deep lane already named on the contract, so the file matches the schema. This UI does not call it.

## How the fixtures map to the views

Numbers and column names were copied on 24 Oct 2026 from `feat/zetaris-data-sync` (PR #12’s branch) and the prep CSVs on `feat/ingestion-sources-terms`. This branch does not modify those branches. When the views change, replace the JSON under `ui/src/fixtures/` and keep the column names.

| Fixture | View | Columns |
| --- | --- | --- |
| `discharge_daily.json` | `floodsense_seed.discharge_daily` (migration 012; live twin is migration 004) | `point_id`, `date`, `discharge_m3s`, `source` |
| `hazard_timeline.json` | `floodsense_seed.hazard_timeline` for 28–30 Oct 2024 (migration 013; live twin is 007) | `point_id`, `ts_utc`, `rain_mm`, `discharge_m3s`, `warning_level` |
| `exposure_join.json` | `floodsense_seed.exposure_join` (migration 016; live twin is 014) | `policy_id`, `site_id`, `lat`, `lon`, `in_footprint`, `sum_insured_eur`, `segment` |
| `provenance.json` | `floodsense_seed.provenance` (migration 017; live twin is 015) | `dataset`, `source_url`, `publisher`, `licence`, `attribution`, `fetched_at` |
| `valencia_points.json` | prep CSV `ingestion/prep/valencia_points.csv`, not a view | joins to discharge on `point_id` |

`discharge_daily.source` in the seed extract is `seed:open-meteo-flood-glofas`. The live view stamps the same series as `open-meteo-flood-glofas`. The evidence drawer explains that. `fetched_at` is the prep `accessed_at` date written as midnight UTC, which is what the provenance view does when it casts that date to a timestamp.

The discharge figures are the frozen Open-Meteo Flood (GloFAS) copy from migration 012: VAL01–VAL08, 20 Oct–5 Nov 2024, modelled, not observed. Neighbouring points can share a value because Open-Meteo snaps them to a 0.05° cell. The portfolio behind `exposure_join` is synthetic.

After PR #12 is on `main`, Zetaris has the views. This UI still will not read Zetaris itself. Point `VITE_API_URL` at an API that serves the arrays above, or keep the fixtures until that route exists. The answer banner stays on the replay fixture until a runs API returns an `Answer` with its own `served_from` and `cached_at`.

`compose.yaml` is unchanged. The UI container still runs `npm run dev` on port 5173.
