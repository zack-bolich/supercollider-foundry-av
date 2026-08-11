# Infernal Foundry // Machine War

An original live audiovisual battle between two infernal scrapyard robots. The characters are procedurally modeled and exported from Blender, rendered and articulated in Three.js, and driven by SuperCollider OSC or the public browser-audio arrangement.

**Public:** https://zack-bolich.github.io/supercollider-foundry-av/

Click **START MACHINE WAR** on the public page to run the 164 BPM industrial drum/bass/metal arrangement and robotic German voice. Browser autoplay policy requires that initial gesture.

## Architecture

```text
SuperCollider audio + semantic events
  -> OSC UDP 127.0.0.1:57220
  -> Node relay
  -> WebSocket 127.0.0.1:8899
  -> Three.js combat runtime
       |- Blender-exported Butcher robot (hydraulic hammer)
       |- Blender-exported Ripper robot (rotary saw)
       |- attack state machines, recoil, damage and lunges
       `- sparks, smoke, impact lights and camera shake
```

The static GitHub Pages edition uses the same Three.js combat renderer with a self-contained Web Audio score. A secure relay can drive it remotely with `?ws=wss://YOUR-RELAY`.

## Run locally

Double-click `RUN-FULL-AV.cmd`. It starts or reuses the relay, restarts the port-safe SuperCollider performance, and opens the visualizer.

Manual components remain available as `RUN-FOUNDRY-AV.cmd` and the SuperCollider launcher.

## Battle mapping

- Kick: the Butcher winds up, lunges, and swings its hammer.
- Snare: the Ripper drives its spinning saw into the melee.
- Hi-hat: rotary machinery and high-speed mechanisms.
- Bass notes: flywheel torque and furnace intensity.
- Section changes: combat phases, including synchronized overload attacks.
- Impact: opponent recoil, damage tilt, sparks, flash, point light, and camera shake.
- Voice: cyan battlefield command transmission.

## Blender assets

`blender/build_scrapyard_robots.py` builds both original articulated robot assets and exports:

- `assets/robot-butcher.glb`
- `assets/robot-ripper.glb`

Blender is not required to view or run the project. It is only required to regenerate the assets.

## Voice

The arrangement includes an original German machine-voice passage:

> Wir sind der Rhythmus der Maschinen. Stahl und Strom. Schatten werden zu Signalen. Kein Schlaf. Nur Bewegung. Die Zukunft beginnt jetzt.

## Controls

- `F`: fullscreen
- `D`: toggle autonomous battle events
- `H`: toggle HUD

The relay accepts only `/av/section`, `/av/beat`, `/av/hit`, `/av/note`, and `/av/stop`, and binds to localhost only.

## Ableton Live 11 Intro export

`ableton/export_live11_intro.py` renders a stock-compatible, device-neutral port of the composition: five editable MIDI tracks, seven synchronized 48 kHz/24-bit WAV stems, a pre-rendered vocoded voice, section markers, and a reference mix. The 12-track MIDI-plus-stems layout stays within Live 11 Intro's 16-track limit.

```bash
python ableton/export_live11_intro.py
python -m unittest ableton/test_export_live11_intro.py -v
```

The default export location is `C:\\Users\\learn\\Downloads\\Infernal-Foundry-Ableton-Live-11-Intro`. Its README contains the exact drag-and-drop procedure for Live 11 Intro.
