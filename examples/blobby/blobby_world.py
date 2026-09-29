"""The sunset sky of the Blobby reel.

Two backdrops share one look:

* the chase: a hilltop, cloud platforms, parallax clouds, a low sun, wind and stars, in world
  coordinates that scroll with the camera (``cx, cy`` is the camera's top-left corner);
* the reveal: dusk above a sea of clouds, with the sun and slowly turning light rays behind the
  name, in screen coordinates.

Everything sits on a pixel grid and is cached, so a frame is a handful of crops and composites.
"""

from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from kit import art
from kit.draw import blit, clamp, fill_rect, hexc, mix, seg, snap

W, H = 1080, 1920
GROUND_Y = 1450  # world y of the hilltop spot where the pet starts; the camera starts at cy = 0
CHASE_TOP = -2400  # highest world y the chase camera shows
CELL = 12  # chase detail grid: half a pet pixel at scale 3
WIDE_CELL = 8  # reveal detail grid: half a pet pixel at scale 2

# Sunset sky by altitude above the hilltop: gold at the hill, pink, then purple dusk.
SKY_KEYS = [(-800, '#ffd9a0'), (0, '#ffcb88'), (700, '#ffab7c'), (1400, '#ff8b8d'), (2100, '#e574ad'),
	(2800, '#a765c3'), (3500, '#6552b0'), (4300, '#2f2b6e')]


def _lerp_keys(keys: list, v: float) -> tuple:
	if v <= keys[0][0]:
		return hexc(keys[0][1])
	for (a0, c0), (a1, c1) in zip(keys, keys[1:]):
		if v <= a1:
			return mix(hexc(c0), hexc(c1), (v - a0) / (a1 - a0))
	return hexc(keys[-1][1])


def sky_color(world_y: float) -> tuple:
	return _lerp_keys(SKY_KEYS, GROUND_Y - world_y)


def _banded(colors_for_row, height: int, band: int = 8) -> Image.Image:
	arr = np.zeros((height, W, 4), np.uint8)
	for y0 in range(0, height, band):
		arr[y0:y0 + band, :, :] = colors_for_row(y0 + band / 2)
	return Image.fromarray(arr, 'RGBA')


@lru_cache(maxsize=None)
def _chase_sky() -> Image.Image:
	"""The whole chase sky from ``CHASE_TOP`` to below the hill, in 8 px bands."""
	return _banded(lambda y: sky_color(CHASE_TOP + y), GROUND_Y + H - CHASE_TOP)


# --------------------------------------------------------------------------------------------
# Clouds: cumulus shapes on a cell grid, shaded with a sunlit rim and soft shadows

CLOUD_WARM = ('#ffffff', '#fff1ea', '#ffc8c9', '#eea0b4')  # rim, body, shade, deep
CLOUD_PINK = ('#ffffff', '#ffe8f1', '#f9b8d3', '#e29ac2')
CLOUD_SPRING = ('#ffffff', '#fff3f8', '#ffb7d6', '#f08fbf')


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
		mid = 1 - abs(u - 0.5) * 2
		r = rows * (0.30 + 0.28 * mid) * rng.uniform(0.9, 1.08)
		px = cols * (0.18 + 0.64 * u) + rng.uniform(-0.6, 0.6)
		m |= (xs - px) ** 2 + (ys - (base_top + r * 0.15)) ** 2 <= r * r
	return m


def shade_mask(m: np.ndarray, palette: tuple, alpha: int = 255) -> Image.Image:
	"""Colors a cell mask: sunlit rim on top, body, shade on the lower sides, deep bottom row."""
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
	lower = yy >= rows * 0.6
	out[m & lower & (~left | ~right)] = shade
	out[m & (yy >= rows - 2)] = shade
	out[m & (yy == rows - 1)] = deep
	out[m & ~above] = rim
	return Image.fromarray(out, 'RGBA')


@lru_cache(maxsize=None)
def cloud_sprite(seed: int, cols: int, rows: int, cell: int, palette: tuple, alpha: int = 255) -> Image.Image:
	return shade_mask(cloud_mask(seed, cols, rows), palette, alpha).resize((cols * cell, rows * cell), Image.NEAREST)


def surface_offset(seed: int, cols: int, rows: int) -> int:
	"""Cells from the sprite's top to the cloud's top in the middle column (where the pet lands)."""
	m = cloud_mask(seed, cols, rows)
	col = m[:, cols // 2]
	return int(np.argmax(col)) if col.any() else 0


SINK = CELL // 2  # the pet's feet sink half a cell into the fluff


class Platform:
	"""A cloud the pet stands on. ``top`` is the world y of its surface under the pet.

	The bottom stays put when the cloud is squashed (``rows`` smaller than at rest), so a spring
	cloud compresses under the pet and ``surface(rows)`` follows it down.
	"""

	def __init__(self, x: float, top: float, cols: int, rows: int, seed: int, palette: tuple = CLOUD_WARM):
		self.x, self.top, self.cols, self.rows, self.seed, self.palette = x, top, cols, rows, seed, palette
		self.bottom = top - surface_offset(seed, cols, rows) * CELL - SINK + rows * CELL

	def sprite_top(self, rows: int) -> float:
		return self.bottom - rows * CELL

	def surface(self, rows: int | None = None) -> float:
		rows = rows or self.rows
		return self.sprite_top(rows) + surface_offset(self.seed, self.cols, rows) * CELL + SINK

	def draw(self, img: Image.Image, cx: float, cy: float, dip: float = 0.0, rows: int | None = None) -> None:
		rows = rows or self.rows
		spr = cloud_sprite(self.seed, self.cols, rows, CELL, self.palette)
		blit(img, spr, snap(self.x - spr.width / 2 - cx, 4), snap(self.sprite_top(rows) + dip - cy, 4))


def dip(t: float, landings: list, amplitude: float = 22.0) -> float:
	"""A soft bounce after each landing time: down, a little overshoot, settle."""
	d = 0.0
	for tl in landings:
		dt = t - tl
		if 0 <= dt < 0.6:
			d += amplitude * math.exp(-dt * 7.0) * math.sin(dt * 16)
	return d


# --------------------------------------------------------------------------------------------
# The chase backdrop


def _hill_surface(x: float) -> float:
	"""World y of the hill's grass line: a gentle dome peaking under the pet's starting spot."""
	u = (x - 380) / 560
	return GROUND_Y + u * u * 330


@lru_cache(maxsize=None)
def _hill() -> Image.Image:
	"""The grassy hill in world space (top-left at world (0, GROUND_Y - 60)), with flowers."""
	top = GROUND_Y - 60
	height = H + 60
	cols, rows = W // CELL, height // CELL
	out = np.zeros((rows, cols, 4), np.uint8)
	rim, grass, mid, deep, dark = (hexc(c) for c in ('#c9ea7c', '#79c35a', '#5aa94d', '#438f47', '#2f6f40'))
	for c in range(cols):
		surf = int(round((_hill_surface(c * CELL + CELL / 2) - top) / CELL))
		for r in range(max(0, surf), rows):
			d = r - surf
			color = rim if d == 0 else grass if d < 5 else mid if d < 11 else deep if d < 19 else dark
			if d in (5, 11, 19) and (c + r) % 2:  # dithered band edges
				color = grass if d == 5 else mid if d == 11 else deep
			out[r, c] = color
	img = Image.fromarray(out, 'RGBA').resize((cols * CELL, rows * CELL), Image.NEAREST)
	rng = random.Random(11)
	petals = [hexc('#ff8fc0'), hexc('#fff3a0'), hexc('#ffffff'), hexc('#ffb86b')]
	for i in range(16):
		x = rng.randrange(40, W - 40)
		if abs(x - 380) < 170:  # keep the pet's spot clear
			continue
		y = _hill_surface(x) - top
		px, py = snap(x, CELL), snap(y, CELL) - CELL
		col = petals[i % len(petals)]
		fill_rect(img, px, py + CELL, CELL, CELL, hexc('#3f8a3f'))  # stem
		for (dx, dy) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
			fill_rect(img, px + dx * CELL, py + dy * CELL, CELL, CELL, col)
		fill_rect(img, px, py, CELL, CELL, hexc('#ffd24a'))
	return img


@lru_cache(maxsize=None)
def _ridge(seed: int, color: str, base: float, amp: float) -> Image.Image:
	"""A far hill ridge (world-space silhouette, drawn with parallax)."""
	rng = random.Random(seed)
	phases = [rng.uniform(0, math.tau) for _ in range(3)]
	cols = W // CELL
	h = 700
	img = Image.new('RGBA', (W, h), (0, 0, 0, 0))
	for c in range(cols):
		x = c / cols
		y = base + amp * (0.55 * math.sin(x * 5.1 + phases[0]) + 0.3 * math.sin(x * 11.3 + phases[1]) + 0.15 * math.sin(x * 23 + phases[2]))
		fill_rect(img, c * CELL, snap(y, CELL), CELL, h, hexc(color))
	return img


@lru_cache(maxsize=None)
def _sun(radius: int, cell: int, stripes: bool = True) -> Image.Image:
	"""A pixel sun with two soft halo rings; the lower half has sunset stripes."""
	n = radius // cell
	size = (n * 2 + 9) * cell
	img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
	c0 = size / 2
	core, body, rim = hexc('#fff6c8'), hexc('#ffd66e'), hexc('#ffac4f')
	for ring, alpha in ((n + 4, 38), (n + 2, 64)):
		for gy in range(size // cell):
			for gx in range(size // cell):
				dx, dy = gx * cell + cell / 2 - c0, gy * cell + cell / 2 - c0
				if dx * dx + dy * dy <= (ring * cell) ** 2:
					fill_rect(img, gx * cell, gy * cell, cell, cell, hexc('#fff0c4', alpha))
	for gy in range(size // cell):
		for gx in range(size // cell):
			dx, dy = gx * cell + cell / 2 - c0, gy * cell + cell / 2 - c0
			d2 = dx * dx + dy * dy
			if d2 <= (n * cell) ** 2:
				row = dy / (n * cell)
				if stripes and row > 0.25 and int((row - 0.25) * 12) % 3 == 2:
					continue
				col = core if d2 <= ((n - 3) * cell) ** 2 and dy < 0 else mix(body, rim, clamp(row * 0.9 + 0.35, 0, 1))
				img.paste(col, (gx * cell, gy * cell, gx * cell + cell, gy * cell + cell))
	return img


def _layer_clouds(seed: int, n: int, y0: float, y1: float, size: tuple, palette: tuple, alpha: int, cell: int) -> list:
	rng = random.Random(seed)
	out = []
	for i in range(n):
		cols = rng.randrange(*size)
		rows = max(6, round(cols / 2.4))
		x = rng.uniform(-80, W + 80)
		y = y0 + (y1 - y0) * (i + rng.uniform(0.1, 0.9)) / n
		out.append((x, y, cloud_sprite(seed * 100 + i, cols, rows, cell, palette, alpha)))
	return out


FAR_CLOUDS = None
MID_CLOUDS = None


def _cloud_layers() -> tuple:
	global FAR_CLOUDS, MID_CLOUDS
	if FAR_CLOUDS is None:
		FAR_CLOUDS = _layer_clouds(21, 12, 300, 2000, (10, 18), ('#ffe9e0', '#ffcdc4', '#f3a9b6', '#e493ad'), 110, 8)
		MID_CLOUDS = _layer_clouds(34, 12, -1200, 1400, (12, 20), ('#fff1f0', '#ffd4d4', '#f0a7bd', '#d98cb2'), 140, 10)
	return FAR_CLOUDS, MID_CLOUDS


@lru_cache(maxsize=None)
def _stars(seed: int, n: int) -> list:
	rng = random.Random(seed)
	return [(rng.uniform(20, W - 20), rng.uniform(-1500, 900), rng.random(), rng.random() < 0.18) for _ in range(n)]


def _star(img: Image.Image, x: float, y: float, big: bool, color: tuple) -> None:
	x, y = snap(x, 4), snap(y, 4)
	if big:
		fill_rect(img, x - 4, y, 12, 4, color)
		fill_rect(img, x, y - 4, 4, 12, color)
	else:
		fill_rect(img, x, y, 4, 4, color)


def draw_chase_backdrop(img: Image.Image, t: float, cx: float, cy: float) -> None:
	"""Sky, stars, sun, far ridges, far and mid clouds and the hill for camera ``(cx, cy)``."""
	sky = _chase_sky()
	top = int(round(cy)) - CHASE_TOP
	img.paste(sky.crop((0, top, W, top + H)), (0, 0))
	altitude = -cy
	star_k = seg(altitude, 900, 1900)
	if star_k > 0:
		for (x, y, ph, big) in _stars(5, 70):
			sy = y - cy * 0.25
			if -8 <= sy < H and y - cy * 0.25 < H * 0.8:
				tw = 0.55 + 0.45 * math.sin(t * 5 + ph * 30)
				a = int(255 * star_k * tw)
				if a > 20:
					_star(img, x, sy, big, (255, 246, 214, a))
	sun = _sun(156, CELL)
	blit(img, sun, snap(900 - sun.width / 2 - cx * 0.15, 4), snap(1150 - sun.height / 2 - cy * 0.15, 4))
	far, mid = _cloud_layers()
	for (x, y, spr) in far:
		sy = y - cy * 0.3
		if -spr.height < sy < H:
			blit(img, spr, snap(x - spr.width / 2 + math.sin(t * 0.4 + y) * 6, 4), snap(sy, 4))
	blit(img, _ridge(3, '#f0a18a', 140, 70), 0, snap(GROUND_Y - 330 - cy * 0.55, 4))
	blit(img, _ridge(8, '#d9837d', 230, 60), 0, snap(GROUND_Y - 300 - cy * 0.75, 4))
	for (x, y, spr) in mid:
		sy = y - cy * 0.6
		if -spr.height < sy < H:
			blit(img, spr, snap(x - spr.width / 2 - cx * 0.6, 4), snap(sy, 4))
	hill = _hill()
	hy = GROUND_Y - 60 - cy
	if hy < H:
		blit(img, hill, -cx, hy)


# --------------------------------------------------------------------------------------------
# Effects in the sky


def wind(img: Image.Image, t: float, t0: float, cx: float, cy: float, origin: tuple, length: float = 0.7) -> None:
	"""A gust: white streaks and petals racing up and to the right from ``origin`` (world)."""
	dt = t - t0
	if not (0 <= dt < length):
		return
	rng = random.Random(4)
	fade = 1 - seg(dt, length * 0.6, length)
	for i in range(16):
		delay = rng.uniform(0, 0.25)
		k = dt - delay
		if k < 0:
			continue
		speed = rng.uniform(1500, 2300)
		x = origin[0] - 520 + rng.uniform(-60, 380) + k * speed
		y = origin[1] + rng.uniform(-320, 260) - k * speed * 0.42
		ln = rng.choice((36, 60, 84, 108))
		a = int(210 * fade)
		fill_rect(img, snap(x - cx, 4), snap(y - cy, 4), ln, 6, (255, 255, 255, a))
		fill_rect(img, snap(x - cx + ln, 4), snap(y - cy - 6, 4), ln // 3, 6, (255, 255, 255, a // 2))
	petals = [hexc('#ff8fc0'), hexc('#fff3a0'), hexc('#ffffff')]
	for i in range(9):
		k = dt - i * 0.03
		if k < 0:
			continue
		x = origin[0] - 200 + i * 40 + k * 900 + math.sin(k * 14 + i) * 30
		y = origin[1] + 60 - k * 700 - math.cos(k * 11 + i) * 20
		col = petals[i % 3]
		fill_rect(img, snap(x - cx, 4), snap(y - cy, 4), CELL, CELL, col[:3] + (int(255 * fade),))


def rise_streaks(img: Image.Image, t: float, t0: float, t1: float, cx: float, cy: float) -> None:
	"""Speed lines falling past the camera while the pet shoots upward."""
	if not (t0 <= t < t1):
		return
	k = seg(t, t0, t0 + 0.15) * (1 - seg(t, t1 - 0.3, t1))
	rng = random.Random(9)
	for i in range(18):
		x = rng.uniform(80, W - 80)
		speed = rng.uniform(1800, 2600)
		ln = rng.choice((72, 120, 168))
		y = (rng.uniform(0, H) + (t - t0) * speed) % (H + ln) - ln
		fill_rect(img, snap(x, 4), snap(y, 4), 6, ln, (255, 255, 255, int(120 * k)))


def butterfly(img: Image.Image, t: float, cx: float, cy: float, t_gust: float) -> None:
	"""A butterfly fluttering over the hill until the gust carries it off."""
	if t < t_gust:
		x = 190 + math.sin(t * 2.1) * 50
		y = GROUND_Y - 330 + math.sin(t * 3.3) * 40
	else:
		k = max(0.0, t - t_gust - 0.1)
		x = 190 + math.sin((t_gust + 0.1) * 2.1) * 50 + k * 1100
		y = GROUND_Y - 330 - k * 1500 + math.sin(k * 20) * 20
	if x - cx > W + 60:
		return
	spr = art.butterfly(int(t * 12) % 3)
	blit(img, spr, snap(x - spr.width / 2 - cx, 4), snap(y - spr.height / 2 - cy, 4))


def shadow(img: Image.Image, x: float, y: float, cx: float, cy: float, width: float, alpha: int = 70) -> None:
	"""A soft oval shadow under the pet on a surface at world ``(x, y)``."""
	w = snap(width, CELL)
	fill_rect(img, snap(x - w / 2 - cx, 4) + CELL, snap(y - cy, 4) - 6, w - 2 * CELL, 12, (90, 30, 80, alpha))
	fill_rect(img, snap(x - w / 2 - cx, 4), snap(y - cy, 4) - 3, w, 6, (90, 30, 80, alpha // 2))


# --------------------------------------------------------------------------------------------
# The reveal backdrop: dusk above a sea of clouds, in screen space

DUSK_KEYS = [(0, '#1b1a48'), (420, '#2f2a70'), (820, '#5b3f98'), (1120, '#9a55a3'), (1360, '#d8699a'),
	(1540, '#ff9483'), (1700, '#ffbf8d'), (1920, '#ffd6a0')]
SUN_CENTER = (510, 1020)


@lru_cache(maxsize=None)
def _dusk_sky() -> Image.Image:
	return _banded(lambda y: _lerp_keys(DUSK_KEYS, y), H)


@lru_cache(maxsize=None)
def _cloud_sea() -> Image.Image:
	"""Three rows of lit cumulus at the bottom of the reveal frame, lighter toward the front."""
	img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
	rows_spec = [
		(1380, 12, (20, 30), ('#ffd2c6', '#eea6bd', '#cf86b6', '#9f6cab'), 300),
		(1470, 14, (24, 34), ('#ffe2d2', '#fbb8bb', '#e393b5', '#b776ad'), 400),
		(1570, 16, (28, 38), ('#fff0e0', '#ffcbbd', '#f0a2b4', '#c983ae'), 500),
	]
	for (y, rows, (c0, c1), palette, seed) in rows_spec:
		rng = random.Random(seed)
		x = -rng.uniform(40, 140)
		i = 0
		while x < W + 60:
			cols = rng.randrange(c0, c1)
			spr = cloud_sprite(seed + i, cols, rows, WIDE_CELL, palette)
			blit(img, spr, snap(x, 8), snap(y - rng.uniform(0, 40), 8))
			x += cols * WIDE_CELL * rng.uniform(0.55, 0.75)
			i += 1
	fill_rect(img, 0, 1690, W, H - 1690, hexc('#ffcbbd'))
	return img


def rays(img: Image.Image, t: float, center: tuple, strength: float, count: int = 14, speed: float = 0.22) -> None:
	"""Slowly turning light rays from ``center``, drawn on a coarse grid so they stay pixelated."""
	if strength <= 0:
		return
	g = WIDE_CELL
	small = Image.new('RGBA', (W // g, H // g), (0, 0, 0, 0))
	d = ImageDraw.Draw(small)
	cxs, cys = center[0] / g, center[1] / g
	r = 400
	a0 = t * speed
	for i in range(count):
		a = a0 + i * math.tau / count
		half = math.tau / count * 0.23
		pts = [(cxs, cys), (cxs + r * math.cos(a - half), cys + r * math.sin(a - half)), (cxs + r * math.cos(a + half), cys + r * math.sin(a + half))]
		d.polygon(pts, fill=(255, 236, 190, int(58 * strength)))
	img.alpha_composite(small.resize((W, H), Image.NEAREST))


def draw_reveal_backdrop(img: Image.Image, t: float, ray_strength: float, t0: float) -> None:
	"""Dusk sky, twinkling stars, rays, the sun and the cloud sea (screen space)."""
	img.paste(_dusk_sky(), (0, 0))
	for (x, y, ph, big) in _stars(17, 60):
		sy = (y + 1500) * 0.55
		if sy < 1150:
			tw = 0.5 + 0.5 * math.sin(t * 4 + ph * 40)
			a = int(235 * tw * (1 - sy / 1400))
			if a > 25:
				_star(img, x, sy, big, (255, 244, 220, a))
	rays(img, t - t0, SUN_CENTER, ray_strength)
	sun = _sun(304, WIDE_CELL, stripes=True)
	blit(img, sun, snap(SUN_CENTER[0] - sun.width / 2, 8), snap(SUN_CENTER[1] - sun.height / 2, 8))
	for i in range(4):  # a few small clouds drifting across mid-sky
		spr = cloud_sprite(500 + i, 12 + i * 3, 6, WIDE_CELL, ('#f7d3f0', '#d9a6d8', '#b384c4', '#8f68b2'), 170)
		x = ((140 + i * 290) - (t - t0) * (14 + i * 5)) % (W + 300) - 150
		blit(img, spr, snap(x, 8), 380 + i * 170 + (i % 2) * 40)
	img.alpha_composite(_cloud_sea())
