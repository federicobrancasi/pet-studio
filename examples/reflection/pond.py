"""Art for the reflection reel: a night pond whose water reflects everything above it.

Everything above the surface is drawn into one layer, which the water mirrors (flipped, rippled
and tinted), so the pets, the moon, the reeds and the fireflies all have reflections for free.
Things that float on the surface (lily pads, a lotus) are drawn after the water.
"""

from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image

from kit import land, sky
from kit.draw import blit, fill_rect, grid_sprite, hexc, snap

W, H = 1080, 1920
WATER_Y = 1004   # the surface
CELL = 12        # half a pet pixel at scale 3
WATER = np.array((12, 20, 56), np.float32)

# --------------------------------------------------------------------------------------------
# Sprites

PAL = {
	'L': hexc('#7fd46a'), 'G': hexc('#4fa84a'), 'D': hexc('#2f6f3a'), 'K': hexc('#1d4a2a'),   # pad
	'P': hexc('#ff9cc8'), 'p': hexc('#ffd0e4'), 'M': hexc('#e0609a'), 'Y': hexc('#ffe070'),  # lotus
	'S': hexc('#2e5a3a'), 's': hexc('#3f7a4a'), 'B': hexc('#7a4a2a'), 'b': hexc('#9a6a3a'),   # reeds
	'R': hexc('#ff3b3b'), 'r': hexc('#b01e2a'), 'W': hexc('#ffffff'),                          # arrow
}
PAD = [
	'.......LLLLLLLLLLLL.......',
	'...LLLLGGGGGGGGGGGGLLLL...',
	'.LGGGGGGGGGGG..GGGGGGGGGL.',
	'DGGGGGGGGGGG....GGGGGGGGGD',
	'.KDDDDDDDDDD....DDDDDDDDK.',
]
SMALL_PAD = ['..LLLLLL..', '.LGGGGGGL.', 'DGGGGGGGGD', '.KDDDDDDK.']
LOTUS = [
	'...p...',
	'..pPp..',
	'.pPYPp.',
	'pMPYPMp',
	'.MPPPM.',
]
REED = [
	'..B..', '.bBB.', '.bBB.', '.bBB.', '.bBB.', '..B..', '..S..', 's.S..', '.sS..', '.sS.s',
	'..SsS', '..S..', 's.S..', '.sS..', '..S.s', '..SsS', '..S..', '..S..',
]
ARROW = [  # points up-left, with a dark edge so it reads on the water
	'rrrrrr.......',
	'rRRRRRr......',
	'rRRRRr.......',
	'rRRRRRr......',
	'rRRrRRRr.....',
	'rRr.rRRRr....',
	'.r...rRRRr...',
	'......rRRRr..',
	'.......rRRRr.',
	'........rRRRr',
	'.........rRRr',
	'..........rr.',
]


@lru_cache(maxsize=None)
def sprite(name: str) -> Image.Image:
	if name == 'arrow_big':
		return grid_sprite(ARROW, PAL, CELL)
	rows = {'pad': PAD, 'small_pad': SMALL_PAD, 'lotus': LOTUS, 'reed': REED}[name]
	return grid_sprite(rows, PAL, CELL)


def pad(img: Image.Image, x: float, dip: float = 0.0, small: bool = False) -> None:
	"""A lily pad floating at the surface, centered on ``x``; its top is where a pet stands."""
	spr = sprite('small_pad' if small else 'pad')
	blit(img, spr, snap(x - spr.width / 2, 4), WATER_Y - 2 * CELL + snap(dip, 4))


PAD_TOP = WATER_Y - 2 * CELL + CELL // 2  # where the pets' feet go (half a cell into the pad)

# --------------------------------------------------------------------------------------------
# The scenery above the water

SKY = ((0.0, '#070a26'), (0.45, '#161a52'), (0.8, '#34296f'), (1.0, '#57387f'))
FAR = land.Ridge(seed=4, color='#1c2150', y=915, amp=46, parallax=0.0, rim='#262c63')
NEAR = land.Ridge(seed=9, color='#11152f', y=968, amp=26, parallax=0.0)
REEDS = [(34, 0), (96, 2), (150, 1), (962, 1), (1016, 0), (1062, 2)]
MOON = (905, 860)  # rising over the far bank on the right, clear of the captions


@lru_cache(maxsize=1)
def backdrop() -> Image.Image:
	"""The still part of the scene above the water: sky, moon, far banks and reeds."""
	img = Image.new('RGBA', (W, WATER_Y))
	img.paste(sky.gradient((W, WATER_Y), SKY), (0, 0))
	moon = sky.moon(84, CELL)
	blit(img, moon, MOON[0] - moon.width // 2, MOON[1] - moon.height // 2)
	FAR.draw(img, 0, 0)
	NEAR.draw(img, 0, 0)
	reed = sprite('reed')
	for (x, sink) in REEDS:
		blit(img, reed, snap(x - reed.width / 2, 4), WATER_Y - reed.height + sink * CELL)
	return img


@lru_cache(maxsize=None)
def _fireflies(seed: int = 3, n: int = 11) -> tuple:
	rng = random.Random(seed)
	return tuple((rng.uniform(90, 990), rng.uniform(640, 960), rng.uniform(0, math.tau), rng.uniform(0.6, 1.1)) for _ in range(n))


def fireflies(img: Image.Image, t: float) -> None:
	for (x, y, ph, sp) in _fireflies():
		fx = x + math.sin(t * sp + ph) * 60 + math.sin(t * 2.3 * sp + ph * 2) * 14
		fy = y + math.cos(t * 0.8 * sp + ph) * 40
		glow = 0.5 + 0.5 * math.sin(t * 3.1 + ph * 5)
		if glow < 0.15:
			continue
		fill_rect(img, snap(fx - 12, 4), snap(fy - 12, 4), 24, 24, (230, 255, 150, int(55 * glow)))
		fill_rect(img, snap(fx - 6, 4), snap(fy - 6, 4), 12, 12, (240, 255, 170, int(255 * glow)))


def above(t: float) -> Image.Image:
	"""The scene above the water at ``t`` (no pets yet): the backdrop, twinkling stars, fireflies."""
	img = Image.new('RGBA', (W, H))
	img.paste(backdrop(), (0, 0))
	sky.stars(img, t, 0, 0, area=(0, 0, W, 780), count=80)
	fireflies(img, t)
	return img


# --------------------------------------------------------------------------------------------
# The water


def reflect(layer: Image.Image, t: float, stir: float = 0.0) -> Image.Image:
	"""The water below ``WATER_Y``: ``layer`` mirrored, rippled in whole-pixel steps and tinted.

	``stir`` (px) adds a splash's extra wobble.
	"""
	depth = H - WATER_Y
	arr = np.asarray(layer.crop((0, WATER_Y - depth, W, WATER_Y)).transpose(Image.FLIP_TOP_BOTTOM)).astype(np.float32)
	out = np.empty_like(arr)
	for y0 in range(0, depth, 6):
		amp = 3 + y0 * 0.012 + stir * math.exp(-y0 / 260)
		shift = int(round(amp * math.sin(y0 * 0.045 + t * 2.6) / 3)) * 3
		out[y0:y0 + 6] = np.roll(arr[y0:y0 + 6], shift, axis=1)
	k = (0.42 + 0.3 * np.arange(depth, dtype=np.float32) / depth)[:, None, None]
	rgb = out[..., :3] * (1 - k) + WATER * k
	alpha = np.full(out.shape[:2] + (1,), 255, np.float32)
	return Image.fromarray(np.concatenate([rgb, alpha], axis=2).round().astype(np.uint8))


def moon_glints(img: Image.Image, t: float) -> None:
	"""Little light dashes on the water under the moon, shimmering."""
	rng = random.Random(int(t * 8))
	for i in range(12):
		y = WATER_Y + 40 + i * 30 + rng.randrange(0, 12)
		w = rng.choice((24, 36, 48, 72)) * max(0.3, 1 - i / 16)
		x = MOON[0] - 20 - w / 2 + rng.uniform(-40, 40)
		fill_rect(img, snap(x, 4), snap(y, 4), snap(w, 4), 6, (220, 226, 255, 150 - i * 7))


def ripple_ring(img: Image.Image, t: float, t0: float, x: float, life: float = 1.2, big: bool = False) -> None:
	"""An expanding ring on the surface around ``x`` from ``t0`` (a flat ellipse of light cells)."""
	dt = t - t0
	if not (0 <= dt < life):
		return
	k = dt / life
	rx = (60 if not big else 90) + (260 if big else 170) * (1 - (1 - k) ** 2)
	ry = rx / 6
	a = int(200 * (1 - k))
	n = int(rx / 5)
	for i in range(n):
		ang = i / n * math.tau
		fill_rect(img, snap(x + math.cos(ang) * rx - 6, 4), snap(WATER_Y + 6 + math.sin(ang) * ry, 4), 12, 6, (200, 220, 255, a))


def splash(img: Image.Image, t: float, t0: float, x: float, n: int = 26) -> None:
	"""Droplets thrown up from the surface at ``x`` at ``t0``, falling back on arcs."""
	dt = t - t0
	if not (0 <= dt < 1.1):
		return
	rng = random.Random(7)
	for _ in range(n):
		vx = rng.choice((-1, 1)) * rng.uniform(200, 520)
		vy = rng.uniform(-1400, -650)
		dx = vx * dt
		dy = vy * dt + 1300 * dt * dt
		if dy > 20:
			continue
		s = 24 if rng.random() < 0.3 else 12
		c = (255, 255, 255, 255) if rng.random() < 0.5 else (170, 210, 255, 255)
		fill_rect(img, snap(x + dx - s / 2, 4), snap(WATER_Y + dy - s / 2, 4), s, s, c)


def red_ring(img: Image.Image, cx: float, cy: float, rx: float, ry: float) -> None:
	"""A red 'look here' circle, drawn in pixel cells with a dark edge (thumbnail style)."""
	n = int((rx + ry) / 5)
	for i in range(n):
		a = i / n * math.tau
		x, y = snap(cx + math.cos(a) * rx - 6, 12), snap(cy + math.sin(a) * ry - 6, 12)
		fill_rect(img, x + 4, y + 4, 12, 12, PAL['r'])
	for i in range(n):
		a = i / n * math.tau
		x, y = snap(cx + math.cos(a) * rx - 6, 12), snap(cy + math.sin(a) * ry - 6, 12)
		fill_rect(img, x, y, 12, 12, PAL['R'])
