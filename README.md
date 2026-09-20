# Garden Bot

Raspberry Pi-based indoor growing monitoring and automation system.

## Features

- Configurable device registry - sensors, relays, cameras defined in the DB
  and editable from the UI (BME280, DS18B20, mock, relay actuators)
- Pi Camera 2 video streaming (placeholder stream when off-Pi)
- FastAPI backend with SQLite storage
- React dashboard: editable widget canvas (drag/resize/add), devices and
  ask pages, Recharts history
- Agent wake loop with provider-agnostic LLM + Open-Meteo weather context
  (see `docs/agent-plan.md`): narrates, answers questions, remembers facts,
  and can act on devices (`fan_*`, `water`) behind a deterministic safety
  layer - rate limits, soil-wetness veto, timed pump runs
- Event-driven wakes - the poller pokes the agent on actuator flips,
  metric swings, and sensor failures
- `mock` driver + laptop test setup for developing without Pi hardware

## Hardware

| Sensor | Model | Location | Interface |
|--------|-------|----------|-----------|
| BME280 | BME280 | Inside tent | I2C (0x76) |
| DS18B20 | x2 | Inside/outside air | 1-Wire |
| Camera | Pi Camera 2 | Inside tent | CSI |

## Quick Start

### Clone and Setup (fresh Pi)

```bash
git clone https://github.com/JamieDF/garden-bot.git
cd garden-bot
bash scripts/setup-pi.sh
```

Dashboard available at `http://<pi-ip>:8000`

### Update

```bash
cd ~/garden-bot
git pull
bash scripts/setup-pi.sh
```

### Development (on local machine)

```bash
# Clone
git clone https://github.com/JamieDF/garden-bot.git
cd garden-bot

# Rsync to Pi (exclude venv/node_modules)
rsync -av --exclude='.venv' --exclude='node_modules' pi/ pi@<pi-ip>:~/garden-bot/pi/
rsync -av --exclude='node_modules' frontend/ pi@<pi-ip>:~/garden-bot/frontend/

# On Pi - rebuild and restart
ssh pi@<pi-ip>
cd ~/garden-bot && bash scripts/setup-pi.sh
```

### Laptop testing (no Pi hardware)

The `mock` device driver produces fake drifting sensor values, and the camera
stream falls back to a placeholder frame when `rpicam-vid` isn't installed.
Relays no-op safely without GPIO.

```bash
# 1. API (uses .env for LLM config if present)
cd pi && uvicorn src.main:app --port 8000

# 2. Mock devices - fake sensors + a pump
./scripts/mock-devices.sh

# 3. Poller - generates readings every 30s
cd pi && python -m src.poller

# 4. Agent daemon - wakes the bot every GROW_AGENT_WAKE_INTERVAL seconds
cd pi && python -m src.agent

# 5. Frontend - proxies API/stream to localhost:8000
cd frontend && PI_HOST=127.0.0.1 npm run dev
```

Add more fake sensors via the Devices page or the API — driver `mock`,
`params` maps metric names to base values, e.g. `{"temperature": 22, "humidity": 60}`.

## Configuration

Environment variables (prefix with `GROW_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `GROW_DATABASE_PATH` | `/var/lib/garden-bot/readings.db` | SQLite database path |
| `GROW_POLL_INTERVAL` | `30` | Seconds between readings |
| `GROW_BME280_ADDRESS` | `118` (0x76) | I2C address |
| `GROW_LOG_LEVEL` | `INFO` | Logging level |
| `GROW_LLM_ENABLED` | `false` | Enable the agent wake loop |
| `GROW_LLM_BASE_URL` | `http://localhost:8080/v1` | Any OpenAI-compatible endpoint |
| `GROW_LLM_MODEL` | `smollm2-135m` | Model name to request |
| `GROW_LLM_API_KEY` | `none` | Bearer token if provider needs one |
| `GROW_AGENT_WAKE_INTERVAL` | `1800` | Seconds between agent wakes |
| `GROW_AGENT_EVENT_WAKE_MIN` | `300` | Min seconds between event-triggered wakes (threshold flips, swings, sensor failures) |
| `GROW_WEATHER_LAT` / `GROW_WEATHER_LON` | unset | Coordinates for Open-Meteo; agent observes weather when set |

The agent works with llama.cpp `llama-server`, Ollama, or hosted APIs
(tested with DeepSeek). Point `GROW_LLM_BASE_URL` at any of them.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard |
| GET | `/api/readings/current` | Latest value per device metric |
| GET | `/api/readings` | Current values (legacy shape) |
| GET | `/api/readings/latest` | Most recent reading per sensor |
| GET | `/api/history` | Historical readings |
| GET | `/api/stats` | Min/max stats for 24h, 7d, 30d |
| GET | `/api/devices` | All configured devices |
| POST | `/api/devices` | Create a device |
| PUT | `/api/devices/{name}` | Update a device |
| DELETE | `/api/devices/{name}` | Delete a device |
| GET | `/api/devices/{name}/state` | Actuator/sensor state |
| POST | `/api/devices/{name}/action` | Actuator on/off/auto/manual |
| GET | `/api/fan` | Default fan state (adapter) |
| POST | `/api/fan` | Manual fan on/off |
| PUT | `/api/fan/auto` | Auto mode + thresholds |
| GET | `/api/dashboard/layout` | Widget canvas layout |
| PUT | `/api/dashboard/layout` | Save widget canvas layout |
| GET | `/api/agent/status` | Agent config and runtime state |
| GET | `/api/agent/journal` | Agent journal entries |
| POST | `/api/agent/wake` | Trigger an agent wake manually |
| POST | `/api/agent/chat` | Ask the bot a question |
| GET | `/stream.mjpg` | Live camera MJPEG stream |
| GET | `/health` | Service health check |

### History Query

```
GET /api/history?sensor=inside_air.temperature&from_time=2024-01-01T00:00:00&limit=5000
```

## Data Model

### Reading

```json
{
  "id": 123,
  "timestamp": "2024-01-01T12:00:00",
  "sensor": "inside_air.temperature",
  "value": 24.5,
  "unit": "°C"
}
```

### Devices

Devices live in the `devices` table; each has a `name`, `label`, `driver`,
`params` (JSON), `location`, and `enabled` flag. Sensor readings are keyed
`{device}.{metric}` — e.g. `inside_air.temperature`, `bed_a_moisture.moisture`.

| Driver | Kind | Params example |
|--------|------|----------------|
| `bme280` | sensor | `{"bus": 1, "address": 118}` |
| `ds18b20` | sensor | `{"index": 0}` or `{"id": "28-xxx"}` |
| `mock` | sensor | `{"temperature": 22, "humidity": 60}` |
| `fan` / `pump` | actuator | `{"pin": 17, "watch": "inside_air.temperature", "on_threshold": 20, "off_threshold": 19}` |
| `camera` | stream | `{"width": 640, "height": 480, "fps": 15}` |

Actuator `watch` points at a `{device}.{metric}` key; auto mode drives it
between `on_threshold`/`off_threshold` deterministically.

## Services

```bash
# View logs
sudo journalctl -u sensor-poller -f
sudo journalctl -u garden-api -f
sudo journalctl -u garden-agent -f

# Restart services
sudo systemctl restart sensor-poller
sudo systemctl restart garden-api
sudo systemctl restart garden-agent

# Check status
systemctl status sensor-poller
systemctl status garden-api
systemctl status garden-agent
```

## Database

SQLite at `/var/lib/garden-bot/readings.db`

## Project Structure

```
garden-bot/
├── pi/
│   ├── src/
│   │   ├── main.py              # FastAPI entry + serves frontend
│   │   ├── config.py            # Settings from env
│   │   ├── database.py          # SQLite ops (readings, devices, journal)
│   │   ├── registry.py          # device -> driver/actuator instances
│   │   ├── poller.py            # Sensor polling daemon
│   │   ├── weather.py           # Open-Meteo fetch for agent observe()
│   │   ├── agent/               # LLM agent wake loop
│   │   ├── sensors/             # bme280, ds18b20, mock, fan/pump drivers
│   │   ├── camera/              # MJPEG streaming (+ off-Pi placeholder)
│   │   └── routers/             # API endpoints
│   ├── services/                # systemd units
│   └── requirements.txt
├── frontend/                    # Vite/React app
│   ├── src/
│   └── vite.config.ts
├── docs/
│   ├── wiring.md               # GPIO wiring reference
│   └── agent-plan.md           # Agent design + phases
└── scripts/
    ├── setup-pi.sh             # Full Pi setup script
    ├── mock-devices.sh         # Configure mock devices for laptop testing
    └── eval-agent.py           # Canned scenarios through decide() + safety
```
