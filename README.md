# Foundry Signal Organism

A local live audiovisual system with a public autonomous visual edition.

**Public:** https://zack-bolich.github.io/supercollider-foundry-av/

GitHub Pages is static, so the public URL includes a self-contained Web Audio edition: click **START AUDIO** to run the 164 BPM industrial drum/bass/metal arrangement and robotic German voice directly in the browser. The original SuperCollider engine and localhost OSC relay remain the higher-fidelity local edition. A temporary secure WebSocket tunnel can drive the public visuals from SuperCollider by opening the page with `?ws=wss://YOUR-RELAY`.

```text
SuperCollider audio + semantic events
  -> OSC UDP 127.0.0.1:57220
  -> Node relay
  -> WebSocket 127.0.0.1:8899
  -> p5.js visual state machine
```

## Run

Double-click `RUN-FULL-AV.cmd`. It starts or reuses the relay, restarts the port-safe SuperCollider performance, and opens the visualizer.

Manual components remain available as `RUN-FOUNDRY-AV.cmd` and the SuperCollider launcher.

The arrangement includes an original German machine-voice passage processed through a 16-band SuperCollider vocoder:

> Wir sind der Rhythmus der Maschinen. Stahl und Strom. Schatten werden zu Signalen. Kein Schlaf. Nur Bewegung. Die Zukunft beginnt jetzt.

## Controls

- `F`: fullscreen
- `S`: save PNG
- `D`: toggle visual demo events (clearly labelled)
- `H`: toggle HUD
- Click: inject a local visual rupture

The relay accepts only `/av/section`, `/av/beat`, `/av/hit`, `/av/note`, and `/av/stop`, and binds to localhost only.
