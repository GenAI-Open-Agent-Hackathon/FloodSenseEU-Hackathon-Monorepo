> Provider: Anthropic Sonnet via the test-only provider switch (`--provider anthropic`), not Nightshift. Date: 2026-10-27, live Zetaris.

# FloodSense evals — 2026-10-27 02:36 UTC

LLM `ProviderSwitch` (provider `anthropic`) · Zetaris `ZetarisClient` · targets: hallucination ≤ 5 %, coverage 100 %, numeric 100 %

## EMSR773

**hallucination 5.6%** ❌ · **coverage 100%** ✅ · **numeric 92%** ❌ · judge pass 78% (overall 0.92) · expected tokens 67% · forbidden figures 0 · repairs 2 · skeptic rejections 3 · 37.46 s/item

| id | halluc. | coverage | numeric | claims | repairs | expected | forbidden | status |
|---|---|---|---|---|---|---|---|---|
| val-01 | 25% | 100% | 75% | 4 | 1 | 0/2 | — | approved |
| val-02 | 0% | 100% | 100% | 8 | 0 | 2/2 | — | approved |
| val-03 | 0% | 100% | 100% | 8 | 0 | 1/1 | — | approved |
| val-04 | 0% | 100% | 75% | 8 | 0 | 2/2 | — | approved |
| val-05 | 0% | 100% | 100% | 7 | 0 | 2/2 | — | approved |
| val-06 | 0% | 100% | 100% | 7 | 0 | 1/1 | — | approved |
| val-07 | 0% | 100% | 100% | 3 | 0 | 0/1 | — | approved |
| val-08 | 0% | 100% | 100% | 8 | 0 | 1/1 | — | approved |
| val-09 | 25% | 100% | 75% | 4 | 1 | 0/1 | — | approved |
| val-10 | 0% | 100% | 100% | 0 | 0 | 0/0 | — | out_of_scope |

## EMSR517

**hallucination 9.1%** ❌ · **coverage 91%** ❌ · **numeric 98%** ❌ · judge pass 91% (overall 0.87) · expected tokens 43% · forbidden figures 0 · repairs 0 · skeptic rejections 11 · 29.23 s/item

| id | halluc. | coverage | numeric | claims | repairs | expected | forbidden | status |
|---|---|---|---|---|---|---|---|---|
| ahr-01 | 0% | 100% | 100% | 5 | 0 | 0/3 | — | approved |
| ahr-02 | 0% | 100% | 75% | 4 | 0 | 1/1 | — | approved |
| ahr-03 | 0% | 100% | 100% | 5 | 0 | 1/1 | — | approved |
| ahr-04 | 0% | 100% | 100% | 4 | 0 | 0/1 | — | approved |
| ahr-05 | 0% | 100% | 100% | 5 | 0 | 1/1 | — | approved |
| ahr-06 | 0% | 100% | 100% | 5 | 0 | 0/1 | — | approved |
| ahr-07 | 0% | 100% | 100% | 5 | 0 | 0/0 | — | approved |
| ahr-08 | 0% | 100% | 100% | 9 | 0 | 0/0 | — | approved |
| ahr-09 | 100% | 0% | 100% | 0 | 0 | 0/1 | — | approved |
| ahr-10 | 0% | 100% | 100% | 4 | 0 | 0/0 | — | approved |
| ahr-11 | 0% | 100% | 100% | 5 | 0 | 0/0 | — | approved |
