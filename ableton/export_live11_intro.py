#!/usr/bin/env python
"""Deterministically export the Hermes industrial SuperCollider piece for Live 11 Intro.

The pack contains only standard MIDI files, PCM WAV files, and documentation; it has
no third-party or unsupported Ableton devices.  Audio is synthesized offline from
translations of the source SynthDefs and patterns.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import wave
from pathlib import Path

import mido
import numpy as np
from scipy import signal
from scipy.io import wavfile

BPM = 164
BARS = 64
BEATS_PER_BAR = 4
TOTAL_BEATS = BARS * BEATS_PER_BAR
SAMPLE_RATE = 48_000
TOTAL_FRAMES = round(TOTAL_BEATS * 60 / BPM * SAMPLE_RATE)
DURATION_SECONDS = TOTAL_FRAMES / SAMPLE_RATE
PPQ = 480
TOTAL_TICKS = TOTAL_BEATS * PPQ
SEED = 0xF0A4D8
VOICE_BARS = (5, 21, 37, 53)
SECTION_MARKERS = ((1, "FOUNDRY"), (17, "CRUCIBLE"), (33, "OVERLOAD"), (49, "BLACKOUT"))
TRACK_CHANNELS = {"Kick": 0, "Snare": 1, "Hats": 2, "Bass": 3, "Metal": 4}
DEFAULT_ROOT = Path(r"C:\Users\learn\Downloads\supercollider-foundry-av")
DEFAULT_OUTPUT = Path(r"C:\Users\learn\Downloads\Infernal-Foundry-Ableton-Live-11-Intro")
DEFAULT_VOICE = DEFAULT_ROOT / "assets" / "german-machine-voice.wav"
Event = tuple[float, float, int, int, float, float]


def beat_to_frame(beat: float) -> int:
    return round(beat * 60 / BPM * SAMPLE_RATE)


def bar_to_frame(bar: int) -> int:
    """Convert a one-based bar number to its sample position."""
    return beat_to_frame((bar - 1) * BEATS_PER_BAR)


def make_event_plan(seed: int = SEED) -> dict[str, list[Event]]:
    """Translate the five Pbind patterns into a deterministic 64-bar event plan."""
    rng = np.random.default_rng(seed)
    events: dict[str, list[Event]] = {name: [] for name in TRACK_CHANNELS}

    kick_amp = (0.82, 0.64, 0.76, 0.66, 0.85, 0.61, 0.78, 0.0)
    for step in range(TOTAL_BEATS * 2):
        amp = kick_amp[step % len(kick_amp)]
        if amp:
            events["Kick"].append((step * 0.5, 0.34, 36, round(amp * 127), 0.0, amp))

    for beat in range(TOTAL_BEATS):
        amp = (0.0, 0.46)[beat % 2]
        if amp:
            events["Snare"].append((float(beat), 0.19, 38, round(amp * 127), float(rng.uniform(-0.08, 0.08)), amp))

    hat_amps = np.array((0.07, 0.13, 0.22, 0.0))
    hat_probs = np.array((0.36, 0.34, 0.20, 0.10))
    hat_rels = np.array((0.035, 0.07, 0.14))
    rel_probs = np.array((0.6, 0.3, 0.1))
    for step in range(TOTAL_BEATS * 4):
        amp = float(rng.choice(hat_amps, p=hat_probs))
        if amp:
            rel = float(rng.choice(hat_rels, p=rel_probs))
            events["Hats"].append((step * 0.25, rel, 42, max(1, round(amp * 127)), float(rng.uniform(-0.7, 0.7)), rel))

    # SC Scale.phrygian, root 4, octave 2 produces this MIDI sequence.
    bass_notes = (40, 40, 39, 40, 43, 40, 41, 39, 40, 45, 43, 40, 39, 41, 40, None)
    legato = (0.72, 0.35, 0.70, 0.35)
    for step in range(TOTAL_BEATS * 4):
        note = bass_notes[step % 16]
        if note is not None:
            events["Bass"].append((step * 0.25, 0.25 * legato[step % 4], note, round(0.29 * 127), 0.0, 0.0))

    phrygian = (0, 1, 3, 5, 7, 8, 10)
    beat = 0.0
    durations = (0.5, 0.75, 1.0, 1.5)
    degrees = (0, 1, 2, 4, 6)
    while beat < TOTAL_BEATS:
        duration = float(rng.choice(durations))
        octave = int(rng.choice((4, 5)))
        degree = int(rng.choice(degrees))
        note = 12 * (octave + 1) + 4 + phrygian[degree]
        amp = float(rng.uniform(0.045, 0.13))
        rel = float(rng.uniform(0.07, 0.28))
        events["Metal"].append((beat, min(rel, TOTAL_BEATS - beat), note, max(1, round(amp * 127)), float(rng.uniform(-0.9, 0.9)), rel))
        beat += duration
    return events


def _absolute_to_delta(track: mido.MidiTrack, messages: list[tuple[int, int, mido.Message | mido.MetaMessage]]) -> None:
    last = 0
    for tick, _, message in sorted(messages, key=lambda item: (item[0], item[1])):
        message.time = tick - last
        track.append(message)
        last = tick
    track.append(mido.MetaMessage("end_of_track", time=TOTAL_TICKS - last))


def _note_messages(name: str, events: list[Event], channel: int) -> list[tuple[int, int, mido.Message]]:
    messages: list[tuple[int, int, mido.Message]] = []
    for beat, duration, note, velocity, _pan, _extra in events:
        start = round(beat * PPQ)
        end = min(TOTAL_TICKS, max(start + 1, round((beat + duration) * PPQ)))
        messages.append((start, 1, mido.Message("note_on", channel=channel, note=note, velocity=velocity)))
        messages.append((end, 0, mido.Message("note_off", channel=channel, note=note, velocity=0)))
    return messages


def _conductor_messages() -> list[tuple[int, int, mido.MetaMessage]]:
    messages: list[tuple[int, int, mido.MetaMessage]] = [
        (0, 0, mido.MetaMessage("track_name", name="Infernal Foundry Conductor")),
        (0, 1, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM))),
        (0, 2, mido.MetaMessage("time_signature", numerator=4, denominator=4)),
        (0, 3, mido.MetaMessage("key_signature", key="C")),  # E Phrygian uses C's pitch set.
    ]
    for bar, label in SECTION_MARKERS:
        messages.append(((bar - 1) * BEATS_PER_BAR * PPQ, 4, mido.MetaMessage("marker", text=f"BAR {bar:02d} - {label}")))
    for bar in VOICE_BARS:
        messages.append(((bar - 1) * BEATS_PER_BAR * PPQ, 5, mido.MetaMessage("marker", text=f"VOICE - BAR {bar:02d}")))
    return messages


def write_midi_files(output: Path, plan: dict[str, list[Event]]) -> list[Path]:
    midi_dir = output / "MIDI"
    midi_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, events in plan.items():
        mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)
        conductor = mido.MidiTrack()
        mid.tracks.append(conductor)
        _absolute_to_delta(conductor, _conductor_messages())
        notes = mido.MidiTrack()
        mid.tracks.append(notes)
        messages: list[tuple[int, int, mido.Message | mido.MetaMessage]] = [(0, 0, mido.MetaMessage("track_name", name=name))]
        messages.extend(_note_messages(name, events, TRACK_CHANNELS[name]))
        _absolute_to_delta(notes, messages)
        path = midi_dir / f"{name}.mid"
        mid.save(path)
        written.append(path)

    arrangement = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    conductor = mido.MidiTrack()
    arrangement.tracks.append(conductor)
    _absolute_to_delta(conductor, _conductor_messages())
    for name, events in plan.items():
        track = mido.MidiTrack()
        arrangement.tracks.append(track)
        messages = [(0, 0, mido.MetaMessage("track_name", name=name))]
        messages.extend(_note_messages(name, events, TRACK_CHANNELS[name]))
        _absolute_to_delta(track, messages)
    arrangement_path = midi_dir / "arrangement.mid"
    arrangement.save(arrangement_path)
    written.append(arrangement_path)
    return written


def _pan_mono(mono: np.ndarray, pan: float) -> np.ndarray:
    angle = (pan + 1.0) * math.pi / 4.0
    return np.column_stack((mono * math.cos(angle), mono * math.sin(angle))).astype(np.float32)


def _add_hit(stem: np.ndarray, start: int, mono: np.ndarray, pan: float = 0.0) -> None:
    if start >= len(stem):
        return
    n = min(len(mono), len(stem) - start)
    stem[start : start + n] += _pan_mono(mono[:n], pan)


def _section_gain(beat: float) -> float:
    return (0.72, 0.88, 1.0, 0.76)[min(3, int(beat // 64))]


def synth_kick(plan: list[Event], rng: np.random.Generator) -> np.ndarray:
    stem = np.zeros((TOTAL_FRAMES, 2), np.float32)
    n = round(0.42 * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    for beat, _dur, _note, _velocity, pan, amp in plan:
        freq = 38 + 67 * np.exp(-t / 0.038)
        phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        env = np.exp(-t / 0.115) * (1 - np.exp(-t / 0.0008))
        click = rng.standard_normal(n) * np.exp(-t / 0.005)
        click = signal.sosfilt(signal.butter(2, 7000, btype="highpass", fs=SAMPLE_RATE, output="sos"), click)
        mono = np.tanh(np.sin(phase) * env + click * 0.055) * amp * 0.82 * _section_gain(beat)
        _add_hit(stem, beat_to_frame(beat), mono.astype(np.float32), pan)
    return stem


def synth_snare(plan: list[Event], rng: np.random.Generator) -> np.ndarray:
    stem = np.zeros((TOTAL_FRAMES, 2), np.float32)
    n = round(0.26 * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    sos1 = signal.butter(2, (900, 2900), btype="bandpass", fs=SAMPLE_RATE, output="sos")
    sos2 = signal.butter(2, (2300, 5200), btype="bandpass", fs=SAMPLE_RATE, output="sos")
    for beat, _dur, _note, _velocity, pan, amp in plan:
        noise = signal.sosfilt(sos1, rng.standard_normal(n)) + 0.65 * signal.sosfilt(sos2, rng.standard_normal(n))
        noise /= max(1e-9, np.max(np.abs(noise)))
        env = np.exp(-t / 0.055) * (1 - np.exp(-t / 0.002))
        body = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.032)
        mono = np.tanh(noise * 1.45 + body) * env * amp * 1.30 * _section_gain(beat)
        _add_hit(stem, beat_to_frame(beat), mono.astype(np.float32), pan)
    return stem


def synth_hats(plan: list[Event], rng: np.random.Generator) -> np.ndarray:
    stem = np.zeros((TOTAL_FRAMES, 2), np.float32)
    sos = signal.butter(3, 7200, btype="highpass", fs=SAMPLE_RATE, output="sos")
    for beat, rel, _note, velocity, pan, _extra in plan:
        n = max(16, round((rel + 0.025) * SAMPLE_RATE))
        t = np.arange(n) / SAMPLE_RATE
        noise = np.sign(rng.standard_normal(n))
        noise = signal.sosfilt(sos, noise)
        noise /= max(1e-9, np.max(np.abs(noise)))
        env = np.exp(-t / max(0.006, rel / 4.5)) * (1 - np.exp(-t / 0.0005))
        mono = noise * env * (velocity / 127) * 0.74 * _section_gain(beat)
        _add_hit(stem, beat_to_frame(beat), mono.astype(np.float32), pan)
    return stem


def _cutoff_at_beat(beat: float) -> float:
    points = (350.0, 1800.0, 520.0, 3100.0)
    lengths = (8.0, 8.0, 4.0, 12.0)
    cycle = sum(lengths)
    x = beat % cycle
    for i, length in enumerate(lengths):
        if x < length:
            a, b = points[i], points[(i + 1) % len(points)]
            return a * ((b / a) ** (x / length))
        x -= length
    return points[0]


def synth_bass(plan: list[Event], _rng: np.random.Generator) -> np.ndarray:
    stem = np.zeros((TOTAL_FRAMES, 2), np.float32)
    for beat, duration, note, _velocity, pan, _extra in plan:
        seconds = duration * 60 / BPM + 0.08
        n = max(16, round(seconds * SAMPLE_RATE))
        t = np.arange(n) / SAMPLE_RATE
        freq = 440 * 2 ** ((note - 69) / 12)
        widths = (0.28, 0.52, 0.40)
        freqs = (freq, freq * 1.003, freq * 0.5)
        osc = sum(signal.sawtooth(2 * np.pi * f * t, width=w) for f, w in zip(freqs, widths)) * 0.14
        cutoff = np.clip(_cutoff_at_beat(beat) + 90, 100, 6500)
        osc = signal.sosfilt(signal.butter(2, cutoff, btype="lowpass", fs=SAMPLE_RATE, output="sos"), osc)
        attack = 1 - np.exp(-t / 0.004)
        release_start = duration * 60 / BPM
        release = np.where(t <= release_start, 1.0, np.exp(-(t - release_start) / 0.025))
        env = attack * release
        mono = np.tanh(osc * 3.2) * env * 0.58 * _section_gain(beat)
        _add_hit(stem, beat_to_frame(beat), mono.astype(np.float32), pan)
    return stem


def synth_metal(plan: list[Event], _rng: np.random.Generator) -> np.ndarray:
    stem = np.zeros((TOTAL_FRAMES, 2), np.float32)
    ratios = (1.0, 1.414, 2.71, 3.93)
    levels = (0.45, 0.24, 0.18, 0.12)
    for beat, _duration, note, velocity, pan, rel in plan:
        n = max(16, round((rel + 0.04) * SAMPLE_RATE))
        t = np.arange(n) / SAMPLE_RATE
        freq = 440 * 2 ** ((note - 69) / 12)
        raw = sum(level * np.sin(2 * np.pi * freq * ratio * t) for ratio, level in zip(ratios, levels))
        folded = np.abs((raw * 2.8 + 0.7) % 2.8 - 1.4) - 0.7
        env = np.exp(-t / max(0.008, rel / 5.0)) * (1 - np.exp(-t / 0.0008))
        mono = folded * env * (velocity / 127) * 1.10 * _section_gain(beat)
        _add_hit(stem, beat_to_frame(beat), mono.astype(np.float32), pan)
    return stem


def _load_voice(path: Path) -> np.ndarray:
    rate, data = wavfile.read(path)
    if data.ndim == 2:
        data = data.mean(axis=1)
    if np.issubdtype(data.dtype, np.integer):
        data = data.astype(np.float32) / max(abs(np.iinfo(data.dtype).min), np.iinfo(data.dtype).max)
    else:
        data = data.astype(np.float32)
    if rate != SAMPLE_RATE:
        data = signal.resample_poly(data, SAMPLE_RATE, rate).astype(np.float32)
    data -= np.mean(data)
    return data / max(1e-9, np.max(np.abs(data)))


def _vocode(modulator: np.ndarray, base_hz: float) -> np.ndarray:
    t = np.arange(len(modulator)) / SAMPLE_RATE
    carrier = sum(level * signal.sawtooth(2 * np.pi * base_hz * harmonic * t) for harmonic, level in zip((1, 2, 3, 4.01), (0.25, 0.16, 0.11, 0.07)))
    nperseg, overlap = 1024, 768
    _, _, zm = signal.stft(modulator, fs=SAMPLE_RATE, nperseg=nperseg, noverlap=overlap, boundary="zeros")
    _, _, zc = signal.stft(carrier, fs=SAMPLE_RATE, nperseg=nperseg, noverlap=overlap, boundary="zeros")
    smooth_mag = signal.lfilter(np.ones(5) / 5, [1], np.abs(zm), axis=1)
    shaped = smooth_mag * np.exp(1j * np.angle(zc))
    _, voiced = signal.istft(shaped, fs=SAMPLE_RATE, nperseg=nperseg, noverlap=overlap, input_onesided=True, boundary=True)
    voiced = voiced[: len(modulator)]
    consonants = signal.sosfilt(signal.butter(3, 4200, btype="highpass", fs=SAMPLE_RATE, output="sos"), modulator)
    out = np.tanh((voiced * 9.0 + consonants * 0.16) * 2.2)
    fade = min(round(0.02 * SAMPLE_RATE), len(out) // 4)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return (out * 0.36).astype(np.float32)


def synth_voice(voice_path: Path) -> np.ndarray:
    source = _load_voice(voice_path)
    stem = np.zeros((TOTAL_FRAMES, 2), np.float32)
    for bar, base in zip(VOICE_BARS, (36.0, 43.0, 48.0, 43.0)):
        mono = _vocode(source, base)
        _add_hit(stem, bar_to_frame(bar), mono, (-0.10, 0.10, -0.06, 0.06)[VOICE_BARS.index(bar)])
    return stem


def synth_atmosphere(rng: np.random.Generator) -> np.ndarray:
    t = np.arange(TOTAL_FRAMES, dtype=np.float32) / SAMPLE_RATE
    noise = rng.standard_normal(TOTAL_FRAMES).astype(np.float32)
    rumble = signal.sosfilt(signal.butter(3, 170, btype="lowpass", fs=SAMPLE_RATE, output="sos"), noise).astype(np.float32)
    rumble /= max(1e-9, np.max(np.abs(rumble)))
    hum = np.sin(2 * np.pi * 50 * t) + 0.35 * np.sin(2 * np.pi * 100.2 * t)
    pulse = 0.45 + 0.55 * (np.sin(2 * np.pi * (BPM / 60 / 16) * t - np.pi / 2) * 0.5 + 0.5)
    mono = (rumble * 0.11 + hum * 0.018) * pulse
    left = mono + 0.012 * np.sin(2 * np.pi * 311 * t) * np.sin(2 * np.pi * 0.037 * t)
    right = mono + 0.012 * np.sin(2 * np.pi * 337 * t) * np.sin(2 * np.pi * 0.041 * t)
    return np.column_stack((left, right)).astype(np.float32)


def encode_pcm24(audio: np.ndarray) -> bytes:
    clipped = np.clip(audio, -1.0, 1.0)
    values = np.rint(clipped * 8_388_607.0).astype("<i4").reshape(-1)
    raw = values.view(np.uint8).reshape(-1, 4)[:, :3]
    return raw.tobytes()


def write_pcm24(path: Path, audio: np.ndarray) -> dict[str, float | int | str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(3)
        wav.setframerate(SAMPLE_RATE)
        # Chunk encoding keeps peak temporary memory bounded.
        for start in range(0, len(audio), SAMPLE_RATE * 4):
            wav.writeframesraw(encode_pcm24(audio[start : start + SAMPLE_RATE * 4]))
    return {"file": path.name, "frames": len(audio), "seconds": len(audio) / SAMPLE_RATE, "peak": peak, "peak_dbfs": 20 * math.log10(max(peak, 1e-12)), "rms_dbfs": 20 * math.log10(max(rms, 1e-12))}


def _master(audio: np.ndarray) -> np.ndarray:
    # Approximate hMaster: parallel tanh grit, small stereo room, DC block, limiter.
    dry = audio.astype(np.float64)
    grit = np.tanh(dry * 2.4) * 0.22
    wet = np.zeros_like(dry)
    for delay_s, gain in ((0.031, 0.09), (0.047, 0.07), (0.071, 0.05), (0.113, 0.035)):
        d = round(delay_s * SAMPLE_RATE)
        wet[d:, 0] += dry[:-d, 1] * gain
        wet[d:, 1] += dry[:-d, 0] * gain
    out = dry + grit + wet
    out -= np.mean(out, axis=0, keepdims=True)
    return (np.tanh(out / 0.88) * 0.88).astype(np.float32)


def _readme() -> str:
    return f"""# Infernal Foundry — Ableton Live 11 Intro Pack

Deterministic 64-bar translation of `hermes-industrial-supercollider-PORTSAFE.scd`.
Tempo: **{BPM} BPM** · Meter: **4/4** · Length: **64 bars / {DURATION_SECONDS:.6f} s** · Audio: **48 kHz, 24-bit, stereo**.

This is a drag/drop interchange pack, not an `.alp` or `.als`: it contains only standard MIDI and WAV files, so it requires no unsupported Ableton devices, Max for Live, plug-ins, or newer Live features.

## Exact Live 11 Intro import (audio-first, guaranteed sound)

1. Start Live 11 Intro and choose **File > New Live Set**.
2. In the top-left Control Bar set **Tempo = {BPM}.00** and verify **4/4**.
3. Switch to Arrangement View with **Tab**. Turn **Create Fades on Clip Edges** off temporarily in Preferences > Record/Warp/Launch if sample-accurate stem nulling matters.
4. Create **7 Audio Tracks** (`Ctrl+T`). In Live's Browser use **Add Folder...** and select this pack.
5. Drag each file in `Stems/` to its own audio track, all starting exactly at **1.1.1**: Kick, Snare, Hats, Bass, Metal, Vocoded German Voice, FX Atmosphere.
6. For every audio clip, open Clip View and switch **Warp OFF**. All stems are already rendered at {BPM} BPM and have identical length.
7. Name tracks from filenames. Keep `Reference Mix/Infernal Foundry - Full Mix.wav` muted or on a separate comparison track; do not sum it with the stems.
8. Set the Arrangement loop brace to **1.1.1–65.1.1**. Voice entries begin at bars **5, 21, 37, 53**.

## MIDI-first import (editable patterns)

1. Start a new set and set **{BPM} BPM, 4/4**.
2. Drag `MIDI/arrangement.mid` into empty Arrangement space at **1.1.1**. Accept Live's prompt to import tempo/time information if shown. It creates five MIDI tracks: Kick, Snare, Hats, Bass, Metal.
3. If your Live build does not split a format-1 file automatically, create five MIDI tracks (`Ctrl+Shift+T`) and drag `Kick.mid`, `Snare.mid`, `Hats.mid`, `Bass.mid`, and `Metal.mid` separately to **1.1.1**.
4. Add instruments. The MIDI is intentionally device-neutral; rendered stems are the authoritative sound reference.

## Live 11 Intro track limit

Live 11 Intro allows **16 total audio/MIDI tracks**. Recommended working set: **5 MIDI + 7 rendered audio = 12 tracks**. Add the reference mix as track 13 and keep it muted for A/B. This leaves three tracks free. Alternatively use only the seven stems plus reference (8 tracks). Return/folder/group counting depends on Live's edition/build, so avoid unnecessary tracks.

## Suggested stock-only device chains

These are optional starting points using common Live 11 Intro devices; the pack itself contains no device presets.

- **Kick:** Drum Rack or Simpler → EQ Three (trim mids/highs) → Saturator (Soft Sine, subtle) → Compressor.
- **Snare:** Drum Rack or Simpler → EQ Three → Saturator → short Reverb on a Return.
- **Hats:** Drum Rack or Simpler → Auto Filter (high-pass) → Utility (width/pan) → short Reverb.
- **Bass:** Simpler in Classic mode using a single-cycle saw, or any included synth → Auto Filter (low-pass, envelope) → Saturator → Compressor. Notes are E Phrygian: E, F, G, A, B in the source pattern's low register.
- **Metal:** Simpler with a metallic one-shot → Saturator → Auto Filter → Delay/Reverb.
- **Voice/FX audio:** Auto Filter → Saturator → Compressor; optionally send lightly to Reverb and Delay.
- **Master (optional):** EQ Three for broad correction → Compressor with gentle reduction → Limiter. Gain-match against the supplied full mix.

## File map and arrangement

- `MIDI/arrangement.mid`: conductor/markers plus five named MIDI tracks; 480 PPQ, channels 1–5.
- `MIDI/*.mid`: five standalone 64-bar clips.
- `Stems/*.wav`: seven synchronized 48 kHz/24-bit/stereo stems.
- `Reference Mix/*.wav`: limited reference mix peaking below 0 dBFS.
- `VALIDATION.json`: machine-readable properties, note counts, markers, hashes, and clipping checks.
- Sections: bar 1 FOUNDRY, bar 17 CRUCIBLE, bar 33 OVERLOAD, bar 49 BLACKOUT.

The synthesis mirrors the SuperCollider patch: swept sine/click kick, band-noise/190 Hz snare, unstable high-passed hats, filtered distorted VarSaw-like bass, folded inharmonic metal, STFT channel-vocoder voice, industrial atmosphere, and parallel tanh/room/limiter mastering.
"""


def validate_pack(output: Path, expected_plan: dict[str, list[Event]], audio_stats: list[dict]) -> dict:
    midi_report: dict[str, dict] = {}
    for path in sorted((output / "MIDI").glob("*.mid")):
        mid = mido.MidiFile(path)
        names, markers, channels, note_ons = [], [], set(), 0
        max_ticks = 0
        for track in mid.tracks:
            ticks = 0
            for msg in track:
                ticks += msg.time
                if msg.type == "track_name": names.append(msg.name)
                elif msg.type == "marker": markers.append(msg.text)
                elif msg.type == "note_on" and msg.velocity > 0:
                    note_ons += 1
                    channels.add(msg.channel + 1)
            max_ticks = max(max_ticks, ticks)
        if mid.ticks_per_beat != PPQ or max_ticks != TOTAL_TICKS:
            raise ValueError(f"MIDI timing invalid: {path}")
        midi_report[path.name] = {"type": mid.type, "tracks": len(mid.tracks), "ppq": mid.ticks_per_beat, "duration_ticks": max_ticks, "duration_bars": max_ticks / PPQ / 4, "track_names": names, "markers": markers, "channels_1_based": sorted(channels), "note_ons": note_ons}

    wav_report: dict[str, dict] = {}
    for path in sorted(output.rglob("*.wav")):
        with wave.open(str(path), "rb") as wav:
            props = {"channels": wav.getnchannels(), "sample_rate": wav.getframerate(), "bit_depth": wav.getsampwidth() * 8, "frames": wav.getnframes(), "seconds": wav.getnframes() / wav.getframerate()}
        if (props["channels"], props["sample_rate"], props["bit_depth"], props["frames"]) != (2, SAMPLE_RATE, 24, TOTAL_FRAMES):
            raise ValueError(f"WAV properties invalid: {path}: {props}")
        stat = next(item for item in audio_stats if item["relative_path"] == str(path.relative_to(output)).replace("\\", "/"))
        props.update({k: stat[k] for k in ("peak", "peak_dbfs", "rms_dbfs")})
        props["clipping"] = bool(stat["peak"] >= 1.0)
        props["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        if props["clipping"]:
            raise ValueError(f"Clipping detected: {path}")
        wav_report[str(path.relative_to(output)).replace("\\", "/")] = props

    arrangement = midi_report["arrangement.mid"]
    required_markers = [f"VOICE - BAR {bar:02d}" for bar in VOICE_BARS]
    if not all(marker in arrangement["markers"] for marker in required_markers):
        raise ValueError("Voice markers missing")
    expected_total = sum(len(events) for events in expected_plan.values())
    if arrangement["note_ons"] != expected_total or arrangement["tracks"] != 6:
        raise ValueError("Arrangement MIDI event/track count mismatch")
    return {
        "status": "PASS",
        "spec": {"bpm": BPM, "meter": "4/4", "bars": BARS, "seconds": DURATION_SECONDS, "sample_rate": SAMPLE_RATE, "bit_depth": 24, "seed": SEED},
        "event_counts": {name: len(events) for name, events in expected_plan.items()},
        "midi": midi_report,
        "wav": wav_report,
    }


def export_pack(output: Path, voice_path: Path) -> dict:
    if not voice_path.is_file():
        raise FileNotFoundError(f"Required voice asset not found: {voice_path}")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    plan = make_event_plan()
    write_midi_files(output, plan)

    generators = (
        ("Kick", lambda rng: synth_kick(plan["Kick"], rng)),
        ("Snare", lambda rng: synth_snare(plan["Snare"], rng)),
        ("Hats", lambda rng: synth_hats(plan["Hats"], rng)),
        ("Bass", lambda rng: synth_bass(plan["Bass"], rng)),
        ("Metal", lambda rng: synth_metal(plan["Metal"], rng)),
        ("Vocoded German Voice", lambda rng: synth_voice(voice_path)),
        ("FX Atmosphere", synth_atmosphere),
    )
    mix = np.zeros((TOTAL_FRAMES, 2), np.float32)
    stats: list[dict] = []
    for index, (name, generator) in enumerate(generators):
        rng = np.random.default_rng(SEED + 1000 + index)
        audio = generator(rng)
        # Fixed conservative trim preserves stem headroom and guarantees no encoded clipping.
        peak = float(np.max(np.abs(audio)))
        if peak > 0.94:
            audio *= 0.94 / peak
        rel = Path("Stems") / f"{index + 1:02d} - {name}.wav"
        stat = write_pcm24(output / rel, audio)
        stat["relative_path"] = str(rel).replace("\\", "/")
        stats.append(stat)
        mix += audio
        del audio

    full_mix = _master(mix)
    rel = Path("Reference Mix") / "Infernal Foundry - Full Mix.wav"
    stat = write_pcm24(output / rel, full_mix)
    stat["relative_path"] = str(rel).replace("\\", "/")
    stats.append(stat)
    del mix, full_mix

    (output / "README.md").write_text(_readme(), encoding="utf-8")
    report = validate_pack(output, plan, stats)
    (output / "VALIDATION.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--voice", type=Path, default=DEFAULT_VOICE)
    args = parser.parse_args()
    report = export_pack(args.output.resolve(), args.voice.resolve())
    print(json.dumps({"status": report["status"], "output": str(args.output.resolve()), "event_counts": report["event_counts"], "wav_files": len(report["wav"]), "midi_files": len(report["midi"]), "seconds": DURATION_SECONDS}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
