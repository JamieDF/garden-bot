# Garden Bot

Raspberry Pi-based indoor growing monitoring and automation system.

## Features

- BME280 sensor (temperature, humidity, pressure)
- DS18B20 temperature probes (inside/outside air)
- Pi Camera 2 video streaming
- FastAPI backend with SQLite storage
- Vite/React dashboard with Tailwind CSS and Recharts
- Multi-client MJPEG streaming
- Chart switching (temperature, humidity, pressure)

## Hardware

| Sensor | Model | Location | Interface |
|--------|-------|----------|-----------|
| BME280 | BME280 | Inside tent | I2C |
| DS18B20 | x2 | Inside/outside air | 1-Wire |
| Camera | Pi Camera 2 | Inside tent | CSI |

## Quick Start

### Pi Setup

```bash
# Clone onto Pi
git clone https://github.com/JamieDF/garden-bot.git
cd garden-bot

# Run setup script
bash scripts/setup-pi.sh

# Start services
sudo systemctl enable --now sensor-poller
sudo systemctl enable --now garden-api
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Configuration

Environment variables (prefix with `GROW_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sensors.db` | SQLite database path |
| `POLL_INTERVAL` | `30` | Seconds between readings |
| `BME280_ADDRESS` | `0x76` | I2C address |
| `LOG_LEVEL` | `INFO` | Logging level |

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/readings` | Current sensor values |
| GET | `/api/readings/latest` | Most recent reading per sensor |
| GET | `/api/history` | Historical readings |
| GET | `/stream.mjpg` | Live camera MJPEG stream |
| GET | `/health` | Service health check |

### History Query Parameters

```
GET /api/history?sensor=inside_air_temp&from_time=2024-01-01T00:00:00&limit=5000
```

## Data Model

### Reading

```json
{
  "id": 123,
  "timestamp": "2024-01-01T12:00:00",
  "sensor": "inside_air_temp",
  "value": 24.5,
  "unit": "°C"
}
```

### Sensors

| Sensor Name | Description | Unit |
|-------------|-------------|------|
| `inside_air_temp` | DS18B20 inside air temp | °C |
| `outside_air_temp` | DS18B20 outside air temp | °C |
| `inside_temp` | BME280 inside temp | °C |
| `inside_humidity` | BME280 humidity | % |
| `inside_pressure` | BME280 pressure | hPa |

## Database

SQLite at `~/garden-bot/data/readings.db`

```sql
CREATE TABLE readings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL,
  sensor TEXT NOT NULL,
  value REAL NOT NULL,
  unit TEXT NOT NULL
);
```

## Services (systemd)

- `sensor-poller.service` — polls sensors every 30s, writes to DB
- `garden-api.service` — FastAPI server

```bash
sudo systemctl restart sensor-poller
sudo systemctl restart garden-api
sudo journalctl -u sensor-poller -f  # follow logs
```

## Pi Setup Requirements

1. Enable I2C: `raspi-config` → Interface Options → I2C
2. Enable 1-Wire: `raspi-config` → Interface Options → 1-Wire
3. Enable camera: `raspi-config` → Interface Options → Camera
4. Install deps: `pip install -r pi/requirements.txt`

## Project Structure

```
Garden_Bot/
├── pi/
│   ├── src/
│   │   ├── main.py              # FastAPI entry
│   │   ├── config.py            # Settings
│   │   ├── database.py          # SQLite ops
│   │   ├── poller.py            # Sensor polling
│   │   ├── sensors/             # BME280, DS18B20 drivers
│   │   ├── camera/              # MJPEG streaming
│   │   └── routers/             # API endpoints
│   └── services/                # systemd units
├── frontend/                    # Vite/React app
└── scripts/                     # Setup scripts
```
