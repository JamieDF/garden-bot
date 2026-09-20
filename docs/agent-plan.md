# Garden Bot Agent — Plan

Making the bot agentic: a wake loop where an LLM observes the garden,
remembers what happened, decides what to do, and journals it all.

## Design rules

- **Provider-agnostic**: the brain is any OpenAI-compatible endpoint
  (llama-server, Ollama, hosted API). Swap via `GROW_LLM_*` env vars.
- **The LLM proposes, rules dispose**: the model narrates and suggests;
  all hardware actions pass a deterministic safety layer.
- **The journal is memory**: every wake is recorded, past entries are
  fed back to the model as short-term memory.
- **No frameworks**: the loop is plain Python (~300 lines). Structured
  output via pydantic schema -> `response_format` json_schema.

## The wake cycle

```
WAKE -> OBSERVE (sensors, stats, fan) -> RECALL (journal) ->
DECIDE (LLM, structured JSON) -> ACT (whitelist) -> JOURNAL -> SLEEP
```

Wake triggers: scheduled every `GROW_AGENT_WAKE_INTERVAL` seconds,
manual via `POST /api/agent/wake`, (later) event-driven pokes from the
poller on threshold crossings.

## Phase 0 — Foundation ✅

- `src/agent/` package: `llm.py` (client), `schemas.py` (Decision),
  `loop.py` (wake cycle), `__main__.py` (daemon)
- `agent_journal` SQLite table + `/api/agent/{status,journal,wake}`
- `garden-agent.service` systemd unit

## Phase 1 — Cute narrator (mostly done, on hosted API for now)

- ✅ Decision schema: `{mood, observation, action: none|speak, speak}`
- ✅ Observe adds external env: Open-Meteo weather (`GROW_WEATHER_LAT/LON`)
- ✅ Dashboard: bot card with narration + musings, journal feed, chat
- ⏸ llama.cpp `llama-server` + SmolLM2-135M Q4_K_M (~100MB) — deferred,
  using DeepSeek during laptop dev; config swap when on-Pi
- ⬜ Event-driven wakes from poller thresholds (last item)

## Phase 2 — Actual agent (tool-capable LLM)

- Decision schema gains real actions: `fan_on/off/auto`, `water`,
  `alert`, `log_note`, `wait` — same schema whether the backend is a
  local small model (grammar) or a hosted one (tool calling)
- Deterministic safety layer: rate limits (max 1 water/6h), sensor
  bounds, hysteresis
- Memory upgrade: journal summaries + facts table
- Eval harness: canned sensor scenarios to compare providers

## Phase 3 — Expansion

- ✅ Config-driven sensors/actuators — device registry (`devices` table,
  CRUD API, `mock` driver, per-device relay controllers incl. pumps)
- ⬜ Watering relay/pump hardware (registry + `pump` driver already supports it)
- ⬜ Vision: camera frame -> VLM (hosted or bigger local hardware)

## Hardware notes

- Pi 3B+ (1GB): runs the loop + SmolLM2-135M fine; narration quality
  is the ceiling. Real decisions need 3B+ params -> Pi 5 8GB, used
  mini PC, old phone via Termux, or hosted free tier.
- The provider abstraction means hardware upgrades are a config change.
