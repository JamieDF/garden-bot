# Wiring Diagram

## BME280 / BMP280 Sensor (x2)

```
                         Raspberry Pi 3B
                       ┌────────────────┐
                       │                │
    ┌─────────┐        │   3.3V  [1]  ○  │
    │         │        │   GND   [6]  ○──┼──────┐
    │  BME280 │        │   SDA   [3]  ○──┼──────┤
    │  (or    │        │   SCL   [5]  ○──┼──────┤
    │  BMP280)│        │                │      │
    │         │        │   GPIO4  [7]  ○──────┤
    └────┬────┘        │                │      │
         │             │                │      │
         │             └────────────────┘      │
         │                                      │
         │         4.7kΩ pull-up (between SDA and 3.3V)
         │         4.7kΩ pull-up (between SCL and 3.3V)
         │
         │  ┌───────────────────────────────────┐
         │  │  BME280 #1 (Inside Tent)        │
         │  │  Address: 0x76 (default)         │
         │  └───────────────────────────────────┘
         │
         │  ┌───────────────────────────────────┐
         │  │  BME280 #2 (Outside Tent)        │
         │  │  Address: 0x77 (via ADR jumper)  │
         │  └───────────────────────────────────┘
```

### BME280 Pinout (top view)

```
     ┌──────┐
     │ BME  │
     │ 280  │
     └────┘
      ↓↓↓↓↓
     VCC GND SDA SCL
     
Pin 1: VCC  → 3.3V (Pi pin 1)
Pin 2: GND  → GND (Pi pin 6)
Pin 3: SDA  → SDA (Pi pin 3) + 4.7kΩ pull-up to 3.3V
Pin 4: SCL  → SCL (Pi pin 5) + 4.7kΩ pull-up to 3.3V
```

### Two BME280s on same bus

| BME280 #1 (Inside) | BME280 #2 (Outside) | Pi Pin |
|--------------------|---------------------|--------|
| VCC                | VCC                 | 3.3V (1) |
| GND                | GND                 | GND (6) |
| SDA                | SDA                 | SDA (3) |
| SCL                | SCL                 | SCL (5) |

**Important:** They need different I2C addresses. If both are 0x76:
- BME280 #1: use as-is (0x76)
- BME280 #2: bridge the ADR solder pad to change to 0x77

Check your module's datasheet for the ADR jumper location.

---

## DS18B20 Temperature Probe (x1)

```
                         Raspberry Pi 3B
                       ┌────────────────┐
                       │                │
    ┌─────────────┐    │   3.3V  [1]  ○──┼──────────┐
    │ DS18B20     │    │   GND   [6]  ○──┼──────────┤
    │  (Air)      │    │                │          │
    │  red   VCC  │    │   GPIO4  [7]  ○──┼──────────┤
    │  yellow DATA │    │                │          │
    │  black   GND │    │                │          │
    └──────────────┘    └────────────────┘          │

    4.7kΩ pull-up resistor between DATA and 3.3V
```
                         Raspberry Pi 3B
                       ┌────────────────┐
                       │                │
    ┌─────────────┐    │   3.3V  [1]  ○──┼──────────┐
    │ DS18B20 #1  │    │   GND   [6]  ○──┼──────────┤
    │  (Air)      │    │                │          │
    │  red   VCC  │    │   GPIO4  [7]  ○──┼──────────┤
    │  yellow DATA │    │                │          │
    │  black   GND │    │                │          │
    └──────┬──────┘    │                │          │
           │           └────────────────┘          │
           │                                      │
           │         ┌────────────────────────────┘
           │         │
           │         ├──── 4.7kΩ resistor (pull-up between DATA and VCC)
           │         │
           ├─────────┴─────── Yellow (DATA) → GPIO 4
           │                    Red (VCC) → 3.3V
           │                    Black (GND) → GND
           │
           └────────────────── Same wiring for DS18B20 #2 (Soil)

    Multiple probes can share the same 3.3V and GND wires (parallel wiring)
```

### DS18B20 Probe Wire Colors

| Wire Color | Function | Connect To |
|------------|----------|------------|
| Red        | VCC (power) | 3.3V |
| Black      | GND (ground) | GND |
| Yellow/White | DATA (1-Wire) | GPIO 4 + 4.7kΩ pull-up to 3.3V |

### DS18B20 Connection Options

**Option A: Individual probes (cleaner)**
- Each probe has its own 3.3V, GND, and DATA wire
- All DATA wires connect to GPIO 4 (with shared pull-up)
- All 3.3V wires connect to 3.3V
- All GND wires connect to GND

**Option B: Shared bus (longer runs)**
- Single pair of 3.3V and GND wires from Pi
- Both DATA wires connected to GPIO 4
- 4.7kΩ pull-up between DATA and 3.3V

---

## Quick Reference: All Pi GPIO Pins Used

```
    3.3V  (1) ○──────────────┬── BME280 VCC
                              │
    GND   (6) ○───────────────┼── BME280 GND
                              │     DS18B20 GND (both)
                              │
    SDA   (3) ○──┬────────────┼── BME280 SDA
                 │            │     (pull-up 4.7kΩ to 3.3V)
                 │            │
    SCL   (5) ○──┴────────────┼── BME280 SCL
                              │     (pull-up 4.7kΩ to 3.3V)
                              │
   GPIO4  (7) ○───────────────┼── DS18B20 DATA
                              │     (pull-up 4.7kΩ to 3.3V)
                              │
    3.3V  (1) ○───┬────────────┘
                  │
                  └──DS18B20 VCC (both probes)

```

---

## Pull-up Resistor Note

The 4.7kΩ pull-up resistors are required for I2C (SDA/SCL) and 1-Wire (DATA). Without them, the sensors won't communicate reliably.

You can buy pre-assembled BME280 modules that include the pull-up resistors on the board — check before adding external ones.
