"""Scene building blocks: the code-city backdrop, code-line platforms, the chat
input, a VS Code terminal panel and pixel titles.

World coordinates are screen pixels in a long horizontal world; pass the camera's top-left
corner ``cx, cy`` to every ``draw`` call. Colors follow VS Code's Dark Modern theme.
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, field
from typing import Callable, Sequence

from PIL import Image

from .draw import LP, TP, blit, ease_out_back, fill_rect, hexc, mix, seg, smooth, snap
from .font import ADVANCE, draw_text, glyph_image, text_width

# --------------------------------------------------------------------------------------------
# Dark Modern syntax palette

KW = hexc('#569cd6')     # let, const, new, function, true
CTRL = hexc('#c586c0')   # if, while, return, import, export, default
FN = hexc('#dcdcaa')     # function calls
VAR = hexc('#9cdcfe')    # variables
TYPE = hexc('#4ec9b0')   # Types and Classes
PUNC = hexc('#d4d4d4')   # operators and punctuation
CMT = hexc('#6a9955')    # comments
BR1 = hexc('#ffd700')    # brackets, depth 1
BR2 = hexc('#da70d6')    # brackets, depth 2
BR3 = hexc('#179fff')    # brackets, depth 3
NUM = hexc('#b5cea8')
STR = hexc('#ce9178')
ERR = hexc('#f14c4c')
OK = hexc('#89d185')
WHITE = hexc('#ffffff')
FG = hexc('#cccccc')
FOCUS = hexc('#0078d4')
SHADOW_INK = hexc('#05060a')

SYNTAX_DIM = [KW, CTRL, FN, VAR, TYPE, CMT, STR, NUM, BR1]
CH = ADVANCE * TP  # 48 px monospace advance for code at text size 8

_KEYWORDS = {'let', 'const', 'var', 'function', 'new', 'class', 'this', 'true', 'false', 'null', 'undefined', 'async', 'await', 'typeof', 'void', 'of', 'in'}
_CONTROL = {'if', 'else', 'while', 'for', 'do', 'return', 'import', 'export', 'default', 'from', 'try', 'catch', 'finally', 'throw', 'switch', 'case', 'break', 'continue', 'yield'}
_TOKEN = re.compile(r'(?P<comment>//.*)|(?P<string>\'[^\']*\'|"[^"]*"|`[^`]*`)|(?P<number>\b\d[\d_.]*\b)|(?P<word>[A-Za-z_$][\w$]*)|(?P<bracket>[()\[\]{}])|(?P<space>\s+)|(?P<other>.)')


def highlight(code: str) -> list[tuple[str, tuple]]:
	"""Colors a line of JS/TS-like code the way VS Code's Dark Modern theme does."""
	out: list[tuple[str, tuple]] = []
	depth = 0
	for m in _TOKEN.finditer(code):
		kind, text = m.lastgroup, m.group()
		if kind == 'comment':
			out.append((text, CMT))
		elif kind == 'string':
			out.append((text, STR))
		elif kind == 'number':
			out.append((text, NUM))
		elif kind == 'word':
			rest = code[m.end():]
			if text in _CONTROL:
				out.append((text, CTRL))
			elif text in _KEYWORDS:
				out.append((text, KW))
			elif rest.startswith('('):
				out.append((text, FN))
			elif text[0].isupper():
				out.append((text, TYPE))
			else:
				out.append((text, VAR))
		elif kind == 'bracket':
			if text in ')]}':
				depth = max(0, depth - 1)
			out.append((text, (BR1, BR2, BR3)[depth % 3]))
			if text in '([{':
				depth += 1
		else:
			out.append((text, PUNC))
	return out


# --------------------------------------------------------------------------------------------
# Code-line platforms

GUTTER_W = 136
CODE_X = 160
LINE_H = 13 * TP

SLAB = hexc('#262b36')
SLAB_TOP = hexc('#3b4253')
SLAB_TOP2 = hexc('#2e3441')
SLAB_BOTTOM = hexc('#1a1e27')
GUTTER = hexc('#20242e')
LINE_NO = hexc('#5d6574')
LINE_NO_ACTIVE = hexc('#c6c6c6')
SLAB_SHADOW = (5, 6, 10, 150)


@dataclass
class Char:
	ch: str
	color: tuple
	appear: float = -1.0  # time the character appears; -1 = always there
	pop: bool = False     # drops in with a little bounce


def tokens(*pairs: tuple, appear: float = -1.0, step: float = 0.0, pop: bool = False) -> list[Char]:
	"""``tokens(('let', KW), (' joy', VAR))``; with ``appear``/``step`` it types itself."""
	out: list[Char] = []
	i = 0
	for text, color in pairs:
		for ch in text:
			out.append(Char(ch, color, appear + i * step if appear >= 0 else -1.0, pop))
			i += 1
	return out


def code(line: str, appear: float = -1.0, step: float = 0.0, pop: bool = False) -> list[Char]:
	"""Syntax-highlighted characters for a line of code."""
	return tokens(*highlight(line), appear=appear, step=step, pop=pop)


@dataclass
class CodeLine:
	"""A floating line of code the pet can stand on. ``top`` is the walkable surface."""
	key: str
	line: int
	x0: int
	top: int
	chars: list = field(default_factory=list)
	appear: float = -1.0  # time the empty line starts to grow (for lines typed in later)
	gutter: bool = True   # False hides the line number, for tight spaces

	@property
	def code_x(self) -> int:
		return CODE_X if self.gutter else 4 * TP

	@property
	def width(self) -> int:
		return self.code_x + len(self.chars) * CH + 32

	@property
	def x1(self) -> int:
		return self.x0 + self.width

	def char_x(self, i: int) -> int:
		return self.x0 + self.code_x + i * CH

	def visible_chars(self, t: float) -> int:
		n = 0
		for c in self.chars:
			if c.appear < 0 or t >= c.appear:
				n += 1
			else:
				break
		return n

	def contains(self, x: float, y: float) -> bool:
		return self.x0 <= x <= self.x1 and abs(self.top - y) < 2

	def draw(self, img: Image.Image, t: float, cx: float, cy: float, active: bool = False, dip: Callable[[float], int] | None = None) -> None:
		"""Draws the line; ``dip(x)`` can push characters down (e.g. under a landing)."""
		if self.x1 - cx < -50 or self.x0 - cx > img.width + 50:
			return
		sx, sy = self.x0 - cx, self.top - cy
		if self.appear >= 0:
			if t < self.appear:
				return
			n = self.visible_chars(t)
			grow = smooth(seg(t, self.appear, self.appear + 0.12))
			w = self.code_x + n * CH + 32 if n > 0 else int(self.code_x * grow)
			line_body(img, sx, sy, max(3 * TP, snap(w)), GUTTER_W if self.gutter else 0)
		else:
			line_body(img, sx, sy, self.width, GUTTER_W if self.gutter else 0)
		if self.gutter:
			draw_text(img, sx + 2 * TP, sy + 3 * TP, f'{self.line:>2}', LINE_NO_ACTIVE if active else LINE_NO, TP)
		for i, c in enumerate(self.chars):
			if c.appear >= 0 and t < c.appear:
				break
			if c.ch == ' ':
				continue
			x = self.char_x(i)
			y = self.top + 3 * TP + (dip(x + CH / 2) if dip else 0)
			if c.pop:
				k = seg(t, c.appear, c.appear + 0.16)
				y -= int(round((1 - ease_out_back(k, 3.0)) * 3)) * TP if k < 1 else 0
			blit(img, glyph_image(c.ch, c.color, TP), x - cx, y - cy)


def line_body(img: Image.Image, x: float, y: float, w: int, gutter_w: int = GUTTER_W) -> None:
	"""The slab behind a code line: bevel, gutter and a soft drop shadow."""
	h = LINE_H
	fill_rect(img, x + 2 * TP, y + h, w - 2 * TP, 2 * TP, SLAB_SHADOW)
	fill_rect(img, x + TP, y, w - 2 * TP, h, SLAB)
	fill_rect(img, x, y + TP, w, h - 2 * TP, SLAB)
	fill_rect(img, x + TP, y, w - 2 * TP, TP, SLAB_TOP)
	fill_rect(img, x + TP, y + TP, w - 2 * TP, TP, SLAB_TOP2)
	fill_rect(img, x, y + TP, TP, h - 2 * TP, SLAB_TOP2)
	fill_rect(img, x + TP, y + h - TP, w - 2 * TP, TP, SLAB_BOTTOM)
	fill_rect(img, x + w - TP, y + TP, TP, h - 2 * TP, SLAB_BOTTOM)
	if gutter_w > 0:
		fill_rect(img, x + TP, y + 2 * TP, gutter_w - TP, h - 3 * TP, GUTTER)


def landing_dip(t: float, landings: Sequence[tuple], top: float, x: float, radius: float = 110, length: float = 0.14) -> int:
	"""Characters near a landing on this line sink one text pixel for a moment."""
	for (tl, lx, ly) in landings:
		if abs(ly - top) < 2 and 0 <= t - tl < length and abs(lx - x) < radius:
			return TP
	return 0


def squiggle(img: Image.Image, x0: float, x1: float, y: float, cx: float, cy: float, color: tuple = ERR) -> None:
	"""A red error squiggle under code, from world x0 to x1 at world y."""
	for i, x in enumerate(range(int(x0), int(x1), TP)):
		fill_rect(img, x - cx, y - cy + (TP if i % 2 else 0), TP, TP, color)


# --------------------------------------------------------------------------------------------
# Backdrop: night sky, stars, glyph clouds, moon and two skylines of editor-window towers

SKY_BANDS = ['#0a0c15', '#0c0f19', '#0e121e', '#111624', '#141a2a', '#171e30', '#1a2236']
CLOUD_COLOR = hexc('#191f30')


class CodeCity:
	"""A night skyline of editor windows. Each ``seed`` gives a different city (the coding-world
	example uses ``seed=0``).

	``moon`` is the moon's top-left corner in screen pixels (None hides it). Stars fill the
	top ``star_band`` pixels (default: the top 52% of the frame).
	"""

	FAR_F = 0.22
	CLOUD_F = 0.33
	NEAR_F = 0.48

	def __init__(self, size: tuple[int, int] = (1920, 1080), world_width: int = 10000, seed: int = 0, moon: tuple[int, int] | None = (1744, 24), stars: int = 150, star_band: int | None = None):
		self.w, self.h = size
		self.moon_at = moon
		self.sky = _sky(self.w, self.h)
		self.moon = _moon()
		self.far = _skyline(int(self.w + world_width * self.FAR_F + 400), 900, 11 + seed, near=False)
		self.clouds = _glyph_clouds(int(self.w + world_width * self.CLOUD_F + 400), 5 + seed)
		self.near = _skyline(int(self.w + world_width * self.NEAR_F + 400), 760, 23 + seed, near=True)
		rng = random.Random(3 + seed)
		band = star_band if star_band is not None else int(round(self.h * 560 / 1080))
		self.stars = [(rng.randint(0, self.w * 2), rng.randint(0, band), rng.random(), rng.random()) for _ in range(stars)]

	def draw(self, img: Image.Image, t: float, cx: float, cy: float, clouds_fade: float = 0.0, clouds_fade_above: int = 420, keep_clear: tuple | None = None) -> None:
		"""``clouds_fade`` (0..1) fades out glyph clouds above ``clouds_fade_above`` (e.g. behind a
		title). ``keep_clear=(x0, y0, x1, y1)`` leaves stars and clouds out of that screen box."""
		w, h = self.w, self.h
		img.paste(self.sky, (0, 0))

		def blocked(x: float, y: float, bw: float, bh: float) -> bool:
			if keep_clear is None:
				return False
			x0, y0, x1, y1 = keep_clear
			return x < x1 and x + bw > x0 and y < y1 and y + bh > y0

		for (sx, sy, ph, br) in self.stars:
			x = snap(int((sx - cx * 0.06) % (w + 200)) - 100)
			y = snap(int(sy - cy * 0.03))
			if blocked(x - TP, y - TP, 3 * TP, 3 * TP):
				continue
			tw = (math.sin(t * (1.5 + br * 2.5) + ph * 20) + 1) / 2
			if br > 0.86:
				c = hexc('#ffe9a8') if br > 0.95 else hexc('#c9d3ff')
				if tw > 0.5:
					fill_rect(img, x - TP, y, 3 * TP, TP, mix(c, hexc('#0d1019'), 0.4))
					fill_rect(img, x, y - TP, TP, 3 * TP, mix(c, hexc('#0d1019'), 0.4))
				fill_rect(img, x, y, TP, TP, c)
			else:
				c = mix(hexc('#8c96c8'), hexc('#0d1019'), 0.25 + 0.5 * (1 - tw))
				fill_rect(img, x, y, TP // 2 if br < 0.5 else TP, TP // 2 if br < 0.5 else TP, c)
		ox, oy = -int(cx * self.CLOUD_F) - 200, -40 - int(cy * self.CLOUD_F)
		for (gx, gy, g) in self.clouds:
			x, y = gx + ox, gy + oy
			if x > w or x + text_width(g, LP) < 0 or blocked(x, y, text_width(g, LP), 9 * LP):
				continue
			color = CLOUD_COLOR
			if y < clouds_fade_above and clouds_fade > 0:
				if clouds_fade >= 1:
					continue
				color = CLOUD_COLOR[:3] + (int(round(255 * (1 - clouds_fade) / 32)) * 32,)
				if color[3] == 0:
					continue
			draw_text(img, x, y, g, color, LP)
		if self.moon_at is not None:
			blit(img, self.moon, *self.moon_at)
		blit(img, self.far, -int(cx * self.FAR_F) - 200, h - self.far.height + 40 - int(cy * self.FAR_F))
		blit(img, self.near, -int(cx * self.NEAR_F) - 200, h - self.near.height + 150 - int(cy * self.NEAR_F))


def _sky(w: int, h: int) -> Image.Image:
	im = Image.new('RGBA', (w, h), hexc(SKY_BANDS[0]))
	band_h = h // len(SKY_BANDS) + 1
	for i, c in enumerate(SKY_BANDS):
		fill_rect(im, 0, i * band_h, w, band_h, hexc(c))
		if i > 0:
			prev = hexc(SKY_BANDS[i - 1])
			for x in range(0, w, TP * 2):
				fill_rect(im, x + (TP if (x // (TP * 2)) % 2 else 0), i * band_h, TP, TP, prev)
	return im


def _moon() -> Image.Image:
	r = 4
	im = Image.new('RGBA', ((2 * r + 1) * LP, (2 * r + 1) * LP), (0, 0, 0, 0))
	lit, glow, shade = hexc('#f3e7b5'), hexc('#fff8dc'), hexc('#d8c88e')
	for yy in range(-r, r + 1):
		for xx in range(-r, r + 1):
			if xx * xx + yy * yy <= r * r + 1:
				c = shade if (xx - 1) * (xx - 1) + (yy - 1) * (yy - 1) > r * r - 3 and xx > 0 else lit
				if (xx + 2) * (xx + 2) + (yy + 2) * (yy + 2) <= 2:
					c = glow
				fill_rect(im, (xx + r) * LP, (yy + r) * LP, LP, LP, c)
	for (xx, yy) in [(1, -1), (-1, 2), (2, 2)]:
		fill_rect(im, (xx + r) * LP, (yy + r) * LP, LP, LP, shade)
	return im


def _tower(im: Image.Image, x: int, y: int, w: int, h: int, rng: random.Random, body: tuple, edge: tuple, bar: tuple, dim: float) -> None:
	fill_rect(im, x, y, w, h, edge)
	fill_rect(im, x + TP, y + TP, w - 2 * TP, h - TP, body)
	fill_rect(im, x + TP, y + TP, w - 2 * TP, 3 * TP, bar)
	tab_w = rng.randint(9, 15) * TP
	fill_rect(im, x + TP, y + TP, min(tab_w, w - 2 * TP), 3 * TP, mix(bar, (255, 255, 255, 255), 0.06))
	dot = rng.choice(SYNTAX_DIM)
	fill_rect(im, x + 2 * TP, y + 2 * TP, TP, TP, mix(dot, body, dim * 0.7))
	yy = y + 6 * TP
	indent = 0
	while yy < y + h - 2 * TP:
		if rng.random() < 0.18:
			yy += 2 * TP
			continue
		indent = max(0, min(4, indent + rng.choice([-1, 0, 0, 1])))
		xx = x + 3 * TP + indent * 2 * TP
		for _ in range(rng.randint(1, 4)):
			ln = rng.randint(2, 7) * TP
			if xx + ln > x + w - 2 * TP:
				break
			fill_rect(im, xx, yy, ln, TP, mix(rng.choice(SYNTAX_DIM), body, dim))
			xx += ln + TP
		yy += 2 * TP


def _skyline(width: int, height: int, seed: int, near: bool) -> Image.Image:
	rng = random.Random(seed)
	im = Image.new('RGBA', (width, height), (0, 0, 0, 0))
	x = -rng.randint(0, 12) * LP
	while x < width:
		if near:
			tw = rng.randint(14, 24) * LP
			th = rng.randint(20, 36) * LP
			body, edge, bar, dim = hexc('#1b2133'), hexc('#29324a'), hexc('#222a3f'), 0.55
		else:
			tw = rng.randint(10, 20) * LP
			th = rng.randint(26, 50) * LP
			body, edge, bar, dim = hexc('#151b2a'), hexc('#1e2538'), hexc('#191f30'), 0.72
		_tower(im, x, height - th, tw, th + LP, rng, body, edge, bar, dim)
		x += tw + rng.randint(1, 5) * LP
	return im


def _glyph_clouds(width: int, seed: int) -> list[tuple[int, int, str]]:
	rng = random.Random(seed)
	glyphs = ['{ }', '</>', '( )', ';', '[ ]', '=>', '#', '&&']
	out = []
	x = 200
	while x < width:
		g = rng.choice(glyphs)
		y = rng.randint(6, 26) * LP
		out.append((x, y, g))
		x += text_width(g, LP) + rng.randint(20, 50) * LP
	return out


# --------------------------------------------------------------------------------------------
# The chat input box (the pet's home)


def chat_input(img: Image.Image, t: float, x0: float, x1: float, top: float, cx: float, cy: float, text: str = '', placeholder: str | None = 'Ask anything', focused: bool = False, typing: bool = False, send_flash: bool = False, height: int = 160) -> None:
	"""VS Code's chat input: ``text`` typed so far, a blinking caret and the send button."""
	x0, x1 = x0 - cx, x1 - cx
	if x1 < 0 or x0 > img.width:
		return
	y0 = top - cy
	w, h = x1 - x0, height
	border = FOCUS if focused else hexc('#3c3c3c')
	fill_rect(img, x0 + TP, y0, w - 2 * TP, h, border)
	fill_rect(img, x0, y0 + TP, w, h - 2 * TP, border)
	fill_rect(img, x0 + TP, y0 + TP, w - 2 * TP, h - 2 * TP, hexc('#1f1f1f'))
	fill_rect(img, x0 + 2 * TP, y0 + TP, w - 4 * TP, TP, hexc('#262626'))
	n = len(text)
	tx, ty = x0 + 4 * TP, y0 + 4 * TP
	if n:
		draw_text(img, tx, ty, text, FG, TP)
	elif placeholder:
		draw_text(img, tx, ty, placeholder, hexc('#6b6b6b'), TP)
	if (int(t * 2.4) % 2 == 0) or typing:
		fill_rect(img, tx + n * CH - (TP if n else 0) + 2, ty - TP, TP // 2, 9 * TP, FG)
	draw_text(img, x0 + 4 * TP, y0 + h - 7 * TP, 'Agent', hexc('#8b8b8b'), 4)
	bx, by = x1 - 12 * TP, y0 + h - 9 * TP
	fill_rect(img, bx, by, 8 * TP, 7 * TP, hexc('#0078d4') if send_flash else hexc('#2b2b2b'))
	blit(img, glyph_image('\u25b6', WHITE if send_flash else hexc('#9d9d9d'), 4), bx + 3 * TP - 2, by + 2 * TP - 2)


def typed(text: str, t: float, start: float, step: float, until: float | None = None) -> str:
	"""The part of ``text`` typed ``t - start`` seconds in, one character every ``step`` s."""
	if t < start or (until is not None and t >= until):
		return ''
	return text[:min(len(text), int((t - start) / step) + 1)]


# --------------------------------------------------------------------------------------------
# A VS Code panel with a terminal


def open_amount(t: float, t_open: float, t_close: float | None = None, length: float = 0.2) -> float | None:
	"""Open amount 0..1 (with a little overshoot) for a panel that pops open and later
	closes, or None while it is hidden."""
	if t < t_open or (t_close is not None and t >= t_close + length):
		return None
	if t < t_open + length:
		return ease_out_back(seg(t, t_open, t_open + length), 1.6)
	if t_close is not None and t >= t_close:
		return 1 - smooth(seg(t, t_close, t_close + length))
	return 1.0


def terminal_panel(img: Image.Image, t: float, center_x: float, top: float, cx: float, cy: float, k: float | None, lines: Sequence[tuple], size: tuple[int, int] = (108 * TP, 42 * TP)) -> None:
	"""A PROBLEMS / OUTPUT / TERMINAL panel. ``k`` is its open amount (see :func:`open_amount`).

	``lines`` is ``[(t_appear, [(text, color), ...], seconds_per_char), ...]``; use 0 to show
	a line at once. A block cursor blinks after the last line.
	"""
	if k is None:
		return
	full_w, full_h = size
	w = max(4 * TP, snap(full_w * k))
	h = max(4 * TP, snap(full_h * min(1.0, k)))
	x = snap(center_x - w / 2) - cx
	y = snap(top + (full_h - h) / 2) - cy
	fill_rect(img, x + TP, y + TP, w, h, hexc('#07080c'))
	fill_rect(img, x, y, w, h, hexc('#3a3a3a'))
	fill_rect(img, x + TP, y + TP, w - 2 * TP, h - 2 * TP, hexc('#181818'))
	if k < 0.98:
		return
	fill_rect(img, x + TP, y + TP, w - 2 * TP, 7 * TP, hexc('#1f1f1f'))
	tab_x = x + 4 * TP
	for label, active in (('PROBLEMS', False), ('OUTPUT', False), ('TERMINAL', True)):
		draw_text(img, tab_x, y + 2 * TP + 4, label, hexc('#e7e7e7') if active else hexc('#8b8b8b'), 4)
		if active:
			fill_rect(img, tab_x, y + 7 * TP, text_width(label, 4), TP // 2, FOCUS)
		tab_x += text_width(label, 4) + 5 * TP
	ly = y + 10 * TP
	last_x = x + 4 * TP
	for (t0, parts, step) in lines:
		if t < t0:
			break
		xx = x + 4 * TP
		count = 0
		limit = 10 ** 6 if step == 0 else int((t - t0) / step) + 1
		for (text, col) in parts:
			for ch in text:
				if count >= limit:
					break
				if ch != ' ':
					blit(img, glyph_image(ch, col, TP), xx, ly)
				xx += CH
				count += 1
		last_x = xx
		ly += 10 * TP
	if lines and int(t * 2.5) % 2 == 0 and t > lines[-1][0]:
		fill_rect(img, last_x + TP, ly - 10 * TP, 5 * TP, 7 * TP, FG)


# --------------------------------------------------------------------------------------------
# Titles


def shadow_offset(px: int) -> int:
	"""Drop-shadow offset for text drawn at ``px``: half a font pixel, never under 4 px."""
	return max(4, px // 2)


def bob_title(img: Image.Image, t: float, text: str, colors: Sequence, x0: int, y0: int, px: int = LP) -> None:
	"""A title whose letters gently bob in a wave. ``colors[i]`` per character (None for spaces)."""
	for i, ch in enumerate(text):
		if ch == ' ':
			continue
		bob = int(round(math.sin(t * 3.2 - i * 0.55) * 1.0)) * TP // 2
		x = x0 + i * ADVANCE * px
		off = shadow_offset(px)
		blit(img, glyph_image(ch, SHADOW_INK, px), x + off, y0 + bob + off)
		blit(img, glyph_image(ch, colors[i], px), x, y0 + bob)


def pop_title(img: Image.Image, t: float, text: str, colors: Sequence, t0: float, y0: int, px: int = LP, step: float = 0.055, x0: int | None = None) -> None:
	"""A title that pops in letter by letter from ``t0`` (centered unless ``x0`` is given)."""
	if t < t0:
		return
	if x0 is None:
		x0 = (img.width - text_width(text, px)) // 2
	for i, ch in enumerate(text):
		ta = t0 + i * step
		if t < ta or ch == ' ':
			continue
		k = seg(t, ta, ta + 0.22)
		lift = int(round((1 - ease_out_back(k, 3.0)) * 4)) * max(4, px // 2) if k < 1 else 0
		x = x0 + i * ADVANCE * px
		off = shadow_offset(px)
		blit(img, glyph_image(ch, SHADOW_INK, px), x + off, y0 + lift + off)
		blit(img, glyph_image(ch, colors[i], px), x, y0 + lift)


def rainbow(text: str) -> list:
	"""Syntax colors cycling across a title's letters (None for spaces)."""
	cycle = [KW, VAR, TYPE, FN, STR, CTRL, NUM, BR1]
	out = []
	i = 0
	for ch in text:
		if ch == ' ':
			out.append(None)
		else:
			out.append(cycle[i % len(cycle)])
			i += 1
	return out


def centered_text(img: Image.Image, y: int, text: str, color: tuple, px: int = TP, shadow: tuple | None = None, center_x: int | None = None) -> None:
	cx = img.width // 2 if center_x is None else center_x
	draw_text(img, cx - text_width(text, px) // 2, y, text, color, px, shadow=shadow)


def fit_px(text: str, max_width: float, sizes: Sequence[int] = (LP, TP, 4)) -> int:
	"""The largest crisp text size (16, 8 or 4 px per font pixel) at which ``text`` fits."""
	for px in sizes:
		if text_width(text, px) <= max_width:
			return px
	return sizes[-1]


SUBTITLE = hexc('#9aa3b5')


def wrap_spans(text: str, px: int, max_width: float) -> list[tuple[int, str]]:
	"""Greedy word wrap: ``[(start_index, line), ...]`` lines that fit ``max_width`` at ``px``."""
	if text_width(text, px) <= max_width:
		return [(0, text)]
	spans: list[tuple[int, str]] = []
	cur_start, cur, i = 0, '', 0
	for word in text.split(' '):
		if not cur:
			cur_start, cur = i, word
		elif text_width(cur + ' ' + word, px) <= max_width:
			cur += ' ' + word
		else:
			spans.append((cur_start, cur))
			cur_start, cur = i, word
		i += len(word) + 1
	if cur:
		spans.append((cur_start, cur))
	return spans


def title_layout(text: str, subtitle: str | None, max_width: float, max_height: float | None = None) -> dict:
	"""Sizes and line breaks for :func:`title_block`, without drawing (use it to plan space).

	The title uses the largest crisp size (16, 8 or 4 px) at which it fits ``max_width`` in at
	most three lines (words never split) and, when given, ``max_height``. The subtitle is half
	the title size (never below 4 px) and wraps.
	"""
	for px in (LP, TP, 4):
		lines = wrap_spans(text, px, max_width)
		if px != 4 and (len(lines) > 3 or any(text_width(line, px) > max_width for _, line in lines)):
			continue
		spx = TP if px == LP else 4
		sub: list[tuple[int, str]] = []
		if subtitle:
			if text_width(subtitle, spx) > max_width:
				spx = 4
			sub = wrap_spans(subtitle, spx, max_width)
		height = (len(lines) - 1) * 11 * px + 9 * px
		sub_top = None
		if sub:
			sub_top = len(lines) * 11 * px + spx
			height = sub_top + (len(sub) - 1) * 11 * spx + 9 * spx
		if max_height is None or height <= max_height or px == 4:
			return {'px': px, 'lines': lines, 'spx': spx, 'sub_lines': sub, 'sub_top': sub_top, 'height': height}
	raise AssertionError('unreachable')


def title_block(img: Image.Image, text: str, top: int, subtitle: str | None = None, center_x: int | None = None, max_width: float | None = None, colors: Sequence | None = None, t: float = 1e9, t0: float = 0.0, subtitle_delay: float = 0.9, step: float = 0.055, max_height: float | None = None) -> int:
	"""A centered title (and subtitle) at the largest crisp size that fits ``max_width``.

	Long titles and subtitles wrap instead of being cut off. Pass ``t``/``t0`` to pop the
	letters in during a film; by default it is drawn complete. Returns the y just below the
	block, for laying out what comes next (see :func:`title_layout` to measure first).
	"""
	cx = img.width // 2 if center_x is None else center_x
	max_width = max_width if max_width is not None else img.width - 128
	lay = title_layout(text, subtitle, max_width, max_height)
	px = lay['px']
	palette = list(colors or rainbow(text))
	for k, (start, line) in enumerate(lay['lines']):
		x0 = cx - text_width(line, px) // 2
		pop_title(img, t, line, palette[start:start + len(line)], t0 + start * step, top + k * 11 * px, px=px, step=step, x0=x0)
	if lay['sub_lines'] and t >= t0 + subtitle_delay:
		for k, (_, line) in enumerate(lay['sub_lines']):
			centered_text(img, top + lay['sub_top'] + k * 11 * lay['spx'], line, SUBTITLE, lay['spx'], center_x=cx)
	return top + lay['height']


def window(img: Image.Image, x: int, y: int, w: int, h: int, tab: str = 'untitled', cx: float = 0, cy: float = 0) -> tuple[int, int, int, int]:
	"""A VS Code editor window with one tab. Returns the content box ``(x, y, w, h)``."""
	x, y = snap(x - cx), snap(y - cy)
	fill_rect(img, x + TP, y + TP, w, h, hexc('#07080c'))
	fill_rect(img, x, y, w, h, hexc('#3a3a3a'))
	fill_rect(img, x + TP, y + TP, w - 2 * TP, h - 2 * TP, hexc('#1e1e1e'))
	fill_rect(img, x + TP, y + TP, w - 2 * TP, 7 * TP, hexc('#181818'))
	tab_w = text_width(tab, 4) + 6 * TP
	fill_rect(img, x + TP, y + TP, tab_w, 7 * TP, hexc('#1e1e1e'))
	fill_rect(img, x + TP, y + TP, tab_w, TP // 2, FOCUS)
	draw_text(img, x + 4 * TP, y + 3 * TP, tab, hexc('#e7e7e7'), 4)
	return x + TP, y + 8 * TP, w - 2 * TP, h - 9 * TP
