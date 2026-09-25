"""Chiptune instruments, sound effects, a stereo mixer and mastering.

Everything is synthesized with numpy, so a score is plain code and renders the same way
every time. Noise-based sounds draw from one seeded generator that the :class:`Mixer`
resets, so call order is the only thing that matters.

Typical use in a film module::

    from kit import audio as A

    def score(mix: A.Mixer) -> None:
        mix.melody([(0, 0.5, 'C5'), (0.5, 0.5, 'E5'), (1, 1, 'G5')], start_beat=8)
        A.groove(mix, 8, 16)
        mix.put(A.boing(), 3.5, gain=0.16)

Levels that work: lead melody 0.10-0.16, bass 0.24-0.26, plucks 0.03-0.09, bells
0.05-0.10, SFX 0.08-0.30. :meth:`Mixer.master` soft-clips and normalizes, so relative
balance is what counts.
"""

from __future__ import annotations

import math
import re
import subprocess
import wave
from pathlib import Path
from typing import Sequence

import numpy as np

SR = 48000
NOTE = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
PENTA = ['C5', 'D5', 'E5', 'G5', 'A5', 'C6', 'D6', 'E6', 'G6', 'A6', 'C7', 'D7', 'E7', 'G7']

_rng = np.random.default_rng(7)


def reseed(seed: int) -> None:
	"""Resets the shared noise generator (done by every new :class:`Mixer`)."""
	global _rng
	_rng = np.random.default_rng(seed)


def rng() -> np.random.Generator:
	"""The shared seeded generator: use it for any randomness in a score."""
	return _rng


def midi_hz(m: float) -> float:
	return 440.0 * 2 ** ((m - 69) / 12)


def n(name: str) -> int:
	"""Note name to MIDI number: 'C5' -> 72, 'F#4' -> 66."""
	if name[1] == '#':
		key, octave = name[:2], int(name[2:])
	else:
		key, octave = name[0], int(name[1:])
	return 12 * (octave + 1) + NOTE[key]


def beat(b: float, bpm: float = 120.0) -> float:
	"""Beat number to seconds."""
	return b * 60.0 / bpm


# --------------------------------------------------------------------------------------------
# Oscillators, envelopes and filters


def env(nsamp: int, a: float, d: float, s: float, r: float) -> np.ndarray:
	"""ADSR envelope: attack, decay, sustain level and release (seconds)."""
	a_n = max(1, int(a * SR))
	d_n = max(1, int(d * SR))
	r_n = max(1, int(r * SR))
	e = np.full(nsamp, s, dtype=np.float64)
	e[:min(a_n, nsamp)] = np.linspace(0, 1, a_n)[:min(a_n, nsamp)]
	if a_n < nsamp:
		decay = np.linspace(1, s, d_n)
		e[a_n:a_n + d_n] = decay[:max(0, min(d_n, nsamp - a_n))]
	if nsamp > r_n:
		e[-r_n:] *= np.linspace(1, 0, r_n)
	return e


def _phase(freq, nsamp: int) -> np.ndarray:
	if np.isscalar(freq):
		return (np.arange(nsamp) * (freq / SR)) % 1.0
	return np.cumsum(np.asarray(freq) / SR) % 1.0


def pulse_wave(freq, nsamp: int, duty: float) -> np.ndarray:
	w = np.where(_phase(freq, nsamp) < duty, 1.0, -1.0)
	return w - (2 * duty - 1)


def tri_wave(freq, nsamp: int) -> np.ndarray:
	w = 4 * np.abs(_phase(freq, nsamp) - 0.5) - 1
	return np.round(w * 7.5) / 7.5  # 4-bit NES-style steps


def sine_wave(freq, nsamp: int) -> np.ndarray:
	return np.sin(2 * np.pi * _phase(freq, nsamp))


def onepole_lp(x: np.ndarray, cutoff: float) -> np.ndarray:
	a = math.exp(-2 * math.pi * cutoff / SR)
	b = 1 - a
	acc = 0.0
	out = []
	append = out.append
	for v in x.tolist():
		acc = b * v + a * acc
		append(acc)
	return np.asarray(out)


def highpass(x: np.ndarray, cutoff: float) -> np.ndarray:
	return x - onepole_lp(x, cutoff)


# --------------------------------------------------------------------------------------------
# Instruments (m = MIDI note, dur = seconds)


def lead(m: int, dur: float, duty: float = 0.25, vib: float = 0.0) -> np.ndarray:
	"""Square-wave lead; ``vib`` adds a gentle delayed vibrato (0.006 is nice on long notes)."""
	ns = int((dur + 0.06) * SR)
	f = midi_hz(m)
	if vib:
		tt = np.arange(ns) / SR
		f = f * (1 + vib * np.sin(2 * np.pi * 5.5 * tt) * np.clip((tt - 0.12) * 4, 0, 1))
	return pulse_wave(f, ns, duty) * env(ns, 0.004, 0.09, 0.62, 0.06)


def pluck(m: int, dur: float, duty: float = 0.125) -> np.ndarray:
	ns = int((dur + 0.05) * SR)
	return pulse_wave(midi_hz(m), ns, duty) * env(ns, 0.002, 0.07, 0.25, 0.04)


def bass(m: int, dur: float) -> np.ndarray:
	"""Plays one octave above the written note so phone speakers can reproduce it."""
	ns = int((dur + 0.02) * SR)
	f = midi_hz(m + 12)
	w = tri_wave(f, ns) * 0.8 + pulse_wave(f, ns, 0.5) * 0.22
	return w * env(ns, 0.003, 0.05, 0.85, 0.03)


def bell(m: int, dur: float = 0.9) -> np.ndarray:
	"""Music-box bell."""
	ns = int(dur * SR)
	tt = np.arange(ns) / SR
	f = midi_hz(m)
	w = np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * f * 2.0 * tt) * np.exp(-tt * 9) + 0.12 * np.sin(2 * np.pi * f * 3.01 * tt) * np.exp(-tt * 14)
	return w * np.exp(-tt * 4.5) * np.clip(tt / 0.003, 0, 1)


def kick(g: float = 1.0) -> np.ndarray:
	ns = int(0.14 * SR)
	tt = np.arange(ns) / SR
	f = 70 + 230 * np.exp(-tt * 34)
	w = np.sin(2 * np.pi * np.cumsum(f) / SR)
	click_ = highpass(_rng.uniform(-1, 1, ns), 2000) * np.exp(-tt * 400) * 0.35
	return (w * np.exp(-tt * 24) + click_) * g * 0.8


def snare(g: float = 1.0) -> np.ndarray:
	ns = int(0.16 * SR)
	tt = np.arange(ns) / SR
	nz = highpass(_rng.uniform(-1, 1, ns), 1200)
	tone = np.sin(2 * np.pi * 190 * tt) * np.exp(-tt * 30)
	return (nz * np.exp(-tt * 24) * 0.8 + tone * 0.5) * g


def hat(g: float = 1.0, open_: bool = False) -> np.ndarray:
	ns = int((0.12 if open_ else 0.035) * SR)
	tt = np.arange(ns) / SR
	nz = highpass(_rng.uniform(-1, 1, ns), 7000)
	return nz * np.exp(-tt * (18 if open_ else 90)) * g


def crash(g: float = 1.0) -> np.ndarray:
	ns = int(1.6 * SR)
	tt = np.arange(ns) / SR
	nz = highpass(_rng.uniform(-1, 1, ns), 3500)
	return nz * np.exp(-tt * 2.6) * g


# --------------------------------------------------------------------------------------------
# Sound effects


def click(pitch: float = 1.0, g: float = 1.0) -> np.ndarray:
	"""A keyboard click; vary ``pitch`` a little per key so typing sounds human."""
	ns = int(0.03 * SR)
	tt = np.arange(ns) / SR
	nz = highpass(_rng.uniform(-1, 1, ns), 2500)
	tone = np.sin(2 * np.pi * 1800 * pitch * tt)
	return (nz * 0.7 + tone * 0.3) * np.exp(-tt * 160) * g


def sweep(f0: float, f1: float, dur: float, kind: str = 'pulse', duty: float = 0.5, curve: float = 1.0) -> np.ndarray:
	"""A pitch sweep from ``f0`` to ``f1`` Hz (``kind``: 'pulse', 'tri' or 'sine')."""
	ns = int(dur * SR)
	u = np.linspace(0, 1, ns) ** curve
	f = f0 * (f1 / f0) ** u
	if kind == 'pulse':
		w = pulse_wave(f, ns, duty)
	elif kind == 'tri':
		w = tri_wave(f, ns)
	else:
		w = sine_wave(f, ns)
	return w * env(ns, 0.003, 0.05, 0.7, min(0.05, dur / 3))


def boing() -> np.ndarray:
	"""Hop take-off."""
	ns = int(0.2 * SR)
	tt = np.arange(ns) / SR
	f = 260 * (2.6 ** np.clip(tt / 0.13, 0, 1)) * (1 + 0.04 * np.sin(2 * np.pi * 30 * tt))
	return pulse_wave(f, ns, 0.5) * env(ns, 0.002, 0.06, 0.55, 0.06)


def land() -> np.ndarray:
	"""Soft landing thump."""
	ns = int(0.09 * SR)
	tt = np.arange(ns) / SR
	f = 150 * np.exp(-tt * 18) + 60
	w = np.sin(2 * np.pi * np.cumsum(f) / SR)
	nz = onepole_lp(_rng.uniform(-1, 1, ns), 900)
	return (w * 0.9 + nz * 0.5) * np.exp(-tt * 40)


def coin() -> np.ndarray:
	a = pulse_wave(midi_hz(n('B5')), int(0.07 * SR), 0.25) * env(int(0.07 * SR), 0.002, 0.02, 0.8, 0.01)
	b = pulse_wave(midi_hz(n('E6')), int(0.28 * SR), 0.25) * env(int(0.28 * SR), 0.002, 0.08, 0.5, 0.18)
	return np.concatenate([a, b])


def blip(m: int, dur: float = 0.08, duty: float = 0.25) -> np.ndarray:
	ns = int(dur * SR)
	return pulse_wave(midi_hz(m), ns, duty) * env(ns, 0.002, 0.02, 0.6, dur / 2)


def noise_burst(dur: float, hp: float, decay: float) -> np.ndarray:
	ns = int(dur * SR)
	tt = np.arange(ns) / SR
	return highpass(_rng.uniform(-1, 1, ns), hp) * np.exp(-tt * decay)


def whoosh(dur: float = 0.35) -> np.ndarray:
	ns = int(dur * SR)
	tt = np.arange(ns) / SR
	x = highpass(onepole_lp(_rng.uniform(-1, 1, ns), 3000), 400)
	return x * np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 2


def uh_oh() -> np.ndarray:
	a = sweep(midi_hz(n('G5')), midi_hz(n('F#5')), 0.16, 'tri')
	b = sweep(midi_hz(n('D5')), midi_hz(n('C#5')), 0.3, 'tri')
	return np.concatenate([a, np.zeros(int(0.03 * SR)), b])


def bonk() -> np.ndarray:
	ns = int(0.28 * SR)
	tt = np.arange(ns) / SR
	f = 520 * np.exp(-tt * 14) + 90
	w = pulse_wave(f, ns, 0.5) * np.exp(-tt * 11)
	nz = onepole_lp(_rng.uniform(-1, 1, ns), 1800) * np.exp(-tt * 30)
	return w * 0.8 + nz * 0.7


def twinkle(notes: Sequence[str], step: float = 0.045, g: float = 1.0) -> np.ndarray:
	"""A quick run of bells, e.g. ``twinkle(['C7', 'E7', 'G7'])``."""
	total = int((len(notes) * step + 0.6) * SR)
	out = np.zeros(total)
	for i, nm in enumerate(notes):
		b = bell(n(nm), 0.5)
		i0 = int(i * step * SR)
		out[i0:i0 + len(b)] += b[:max(0, total - i0)]
	return out * g


def firework() -> tuple[np.ndarray, np.ndarray]:
	"""Returns ``(whistle, boom)``: put the whistle 0.35 s before the burst."""
	whistle = sweep(700, 1500, 0.33, 'sine') * 0.25
	ns = int(0.9 * SR)
	tt = np.arange(ns) / SR
	boom = onepole_lp(_rng.uniform(-1, 1, ns), 1400) * np.exp(-tt * 7) * 0.9
	crackle = np.zeros(ns)
	for _ in range(26):
		i0 = int(_rng.uniform(0.08, 0.8) * SR)
		c = noise_burst(0.012, 4000, 300)
		crackle[i0:i0 + len(c)] += c[:max(0, ns - i0)] * _rng.uniform(0.3, 0.8)
	return whistle, boom + crackle * 0.6


def spring() -> np.ndarray:
	ns = int(0.35 * SR)
	tt = np.arange(ns) / SR
	f = 420 + 260 * np.sin(2 * np.pi * 16 * tt) * np.exp(-tt * 6)
	return pulse_wave(f, ns, 0.25) * env(ns, 0.002, 0.05, 0.6, 0.15)


# --------------------------------------------------------------------------------------------
# Mixer and mastering


class Mixer:
	"""A stereo mix bus ``duration`` seconds long (plus a short tail for ringing notes)."""

	def __init__(self, duration: float, seed: int = 7, tail: float = 0.2, bpm: float = 120.0):
		reseed(seed)
		self.duration = duration
		self.bpm = bpm
		self.n = int(SR * (duration + tail))
		self.left = np.zeros(self.n)
		self.right = np.zeros(self.n)

	def beat(self, b: float) -> float:
		return beat(b, self.bpm)

	def put(self, sig: np.ndarray, t: float, gain: float = 1.0, pan: float = 0.0) -> None:
		"""Adds ``sig`` at ``t`` seconds. ``pan`` goes from -1 (left) to 1 (right)."""
		i0 = int(round(t * SR))
		if i0 >= self.n or len(sig) == 0:
			return
		if i0 < 0:
			sig = sig[-i0:]
			i0 = 0
		m = min(len(sig), self.n - i0)
		gl = gain * math.cos((pan + 1) * math.pi / 4) * math.sqrt(2)
		gr = gain * math.sin((pan + 1) * math.pi / 4) * math.sqrt(2)
		self.left[i0:i0 + m] += sig[:m] * gl
		self.right[i0:i0 + m] += sig[:m] * gr

	def melody(self, notes: Sequence[tuple], start_beat: float = 0.0, inst: str = 'lead', gain: float = 0.16, transpose: int = 0, pan: float = 0.0) -> None:
		"""``notes`` is ``[(beat, length_beats, 'C5'), ...]``; ``inst``: lead, bell or pluck."""
		for (b, length, name) in notes:
			m = n(name) + transpose
			t = self.beat(start_beat + b)
			d = self.beat(length)
			if inst == 'lead':
				self.put(lead(m, d * 0.92, 0.25, vib=0.006 if d >= 0.5 else 0.0), t, gain, pan)
			elif inst == 'bell':
				self.put(bell(m, max(0.5, d * 2.2)), t, gain, pan)
			elif inst == 'pluck':
				self.put(pluck(m, d * 0.8), t, gain, pan)
			else:
				raise ValueError(f'Unknown instrument {inst!r}')

	def master(self, drive: float = 1.6, ceiling: float = 0.76, fade_out: float = 0.25) -> np.ndarray:
		"""Soft-clips, normalizes to ``ceiling`` and fades the end. Returns float stereo.

		The default ceiling lands around -15 LUFS with about -2 dBTP after AAC encoding.
		"""
		stereo = np.stack([self.left, self.right], axis=1)
		peak = np.max(np.abs(stereo))
		stereo = stereo / max(peak, 1e-9) * drive
		stereo = np.tanh(stereo)
		stereo = stereo / max(np.max(np.abs(stereo)), 1e-9) * ceiling
		end = int(self.duration * SR)
		fade = int(fade_out * SR)
		if fade:
			stereo[end - fade:end] *= np.linspace(1, 0, fade)[:, None]
		return stereo[:end]

	def write(self, path: str | Path, **master_args) -> Path:
		"""Masters and writes a 48 kHz 16-bit stereo WAV."""
		path = Path(path)
		path.parent.mkdir(parents=True, exist_ok=True)
		pcm = (self.master(**master_args) * 32767).astype(np.int16)
		with wave.open(str(path), 'wb') as w:
			w.setnchannels(2)
			w.setsampwidth(2)
			w.setframerate(SR)
			w.writeframes(pcm.tobytes())
		return path


def groove(mix: Mixer, b0: float, b1: float, hats16: bool = False, soft: float = 1.0) -> None:
	"""A basic beat from beat ``b0`` to ``b1``: kick on 1 and 3, snare on 2 and 4, hats."""
	b = b0
	while b < b1 - 1e-6:
		beat_in_bar = b % 4
		if beat_in_bar in (0, 2):
			mix.put(kick(0.9 * soft), mix.beat(b))
		if beat_in_bar in (1, 3):
			mix.put(snare(0.32 * soft), mix.beat(b), pan=0.05)
		step = 0.25 if hats16 else 0.5
		k = 0.0
		while k < 1 - 1e-6:
			mix.put(hat(0.10 * soft if k == 0 else 0.07 * soft), mix.beat(b + k), pan=-0.25)
			k += step
		b += 1


def roll(mix: Mixer, b0: float, b1: float, g0: float, g1: float) -> None:
	"""A snare roll in 16ths that swells from gain ``g0`` to ``g1``."""
	steps = int((b1 - b0) * 4)
	for i in range(steps):
		mix.put(snare(g0 + (g1 - g0) * i / max(1, steps - 1)), mix.beat(b0 + i * 0.25), pan=0.05)


# --------------------------------------------------------------------------------------------
# Measurement


def loudness(path: str | Path) -> dict:
	"""Integrated loudness (LUFS) and true peak (dBTP) of an audio or video file."""
	from .media import ffmpeg_exe

	result = subprocess.run([ffmpeg_exe(), '-hide_banner', '-nostats', '-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True, encoding='utf-8', errors='replace')
	text = result.stderr
	summary = text[text.rfind('Summary:'):]
	i_match = re.search(r'I:\s+(-?[\d.]+) LUFS', summary)
	p_match = re.search(r'Peak:\s+(-?[\d.]+|-inf) dBFS', summary)
	return {
		'lufs': float(i_match.group(1)) if i_match else None,
		'true_peak_db': float(p_match.group(1)) if p_match and p_match.group(1) != '-inf' else None,
	}
