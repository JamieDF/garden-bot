# Garden Bot

Raspberry Pi-based indoor growing monitoring and automation system.

## Features

- BME280 sensor (temperature, humidity, pressure)
- DS18B20 temperature probes (inside/outside air)
- Pi Camera 2 video streaming
- FastAPI backend with SQLite storage
- React dashboard with Tailwind CSS and Recharts
- Multi-client MJPEG streaming
- Chart switching (temperature, humidity, pressure)

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

## Configuration

Environment variables (prefix with `GROW_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `GROW_DATABASE_PATH` | `/var/lib/garden-bot/readings.db` | SQLite database path |
| `GROW_POLL_INTERVAL` | `30` | Seconds between readings |
| `GROW_BME280_ADDRESS` | `118` (0x76) | I2C address |
| `GROW_LOG_LEVEL` | `INFO` | Logging level |

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard |
| GET | `/api/readings` | Current sensor values |
| GET | `/api/readings/latest` | Most recent reading per sensor |
| GET | `/api/history` | Historical readings |
| GET | `/stream.mjpg` | Live camera MJPEG stream |
| GET | `/health` | Service health check |

### History Query

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
| `inside_humidity` | BME280 humidity | % |
| `inside_pressure` | BME280 pressure | hPa |

## Services

```bash
# View logs
sudo journalctl -u sensor-poller -f
sudo journalctl -u garden-api -f

# Restart services
sudo systemctl restart sensor-poller
sudo systemctl restart garden-api

# Check status
systemctl status sensor-poller
systemctl status garden-api
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
│   │   ├── database.py          # SQLite ops
│   │   ├── poller.py            # Sensor polling daemon
│   │   ├── sensors/             # BME280, DS18B20 drivers
│   │   ├── camera/              # MJPEG streaming
│   │   └── routers/             # API endpoints
│   ├── services/                # systemd units
│   └── requirements.txt
├── frontend/                    # Vite/React app
│   ├── src/
│   └── vite.config.ts
└── scripts/
    └── setup-pi.sh             # Full Pi setup script
```
