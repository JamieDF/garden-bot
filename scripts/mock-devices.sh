#!/usr/bin/env bash
# Configure mock devices on a dev API (laptop testing, no Pi hardware).
# Usage: ./scripts/mock-devices.sh [api_url]   (default http://localhost:8000)
#
# Switches the seeded sensors to the 'mock' driver (fake drifting values),
# adds a moisture sensor and a water pump relay. Idempotent - safe to re-run.
set -e
API="${1:-http://localhost:8000}"

put() { curl -sf -X PUT "$API/api/devices/$1" -H 'Content-Type: application/json' -d "$2" > /dev/null && echo "updated $1"; }
post() { curl -sf -X POST "$API/api/devices" -H 'Content-Type: application/json' -d "$1" > /dev/null && echo "added $(echo "$1" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)"; }

put inside_climate '{"name":"inside_climate","label":"Inside Climate","driver":"mock","params":{"temperature":22,"humidity":58,"pressure":1012},"location":"inside","enabled":true}'
put inside_air    '{"name":"inside_air","label":"Inside Air","driver":"mock","params":{"temperature":23},"location":"inside","enabled":true}'
put outside_air   '{"name":"outside_air","label":"Outside Air","driver":"mock","params":{"temperature":14},"location":"outside","enabled":true}'
post '{"name":"bed_a_moisture","label":"Bed A Moisture","driver":"mock","params":{"moisture":34},"location":"bed a","enabled":true}' || true
post '{"name":"water_pump","label":"Water Pump","driver":"pump","params":{"pin":18,"watch":"bed_a_moisture.moisture"},"location":"bed a","enabled":true}' || true

echo "done - readings flow on the next poll cycle"
