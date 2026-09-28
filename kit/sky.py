"""Skies and clouds for worlds that aren't code.

A sky that follows the time of day (or a sky as tall as a climb), a pixel sun and moon,
twinkling stars, parallax cloud layers, cloud platforms the pet can land on, light rays, a
gust of wind and speed lines. Like the rest of the kit, everything is a pure function of time
and sits on a pixel grid. Things in world space take the camera's top-left corner ``cx, cy``.

    SKY = sky.gradient(SIZE, sky.day_keys(9.5))      # a morning sky, cached
    CLOUDS = sky.CloudLayer(seed=3, count=8, y=(200, 900), palette='day')
    STEP = sky.CloudPlatform(x=700, top=1100, cols=30, rows=12, seed=7)

    img.paste(SKY, (0, 0))
    CLOUDS.draw(img, t, cx, cy)
    STEP.draw(img, cx, cy, dip=sky.bounce(t, [T_LAND]))   # the pet stands on STEP.top
"""

from __future__ import annotations

import math
import random
from functools import lru_cache
from typing import Sequence

import numpy as np
from PIL import Image, ImageDraw

from .draw import blit, clamp, fill_rect, hexc, mix, seg, snap

CELL = 12  # detail grid: half a pet pixel at scale 3 (use 8 for scale 2)

# --------------------------------------------------------------------------------------------
# Sky colors

SKIES = {  # top to bottom: (fraction of the height, color)
	'dawn': ((0.0, '#39386f'), (0.4, '#9a76b4'), (0.72, '#ffae8e'), (1.0, '#ffe0a6')),
	'morning': ((0.0, '#4c9be8'), (0.55, '#8fcaf7'), (1.0, '#e2f4ff')),
	'noon': ((0.0, '#3584e4'), (0.55, '#6fbcf9'), (1.0, '#c8ecff')),
	'afternoon': ((0.0, '#4a7fd6'), (0.55, '#94c1ec'), (1.0, '#ffe4bd')),
	'sunset': ((0.0, '#4f449e'), (0.35, '#cf679f'), (0.7, '#ff9878'), (1.0, '#ffd394')),
	'dusk': ((0.0, '#1d1b4e'), (0.5, '#473785'), (0.85, '#b4628c'), (1.0, '#e98f82')),
	'night': ((0.0, '#0a0c24'), (0.6, '#171c45'), (1.0, '#262a5e')),
}
DAY = ((5.0, 'night'), (6.5, 'dawn'), (8.5, 'morning'), (12.0, 'noon'), (15.5, 'afternoon'),
	(18.0, 'sunset'), (19.3, 'dusk'), (20.5, 'night'))  # (hour, sky) through one day


def _color_at(keys: Sequence[tuple], f: float) -> tuple:
	stops = [(k, hexc(c) if isinstance(c, str) else c) for (k, c) in keys]
	if f <= stops[0][0]:
		return stops[0][1]
	for (f0, c0), (f1, c1) in zip(stops, stops[1:]):
		if f <= f1:
			return mix(c0, c1, (f - f0) / (f1 - f0))
	return stops[-1][1]


def day_keys(hour: float) -> tuple:
	"""The sky's gradient keys at ``hour`` (0-24), blending the neighboring skies of ``DAY``."""
	hour = round(hour * 20) / 20  # 3-minute steps keep the gradient cache small
	fractions = (0.0, 0.2, 0.35, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
	h = clamp(hour, DAY[0][0], DAY[-1][0])
	for (h0, a), (h1, b) in zip(DAY, DAY[1:]):
		if h <= h1:
			k = (h - h0) / (h1 - h0)
			return tuple((f, mix(_color_at(SKIES[a], f), _color_at(SKIES[b], f), k)) for f in fractions)
	return tuple((f, _color_at(SKIES['night'], f)) for f in fractions)


def day_light(hour: float) -> tuple:
	"""A tint for scenery at ``hour``: ``(color, amount)``, for :func:`kit.land.tinted` and friends."""
	keys = ((5.0, ('#1b2150', 0.62)), (6.5, ('#8a5c9e', 0.32)), (8.5, ('#ffe9c4', 0.08)), (12.0, ('#ffffff', 0.0)),
		(15.5, ('#ffd9a0', 0.10)), (18.0, ('#ff8a6a', 0.28)), (19.3, ('#6a3f8e', 0.42)), (20.5, ('#1b2150', 0.62)))
	h = clamp(round(hour * 20) / 20, keys[0][0], keys[-1][0])
	for (h0, (c0, a0)), (h1, (c1, a1)) in zip(keys, keys[1:]):
		if h <= h1:
			k = (h - h0) / (h1 - h0)
			return mix(hexc(c0), hexc(c1), k)[:3], a0 + (a1 - a0) * k
	return hexc(keys[-1][1][0])[:3], keys[-1][1][1]


@lru_cache(maxsize=48)
def gradient(size: tuple, keys: tuple, band: int = 8) -> Image.Image:
	"""A vertical gradient in ``band``-px steps. ``keys``: ``((fraction, '#hex' or rgba), ...)``.

	For a sky as tall as a climb, make it as tall as the world and paste a crop of it.
	"""
	w, h = size
	arr = np.zeros((h, w, 4), np.uint8)
	for y0 in range(0, h, band):
		arr[y0:y0 + band, :, :] = _color_at(keys, (y0 + band / 2) / h)
	return Image.fromarray(arr)


# --------------------------------------------------------------------------------------------
# Sun, moon and stars


@lru_cache(maxsize=None)
def sun(radius: int = 156, cell: int = CELL, stripes: bool = True) -> Image.Image:
	"""A pixel sun with two soft halo rings; ``stripes`` adds sunset stripes to the lower half."""
	n = radius // cell
	size = (n * 2 + 9) * cell
	img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
	c0 = size / 2
	core, body, rim = hexc('#fff6c8'), hexc('#ffd66e'), hexc('#ffac4f')
	cells = size // cell
	for ring, alpha in ((n + 4, 38), (n + 2, 64)):
		for gy in range(cells):
			for gx in range(cells):
				dx, dy = gx * cell + cell / 2 - c0, gy * cell + cell / 2 - c0
				if dx * dx + dy * dy <= (ring * cell) ** 2:
					fill_rect(img, gx * cell, gy * cell, cell, cell, hexc('#fff0c4', alpha))
	for gy in range(cells):
		for gx in range(cells):
			dx, dy = gx * cell + cell / 2 - c0, gy * cell + cell / 2 - c0
			d2 = dx * dx + dy * dy
			if d2 <= (n * cell) ** 2:
				row = dy / (n * cell)
				if stripes and row > 0.25 and int((row - 0.25) * 12) % 3 == 2:
					continue
				col = core if d2 <= ((n - 3) * cell) ** 2 and dy < 0 else mix(body, rim, clamp(row * 0.9 + 0.35, 0, 1))
				img.paste(col, (gx * cell, gy * cell, gx * cell + cell, gy * cell + cell))
	return img


@lru_cache(maxsize=None)
def moon(radius: int = 84, cell: int = CELL) -> Image.Image:
	"""A pale crescent moon with a soft halo and two craters."""
	n = radius // cell
	size = (n * 2 + 7) * cell
	img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
	c0 = size / 2
	cells = size // cell
	for gy in range(cells):
		for gx in range(cells):
			dx, dy = gx * cell + cell / 2 - c0, gy * cell + cell / 2 - c0
			d2 = dx * dx + dy * dy
			if d2 <= ((n + 3) * cell) ** 2:
				fill_rect(img, gx * cell, gy * cell, cell, cell, hexc('#d9e1ff', 34))
			bite = (dx - n * cell * 0.55) ** 2 + (dy + n * cell * 0.25) ** 2 <= (n * cell * 0.8) ** 2
			if d2 <= (n * cell) ** 2 and not bite:
				shade = dx > -n * cell * 0.2
				col = hexc('#f4f1d8') if not shade else hexc('#dcd6b4')
				img.paste(col, (gx * cell, gy * cell, gx * cell + cell, gy * cell + cell))
	for (fx_, fy, r) in ((-0.45, 0.2, 1), (-0.2, 0.55, 1)):
		x, y = int(c0 + fx_ * n * cell), int(c0 + fy * n * cell)
		fill_rect(img, snap(x, cell), snap(y, cell), r * cell, r * cell, hexc('#c9c29c'))
	return img


@lru_cache(maxsize=None)
def _star_field(seed: int, count: int, width: int, height: int) -> tuple:
	rng = random.Random(seed)
	return tuple((rng.uniform(0, width), rng.uniform(0, height), rng.random(), rng.random() < 0.18) for _ in range(count))


def star(img: Image.Image, x: float, y: float, big: bool, color: tuple) -> None:
	"""One pixel star at screen ``(x, y)``: a dot, or a small plus when ``big``."""
	x, y = snap(x, 4), snap(y, 4)
	if big:
		fill_rect(img, x - 4, y, 12, 4, color)
		fill_rect(img, x, y - 4, 4, 12, color)
	else:
		fill_rect(img, x, y, 4, 4, color)


def stars(img: Image.Image, t: float, cx: float, cy: float, strength: float = 1.0, seed: int = 5, count: int = 70,
		area: tuple = (0, 0, 1080, 1200), parallax: float = 0.1, twinkle: float = 5.0) -> None:
	"""Twinkling stars over ``area`` (screen box, repeated as the camera moves); ``strength`` fades them."""
	if strength <= 0:
		return
	x0, y0, x1, y1 = area
	w, h = x1 - x0, y1 - y0
	for (x, y, ph, big) in _star_field(seed, count, w, h):
		sx = x0 + (x - cx * parallax) % w
		sy = y0 + (y - cy * parallax) % h
		a = int(255 * strength * (0.55 + 0.45 * math.sin(t * twinkle + ph * 30)))
		if a > 20:
			star(img, sx, sy, big, (255, 246, 214, a))


# --------------------------------------------------------------------------------------------
# Clouds

CLOUDS = {  # rim, body, shade, deep
	'day': ('#ffffff', '#f5f9ff', '#d7e5f6', '#b9cbe6'),
	'warm': ('#ffffff', '#fff1ea', '#ffc8c9', '#eea0b4'),
	'pink': ('#ffffff', '#ffe8f1', '#f9b8d3', '#e29ac2'),
	'dusk': ('#ffe3f4', '#f0bde0', '#c48ac8', '#9168ad'),
	'night': ('#9aa2d6', '#6a72a8', '#4e558c', '#3a4072'),
	'storm': ('#9aa0b4', '#7a8096', '#5e6478', '#474c5e'),
}


def _palette(palette) -> tuple:
	return CLOUDS[palette] if isinstance(palette, str) else tuple(palette)


_TINTED: dict = {}


def lit(sprite: Image.Image, light: tuple | None) -> Image.Image:
	"""``sprite`` under ``light = (rgb, amount)`` (see :func:`day_light`), cached per sprite and light."""
	if not light or light[1] <= 0:
		return sprite
	key = (id(sprite), tuple(int(v) for v in light[0]), round(light[1], 3))
	out = _TINTED.get(key)
	if out is None:
		if len(_TINTED) > 4096:
			_TINTED.clear()
		arr = np.asarray(sprite).astype(np.float32)
		arr[..., :3] = arr[..., :3] * (1 - light[1]) + np.array(light[0][:3], np.float32) * light[1]
		out = _TINTED[key] = Image.fromarray(arr.round().astype(np.uint8))
	return out


@lru_cache(maxsize=None)
def cloud_mask(seed: int, cols: int, rows: int) -> np.ndarray:
	"""A flat-bottomed cumulus on a ``cols x rows`` grid: a wide base with round puffs on top."""
	rng = random.Random(seed)
	yy, xx = np.mgrid[0:rows, 0:cols]
	xs, ys = xx + 0.5, yy + 0.5
	base_top = rows * 0.62
	m = ((xs - cols / 2) / (cols / 2)) ** 2 + ((ys - rows) / (rows - base_top)) ** 2 <= 1.0
	n = max(2, round(cols / 5))
	for i in range(n):
		u = i / (n - 1)
		middle = 1 - abs(u - 0.5) * 2
		r = rows * (0.30 + 0.28 * middle) * rng.uniform(0.9, 1.08)
		px = cols * (0.18 + 0.64 * u) + rng.uniform(-0.6, 0.6)
		m |= (xs - px) ** 2 + (ys - (base_top + r * 0.15)) ** 2 <= r * r
	return m


def _shade(m: np.ndarray, palette: tuple, alpha: int) -> Image.Image:
	rim, body, shade, deep = (hexc(c, alpha) for c in palette)
	rows, cols = m.shape
	above = np.zeros_like(m)
	above[1:, :] = m[:-1, :]
	left = np.zeros_like(m)
	left[:, 1:] = m[:, :-1]
	right = np.zeros_like(m)
	right[:, :-1] = m[:, 1:]
	yy = np.mgrid[0:rows, 0:cols][0]
	out = np.zeros((rows, cols, 4), np.uint8)
	out[m] = body
	out[m & (yy >= rows * 0.6) & (~left | ~right)] = shade
	out[m & (yy >= rows - 2)] = shade
	out[m & (yy == rows - 1)] = deep
	out[m & ~above] = rim
	return Image.fromarray(out)


@lru_cache(maxsize=None)
def cloud(seed: int, cols: int, rows: int, cell: int = CELL, palette='day', alpha: int = 255) -> Image.Image:
	"""A shaded pixel cloud ``cols x rows`` cells big (sunlit rim, body, shade, deep bottom row)."""
	return _shade(cloud_mask(seed, cols, rows), _palette(palette), alpha).resize((cols * cell, rows * cell), Image.NEAREST)


def cloud_top(seed: int, cols: int, rows: int) -> int:
	"""Cells from the sprite's top to the cloud's top in the middle column (where the pet lands)."""
	col = cloud_mask(seed, cols, rows)[:, cols // 2]
	return int(np.argmax(col)) if col.any() else 0


class CloudPlatform:
	"""A cloud the pet can stand on: ``top`` is the world y under the pet's feet at ``x``.

	The pet's feet sink half a cell into the fluff. Squashing the cloud (fewer ``rows``, as a
	spring cloud does under a landing) keeps its bottom still, and :meth:`surface` follows it.
	"""

	def __init__(self, x: float, top: float, cols: int, rows: int, seed: int, palette='warm', cell: int = CELL):
		self.x, self.top, self.cols, self.rows, self.seed, self.cell = x, top, cols, rows, seed, cell
		self.palette = _palette(palette)
		self.sink = cell // 2
		self.bottom = top - cloud_top(seed, cols, rows) * cell - self.sink + rows * cell

	def surface(self, rows: int | None = None) -> float:
		"""The world y of the top under the pet when the cloud is ``rows`` cells tall."""
		rows = rows or self.rows
		return self.bottom - rows * self.cell + cloud_top(self.seed, self.cols, rows) * self.cell + self.sink

	def draw(self, img: Image.Image, cx: float, cy: float, dip: float = 0.0, rows: int | None = None, alpha: float = 1.0,
			light: tuple | None = None) -> None:
		"""Draws the cloud; ``alpha`` below 1 fades it in (in five steps, so the sprites stay cached)."""
		if alpha <= 0:
			return
		rows = rows or self.rows
		spr = lit(cloud(self.seed, self.cols, rows, self.cell, self.palette, int(255 * min(1.0, round(alpha * 5) / 5)) or 51), light)
		blit(img, spr, snap(self.x - spr.width / 2 - cx, 4), snap(self.bottom - rows * self.cell + dip - cy, 4))


def bounce(t: float, landings: Sequence[float], amplitude: float = 22.0) -> float:
	"""A soft bounce for a platform after each landing time: down, a little back up, settle."""
	d = 0.0
	for tl in landings:
		dt = t - tl
		if 0 <= dt < 0.6:
			d += amplitude * math.exp(-dt * 7.0) * math.sin(dt * 16)
	return d


class CloudLayer:
	"""A parallax layer of background clouds that repeats every ``span`` px as the camera moves.

	``parallax`` is how fast the layer follows the camera (0: fixed to the screen, 1: world
	speed); ``drift`` moves the clouds by themselves, in px per second.
	"""

	def __init__(self, seed: int, count: int, y: tuple, palette='day', alpha: int = 170, sizes: tuple = (12, 22),
			cell: int = 10, parallax: tuple = (0.3, 0.3), drift: float = 0.0, span: int = 1500):
		rng = random.Random(seed)
		self.parallax, self.drift, self.span = parallax, drift, span
		self.clouds = []
		for i in range(count):
			cols = rng.randrange(*sizes)
			rows = max(6, round(cols / 2.4))
			x = rng.uniform(0, span)
			cy = y[0] + (y[1] - y[0]) * (i + rng.uniform(0.1, 0.9)) / count
			self.clouds.append((x, cy, cloud(seed * 100 + i, cols, rows, cell, palette, alpha)))

	def draw(self, img: Image.Image, t: float, cx: float, cy: float, light: tuple | None = None) -> None:
		px, py = self.parallax
		for (x, y, spr) in self.clouds:
			spr = lit(spr, light)
			sx = (x - cx * px + t * self.drift) % self.span - (self.span - img.width) / 2
			sy = y - cy * py
			if -spr.width < sx < img.width and -spr.height < sy < img.height:
				blit(img, spr, snap(sx - spr.width / 2, 4), snap(sy, 4))


# --------------------------------------------------------------------------------------------
# Light and air


def rays(img: Image.Image, t: float, center: tuple, strength: float, count: int = 14, speed: float = 0.22,
		cell: int = 8, color: tuple = (255, 236, 190), alpha: int = 58) -> None:
	"""Slowly turning light rays from screen ``center``, drawn on a ``cell`` grid so they stay pixelated."""
	if strength <= 0:
		return
	w, h = img.size
	small = Image.new('RGBA', (w // cell + 1, h // cell + 1), (0, 0, 0, 0))
	d = ImageDraw.Draw(small)
	cxs, cys = center[0] / cell, center[1] / cell
	r = (w + h) / cell
	for i in range(count):
		a = t * speed + i * math.tau / count
		half = math.tau / count * 0.23
		d.polygon([(cxs, cys), (cxs + r * math.cos(a - half), cys + r * math.sin(a - half)),
			(cxs + r * math.cos(a + half), cys + r * math.sin(a + half))], fill=color + (int(alpha * strength),))
	img.alpha_composite(small.resize((small.width * cell, small.height * cell), Image.NEAREST).crop((0, 0, w, h)))


def gust(img: Image.Image, t: float, t0: float, cx: float, cy: float, origin: tuple, length: float = 0.7,
		direction: tuple = (1.0, -0.42), petals: bool = True, seed: int = 4) -> None:
	"""A gust of wind from world ``origin`` at ``t0``: white streaks (and petals) racing along ``direction``."""
	dt = t - t0
	if not (0 <= dt < length):
		return
	rng = random.Random(seed)
	fade = 1 - seg(dt, length * 0.6, length)
	dx, dy = direction
	for i in range(16):
		k = dt - rng.uniform(0, 0.25)
		speed = rng.uniform(1500, 2300)
		ox, oy = rng.uniform(-60, 380), rng.uniform(-320, 260)
		ln = rng.choice((36, 60, 84, 108))
		if k < 0:
			continue
		x = origin[0] - 520 + ox + k * speed * dx
		y = origin[1] + oy + k * speed * dy
		a = int(210 * fade)
		fill_rect(img, snap(x - cx, 4), snap(y - cy, 4), ln, 6, (255, 255, 255, a))
		fill_rect(img, snap(x - cx + ln, 4), snap(y - cy - 6, 4), ln // 3, 6, (255, 255, 255, a // 2))
	if petals:
		colors = [hexc('#ff8fc0'), hexc('#fff3a0'), hexc('#ffffff')]
		for i in range(9):
			k = dt - i * 0.03
			if k < 0:
				continue
			x = origin[0] - 200 + i * 40 + k * 900 * dx + math.sin(k * 14 + i) * 30
			y = origin[1] + 60 + k * 1650 * dy - math.cos(k * 11 + i) * 20
			fill_rect(img, snap(x - cx, 4), snap(y - cy, 4), CELL, CELL, colors[i % 3][:3] + (int(255 * fade),))


def speed_lines(img: Image.Image, t: float, t0: float, t1: float, vertical: bool = True, seed: int = 9, alpha: int = 120) -> None:
	"""Speed lines rushing past the screen between ``t0`` and ``t1``: downward (the pet shoots
	up) when ``vertical``, else leftward (the pet dashes right)."""
	if not (t0 <= t < t1):
		return
	k = seg(t, t0, t0 + 0.15) * (1 - seg(t, t1 - 0.3, t1))
	rng = random.Random(seed)
	w, h = img.size
	for _ in range(18):
		across = rng.uniform(80, (w if vertical else h) - 80)
		speed = rng.uniform(1800, 2600)
		ln = rng.choice((72, 120, 168))
		along = (rng.uniform(0, h if vertical else w) + (t - t0) * speed) % ((h if vertical else w) + ln) - ln
		color = (255, 255, 255, int(alpha * k))
		if vertical:
			fill_rect(img, snap(across, 4), snap(along, 4), 6, ln, color)
		else:
			fill_rect(img, snap(w - along, 4), snap(across, 4), ln, 6, color)
