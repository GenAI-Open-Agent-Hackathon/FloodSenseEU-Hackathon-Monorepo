# Deploy the judge demo on Nebius AI Cloud

One VM (or DevPod with Docker), one command, a login in front. Nothing here has been run on a real
Nebius VM yet: the files were validated offline (compose parses, Caddyfile validates, scripts lint).
Treat the first deploy as the test, and run the smoke script before you send the link.

## What runs

| Service | Role | Published |
|---|---|---|
| `proxy` (Caddy) | Basic-auth login, TLS when a domain is set, 32 KB request cap, `/api/*` to API, rest to UI | 80, 443 |
| `ui` | Vite dev server (`ui/Dockerfile` as is) built with `VITE_API_URL=/api` | no |
| `api` | FastAPI, rate limits, semantic cache, replay | no |
| `agents` | LangGraph agents, `LLM_BACKEND=nebius` (Token Factory), `ZETARIS_MODE=fake` | no |
| `redis` | Cache and replay recordings, 128 MB LRU, no persistence | no |

Not started: Zetaris, `engines` (H-MEM stays off), `pgvector` (RAG stays off), `pegel-poller` (it needs the Docker
socket and Zetaris). The file is `compose.hosted.yaml`; the project is `floodsense-hosted`, separate from the dev stack.

## Which lanes work hosted

Zetaris is not reachable from the cloud, so the agents run on the offline stand-in ("Demo data": seeded tables,
no live Zetaris views). Chat answers are real model calls through Nebius Token Factory.

| Lane / feature | Hosted | Notes |
|---|---|---|
| Front door (small talk) | works | model call, cheap |
| Quick lane, forecast lane | works on Demo data | public sources (Open-Meteo, PEGELONLINE) are called from the VM if the lane fetches them directly; Zetaris-backed views fall back to the stand-in |
| Full lane (Watchers, Investigator, Skeptic, Judge, approval) | works on seeded data | answers are about the seed data, not live gauges |
| Past flood replay, cached answers, labelled replay | works | `FF_SEMANTIC_CACHE` and `FF_CACHED_REPLAY` on; labelled "not live" |
| Live German gauges, Zetaris `/views` with live tables | not available | needs Zetaris |
| H-MEM, World Model, RAG docs | off | need `engines` / `pgvector` |
| Tavily web context | optional | set `TAVILY_API_KEY` and `FF_TAVILY=true` |

Not verified: exactly which UI panels show "unavailable" with the stand-in. Click through once as a judge would.

## Steps

1. **Create the VM** in the Nebius console: Ubuntu 22.04, 2 vCPU / 8 GB RAM / 40 GB disk is enough (no GPU; models run in
   Token Factory). Add your SSH key and a public IP. Security group: allow 22 (your IP only), 80, and 443 if you use a domain.
   A DevPod with Docker works the same; expose port 80.
2. **Install Docker** (on the VM):
   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker $USER && newgrp docker
   docker compose version   # must be v2.x
   ```
3. **Clone**:
   ```bash
   git clone https://github.com/GenAI-Open-Agent-Hackathon/FloodSenseEU-Hackathon-Monorepo.git
   cd FloodSenseEU-Hackathon-Monorepo
   cp deploy/hosted/hosted.env.example deploy/hosted/hosted.env
   ```
4. **Judge login**: `python3 scripts/hosted_auth.py` prints `JUDGE_USER`, `JUDGE_HASH` and the plain password. Paste the two
   env lines into `deploy/hosted/hosted.env`. Keep the password for step 8. (The hash line stays in single quotes.)
5. **Fill the env file**: `NEBIUS_API_KEY`, optionally `TAVILY_API_KEY`, `WATCH_ADMIN_TOKEN` (long random string,
   `openssl rand -hex 24`). For HTTPS set `SITE_ADDRESS=demo.example.org` after pointing its A record at the VM IP; Caddy
   fetches the certificate on first start. Otherwise leave `:80`.
6. **Start**:
   ```bash
   docker compose -f compose.hosted.yaml --env-file deploy/hosted/hosted.env -p floodsense-hosted up -d --build
   docker compose -f compose.hosted.yaml --env-file deploy/hosted/hosted.env -p floodsense-hosted ps
   ```
7. **Verify with curl**:
   ```bash
   curl -i http://VM_IP/healthz                       # 200 ok (no login)
   curl -i http://VM_IP/api/health                    # 401 without login
   curl -u judge:PASSWORD http://VM_IP/api/health     # {"status":"ok",...}
   curl -u judge:PASSWORD http://VM_IP/api/config     # "llm_backend":"nebius"
   curl -u judge:PASSWORD http://VM_IP/api/platform/status
   ```
8. **Smoke test** (stdlib only, from your laptop or the VM):
   ```bash
   python3 scripts/smoke_hosted.py http://VM_IP --user judge --password PASSWORD
   ```
   It checks liveness, login, API health, backend `nebius`, UI, one real question (this spends a few Token Factory calls) and
   that the operator switch is blocked. A 429 means the cap is working; wait a minute.
9. **Give judges the login**: send `http://VM_IP` (or the domain), user and password through a private channel, plus the
   end date (15 Dec). Open the URL yourself first and ask one question in each desk.
10. **After 15 Dec**: `docker compose -f compose.hosted.yaml -p floodsense-hosted down` and delete the VM. Rotate or delete the
    Token Factory key.

Logs: `docker compose -f compose.hosted.yaml -p floodsense-hosted logs -f agents api proxy`.
Update: `git pull` then rerun the `up -d --build` line.

## Caps

| Cap | Where | Default | Effect |
|---|---|---|---|
| Login | Caddy `basic_auth` | env | Nothing but `/healthz` is reachable without it |
| `FF_AUTO_ASSESS=false`, `WATCH_AUTO_PER_HOUR/DAY=0` | compose (fixed, not in env file) | off | The control tower never starts a model run by itself |
| `/api/watch/auto-assess`, `/api/watch/cycle` | Caddy 403 | blocked | Judges cannot switch auto-assess on; `WATCH_ADMIN_TOKEN` is a second lock |
| `RATE_LIMIT_RUNS_PER_MIN` | api | 4 | Token bucket on `POST /runs`. Every judge shares the proxy IP, so this is a global limit |
| `RATE_LIMIT_MAX_CONCURRENT_RUNS` | api | 2 | Live runs in flight; 429 with Retry-After |
| `NIGHTSHIFT_MAX_CONCURRENCY`, `NIGHTSHIFT_RPM` | agents | 2, 20 | Process-wide model calls in flight and starts per minute (applies to the Nebius client too) |
| `LLM_MAX_TOKENS_FAST/DEEP` | agents | 4000, 5000 | Completion ceiling per call. Too low can truncate reasoning models; raise if answers fail |
| `SKEPTIC_MAX_ROUNDS=1`, `JUDGE_REPAIR_ROUNDS=0` | agents | 1, 0 | Fewer calls per full run |
| `FF_SEMANTIC_CACHE`, `FF_CACHED_REPLAY` | api, agents | true | Repeat questions cost nothing; failures fall back to a labelled replay |
| Request size | Caddy `request_body` | 32 KB | Larger bodies rejected |
| Redis | compose | 128 MB LRU, no disk | Bounded memory |
| `WATCH_INTERVAL_S` | agents | 1800 | Rule-based scan, no model calls; Open-Meteo calls only |

Also set a spend limit or budget alert on the Nebius project in the console. These caps bound the rate, not the total.
Worst case per day is roughly `RATE_LIMIT_RUNS_PER_MIN x 1440` runs; use the worksheet to turn that into money.

## Cost estimate worksheet

Fill the blanks from the Nebius price page and from `GET /api/platform/status` after a test session. Prices are not
filled in here on purpose.

| Symbol | Meaning | Value |
|---|---|---|
| `P_vm` | VM price per hour | ____ |
| `H` | hours the VM runs (e.g. now to 15 Dec) | ____ |
| `P_disk` | disk + public IP per month | ____ |
| `M` | months | ____ |
| `Pin_f`, `Pout_f` | fast model price per 1M input / output tokens | ____ / ____ |
| `Pin_d`, `Pout_d` | deep model price per 1M input / output tokens | ____ / ____ |
| `calls_q`, `calls_f` | model calls per quick / full run (measure in a test) | ____ / ____ |
| `tin`, `tout` | average input / output tokens per call (measure) | ____ / ____ |
| `Rq`, `Rf` | expected quick / full runs per day | ____ / ____ |
| `D` | days open to judges | ____ |
| `hit` | cache hit rate 0..1 (`/api/platform/status`) | ____ |

```
infra   = P_vm * H + P_disk * M
cost_call(fast) = tin/1e6 * Pin_f + tout/1e6 * Pout_f      (same for deep with the _d prices)
cost_quick = calls_q * cost_call(fast)
cost_full  = calls_f * (mix of fast and deep calls, each at its own cost_call)
llm     = D * (1 - hit) * (Rq * cost_quick + Rf * cost_full)
total   = infra + llm
ceiling = D * 1440 * RATE_LIMIT_RUNS_PER_MIN * cost_full * (1 - hit)   # absolute worst case under the cap
```

If `ceiling` is above the credits you are willing to burn, lower `RATE_LIMIT_RUNS_PER_MIN` or the token ceilings.
