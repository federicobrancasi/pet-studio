"""Big bubble letters: a word in chunky, shaded pixel letters, sized to fit, that the pet can
stand on and hop along (each letter squashes when it's hit).

    WORD = letters.BubbleWord('HOORAY', center_x=510, baseline=1000, max_width=880)
    HITS = {0: [6.5], 1: [7.0]}                      # letter index -> times it gets hit
    WORD.draw(img, t, hits=HITS)
    y = WORD.top(0, t, HITS)                         # where the pet's feet go on letter 0

Every font pixel becomes a 2 x 2 block of cells, with an outline, three shading bands, a glint
and a drop shadow. Cells are whole pixels (16, 12, 8, 6 or 4 px), so the letters stay crisp.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Mapping, Sequence

import numpy as np
from PIL import Image

from .draw import blit, hexc, seg, snap
from .font import GLYPHS

PALETTES = {  # outline, highlight, body, shade, glint, lit highlight, lit body, lit shade
	'blue': ('#0c1a4a', '#8fe0ff', '#23a8f2', '#0a7cc4', '#ffffff', '#e2f8ff', '#6fd0ff', '#23a8f2'),
	'green': ('#08301f', '#8ff0d8', '#24bfa5', '#009a7c', '#ffffff', '#e0fff6', '#6fe6cc', '#24bfa5'),
	'gold': ('#4a2a00', '#fff1a8', '#ffc93d', '#d9961c', '#ffffff', '#fffbe0', '#ffe07a', '#ffc93d'),
	'pink': ('#4a0c2c', '#ffd0e6', '#ff7eb6', '#d9508f', '#ffffff', '#fff0f7', '#ffb0d4', '#ff7eb6'),
}
SHADOW = (26, 12, 60, 170)
CELLS = (16, 12, 8, 6, 4)
SPACE = 6  # cells for a space


@lru_cache(maxsize=None)
def _grid(ch: str) -> tuple:
	"""The letter as rows of 'K' (outline), 'H', 'C', 'A' (bands), 'W' (glint) and '.'."""
	rows = GLYPHS.get(ch, GLYPHS['?'])[:7]
	h, w = len(rows) * 2, len(rows[0]) * 2
	fill = np.zeros((h + 2, w + 2), bool)
	for r, row in enumerate(rows):
		for c, x in enumerate(row):
			if x == '#':
				fill[1 + 2 * r:3 + 2 * r, 1 + 2 * c:3 + 2 * c] = True
	ring = fill.copy()
	for dr in (-1, 0, 1):
		for dc in (-1, 0, 1):
			ring |= np.roll(np.roll(fill, dr, 0), dc, 1)
	out = []
	for r in range(h + 2):
		line = ''
		for c in range(w + 2):
			if fill[r, c]:
				line += 'H' if r <= 2 else 'A' if r >= h - 2 else 'C'
			elif ring[r, c]:
				line += 'K'
			else:
				line += '.'
		out.append(line)
	first = next((r for r in range(len(out)) if 'H' in out[r]), None)
	if first is not None:  # a two-cell glint on the first highlight run
		line = list(out[first])
		c = line.index('H')
		if c + 1 < len(line) and line[c + 1] == 'H':
			line[c] = line[c + 1] = 'W'
		out[first] = ''.join(line)
	return tuple(out)


def size(ch: str) -> tuple:
	"""A letter's size in cells: ``(columns, rows)``."""
	g = _grid(ch)
	return len(g[0]), len(g)


@lru_cache(maxsize=512)
def letter_image(ch: str, cw: int, chh: int, palette: str = 'blue', lit: bool = False) -> Image.Image:
	"""One letter with ``cw x chh`` px cells (unequal cells squash or stretch it)."""
	k, h, c, a, w, lh, lc, la = (hexc(x) for x in PALETTES[palette])
	colors = {'K': k, 'H': lh if lit else h, 'C': lc if lit else c, 'A': la if lit else a, 'W': w}
	g = _grid(ch)
	im = Image.new('RGBA', (len(g[0]), len(g)), (0, 0, 0, 0))
	px = im.load()
	for y, row in enumerate(g):
		for x, v in enumerate(row):
			if v != '.':
				px[x, y] = colors[v]
	return im.resize((im.width * cw, im.height * chh), Image.NEAREST)


@lru_cache(maxsize=512)
def _shadow(ch: str, cw: int, chh: int) -> Image.Image:
	alpha = letter_image(ch, cw, chh).getchannel('A').point(lambda v: SHADOW[3] if v else 0)
	sh = Image.new('RGBA', alpha.size, SHADOW)
	sh.putalpha(alpha)
	return sh


def squash(dt: float | None, cell: int) -> tuple:
	"""Cell size ``(width, height)`` ``dt`` seconds after a hit: flat, stretched up, settled."""
	keys = ((0.0, 1.25, 0.69), (0.06, 1.12, 0.81), (0.13, 0.88, 1.19), (0.21, 1.06, 0.94), (0.29, 1.0, 1.0))
	if dt is None or dt < 0 or dt >= keys[-1][0]:
		return cell, cell
	for (t0, kw, kh), (t1, _, _) in zip(keys, keys[1:]):
		if t0 <= dt < t1:
			return max(1, round(cell * kw)), max(1, round(cell * kh))
	return cell, cell


def draw_letter(img: Image.Image, ch: str, x_center: float, baseline: float, cells: tuple, palette: str = 'blue',
		lit: bool = False, shadow: bool = True) -> None:
	"""A letter standing on screen y ``baseline``, centered on ``x_center``, with ``cells = (w, h)``."""
	cw, chh = cells
	im = letter_image(ch, cw, chh, palette, lit)
	x = snap(x_center - im.width / 2, 2)
	y = int(round(baseline)) - im.height
	if shadow:
		blit(img, _shadow(ch, cw, chh), x + max(4, cw), y + max(2, chh // 2))
	blit(img, im, x, y)


class BubbleWord:
	"""A word in bubble letters, laid out in one row centered on ``center_x`` and standing on ``baseline``.

	The cell size is the largest of ``CELLS`` that fits ``max_width`` (or ``cell``, if given).
	"""

	def __init__(self, text: str, center_x: float, baseline: float, max_width: float | None = None, cell: int | None = None,
			palette: str = 'blue', overlap: int = 1):
		self.text, self.baseline, self.palette = text, baseline, palette
		if cell is None:
			cell = next((c for c in CELLS if max_width is None or self._width(text, c, overlap) <= max_width), CELLS[-1])
		self.cell = cell
		self.width = self._width(text, cell, overlap)
		x = center_x - self.width / 2
		self.centers = []
		for ch in text:
			w = SPACE if ch == ' ' else size(ch)[0]
			self.centers.append(x + w * cell / 2)
			x += (w - (0 if ch == ' ' else overlap)) * cell
		self.height = max((size(ch)[1] for ch in text if ch != ' '), default=0) * cell

	@staticmethod
	def _width(text: str, cell: int, overlap: int) -> int:
		cols = sum(SPACE if ch == ' ' else size(ch)[0] - overlap for ch in text) + overlap
		return cols * cell

	def cells(self, i: int, t: float | None = None, hits: Mapping[int, Sequence[float]] | None = None) -> tuple:
		"""The cell size of letter ``i`` at ``t``, squashed after its latest hit."""
		times = [h for h in (hits or {}).get(i, ()) if t is not None and h <= t]
		return squash(t - max(times), self.cell) if times else (self.cell, self.cell)

	def top(self, i: int, t: float | None = None, hits: Mapping[int, Sequence[float]] | None = None, bob: float = 0.0) -> float:
		"""The y of letter ``i``'s top edge (where the pet stands), following its squash and bob."""
		return self.baseline + self.bob(i, t, bob) - size(self.text[i])[1] * self.cells(i, t, hits)[1]

	def bob(self, i: int, t: float | None, amplitude: float) -> float:
		return snap(math.sin((t or 0.0) * 4.4 + i * 0.9) * amplitude, 2) if amplitude else 0

	def draw(self, img: Image.Image, t: float = 0.0, cx: float = 0, cy: float = 0, hits: Mapping[int, Sequence[float]] | None = None,
			bob: float = 0.0, lit_for: float = 0.22, drop: tuple | None = None) -> None:
		"""Draws the word; a letter hit in the last ``lit_for`` seconds lights up. Squashed letters go on top.

		``drop=(t0, step)`` drops the letters in one by one from ``t0`` (``step`` s apart): each
		falls into place in 0.14 s and squashes as it lands.
		"""
		hits = {i: list((hits or {}).get(i, ())) for i in range(len(self.text))}
		fall = {}
		if drop is not None:
			for i in hits:
				land_at = drop[0] + drop[1] * i + 0.14
				hits[i].append(land_at)
				fall[i] = land_at
		order = sorted((i for i, ch in enumerate(self.text) if ch != ' '), key=lambda i: self.cells(i, t, hits)[0])
		for i in order:
			lift = 0.0
			if i in fall:
				if t < fall[i] - 0.14:
					continue
				lift = -160 * (1 - seg(t, fall[i] - 0.14, fall[i])) ** 2
			times = [h for h in hits[i] if h <= t]
			lit = bool(times) and t - max(times) < lit_for
			baseline = self.baseline + self.bob(i, t, bob) + snap(lift, 2) - cy
			draw_letter(img, self.text[i], self.centers[i] - cx, baseline, self.cells(i, t, hits), self.palette, lit)
