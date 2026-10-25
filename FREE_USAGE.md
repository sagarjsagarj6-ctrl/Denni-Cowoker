# Using Dynamic Agents for free

This project can run at **zero monetary cost** in two ways: a cloud free tier
(OpenRouter `:free` models) or a fully local model (Ollama). Nothing in the
codebase requires a paid plan, and no credit card is needed for either path.

---

## Option 1 — Ollama (fully local, unlimited, the recommended setup)

The best free path is a local model: no key, no request quota, no data leaving
your machine.

### Setup

```powershell
# 1. Start the Ollama server (it listens on http://localhost:11434)
ollama serve

# 2. In a second terminal, pull a model
ollama pull qwen2.5:7b
```

`qwen2.5:7b` is the sweet spot on a normal laptop CPU. For weaker machines use
`qwen2.5:3b` or `llama3.2:3b`; with a GPU, `gemma3:12b` or `qwen2.5:14b` work well.

### Point the project at it

Either edit `.env`:

```dotenv
MODEL_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

…or use the **Setup & API Keys** panel in the web UI, choose *Ollama (local,
free)*, press **Test Connection** (it checks the server and warns you if the
model is not pulled yet), then **Save & Apply Configuration**.

The backend talks to Ollama through its OpenAI-compatible `/v1` endpoint, so no
API key is ever sent.

### Cost

$0. Unlimited requests. The only limits are your own hardware (RAM/VRAM and
speed) and disk space for the model weights.

---

## Option 2 — OpenRouter free models (cloud, ~50 requests/day)

A free OpenRouter account gives you access to every model whose ID ends in
`:free` at **$0 per token**, with these limits:

| Account state | Requests/minute | Requests/day |
|---|---|---|
| No credits purchased | 20 | 50 |
| At least $10 purchased (one-time) | 20 | 1,000 |

Verified against OpenRouter's pricing and rate-limit docs; the live counter is
readable from your key:

```powershell
Invoke-RestMethod -Uri "https://openrouter.ai/api/v1/key" -Headers @{ Authorization = "Bearer $env:OPENROUTER_API_KEY" }
```

The `free_model_daily_requests` object reports `used`, `limit`, and `remaining`
for the current UTC day.

### The catch that actually matters here

A single multi-agent run makes **many** model calls — up to 3 per specialist
agent (12 agents by default) plus the master planner and the final decision
synthesis, i.e. roughly 30–40 calls for one run. **One run can consume most of
the 50-request daily free quota**, and failed requests count against the quota
too. So the free OpenRouter tier is good for evaluation and demos, not for
continuous use.

### Free models currently available

Confirmed live in the OpenRouter catalog:

- `google/gemma-4-31b-it:free` ← **project default**
- `google/gemma-4-26b-a4b-it:free`
- `nvidia/nemotron-3-super-120b-a12b:free`
- `nvidia/nemotron-3-ultra-550b-a55b:free`
- `nvidia/nemotron-3.5-lightning:free`
- `nvidia/nemotron-3.5-content-safety:free`
- `nvidia/nemotron-3-super-vl:free`
- `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`
- `poolside/laguna-s-2.1:free`, `poolside/laguna-xs-2.1:free` (code)
- `cohere/north-mini-code:free`
- `recursive/flint-v1.0:free`
- `liquid/lfm-2.5-2.6b:free`
- `thinkingmachines/inkling:free`, `thinkingmachines/inkling-small:free`
- `dots-studio/dots-3-note-preview:free`
- `xingchen-agi/xing4.0-29b-a4b:free`

To refresh the list at any time:

```powershell
Invoke-RestMethod -Uri "https://openrouter.ai/api/v1/models" |
  Select-Object -ExpandProperty data |
  Where-Object { $_.id -like '*:free' } |
  Select-Object id
```

### Zero-config alternative: the Free Models Router

Set the model to `openrouter/free` and OpenRouter picks a free model for each
request. Convenient, but it can select a very small model that fails to
produce the strict JSON this project needs. **Pin a specific model instead**
(the default `google/gemma-4-31b-it:free`) for reliable structured output.

---

## Recommendation

| Goal | Setup |
|---|---|
| Best overall free experience | Ollama + `qwen2.5:7b` |
| Zero install, quick evaluation | OpenRouter + `google/gemma-4-31b-it:free` |
| Highest free-model quality, occasional use | OpenRouter + `nvidia/nemotron-3-super-120b-a12b:free` |
| Continuous/heavy use | Ollama — the cloud free tier cannot sustain it |

If you want more cloud headroom, one $10 top-up on OpenRouter raises the free
model ceiling to 1,000 requests/day and never expires; the $10 itself is never
spent on `:free` models.

---

## Saving tokens (matters most on the free tier)

Tune `.env` for smaller runs:

```dotenv
MAX_AGENTS_PER_RUN=6
MAX_MODEL_CALLS=40
MAX_PARALLEL_TASKS=4
KNOWLEDGE_TOP_K=5
```

---

## Troubleshooting

**"check OpenRouter usage" (HTTP 429)** — daily or per-minute free quota
exhausted. Check `free_model_daily_requests.remaining`, wait for the UTC day to
roll over, or switch to Ollama. The gateway already retries with exponential
backoff and honours `Retry-After`.

**"check that the Ollama server is running and the model is loaded"** — start
`ollama serve`, then `ollama pull <model>`. The Setup panel's **Test
Connection** button reports exactly which models the server has.

**Model returns invalid JSON** — the gateway asks for strict JSON, strips
markdown fences, scans for the first balanced JSON value, and performs one
self-repair retry. If a free model still fails, switch to a larger free model
(`gemma-4-31b-it` or `nemotron-3-super-120b-a12b`) or a local 7B model.

**Context truncation on long documents** — free endpoints sometimes expose
smaller context windows than the paid variant; chunk documents before upload.

---

## Security note

Your key lives in `.env`, which is git-ignored, and is only ever displayed
masked (`sk-or-v1-…abcd`) in the UI and logs. Provider error messages are
sanitized so keys are never written to logs or checkpoints.
