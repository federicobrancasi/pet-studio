"""Particles and pet effects. Every effect is a pure function of time (no hidden state).

All effects take ``cx, cy``: the camera's top-left corner in world coordinates. Pass
``0, 0`` when drawing in screen space.
"""

from __future__ import annotations

import math
import random
from functools import lru_cache
from typing import Sequence

from PIL import Image

from . import art
from . import pet as P
from .draw import TP, blit, ease_out, ease_out_back, fill_rect, hexc, mix, seg, snap
from .font import draw_text

WHITE = hexc('#ffffff')


def dust(img: Image.Image, t: float, landings: Sequence[tuple], cx: float, cy: float, color: tuple = hexc('#7d8595')) -> None:
	"""Little dust puffs on both sides of every landing ``(t, x, y)``."""
	for (tl, x, y) in landings:
		dt = t - tl
		if 0 <= dt < 0.26:
			k = dt / 0.26
			for side in (-1, 1):
				for j in range(2):
					dx = side * (70 + 90 * ease_out(k) + j * 26)
					dy = -12 - 26 * ease_out(k) + j * 10
					s = TP if k < 0.6 else TP // 2
					fill_rect(img, snap(x + dx - cx, 4), snap(y + dy - cy, 4), s, s, color)


def sparks(img: Image.Image, t: float, t0: float, x: float, y: float, cx: float, cy: float, colors: Sequence[tuple], n: int = 8, dist: float = 90, life: float = 0.35) -> None:
	"""A ring of sparks bursting out from ``(x, y)`` at ``t0``."""
	dt = t - t0
	if not (0 <= dt < life):
		return
	k = ease_out(dt / life)
	for i in range(n):
		a = i / n * math.tau + 0.3
		r = 20 + dist * k
		s = TP if dt < life * 0.65 else TP // 2
		fill_rect(img, snap(x + math.cos(a) * r - cx, 4), snap(y + math.sin(a) * r - cy, 4), s, s, colors[i % len(colors)])


CONFETTI_COLORS = [hexc(c) for c in ['#23a8f2', '#24bfa5', '#ffbe30', '#ff7ac8', '#c586c0', '#ffffff', '#ed1c24', '#dcdcaa']]


def confetti_burst(seed: int, x: float, y: float, n: int, spread: float) -> list:
	"""Pieces for one upward confetti burst (seeded, so it is the same every render)."""
	rng = random.Random(seed)
	out = []
	for _ in range(n):
		a = -math.pi / 2 + rng.uniform(-spread, spread)
		v = rng.uniform(700, 1250)
		out.append((x, y, math.cos(a) * v, math.sin(a) * v, rng.choice(CONFETTI_COLORS), rng.random() * 6, rng.uniform(0.8, 1.3)))
	return out


def confetti(img: Image.Image, t: float, bursts: Sequence[tuple], cx: float, cy: float) -> None:
	"""Draws ``[(t0, confetti_burst(...)), ...]`` with drag, gravity and flutter."""
	w, h = img.size
	for (t0, parts) in bursts:
		dt = t - t0
		if dt < 0 or dt > 4.5:
			continue
		for (x, y, vx, vy, col, ph, drag) in parts:
			k = 2.2 * drag
			e = math.exp(-k * dt)
			vt = 260.0  # terminal fall speed
			px = x + vx / k * (1 - e) + math.sin(dt * 7 + ph) * 18 * min(1, dt * 2)
			py = y + vt * dt + (vy - vt) / k * (1 - e)
			flip = int(dt * 9 + ph) % 2
			pw, ph_ = (TP, TP * 2) if flip else (TP * 2, TP)
			sx, sy = snap(px - cx, 4), snap(py - cy, 4)
			if -20 < sx < w + 20 and -20 < sy < h + 20:
				fill_rect(img, sx, sy, pw, ph_, col)


def fireworks(img: Image.Image, t: float, shows: Sequence[tuple], cx: float, cy: float) -> None:
	"""``[(t_burst, x, y, '#color'), ...]``: a rising trail, then a burst at ``t_burst``."""
	for (tb, x, y, c) in shows:
		col = hexc(c)
		bright = mix(col, WHITE, 0.55)
		if tb - 0.35 <= t < tb:
			k = seg(t, tb - 0.35, tb)
			ry = y + 420 * (1 - ease_out(k))
			for j in range(3):
				fill_rect(img, snap(x - cx, 4), snap(ry + j * 20 - cy, 4), TP // 2 * (2 if j == 0 else 1), TP, bright if j == 0 else col)
		dt = t - tb
		if 0 <= dt < 1.25:
			n = 20
			for i in range(n):
				a = i / n * math.tau
				sp = 330 if i % 2 == 0 else 250
				r = sp * (1 - math.exp(-dt * 3.2))
				px = x + math.cos(a) * r
				py = y + math.sin(a) * r + 90 * dt * dt
				if dt > 0.9 and (i + int(dt * 20)) % 2:
					continue
				s = TP if dt < 0.7 else TP // 2
				fill_rect(img, snap(px - cx, 4), snap(py - cy, 4), s, s, bright if dt < 0.25 else col)
				r2 = sp * (1 - math.exp(-(dt - 0.05) * 3.2)) if dt > 0.05 else 0
				fill_rect(img, snap(x + math.cos(a) * r2 - cx, 4), snap(y + math.sin(a) * r2 + 90 * dt * dt - cy, 4), TP // 2, TP // 2, col)


def floating_hearts(img: Image.Image, t: float, t0: float, x: float, y: float, cx: float, cy: float, count: int = 14, every: float = 0.22, life: float = 1.4, rise: float = 190, spread: float = 60, flicker_after: float = 1.1) -> None:
	"""Hearts that float up from ``(x, y)``, one every ``every`` seconds from ``t0``."""
	if t < t0:
		return
	for i in range(count):
		dt = t - (t0 + i * every)
		if 0 <= dt < life:
			hx = x + math.sin(i * 1.7) * spread + math.sin(dt * 5 + i) * 18
			hy = y - dt * rise
			im = art.heart(TP, small=(i % 3 == 0))
			if dt > flicker_after and int(dt * 20) % 2:
				continue
			blit(img, im, snap(hx - im.width / 2 - cx, 4), snap(hy - cy, 4))


def zzz(img: Image.Image, t: float, x: float, y: float, cx: float, cy: float, color: tuple = hexc('#9cdcfe')) -> None:
	"""Three sleepy z's drifting up from ``(x, y)``."""
	for i in range(3):
		ph = ((t + i * 0.45) % 1.35) / 1.35
		zx = x + i * 34 + math.sin(ph * 6 + i) * 10
		zy = y - ph * 150
		draw_text(img, snap(zx - cx, 4), snap(zy - cy, 4), 'z', color, 4 + (i % 2) * 2)


def collectible_stars(img: Image.Image, t: float, stars: Sequence[tuple], cx: float, cy: float) -> None:
	"""Gold stars ``[(t_collected, x, y), ...]`` that bob, then burst with a '+1'."""
	for (tc, x, y) in stars:
		if t < tc:
			bob = math.sin(t * 5 + x) * 8
			st = art.star()
			blit(img, st, snap(x - st.width / 2 - cx, 4), snap(y - st.height / 2 + bob - cy, 4))
			if int(t * 6 + x) % 8 == 0:
				blit(img, art.spark('B'), snap(x + 30 - cx, 4), snap(y - 38 + bob - cy, 4))
		else:
			sparks(img, t, tc, x, y, cx, cy, [hexc('#ffbe30'), hexc('#ffe780')], 8, 80, 0.32)
			dt = t - tc
			if dt < 0.55:
				draw_text(img, snap(x - 30 - cx, 4), snap(y - 70 - dt * 140 - cy, 4), '+1', hexc('#ffe780'), 6, shadow=hexc('#8a5a00'))


def speech_bubble(img: Image.Image, elapsed: float, pose: P.PetPose, cx: float, cy: float, scale: int = 3) -> None:
	"""The real thinking bubble above ``pose`` (``elapsed`` seconds into the loop)."""
	f = P.frame_at('speech', elapsed * 1000)
	bubble = P.effect_frame('speech', f, pose.variant, scale)
	left = round(pose.x) - 96 - cx
	top = round(pose.y) - 192 - cy
	blit(img, bubble, left + 16, top - 128)


def bang(img: Image.Image, t: float, t0: float, t1: float, x: float, y: float, cx: float, cy: float, scale: int = 16) -> None:
	"""A yellow '!' shown from ``t0`` to ``t1`` above ``(x, y)`` (pass the top of the head)."""
	if not (t0 <= t < t1):
		return
	k = seg(t, t0, t0 + 0.12)
	lift = int((1 - ease_out_back(k)) * 3) * TP
	blit(img, art.bang(scale), round(x) - 16 - cx, round(y) - 96 + lift - cy)


def respawn(img: Image.Image, elapsed: float, x: float, y: float, cx: float, cy: float, variant: str = 'stable', scale: int = 2, reverse: bool = False) -> None:
	"""The real portal burst centered on ``(x, y)``: forward = appear, reverse = vanish."""
	durs = P.durations('respawn')
	ms = elapsed * 1000
	if reverse:
		ms = sum(durs) - 1 - ms
	f = P.frame_at('respawn', ms, loop=False)
	im = P.effect_frame('respawn', f, variant, scale)
	blit(img, im, x - im.width // 2 - cx, round(y) - im.height // 2 - cy)


POOF_COLORS = {
	(0x00, 0x77, 0xB8): hexc('#ff7ac8'),
	(0x23, 0xA8, 0xF2): hexc('#ffe780'),
	(0xA3, 0xEB, 0xE6): hexc('#ffffff'),
	(0x00, 0x4E, 0x7C): hexc('#c94f9b'),
	(0xFF, 0xFF, 0xFF): hexc('#ffffff'),
}
POOF_STEPS = (0.08, 0.08, 0.10, 0.12, 0.10, 0.12)


@lru_cache(maxsize=None)
def poof_frame(frame: int, scale: int = 3) -> Image.Image:
	"""The respawn burst recolored pink and gold: a magical transformation poof."""
	src = P.effect_frame('respawn', frame, 'stable', scale).copy()
	px = src.load()
	for yy in range(src.height):
		for xx in range(src.width):
			p = px[xx, yy]
			if p[3]:
				px[xx, yy] = POOF_COLORS.get(p[:3], p)
	return src


def poof(img: Image.Image, t: float, t0: float, x: float, y: float, cx: float, cy: float) -> None:
	"""A 0.6 s transformation poof centered on ``(x, y)``: core, ring, scattered dots."""
	if not (t0 <= t < t0 + sum(POOF_STEPS)):
		return
	acc = t0
	for i, d in enumerate(POOF_STEPS):
		if t < acc + d:
			im = poof_frame(5 - i)
			blit(img, im, round(x) - im.width // 2 - cx, y - im.height // 2 - cy)
			return
		acc += d
