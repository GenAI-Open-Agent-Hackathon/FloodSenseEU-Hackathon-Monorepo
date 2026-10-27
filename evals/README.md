# Evals

Owners: Saleeta, Zain, Mihir (docs/OWNERSHIP.md). Two real floods, at least 10 items each (gameplan §11).

- `valencia_2024.yaml` — Copernicus EMSR773, 29 Oct 2024
- `ahr_2021.yaml` — Copernicus EMSR517, 14–15 Jul 2021
- `insurer_docs.yaml` — layer (c) insurer and authority documents, own aggregate
- `run_evals.py` — runs every item through the graph (auto-approving at the interrupt), reports the Judge metrics per item and per event

```bash
python evals/run_evals.py --out reports/evals.md            # both events; fakes when no credentials are set
python evals/run_evals.py --event EMSR773 --strict          # exit 1 when a target is missed (CI)
python evals/run_evals.py --items val-01,ahr-01               # only these items
python evals/run_evals.py --provider anthropic               # a test provider (needs LLM_PROVIDER_SWITCH); default is Nightshift
```

Headline number: **hallucination rate** = claims the Judge marks unsupported / all claims (target ≤ 5 %). Also citation
coverage (target 100 %), numeric accuracy (100 %), Judge pass rate, Skeptic rejections, repair rounds.

Item fields: `question`, optional `replay_ts` (what the run may know), `expect` (tokens a good answer states, whole-token
match against summary + claims + playbook), `forbid` (figures that must not appear, e.g. casualty numbers that are not in
our views). The `expect` / `forbid` tokens were written against the seed views; Saleeta and Urvashi validate them against the
ingested sources and add the reference answers and human labels per claim for the Judge–human agreement rate.

`insurer_docs.yaml` (`ins-01` to `ins-03`, run with `--set insurer_docs`, or by default with everything) is a separate block
with its own aggregate. Its items add `doc_query` (passed to the run so the Investigator calls `retrieve_docs`) and `expect_source` (the corpus URL a cited claim should carry, reported as `source_cited`). They need `FF_RAG_DOCS` on and the corpus ingested.

The report header names the provider. Numbers from a test provider are not the judged Nightshift path; say which one you report.
