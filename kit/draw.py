"""Raster helpers, easing and pixel-grid constants shared by every kit module.

Film scale: one source pixel of a pet sprite is ``S = 2`` screen pixels, so one pet
*logical pixel* (8 source px) is ``LP = 16`` screen px. Text and small details use the
half step ``TP = 8``. Snap positions to 4 or 8 px so nothing lands off the pixel grid.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Sequence

from PIL import Image

S = 2
TP = 8
LP = 16

Color = tuple


def hexc(h: str, a: int = 255) -> Color:
	"""'#rrggbb' -> (r, g, b, a)."""
	h = h.lstrip('#')
	return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def mix(c1: Color, c2: Color, t: float) -> Color:
	"""Linear blend of two colors; keeps c1's alpha."""
	return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(3)) + (c1[3] if len(c1) > 3 else 255,)


def blit(dst: Image.Image, src: Image.Image, x: float, y: float) -> None:
	"""Alpha-composites ``src`` onto ``dst`` at integer (x, y), clipping to bounds."""
	x = int(round(x))
	y = int(round(y))
	sw, sh = src.size
	dw, dh = dst.size
	if x >= dw or y >= dh or x + sw <= 0 or y + sh <= 0:
		return
	sx0 = max(0, -x)
	sy0 = max(0, -y)
	sx1 = min(sw, dw - x)
	sy1 = min(sh, dh - y)
	if sx0 == 0 and sy0 == 0 and sx1 == sw and sy1 == sh:
		dst.alpha_composite(src, (x, y))
	else:
		dst.alpha_composite(src, (x + sx0, y + sy0), (sx0, sy0, sx1, sy1))


def grid_sprite(rows: Sequence[str], palette: dict, px: int) -> Image.Image:
	"""Builds an RGBA sprite from a character grid ('.' or ' ' is transparent), scaled by ``px``."""
	h = len(rows)
	w = max(len(r) for r in rows)
	im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
	pix = im.load()
	for y, row in enumerate(rows):
		for x, c in enumerate(row):
			if c != '.' and c != ' ':
				pix[x, y] = palette[c]
	return im.resize((w * px, h * px), Image.NEAREST)


@lru_cache(maxsize=256)
def solid(w: int, h: int, color: Color) -> Image.Image:
	return Image.new('RGBA', (max(1, w), max(1, h)), color)


def fill_rect(dst: Image.Image, x: float, y: float, w: float, h: float, color: Color) -> None:
	"""Fills a rectangle; opaque colors are pasted, translucent ones composited."""
	if w <= 0 or h <= 0:
		return
	if color[3] == 255:
		x0 = int(round(x))
		y0 = int(round(y))
		x1 = min(dst.size[0], x0 + int(w))
		y1 = min(dst.size[1], y0 + int(h))
		x0 = max(0, x0)
		y0 = max(0, y0)
		if x1 > x0 and y1 > y0:
			dst.paste(color, (x0, y0, x1, y1))
	else:
		blit(dst, solid(int(w), int(h), color), x, y)


def upscale(img: Image.Image, k: int) -> Image.Image:
	"""Integer nearest-neighbor upscale; keeps pixel art crisp."""
	if k == 1:
		return img
	return img.resize((img.width * k, img.height * k), Image.NEAREST)


# --------------------------------------------------------------------------------------------
# Timing and easing


def clamp(x: float, a: float, b: float) -> float:
	return a if x < a else b if x > b else x


def seg(t: float, a: float, b: float) -> float:
	"""0 before ``a``, 1 after ``b``, linear in between."""
	return clamp((t - a) / (b - a), 0.0, 1.0)


def smooth(x: float) -> float:
	return x * x * (3 - 2 * x)


def ease_out(x: float) -> float:
	return 1 - (1 - x) * (1 - x)


def ease_out_back(x: float, s: float = 2.2) -> float:
	"""Overshoots past 1 and settles back: good for pop-ins."""
	x -= 1
	return 1 + (s + 1) * x * x * x + s * x * x


def snap(v: float, g: int = TP) -> int:
	"""Rounds a position to the pixel grid."""
	return int(round(v / g)) * g


def catmull(keys: Sequence[tuple], t: float) -> tuple[float, float]:
	"""Catmull-Rom spline through ``[(t, x, y), ...]`` keys (holds the ends)."""
	if t <= keys[0][0]:
		return keys[0][1], keys[0][2]
	for i in range(len(keys) - 1):
		if keys[i][0] <= t <= keys[i + 1][0]:
			p0 = keys[max(0, i - 1)]
			p1 = keys[i]
			p2 = keys[i + 1]
			p3 = keys[min(len(keys) - 1, i + 2)]
			u = (t - p1[0]) / (p2[0] - p1[0])
			u2, u3 = u * u, u * u * u

			def cr(a: float, b: float, c: float, d: float) -> float:
				return 0.5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u2 + (-a + 3 * b - 3 * c + d) * u3)
			return cr(p0[1], p1[1], p2[1], p3[1]), cr(p0[2], p1[2], p2[2], p3[2])
	return keys[-1][1], keys[-1][2]


def wave(t: float, period: float, amplitude: float, phase: float = 0.0) -> float:
	return math.sin((t / period + phase) * math.tau) * amplitude
