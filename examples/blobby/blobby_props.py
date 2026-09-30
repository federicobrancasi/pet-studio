"""Props for the Blobby reel: the golden envelope, the bubble-letter name logo, the credit panel,
the speech bubble and the reveal flash.

Every prop is drawn from a character grid at a whole-pixel cell size, so it matches the pet.
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from PIL import Image

from kit.draw import blit, ease_out, fill_rect, hexc, snap
from kit.font import draw_text, text_width

NAVY = hexc('#14103a')
INK = hexc('#1b1440')
GOLD = hexc('#ffd35c')
WHITE = hexc('#ffffff')

# --------------------------------------------------------------------------------------------
# The envelope

ENV_PAL = {
	'K': hexc('#7a4a00'), 'Y': hexc('#ffc93d'), 'L': hexc('#ffe7a0'), 'D': hexc('#d9961c'),
	'R': hexc('#e8202a'), 'H': hexc('#ff9aa0'), 'W': hexc('#fffbe8'), 'B': hexc('#5a3600'),
}
ENV_W, ENV_H, ENV_FLAP = 15, 10, 5
_HEART = ['.R.R.', 'RRRRR', '.RRR.', '..R..']


def _envelope_rows(back: bool = False) -> list:
	g = [['.'] * ENV_W for _ in range(ENV_H)]
	for r in range(ENV_H):
		for c in range(ENV_W):
			edge = r in (0, ENV_H - 1) or c in (0, ENV_W - 1)
			corner = (r in (0, ENV_H - 1)) and (c in (0, ENV_W - 1))
			if corner:
				continue
			g[r][c] = 'K' if edge else 'Y'
	if back:
		for r in range(1, ENV_H - 1):  # side folds meeting in the middle
			for c in (r, ENV_W - 1 - r):
				if 0 < c < ENV_W - 1 and r >= ENV_H // 2:
					g[r][c] = 'D'
		for c in range(1, ENV_W - 1):
			g[1][c] = 'L'
		return [''.join(row) for row in g]
	for r in range(1, ENV_FLAP + 1):  # the flap: a lighter V with a darker edge
		for c in range(r + 1, ENV_W - 1 - r):
			g[r][c] = 'L'
		g[r][r] = 'D'
		g[r][ENV_W - 1 - r] = 'D'
	for i, row in enumerate(_HEART):
		for j, ch in enumerate(row):
			if ch == 'R':
				g[ENV_FLAP + i][5 + j] = 'R'
	g[ENV_FLAP + 1][6] = 'H'
	return [''.join(row) for row in g]


def _skew(rows: list, shift: int) -> list:
	"""Slants the top half by ``shift`` cells: a flutter tilt without rotating pixels."""
	out = []
	for r, row in enumerate(rows):
		s = shift if r < len(rows) // 2 else 0
		pad = abs(shift)
		out.append(('.' * (pad + s)) + row + ('.' * (pad - s)))
	return out


_OPEN = [
	'......KLK......',
	'.....KLLLK.....',
	'....KLLLLLK....',
	'...KLLLLLLLK...',
	'..KDLLLLLLLDK..',
	'.KDDDDDDDDDDDK.',
	'KBBBBBBBBBBBBBK',
	'KBWWWWWWWWWWWBK',
] + ['K' + 'Y' * (ENV_W - 2) + 'K'] * 5 + ['.' + 'K' * (ENV_W - 2) + '.']

ENVELOPE_FRAMES = {
	'front': _envelope_rows(),
	'tilt_r': _skew(_envelope_rows(), 1),
	'tilt_l': _skew(_envelope_rows(), -1),
	'edge': ['.' + 'K' * (ENV_W - 2) + '.', 'K' + 'L' * (ENV_W - 2) + 'K', '.' + 'K' * (ENV_W - 2) + '.'],
	'back': _envelope_rows(back=True),
	'open': _OPEN,
}
FLUTTER = ['front', 'tilt_r', 'edge', 'back', 'edge', 'tilt_l']


@lru_cache(maxsize=None)
def envelope_sprite(frame: str, cell: int) -> Image.Image:
	rows = ENVELOPE_FRAMES[frame]
	w = max(len(r) for r in rows)
	im = Image.new('RGBA', (w, len(rows)), (0, 0, 0, 0))
	px = im.load()
	for y, row in enumerate(rows):
		for x, ch in enumerate(row):
			if ch not in '. ':
				px[x, y] = ENV_PAL[ch]
	return im.resize((w * cell, len(rows) * cell), Image.NEAREST)


def draw_envelope(img: Image.Image, x: float, y: float, cx: float, cy: float, frame: str, cell: int, glow: float = 0.0, t: float = 0.0) -> None:
	"""The envelope centered on world ``(x, y)``; ``glow`` 0..1 adds a pulsing golden halo."""
	spr = envelope_sprite(frame, cell)
	sx, sy = snap(x - spr.width / 2 - cx, 4), snap(y - spr.height / 2 - cy, 4)
	if glow > 0:
		pulse = 0.75 + 0.25 * math.sin(t * 26)
		for k, a in ((3, 50), (2, 90)):
			pad = k * cell
			fill_rect(img, sx - pad + cell, sy - pad, spr.width + 2 * pad - 2 * cell, spr.height + 2 * pad, (255, 236, 150, int(a * glow * pulse)))
			fill_rect(img, sx - pad, sy - pad + cell, spr.width + 2 * pad, spr.height + 2 * pad - 2 * cell, (255, 236, 150, int(a * glow * pulse)))
	blit(img, spr, sx, sy)


def sparkle(img: Image.Image, x: float, y: float, size: int, color: tuple) -> None:
	"""A four-point pixel sparkle centered on screen ``(x, y)``."""
	x, y = snap(x, 4), snap(y, 4)
	fill_rect(img, x - size, y - 2, size * 2 + 4, 4, color)
	fill_rect(img, x - 2, y - size, 4, size * 2 + 4, color)
	fill_rect(img, x - 4, y - 4, 8, 8, WHITE[:3] + (color[3],))


def sparkle_ring(img: Image.Image, t: float, t0: float, x: float, y: float, cx: float, cy: float, n: int = 8, radius: float = 150, life: float = 0.4, color: tuple = GOLD, inner: float = 0.0) -> None:
	"""Sparkles flying out from world ``(x, y)`` at ``t0``, starting ``inner`` px from the center."""
	dt = t - t0
	if not (0 <= dt < life):
		return
	k = ease_out(dt / life)
	for i in range(n):
		a = i / n * math.tau + 0.3
		r = inner + (radius - inner) * k
		size = 12 if dt < life * 0.6 else 6
		sparkle(img, x + math.cos(a) * r - cx, y + math.sin(a) * r - cy, size, color[:3] + (int(255 * (1 - k * 0.6)),))


# --------------------------------------------------------------------------------------------
# The name logo: chunky bubble letters in the pet's own blues

_LETTERS = {
	'B': ['######..', '#######.', '###..###', '###..###', '#######.', '######..', '#######.', '###..###', '###..###', '########', '#######.'],
	'L': ['###.....', '###.....', '###.....', '###.....', '###.....', '###.....', '###.....', '###.....', '###.....', '########', '########'],
	'O': ['.######.', '########', '###..###', '###..###', '###..###', '###..###', '###..###', '###..###', '###..###', '########', '.######.'],
	'Y': ['###..###', '###..###', '###..###', '###..###', '.######.', '..####..', '..####..', '..####..', '..####..', '..####..', '..####..'],
}
LOGO_PAL = {'K': hexc('#0c1a4a'), 'H': hexc('#8fe0ff'), 'C': hexc('#23a8f2'), 'A': hexc('#0a7cc4'), 'W': hexc('#ffffff')}
LOGO_LIT = {'K': hexc('#1d3f8a'), 'H': hexc('#e2f8ff'), 'C': hexc('#6fd0ff'), 'A': hexc('#23a8f2'), 'W': hexc('#ffffff')}
LOGO_CELL = 16  # one pet pixel at scale 2
SHADOW = (26, 12, 60, 170)


def _fallback_letter(ch: str) -> list:
	"""Any other character: the kit font glyph, doubled in width for a bold stroke."""
	from kit.font import GLYPHS
	rows = GLYPHS.get(ch, GLYPHS['?'])[:7]
	out = []
	for row in rows:
		wide = ''.join(('##' if c == '#' else '..') for c in row)
		out.append(wide[:10])
	while len(out) < 11:
		out.insert(len(out) // 2, out[len(out) // 2])
	return out


@lru_cache(maxsize=None)
def letter_grid(ch: str) -> tuple:
	"""The letter's cell grid with an outline ring and three-band shading."""
	inner = _LETTERS.get(ch) or _fallback_letter(ch)
	h, w = len(inner), max(len(r) for r in inner)
	fill = np.zeros((h + 2, w + 2), bool)
	for r, row in enumerate(inner):
		for c, x in enumerate(row):
			fill[r + 1, c + 1] = x == '#'
	grow = fill.copy()
	for dr in (-1, 0, 1):
		for dc in (-1, 0, 1):
			grow |= np.roll(np.roll(fill, dr, 0), dc, 1)
	rows = []
	for r in range(h + 2):
		line = ''
		for c in range(w + 2):
			if fill[r, c]:
				band = r - 1
				line += 'H' if band < 2 else 'C' if band < 8 else 'A'
			elif grow[r, c]:
				line += 'K'
			else:
				line += '.'
		rows.append(line)
	# a glint on the first filled cells of the top-left
	for r in (2,):
		line = list(rows[r])
		for c in range(len(line)):
			if line[c] == 'H' and (c + 1 < len(line) and line[c + 1] == 'H'):
				line[c] = 'W'
				line[c + 1] = 'W'
				break
		rows[r] = ''.join(line)
	return tuple(rows)


@lru_cache(maxsize=None)
def letter_image(ch: str, cw: int, chh: int, lit: bool = False) -> Image.Image:
	rows = letter_grid(ch)
	pal = LOGO_LIT if lit else LOGO_PAL
	w, h = len(rows[0]), len(rows)
	im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
	px = im.load()
	for y, row in enumerate(rows):
		for x, c in enumerate(row):
			if c != '.':
				px[x, y] = pal[c]
	return im.resize((w * cw, h * chh), Image.NEAREST)


@lru_cache(maxsize=None)
def letter_shadow(ch: str, cw: int, chh: int) -> Image.Image:
	im = letter_image(ch, cw, chh)
	a = im.getchannel('A')
	sh = Image.new('RGBA', im.size, SHADOW)
	sh.putalpha(a.point(lambda v: SHADOW[3] if v else 0))
	return sh


def letter_size(ch: str) -> tuple:
	rows = letter_grid(ch)
	return len(rows[0]), len(rows)


# Squash keyframes as whole-pixel cell sizes (width, height): land flat, stretch up, settle.
SQUASH_KEYS = [(0.0, (20, 11)), (0.06, (18, 13)), (0.13, (14, 19)), (0.21, (17, 15)), (0.29, (16, 16))]


def squash_cell(dt: float | None) -> tuple:
	if dt is None or dt < 0 or dt >= SQUASH_KEYS[-1][0]:
		return (LOGO_CELL, LOGO_CELL)
	for (t0, size), (t1, _) in zip(SQUASH_KEYS, SQUASH_KEYS[1:]):
		if t0 <= dt < t1:
			return size
	return (LOGO_CELL, LOGO_CELL)


def draw_letter(img: Image.Image, ch: str, x_center: float, baseline: float, cell: tuple, lit: bool = False) -> None:
	"""A logo letter standing on ``baseline`` (bottom center), at a whole-pixel cell size."""
	cw, chh = cell
	im = letter_image(ch, cw, chh, lit)
	x = snap(x_center - im.width / 2, 2)
	y = int(round(baseline)) - im.height
	blit(img, letter_shadow(ch, cw, chh), x + LOGO_CELL, y + LOGO_CELL // 2)
	blit(img, im, x, y)


class Logo:
	"""The name laid out in one row, centered on ``center_x``, standing on ``baseline``."""

	def __init__(self, name: str, center_x: float, baseline: float, overlap: int = 1):
		self.name = name
		self.baseline = baseline
		sizes = [letter_size(c) for c in name]
		pitch = [(w - overlap) * LOGO_CELL for (w, _) in sizes]
		total = sum(pitch) + overlap * LOGO_CELL
		x = center_x - total / 2
		self.centers = []
		for (w, _), p in zip(sizes, pitch):
			self.centers.append(x + w * LOGO_CELL / 2)
			x += p
		self.height = max(h for (_, h) in sizes) * LOGO_CELL
		self.width = total

	def top(self, i: int, cell: tuple = (LOGO_CELL, LOGO_CELL)) -> float:
		"""World y of letter ``i``'s top edge for a given cell size (where the pet's feet go)."""
		return self.baseline - letter_size(self.name[i])[1] * cell[1]


# --------------------------------------------------------------------------------------------
# Text: the hook, the credit panel and the speech bubble


def text_centered(img: Image.Image, text: str, cx: float, y: float, px: int, color: tuple, shadow: tuple | None = NAVY) -> None:
	x = snap(cx - text_width(text, px) / 2, 2)
	draw_text(img, x, int(y), text, color, px, shadow=shadow, shadow_offset=1)


def outlined_text(img: Image.Image, text: str, x: float, y: float, px: int, color: tuple, outline: tuple = NAVY, width: int = 8) -> None:
	"""Text with a solid outline all around (like a caption sticker), readable on any background."""
	x, y = int(x), int(y)
	for dx in (-width, 0, width):
		for dy in (-width, 0, width):
			if dx or dy:
				draw_text(img, x + dx, y + dy, text, outline, px)
	draw_text(img, x + width, y + width + px // 2, text, outline, px)
	draw_text(img, x, y, text, color, px)


def rounded_panel(img: Image.Image, x0: float, y0: float, x1: float, y1: float, fill: tuple, border: tuple | None = None, cell: int = 8) -> None:
	"""A rectangle with its corners cut by one cell, optionally with a one-cell border."""
	x0, y0, x1, y1 = snap(x0, cell), snap(y0, cell), snap(x1, cell), snap(y1, cell)
	if border is not None:
		fill_rect(img, x0 + cell, y0, x1 - x0 - 2 * cell, y1 - y0, border)
		fill_rect(img, x0, y0 + cell, x1 - x0, y1 - y0 - 2 * cell, border)
		x0, y0, x1, y1 = x0 + cell, y0 + cell, x1 - cell, y1 - cell
	fill_rect(img, x0 + cell, y0, x1 - x0 - 2 * cell, y1 - y0, fill)
	fill_rect(img, x0, y0 + cell, x1 - x0, y1 - y0 - 2 * cell, fill)


def speech_bubble(img: Image.Image, text: str, cx: float, bottom: float, tail_x: float, px: int = 8, reveal: float = 1.0) -> None:
	"""A white pixel speech bubble whose tail hangs below it at ``tail_x``; text types in with ``reveal``."""
	cell = 8
	tw = text_width(text, px)
	pad_x, pad_y = 4 * cell, 3 * cell
	w = snap(tw + 2 * pad_x, cell)
	h = snap(7 * px + 2 * pad_y, cell)
	x0 = snap(cx - w / 2, cell)
	y0 = snap(bottom - h, cell)
	rounded_panel(img, x0, y0, x0 + w, y0 + h, WHITE, INK, cell)
	tx = snap(tail_x, cell)
	fill_rect(img, tx, y0 + h - cell, 3 * cell, cell, WHITE)  # open the border where the tail joins
	for i, wc in enumerate((3, 2, 1)):
		yy = y0 + h + i * cell
		fill_rect(img, tx - cell, yy, (wc + 2) * cell, cell, INK)
		fill_rect(img, tx, yy, wc * cell, cell, WHITE)
	fill_rect(img, tx - cell, y0 + h + 3 * cell, 2 * cell, cell, INK)
	shown = text[:max(0, min(len(text), int(round(len(text) * reveal))))]
	draw_text(img, x0 + pad_x, y0 + pad_y, shown, INK, px)


def flash(img: Image.Image, t: float, t0: float, length: float = 0.22) -> None:
	"""One white flash at ``t0`` that fades out (a single flash, never a strobe)."""
	dt = t - t0
	if 0 <= dt < length:
		a = int(235 * (1 - dt / length) ** 1.6)
		img.alpha_composite(Image.new('RGBA', img.size, (255, 250, 235, a)))
