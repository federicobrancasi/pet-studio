"""Landscapes: far hills, the ground the pet walks along, and nature props, lit by the time of day.

    GROUND = land.Ground(lambda x: 1300 + 40 * math.sin(x / 600), biomes=((0, 'meadow'), (5000, 'sand')))
    HILLS = land.Ridge(seed=3, color='#7fae8a', y=1000, amp=90, parallax=0.5)
    light = sky.day_light(hour)                      # warm at sunset, blue at night

    HILLS.draw(img, cx, cy, light)
    GROUND.draw(img, cx, cy, light)                  # the pet stands on GROUND.y(x)
    land.prop(img, 'tree', 900, GROUND.y(900), cx, cy, light)

Props are character grids like :mod:`kit.art`, anchored at their bottom center, so they stand
on the ground. ``light`` is ``(rgb, amount)``: every color is mixed toward ``rgb`` by ``amount``.
"""

from __future__ import annotations

import math
import random
from functools import lru_cache
from typing import Callable, Sequence

import numpy as np
from PIL import Image

from .draw import blit, fill_rect, grid_sprite, hexc, mix, snap

CELL = 12
DAYLIGHT = ((255, 255, 255), 0.0)  # no tint


def lit(color, light: tuple = DAYLIGHT) -> tuple:
	"""``color`` ('#hex' or rgba) under ``light``."""
	c = hexc(color) if isinstance(color, str) else color
	rgb, amount = light
	return mix(c, rgb + (255,), amount) if amount > 0 else c


@lru_cache(maxsize=256)
def _lit_image(key: tuple, light: tuple) -> Image.Image:
	name, cell = key
	img = _prop_image(name, cell)
	rgb, amount = light
	if amount <= 0:
		return img
	arr = np.asarray(img).astype(np.float32)
	arr[..., :3] = arr[..., :3] * (1 - amount) + np.array(rgb, np.float32) * amount
	return Image.fromarray(arr.round().astype(np.uint8))


# --------------------------------------------------------------------------------------------
# Far hills


class Ridge:
	"""A line of far hills that repeats every ``span`` px; ``y`` is its middle when the camera is at 0.

	Lower ``parallax`` values sit farther away. Draw far ridges first.
	"""

	def __init__(self, seed: int, color: str, y: float, amp: float = 80, parallax: float = 0.4, span: int = 2160,
			cell: int = CELL, rim: str | None = None):
		rng = random.Random(seed)
		self.phases = [rng.uniform(0, math.tau) for _ in range(3)]
		self.color, self.rim, self.y, self.amp, self.parallax, self.span, self.cell = color, rim, y, amp, parallax, span, cell

	def height(self, u: float) -> float:
		a, b, c = self.phases
		k = math.tau / self.span
		return self.amp * (0.55 * math.sin(u * k * 2 + a) + 0.3 * math.sin(u * k * 5 + b) + 0.15 * math.sin(u * k * 11 + c))

	def draw(self, img: Image.Image, cx: float, cy: float, light: tuple = DAYLIGHT) -> None:
		body = lit(self.color, light)
		rim = lit(self.rim, light) if self.rim else None
		ox = cx * self.parallax
		y_base = self.y - cy * self.parallax
		c = self.cell
		for sx in range(0, img.width + c, c):
			top = snap(y_base + self.height(sx + ox - (ox % c)), c)
			if top < img.height:
				fill_rect(img, sx - ox % c, top, c, img.height - top, body)
				if rim:
					fill_rect(img, sx - ox % c, top, c, c, rim)


# --------------------------------------------------------------------------------------------
# The ground

BIOMES = {  # rim, grass, middle, deep, dark
	'meadow': ('#c9ea7c', '#79c35a', '#5aa94d', '#438f47', '#2f6f40'),
	'field': ('#f6e59a', '#dcc063', '#c2a14c', '#a7843f', '#7f6231'),
	'sand': ('#ffe9b0', '#f3cd86', '#e0ad68', '#c58c55', '#9a6843'),
	'snow': ('#ffffff', '#eef4ff', '#d3def2', '#b4c3de', '#8e9fc2'),
}
BANDS = (1, 5, 11, 19)  # depths (cells) where the rim, grass, middle and deep bands end


class Ground:
	"""The ground the pet walks along. ``height(x)`` is the world y of the surface at world x.

	``biomes`` is ``((x_start, name), ...)``; neighbors blend over ``blend`` px in ``steps``
	dithered steps (pixel art, not a smooth smear), so a meadow can turn into a golden field and
	then into sand along the way. Put the boundaries between the places where the pet stops.
	"""

	def __init__(self, height: Callable[[float], float], biomes: Sequence[tuple] = ((0, 'meadow'),), blend: float = 240, cell: int = CELL,
			steps: int = 3):
		self.height, self.biomes, self.blend, self.cell, self.steps = height, tuple(biomes), blend, cell, steps

	def y(self, x: float) -> float:
		"""Where the pet stands at world ``x`` (snapped to the grid, like the drawing)."""
		return snap(self.height(x), self.cell)

	def palette(self, x: float, dither: float = 0.0) -> tuple:
		"""The five band colors at world ``x``; ``dither`` (0 or 0.5) alternates between blend steps."""
		colors = [hexc(c) for c in BIOMES[self.biomes[0][1]]]
		for (x0, name) in self.biomes[1:]:
			k = min(1.0, max(0.0, (x - x0 + self.blend / 2) / self.blend))
			k = min(1.0, math.floor(k * self.steps + dither) / self.steps)
			if k > 0:
				colors = [mix(a, hexc(b), k) for a, b in zip(colors, BIOMES[name])]
		return tuple(colors)

	def draw(self, img: Image.Image, cx: float, cy: float, light: tuple = DAYLIGHT) -> None:
		c = self.cell
		x_off = int(cx) % c
		for sx in range(-x_off, img.width + c, c):
			wx = sx + cx + c / 2
			top = self.y(wx) - cy
			if top >= img.height:
				continue
			col = int((sx + cx) // c)
			even, odd = self.palette(wx, 0.0), self.palette(wx, 0.5)
			if even != odd:  # between two blend steps: a checkerboard of both, cell by cell
				palettes = [tuple(lit(p, light) for p in pal) for pal in (even, odd)]
				rows = int((img.height - top) // c) + 1
				for r in range(rows):
					band = next((i for i, depth in enumerate(BANDS) if r < depth), len(BANDS))
					fill_rect(img, sx, top + r * c, c, c, palettes[(col + r) % 2][band])
				continue
			rim, grass, middle, deep, dark = (lit(p, light) for p in even)
			y = top
			for depth, color, next_color in ((BANDS[0], rim, grass), (BANDS[1], grass, middle), (BANDS[2], middle, deep), (BANDS[3], deep, dark)):
				bottom = top + depth * c
				fill_rect(img, sx, y, c, bottom - y, color)
				if col % 2:  # dithered band edge
					fill_rect(img, sx, bottom - c, c, c, next_color if depth > 1 else color)
				y = bottom
			fill_rect(img, sx, y, c, img.height - y, dark)


# --------------------------------------------------------------------------------------------
# Props

PROP_PALETTE = {
	'G': '#5aa94d', 'L': '#8fd46a', 'D': '#3d8440', 'T': '#8a5a3a', 't': '#6b4329',  # trees
	'P': '#ff8fc0', 'Y': '#ffd24a', 'W': '#ffffff', 'V': '#b18cff', 'S': '#3f8a3f',  # flowers
	'R': '#9aa3ad', 'r': '#c3cad2', 'K': '#6f7883',  # rocks
	'F': '#c8925a', 'f': '#a0703f',  # fence
	'C': '#4fae5a', 'c': '#7fd07a', 'k': '#357c3f',  # cactus
	'M': '#e5484d', 'm': '#fff3e0', 's': '#f1e1c6',  # mushroom
	'B': '#3f7fd0', 'b': '#8cc8ff', 'N': '#2a5ea8',  # water
}
PROPS = {
	'tree': [
		'....GGGG....', '..GGLLGGGG..', '.GGLLGGGGGG.', 'GGGLGGGGGDGG', 'GGGGGGGGGDGG', 'GGGGGGGGDDGG',
		'.GGGGGGDDGG.', '..GGDDDDGG..', '....GTtG....', '.....Tt.....', '.....Tt.....', '....TTtt....',
	],
	'pine': [
		'.....D.....', '....DGD....', '...DGLGD...', '....GGG....', '..DGGLGGD..', '.DGGGGGGGD.',
		'...GGGGG...', '.DGGGLGGGD.', 'DGGGGGGGGGD', '.....T.....', '.....T.....',
	],
	'bush': ['..GGGG..', '.GLLGGG.', 'GGLGGGDG', 'GGGGGDDG', '.GGGDDG.'],
	'flower_pink': ['.P.', 'PYP', '.P.', '.S.'],
	'flower_white': ['.W.', 'WYW', '.W.', '.S.'],
	'flower_violet': ['.V.', 'VYV', '.V.', '.S.'],
	'rock': ['..RRRr.', '.RRrrRR', 'RRRRRRK', 'KRRRRKK'],
	'fence': ['F......F', 'FFFFFFFF', 'f......f', 'FFFFFFFF', 'f......f'],
	'cactus': ['..c..', '..C.c', 'c.C.C', 'C.CkC', 'CkC..', '..C..', '..k..', '..C..'],
	'mushroom': ['.MMM.', 'MmMmM', 'MMMMM', '..s..', '..s..'],
	'pond': [
		'...bbbbbbbbbb...', '.bBBBBbBBBBBBBb.', 'bBBBBBBBBBbBBBBb', 'NBBBBBBBBBBBBBBN', '.NNBBBBBBBBBBNN.', '...NNNNNNNNNN...',
	],
}


@lru_cache(maxsize=None)
def _prop_image(name: str, cell: int) -> Image.Image:
	return grid_sprite(PROPS[name], {k: hexc(v) for k, v in PROP_PALETTE.items()}, cell)


def prop(img: Image.Image, name: str, x: float, y: float, cx: float, cy: float, light: tuple = DAYLIGHT, cell: int = CELL,
		sink: int = 0) -> None:
	"""Draws prop ``name`` (see ``PROPS``) standing on world ``(x, y)``: bottom center, sunk ``sink`` cells."""
	spr = _lit_image((name, cell), (tuple(int(v) for v in light[0]), round(light[1], 3)))
	blit(img, spr, snap(x - spr.width / 2 - cx, 4), snap(y - spr.height + sink * cell - cy, 4))
