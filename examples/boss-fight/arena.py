"""Art for the boss-fight reel: the bug boss, the server-room arena, props and the game HUD.

The boss is drawn from shapes sampled on the pet's own grid (24 px cells, one pet pixel at
scale 3), then outlined and shaded like the pet: lit from the upper right.
"""

from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image

from kit import art, sky, world
from kit.draw import blit, fill_rect, grid_sprite, hexc, snap
from kit.font import text_width

W, H = 1080, 1920
FLOOR = 1420          # the pets' feet
CELL = 24             # the boss's grid: one pet pixel at scale 3
SMALL = 12            # small props: half a pet pixel

# --------------------------------------------------------------------------------------------
# The boss

BW, BH = 28, 14       # its grid, before the one-cell outline around it
BOSS_W, BOSS_H = (BW + 2) * CELL, (BH + 2) * CELL
BOSS_PAL = {
	'K': hexc('#1a0b1a'), 'H': hexc('#3a3f63'), 'h': hexc('#5d6390'),
	'R': hexc('#e5484d'), 'r': hexc('#ff8f93'), 'D': hexc('#a3262c'), 'S': hexc('#2a1428'),
	'W': hexc('#ffffff'), 'E': hexc('#140a14'), 'M': hexc('#7a1020'), 'A': hexc('#ff5a64'),
	'Y': hexc('#ffe14d'), 'P': hexc('#ff2a2a'),
	'w': (190, 230, 255, 110), 'v': (225, 245, 255, 190),
}


def _ellipse(cx: float, cy: float, rx: float, ry: float, w: int = BW, h: int = BH) -> np.ndarray:
	yy, xx = np.mgrid[0:h, 0:w]
	return ((xx + 0.5 - cx) / rx) ** 2 + ((yy + 0.5 - cy) / ry) ** 2 <= 1.0


def _cells(cells: list) -> np.ndarray:
	m = np.zeros((BH, BW), bool)
	for (c, r) in cells:
		m[r, c] = True
	return m


def _mirror(cells: list) -> list:
	return cells + [(BW - 1 - c, r) for (c, r) in cells]


SHELL = _ellipse(14, 8.0, 8.3, 4.9)
HEAD = _ellipse(14, 5.2, 5.0, 3.5)
ANTENNAE = _cells(_mirror([(8, 0), (9, 0), (10, 1)]))
BALLS = _cells(_mirror([(8, 0), (9, 0)]))
LEGS = _cells(_mirror([(8, 12), (7, 13), (11, 13)]))
BODY = SHELL | HEAD | ANTENNAE | LEGS
WINGS = (_ellipse(5.2, 4.2, 4.8, 2.6) | _ellipse(22.8, 4.2, 4.8, 2.6),
	_ellipse(4.8, 7.6, 4.6, 2.3) | _ellipse(23.2, 7.6, 4.6, 2.3))
SPOTS = _ellipse(8.8, 8.6, 1.3, 1.2) | _ellipse(19.2, 8.6, 1.3, 1.2) | _ellipse(10.8, 11.2, 1.0, 0.9) | _ellipse(17.2, 11.2, 1.0, 0.9)
SPLIT = _cells([(c, r) for c in (13, 14) for r in range(9, 13)])
EYES = {
	'angry': (_mirror([(10, 4), (11, 4), (10, 5), (11, 5), (10, 6), (11, 6)]), _mirror([(12, 5), (12, 6)])),
	'roar': (_mirror([(10, 4), (11, 4), (12, 4), (10, 5), (11, 5), (10, 6), (11, 6), (12, 6)]), _mirror([(12, 5)])),
	'dazed': (_mirror([(10, 4), (12, 4), (11, 5), (10, 6), (12, 6)]), []),
}
MOUTHS = {
	'angry': (_mirror([(12, 8), (13, 7)]), _mirror([(13, 8)])),
	'roar': (_mirror([(12, 7), (13, 7), (13, 8)]), _mirror([(12, 8)])),
	'dazed': ([(12, 8), (13, 7), (14, 8), (15, 7)], []),
}


def _dilate(m: np.ndarray) -> np.ndarray:
	out = m.copy()
	for dy in (-1, 0, 1):
		for dx in (-1, 0, 1):
			out |= np.roll(np.roll(m, dy, 0), dx, 1)
	return out


@lru_cache(maxsize=64)
def boss_grid(wing: int | None, mood: str = 'angry', flash: bool = False, charge: bool = False) -> tuple:
	"""The boss as rows of palette letters, with a one-cell margin all round."""
	pad = lambda m: np.pad(m, 1)
	body = pad(BODY)
	ring = _dilate(body) & ~body
	grid = np.full(body.shape, '.', dtype='<U1')
	if wing is not None:
		wings = pad(WINGS[wing]) & ~body & ~ring
		edge = wings & ~(np.roll(wings, 1, 0) & np.roll(wings, -1, 0) & np.roll(wings, 1, 1) & np.roll(wings, -1, 1))
		grid[wings] = 'w'
		grid[edge] = 'v'
	grid[ring] = 'K'
	yy, xx = np.mgrid[0:BH, 0:BW]
	shell_lit = ((xx + 0.5 - 14) / 8.3) * 0.6 - ((yy + 0.5 - 8.0) / 4.9) * 0.8
	head_lit = ((xx + 0.5 - 14) / 5.0) * 0.6 - ((yy + 0.5 - 5.2) / 3.5) * 0.8
	inner = np.full((BH, BW), '.', dtype='<U1')
	inner[SHELL] = 'R'
	inner[SHELL & (shell_lit > 0.55)] = 'r'
	inner[SHELL & (shell_lit < -0.45)] = 'D'
	inner[SPOTS & SHELL] = 'S'
	inner[SPLIT] = 'K'
	for (c, r) in ((19, 4), (20, 5)):
		inner[r, c] = 'W'
	inner[HEAD] = 'H'
	inner[HEAD & (head_lit > 0.75)] = 'h'
	inner[ANTENNAE] = 'K'
	inner[BALLS] = 'Y' if charge else 'A'
	inner[LEGS] = 'K'
	whites, pupils = EYES[mood]
	for (c, r) in whites:
		inner[r, c] = 'Y' if charge else 'W'
	for (c, r) in pupils:
		inner[r, c] = 'P' if charge else 'E'
	dark, fangs = MOUTHS[mood]
	for (c, r) in dark:
		inner[r, c] = 'M'
	for (c, r) in fangs:
		inner[r, c] = 'W'
	grid[1:-1, 1:-1] = np.where(inner != '.', inner, grid[1:-1, 1:-1])
	if flash:
		grid[(grid != '.') & (grid != 'w') & (grid != 'v')] = 'W'
	return tuple(''.join(row) for row in grid)


@lru_cache(maxsize=64)
def boss_sprite(wing: int | None, mood: str = 'angry', flash: bool = False, charge: bool = False, cell_h: int = CELL, cell_w: int = CELL) -> Image.Image:
	"""The boss sprite; ``cell_h`` below ``CELL`` squashes it, smaller cells shrink it (whole pixels)."""
	rows = boss_grid(wing, mood, flash, charge)
	im = Image.new('RGBA', (len(rows[0]), len(rows)), (0, 0, 0, 0))
	px = im.load()
	for y, row in enumerate(rows):
		for x, ch in enumerate(row):
			if ch != '.':
				px[x, y] = BOSS_PAL[ch]
	return im.resize((im.width * cell_w, im.height * cell_h), Image.NEAREST)


# --------------------------------------------------------------------------------------------
# Small props (12 px cells)

PROP_PAL = {
	'K': hexc('#3a0710'), 'R': hexc('#e5484d'), 'r': hexc('#ff8f93'), 'D': hexc('#a3262c'), 'W': hexc('#ffffff'),
	'k': hexc('#7a4a00'), 'L': hexc('#fff1a8'), 'Y': hexc('#ffc93d'), 'd': hexc('#d9961c'), 'b': hexc('#8a5200'),
	'G': hexc('#ffe14d'), 'g': hexc('#8a6a00'),
}
ERROR_BLOCK = [
	'.KKKKK.',
	'KrrrrrK',
	'KRWRWRK',
	'KRRWRRK',
	'KRWRWRK',
	'KDDDDDK',
	'.KKKKK.',
]
ITEM_BOX = [
	'.kkkkkkk.',
	'kLLLLLLLk',
	'kYYbbYYYk',
	'kYYYYbYYk',
	'kYYYbYYYk',
	'kYYYYYYYk',
	'kYYYbYYYk',
	'kdddddddk',
	'.kkkkkkk.',
]


@lru_cache(maxsize=None)
def prop(name: str, cell: int = SMALL) -> Image.Image:
	return grid_sprite({'error': ERROR_BLOCK, 'box': ITEM_BOX}[name], PROP_PAL, cell)


@lru_cache(maxsize=None)
def reticle(big: bool) -> Image.Image:
	"""The weak-spot target: a gold ring with four ticks, outlined (11 x 11 cells)."""
	n = 11
	c = n // 2
	r0 = 3.7 if big else 3.0
	yy, xx = np.mgrid[0:n, 0:n]
	d = np.hypot(xx - c, yy - c)
	ring = np.abs(d - r0) < 0.62
	ticks = ((xx == c) & ((yy <= 1) | (yy >= n - 2))) | ((yy == c) & ((xx <= 1) | (xx >= n - 2)))
	dot = (xx == c) & (yy == c)
	shape = ring | ticks | dot
	outline = _dilate(shape) & ~shape
	rows = []
	for y in range(n):
		rows.append(''.join('G' if shape[y, x] else 'g' if outline[y, x] else '.' for x in range(n)))
	return grid_sprite(rows, PROP_PAL, SMALL)


# --------------------------------------------------------------------------------------------
# The arena: a server room in production

RACKS = [(66, 820), (318, 820), (570, 820), (822, 820)]   # (x0, y0) of each rack
RACK_W, SLOT = 192, 48


@lru_cache(maxsize=1)
def _room() -> Image.Image:
	"""The still part of the room: wall, racks (without their lights) and the floor."""
	img = Image.new('RGBA', (W, H))
	img.paste(sky.gradient((W, H), ((0.0, '#10122a'), (0.5, '#1b1f3e'), (0.74, '#232849'), (1.0, '#161a30'))), (0, 0))
	for x in range(0, W, 180):  # wall panels
		fill_rect(img, x, 0, 6, FLOOR, hexc('#171a36'))
	fill_rect(img, 0, 780, W, 8, hexc('#141630'))
	for (x0, y0) in RACKS:
		fill_rect(img, x0 - 8, y0 - 8, RACK_W + 16, FLOOR - y0 + 8, hexc('#0b0d1c'))
		fill_rect(img, x0, y0, RACK_W, FLOOR - y0, hexc('#1c2038'))
		for y in range(y0 + 12, FLOOR - 24, SLOT):
			fill_rect(img, x0 + 12, y, RACK_W - 24, SLOT - 12, hexc('#262b48'))
			fill_rect(img, x0 + 12, y + SLOT - 16, RACK_W - 24, 4, hexc('#171a30'))
			for k in range(4):  # vents
				fill_rect(img, x0 + 24 + k * 16, y + 10, 8, SLOT - 30, hexc('#1c2038'))
	fill_rect(img, 0, FLOOR, W, H - FLOOR, hexc('#343a58'))
	fill_rect(img, 0, FLOOR, W, 8, hexc('#6a7196'))
	for x in range(0, W, 120):
		fill_rect(img, x, FLOOR + 8, 4, H - FLOOR, hexc('#2a2f4a'))
	fill_rect(img, 0, FLOOR + 100, W, 4, hexc('#2a2f4a'))
	for x in range(-24, W, 48):  # a hazard stripe along the edge of the floor
		for k in range(4):
			fill_rect(img, x + k * 6, FLOOR + 16 + k * 6, 24, 6, hexc('#ffc93d'))
	fill_rect(img, 0, FLOOR + 16, W, 2, hexc('#343a58'))
	return img


def _leds(t: float, healthy: float) -> list:
	"""Every rack light: ``(x, y, color)``; red alarms blinking, or calm green once healthy."""
	rng = random.Random(3)
	out = []
	for (x0, y0) in RACKS:
		for y in range(y0 + 12, FLOOR - 24, SLOT):
			for k in range(2):
				ph = rng.random()
				x = x0 + RACK_W - 44 + k * 18
				if healthy >= 1:
					on = (t * 1.2 + ph) % 1 < 0.8
					color = hexc('#57e389') if on else hexc('#1f6b3a')
				else:
					on = (t * 3.0 + ph) % 1 < 0.5
					color = hexc('#ff4b55') if on else hexc('#5a1620') if k == 0 else hexc('#ffb13d') if on else hexc('#5a3a10')
				out.append((x, y + 14, color))
	return out


def room(img: Image.Image, t: float, cx: float, cy: float, alarm: float, healthy: float) -> None:
	"""The server room at ``t``: ``alarm`` (0-1) washes it red; ``healthy`` turns the lights green."""
	fill_rect(img, 0, 0, W, H, hexc('#10122a'))
	blit(img, _room(), -cx, -cy)
	for (x, y, color) in _leds(t, healthy):
		fill_rect(img, x - cx, y - cy, 12, 12, color)
	for (bx, by) in ((RACKS[0][0] + 96, RACKS[0][1] - 32), (RACKS[3][0] + 96, RACKS[3][1] - 32)):
		pulse = 0.5 + 0.5 * math.sin(t * math.tau * 1.25)
		color = hexc('#ff3b4a') if healthy < 1 else hexc('#57e389')
		glow = color[:3] + (int(70 * (pulse if healthy < 1 else 0.5)),)
		fill_rect(img, bx - 60 - cx, by - 40 - cy, 120, 80, glow)
		fill_rect(img, bx - 24 - cx, by - cy, 48, 24, color)
		fill_rect(img, bx - 12 - cx, by - 12 - cy, 24, 12, color)
		fill_rect(img, bx - 32 - cx, by + 24 - cy, 64, 8, hexc('#0b0d1c'))
	if alarm > 0:
		pulse = 0.5 + 0.5 * math.sin(t * math.tau * 1.25)
		img.alpha_composite(Image.new('RGBA', (W, H), (255, 30, 60, int(alarm * (22 + 26 * pulse)))))


# --------------------------------------------------------------------------------------------
# HUD



def boss_bar(img: Image.Image, hp: float, ghost: float, name: str, label: str, slide: float = 0.0) -> None:
	"""The boss's name and health bar at the top of the safe area; ``ghost`` trails the damage."""
	y = 262 - snap(slide, 4)
	world.panel(img, 80, y, 940, y + 124, (18, 10, 32, 225), hexc('#e5484d'))
	world.outlined_text(img, label, 104, y + 14, 7, hexc('#ffe14d'), width=3)
	world.outlined_text(img, name, 104 + text_width(label, 7) + 40, y + 14, 7, hexc('#ffffff'), width=3)
	x0, x1, top = 104, 916, y + 88
	fill_rect(img, x0 - 4, top - 4, x1 - x0 + 8, 24 + 8, hexc('#0b0510'))
	fill_rect(img, x0, top, x1 - x0, 24, hexc('#3a0d16'))
	gw = int((x1 - x0) * max(hp, ghost))
	fill_rect(img, x0, top, gw, 24, hexc('#ffffff'))
	w = int((x1 - x0) * hp)
	fill_rect(img, x0, top, w, 12, hexc('#ff5a5f'))
	fill_rect(img, x0, top + 12, w, 12, hexc('#d42a3a'))
	for k in range(1, 10):
		fill_rect(img, x0 + k * (x1 - x0) // 10, top, 4, 24, hexc('#0b0510'))


def hearts(img: Image.Image, x: int, label: str, color: tuple, count: int, total: int = 3, broken_at: float | None = None, t: float = 0.0) -> None:
	"""A player's label and hearts, bottom of the safe area. ``broken_at`` shakes the last lost heart."""
	y = 1480
	world.outlined_text(img, label, x, y + 12, 6, color, width=3)
	full, empty = art.heart(12), _empty_heart()
	for k in range(total):
		hx = x + 90 + k * 92
		spr = full if k < count else empty
		if k == count and broken_at is not None and 0 <= t - broken_at < 0.4:
			hx += snap(math.sin((t - broken_at) * 60) * 8, 4)
		blit(img, spr, hx, y)


@lru_cache(maxsize=1)
def _empty_heart() -> Image.Image:
	im = art.heart(12).copy()
	arr = np.asarray(im).copy()
	solid = arr[..., 3] > 0
	arr[solid] = (60, 40, 70, 255)
	return Image.fromarray(arr)


def pop(img: Image.Image, t: float, t0: float, text: str, x: float, y: float, color: tuple, px: int = 8, life: float = 0.9, rise: float = 70) -> None:
	"""A floating game text (MISS!, -9999, +SPEED) that rises and blinks out."""
	dt = t - t0
	if not (0 <= dt < life):
		return
	if dt > life * 0.75 and int(dt * 20) % 2:
		return
	lift = snap(rise * (1 - (1 - min(1.0, dt / 0.35)) ** 2), 4)
	world.outlined_text(img, text, snap(x - text_width(text, px) / 2, 2), int(y - lift), px, color, width=max(3, px // 2))


def speed_lines(img: Image.Image, t: float, x: float, y: float, facing: str, strength: float = 1.0) -> None:
	"""Short streaks behind a pet dashing at ``(x, y)`` (its feet)."""
	rng = random.Random(int(t * 30))
	sign = -1 if facing == 'right' else 1
	for _ in range(6):
		ln = rng.choice((48, 72, 96))
		yy = y - rng.randrange(24, 260)
		xx = x + sign * rng.randrange(150, 260)
		fill_rect(img, snap(xx - (ln if sign < 0 else 0), 4), snap(yy, 4), ln, 6, (255, 255, 255, int(170 * strength)))
