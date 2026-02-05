# HelloCubic Amplifier Display

**Date**: 2026-02-03
**Status**: Design complete, ready for implementation

## Overview

A cyberpunk-styled animated bot character displayed on a GeekMagic HelloCubic-Lite holographic crystal, controlled by Amplifier to show system status during the morning routine.

## Character Design

**Style**: Cute android face with cyberpunk aesthetics
- Expressive eyes (large, emotive)
- Soft geometric face shape
- Neon accents (cyan/magenta primary)
- Circuit pattern details
- Glitchy transitions between states

**Emotional range**: Full expressions
- Animated eyes, mouth, and features
- Glitch effects during state transitions
- Subtle idle animations (breathing, blinking)

## Animation States

| State | Trigger | Visual |
|-------|---------|--------|
| `waking` | Morning routine starts | Eyes opening, boot sequence, scan lines clearing |
| `syncing` | Pulling reminders/notes | Eyes scanning side-to-side, data streams |
| `thinking` | Generating dashboard/daily note | Processing animation, pupils spinning, glitch fragments |
| `ready` | Routine complete | Happy expression, soft glow, alert posture |
| `idle` | Nothing happening | Subtle breathing, occasional blink, ambient glow pulse |

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Amplifier                                                  │
│                                                             │
│  tool-hellocubic                                            │
│    └─ set_state(state: str) → POST to cube                  │
│                                                             │
│  Morning routine recipe calls:                              │
│    1. hellocubic state=waking                               │
│    2. hellocubic state=syncing                              │
│    3. hellocubic state=thinking                             │
│    4. hellocubic state=ready                                │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼ HTTP POST (GIF upload)
┌─────────────────────────────────────────────────────────────┐
│  HelloCubic-Lite @ 192.168.x.x                              │
│                                                             │
│  ESPHome firmware                                           │
│    - ST7789 display driver                                  │
│    - HTTP server for GIF upload                             │
│    - Optional: MQTT for push updates                        │
│                                                             │
│  Display: 240x240 holographic crystal                       │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Hardware Setup
1. Connect HelloCubic to WiFi (stock firmware)
2. Test GIF upload via web UI
3. Verify HTTP POST works programmatically

### Phase 2: Firmware
1. Flash ESPHome firmware
2. Configure display driver (ST7789)
3. Set up HTTP endpoint for state changes
4. Optional: Add MQTT support

### Phase 3: Animations
1. Create 240x240 GIF animations for each state
2. Cyberpunk color palette: cyan (#00FFFF), magenta (#FF00FF), dark background
3. Test on actual hardware, adjust timing

### Phase 4: Amplifier Integration
1. Create `tool-hellocubic` module
2. Update morning routine recipe to call tool
3. Test end-to-end

## File Structure

```
amplifier-bundle-joi/
└── modules/
    └── tool-hellocubic/
        ├── __init__.py
        ├── tool.py          # Amplifier tool implementation
        └── animations/
            ├── waking.gif
            ├── syncing.gif
            ├── thinking.gif
            ├── ready.gif
            └── idle.gif
```

## Hardware Specs

- **Device**: GeekMagic HelloCubic-Lite
- **Chip**: ESP32-WROOM-32
- **Display**: ST7789 240x240 TFT
- **Connection**: USB-C (power + serial for flashing)
- **Network**: 2.4GHz WiFi only

## References

- [ESPHome ST7789 config](https://gist.github.com/kmplngj/c02d0f3e0d68ad97dc4c2fcd3a0edb51)
- [GeekMagic-Open-Firmware](https://github.com/Times-Z/GeekMagic-Open-Firmware)
- [Home Assistant thread](https://community.home-assistant.io/t/installing-esphome-on-geekmagic-smart-weather-clock-smalltv-pro/618029)
