"""The real VS Code pet: states, timings, eyes, facing and poses.

Every body pixel comes from the official sprite sheets (see ``kit/sprites.py``). Frame
timings are read from ``chatPetWidget.ts`` at the pinned commit, so animations play at
exactly the speed they have in VS Code.

States whose sprites have empty eye sockets (``DOM_EYE_STATES``) get the runtime eye
layer drawn in, just like VS Code does with its DOM eyes: 1x2 logical-pixel pupils that
can look around (``gaze``), blink, and bob with the idle breathing.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence

from PIL import Image

from . import sprites
from .draw import S, blit

VARIANTS = ('stable', 'insiders')
EYE_COLOR = (0x19, 0x1A, 0x1B, 255)

# Body palettes: light, mid, dark (shadow). One geometry, two color schemes.
BODY_PALETTES = {
	'stable': {'C': (0x23, 0xA8, 0xF2, 255), 'A': (0x00, 0x77, 0xB8, 255), 'B': (0x00, 0x4E, 0x7C, 255)},
	'insiders': {'C': (0x24, 0xBF, 0xA5, 255), 'A': (0x00, 0x9A, 0x7C, 255), 'B': (0x00, 0x45, 0x38, 255)},
}


@dataclass(frozen=True)
class StateInfo:
	name: str
	file: str  # without variant: 'buddy-idle-{v}-96'
	timing: str | None  # chatPetWidget.ts constant, or None when the runtime doesn't time it
	fallback: tuple  # durations used if the constant can't be read
	about: str
	dom_eyes: bool = False


def _ms(*values: int) -> tuple:
	return tuple(values)


STATE_TABLE: dict[str, StateInfo] = {s.name: s for s in [
	StateInfo('idle', 'buddy-idle-{v}-96', 'IDLE_FRAME_DURATIONS', (40,) * 50, 'Resting and breathing, eyes baked in.'),
	StateInfo('idleTracking', 'buddy-idle-{v}-tracking-96', 'IDLE_FRAME_DURATIONS', (40,) * 50, 'Resting with live eyes: use gaze to look around.', True),
	StateInfo('rendering', 'buddy-rendering-{v}-tracking-96', 'IDLE_FRAME_DURATIONS', (40,) * 50, 'Thinking while a request runs (pair with the speech bubble effect).', True),
	StateInfo('sleep', 'buddy-sleep-{v}-96', 'SLEEP_FRAME_DURATIONS', (300,) * 8, 'Asleep with a growing bubble (120 px wide frames).'),
	StateInfo('waking', 'buddy-waking-{v}-96', 'WAKE_FRAME_DURATIONS', _ms(160, 100, 80, 90, 90, 90, 100, 170), 'Waking up; play once after sleep.'),
	StateInfo('typing', 'buddy-typing-{v}-96', 'TYPING_FRAME_DURATIONS', _ms(320, 480), 'Typing at its tiny terminal (168 px wide frames).', True),
	StateInfo('press', 'buddy-press-button-{v}-96', 'BUTTON_PRESS_FRAME_DURATIONS', _ms(500, 300, 350, 250, 450, 1000), 'Button-press celebration; play once (160 px wide frames).', True),
	StateInfo('jump', 'buddy-jump-{v}-96', 'JUMP_FRAME_DURATIONS', _ms(70, 80, 90, 160, 100, 100), 'Hop poses: rest, crouch, stretch, airborne, squash, recover (grid jump:1-6, PetPose index 0-5).'),
	StateInfo('love', 'buddy-love-{v}-96', 'LOVE_FRAME_DURATIONS', _ms(200, 200, 380, 100, 80, 1980), 'Antennae turn into a heart; play once.', True),
	StateInfo('worry', 'buddy-worry-{v}-96', 'WORRY_FRAME_DURATIONS', _ms(600, 600), 'Worried face with sweat drops; loops.'),
	StateInfo('clapping', 'buddy-clapping-{v}-tracking-96', 'CLAPPING_FRAME_DURATIONS', _ms(80, 40, 40, 40, 80, 40, 40, 40, 40, 80, 40, 40, 80), 'Clapping when the agent needs input.', True),
	StateInfo('cool', 'buddy-cool-{v}-96', 'COOL_FRAME_DURATIONS', _ms(600, 120, 120, 120, 160, 80, 80, 80, 1640), 'Puts on sunglasses; play once.'),
	StateInfo('sing', 'buddy-sing-{v}-124', 'SING_FRAME_DURATIONS', _ms(180, 180, 180, 180), 'Sings a musical note (164 x 124 frames).'),
	StateInfo('speechless', 'buddy-speechless-{v}-96', 'SPEECHLESS_FRAME_DURATIONS', _ms(400, 120, 1000, 120, 1080), 'Speechless blinking stare; play once.'),
	StateInfo('dizzy', 'buddy-dizzy-{v}-128', 'DIZZY_FRAME_DURATIONS', (120,) * 8, 'Dizzy with circling stars (96 x 128 frames).'),
	StateInfo('falling', 'buddy-falling-{v}-96', 'FALLING_FRAME_DURATIONS', _ms(120, 80, 80, 120, 80, 80), 'Falling through the air; loops.'),
	StateInfo('splat', 'buddy-splat-{v}-96', 'SPLAT_FRAME_DURATIONS', _ms(120, 100, 100, 200), 'Squashed landing that springs back up; play once.'),
	StateInfo('search', 'buddy-search-{v}-96', 'SEARCH_FRAME_DURATIONS', _ms(500, 500, 500, 500), 'Peeking around while on the run.'),
	StateInfo('yapping', 'buddy-yapping-{v}-96', None, (140,) * 5, 'Rare VS Code icon yapping (not frame-timed at runtime; 140 ms here).'),
]}

# Effect sheets drawn next to the pet rather than as the pet.
EFFECT_TABLE: dict[str, StateInfo] = {s.name: s for s in [
	StateInfo('speech', 'buddy-speech-{v}-96', 'SPEECH_FRAME_DURATIONS', _ms(220, 220, 220, 100, 160, 180), 'Thinking speech bubble (loops).'),
	StateInfo('respawn', 'buddy-respawn-{v}-96', 'RESPAWN_FRAME_DURATIONS', _ms(120, 100, 120, 240, 100, 120), 'Portal burst: forward = appear, reverse = vanish.'),
]}

# Static reduced-motion images that have no sprite sheet.
STATIC_ONLY = {'wallImpact': 'buddy-wall-impact-{v}-96'}

AIRBORNE_OFFSET = 24  # source px: jump frame 3 draws the body this much higher than its baseline


@dataclass
class Move:
	"""A custom animation registered at runtime (see ``kit.moves``)."""
	name: str
	frames: dict  # variant -> list[Image] at source scale
	durations: list
	loop: bool = True
	about: str = ''
	fixed: dict | None = None  # variant -> list[Image] of pixels that must not mirror


_MOVES: dict[str, Move] = {}


def register_move(move: Move) -> None:
	"""Makes a custom move usable everywhere a state name is accepted."""
	if move.name in STATE_TABLE or move.name in EFFECT_TABLE:
		raise ValueError(f'{move.name!r} is a built-in state; a move cannot replace it')
	_MOVES[move.name] = move
	_sheet.cache_clear()
	pet_frame.cache_clear()
	durations.cache_clear()


def state_names() -> list[str]:
	return list(STATE_TABLE) + list(_MOVES)


def _info(name: str) -> StateInfo:
	if name in STATE_TABLE:
		return STATE_TABLE[name]
	if name in EFFECT_TABLE:
		return EFFECT_TABLE[name]
	raise KeyError(f'Unknown pet state {name!r}. Known: {", ".join(state_names() + list(EFFECT_TABLE))}')


@lru_cache(maxsize=None)
def durations(name: str) -> tuple:
	"""Frame durations in ms, as VS Code plays them."""
	if name in _MOVES:
		return tuple(_MOVES[name].durations)
	info = _info(name)
	if info.timing:
		parsed = sprites.widget_durations(info.timing)
		if parsed:
			return tuple(parsed)
	return info.fallback


def frame_count(name: str) -> int:
	return len(durations(name))


def total_ms(name: str) -> int:
	return sum(durations(name))


def frame_at(name: str, elapsed_ms: float, loop: bool = True) -> int:
	"""Frame index after ``elapsed_ms``; loops, or holds the final frame when ``loop=False``."""
	durs = durations(name)
	total = sum(durs)
	if elapsed_ms < 0:
		return 0
	if loop:
		elapsed_ms = elapsed_ms % total
	elif elapsed_ms >= total:
		return len(durs) - 1
	acc = 0
	for i, d in enumerate(durs):
		acc += d
		if elapsed_ms < acc:
			return i
	return len(durs) - 1


@lru_cache(maxsize=None)
def _sheet(name: str, variant: str) -> tuple:
	if name in _MOVES:
		return tuple(_MOVES[name].frames[variant])
	info = _info(name)
	sheet = Image.open(io.BytesIO(sprites.read_bytes(info.file.format(v=variant) + '.spritesheet.png'))).convert('RGBA')
	n = len(durations(name))
	if sheet.width % n:
		raise sprites.SpriteError(f'{name}: sheet width {sheet.width} is not a multiple of {n} frames')
	fw = sheet.width // n
	return tuple(sheet.crop((i * fw, 0, (i + 1) * fw, sheet.height)) for i in range(n))


def source_frame(name: str, frame: int, variant: str = 'stable') -> Image.Image:
	"""One frame at source scale (8 px per logical pixel), exactly as stored in VS Code."""
	return _sheet(name, variant)[frame]


def frame_size(name: str) -> tuple[int, int]:
	return _sheet(name, 'stable')[0].size


@lru_cache(maxsize=None)
def static_image(name: str, variant: str = 'stable') -> Image.Image:
	"""The reduced-motion still that VS Code shows for a state (source scale)."""
	file = STATIC_ONLY.get(name) or _info(name).file
	return Image.open(io.BytesIO(sprites.read_bytes(file.format(v=variant) + '.png'))).convert('RGBA')


def _eye_rects(name: str, frame: int, gaze: tuple, blink: bool) -> list:
	gx, gy = gaze
	if name == 'love':
		top, height = 66, 14
	else:
		top, height = 64, 16
		if name in ('idleTracking', 'rendering') and frame >= 20:
			top += 4  # the eyes bob with the breathing idle frames
	rects = []
	for left in (40, 64):
		x, y, h = left + gx, top + gy, height
		if blink:
			y += 6
			h = max(2, height - 12)
		rects.append((x, y, 8, h))
	return rects


def has_live_eyes(name: str, frame: int) -> bool:
	if name == 'press':
		return frame != frame_count('press') - 1  # the last frame bakes a happy face
	return name in STATE_TABLE and STATE_TABLE[name].dom_eyes


@lru_cache(maxsize=4096)
def pet_frame(name: str, frame: int, variant: str = 'stable', facing: str = 'right', gaze: tuple = (0, 0), blink: bool = False, eyes: bool = True, scale: int = S) -> tuple:
	"""Returns ``(image, anchor_x, anchor_y)`` at screen scale.

	The anchor is the bottom center of the body (x = 48 source px from the body's back
	edge), so wide frames with props overhang without moving the pet. ``gaze`` moves the
	live pupils by up to 4 source px each way, relative to the facing direction.
	"""
	src = source_frame(name, frame, variant).copy()
	fw, fh = src.size
	if eyes and has_live_eyes(name, frame):
		px = src.load()
		for (x, y, w, h) in _eye_rects(name, frame, gaze, blink):
			for yy in range(y, y + h):
				for xx in range(x, x + w):
					if 0 <= xx < fw and 0 <= yy < fh:
						px[xx, yy] = EYE_COLOR
	anchor_x = 48
	if facing == 'left':
		src = src.transpose(Image.FLIP_LEFT_RIGHT)
		anchor_x = fw - 48
		fixed = _fixed_layer(name, frame, variant)
		if fixed is not None:
			# Symbols such as text, check marks and notes keep their screen orientation:
			# erase their mirrored copy, then draw them unmirrored at the mirrored position.
			mask = fixed.split()[3]
			src.paste((0, 0, 0, 0), (0, 0), mask.transpose(Image.FLIP_LEFT_RIGHT))
			bbox = fixed.getbbox()
			if bbox:
				piece = fixed.crop(bbox)
				src.alpha_composite(piece, (fw - bbox[2], bbox[1]))
	return src.resize((fw * scale, fh * scale), Image.NEAREST), anchor_x * scale, fh * scale


def _fixed_layer(name: str, frame: int, variant: str) -> Image.Image | None:
	move = _MOVES.get(name)
	if move is None or not move.fixed:
		return None
	return move.fixed[variant][frame]


@lru_cache(maxsize=512)
def effect_frame(name: str, frame: int, variant: str = 'stable', scale: int = S, facing: str = 'right') -> Image.Image:
	"""A frame of an effect sheet ('speech', 'respawn') or any state, without live eyes."""
	src = _sheet(name, variant)[frame]
	if facing == 'left':
		src = src.transpose(Image.FLIP_LEFT_RIGHT)
	return src.resize((src.width * scale, src.height * scale), Image.NEAREST)


@dataclass
class PetPose:
	"""Where the pet is and what it's doing in one frame. ``x, y`` is the body's bottom center."""
	name: str
	frame: int
	x: float
	y: float
	facing: str = 'right'
	gaze: tuple = (0, 0)
	blink: bool = False
	variant: str = 'stable'
	air_offset: int = 0  # source px added below the anchor (see AIRBORNE_OFFSET)
	scale: int = S


def draw_pose(img: Image.Image, pose: PetPose, cx: float = 0, cy: float = 0) -> None:
	"""Draws a pose; ``cx, cy`` is the camera's top-left corner in world coordinates."""
	im, ax, ay = pet_frame(pose.name, pose.frame, pose.variant, pose.facing, tuple(pose.gaze), pose.blink, True, pose.scale)
	blit(img, im, round(pose.x) - ax - cx, round(pose.y) + pose.air_offset * pose.scale - ay - cy)


# --------------------------------------------------------------------------------------------
# Logical-pixel grids (used to start new moves from real poses)

GRID_LETTERS = {'C': 'body light', 'A': 'body mid', 'B': 'body dark', 'E': 'eye'}
_EXTRA_LETTERS = 'RYGWPOKNHMDFJLQSTUVXZ' + 'abcdefghijklmnopqrstuvwxyz'


def grid(name: str, frame: int, variant: str = 'stable', eyes: bool = True) -> tuple:
	"""Returns ``(rows, extra_colors)``: a real frame as one character per logical pixel."""
	src = source_frame(name, frame, variant).copy()
	if eyes and has_live_eyes(name, frame):
		px = src.load()
		for (x, y, w, h) in _eye_rects(name, frame, (0, 0), False):
			for yy in range(y, y + h):
				for xx in range(x, x + w):
					px[xx, yy] = EYE_COLOR
	lookup = {v[:3]: k for k, v in BODY_PALETTES[variant].items()}
	lookup[EYE_COLOR[:3]] = 'E'
	extra: dict[str, str] = {}
	rows = []
	px = src.load()
	for by in range(src.height // 8):
		row = ''
		for bx in range(src.width // 8):
			p = px[bx * 8 + 4, by * 8 + 4]
			if p[3] < 128:
				row += '.'
				continue
			key = p[:3]
			if key not in lookup:
				letter = _EXTRA_LETTERS[len(extra)]
				extra[letter] = '#%02x%02x%02x' % key
				lookup[key] = letter
			row += lookup[key]
		rows.append(row)
	return rows, extra


def pose_sheet(names: Sequence[str] | None = None, variant: str = 'stable', scale: int = 2) -> Image.Image:
	"""A labelled contact sheet of real poses. Labels are ``state:frame`` numbered from 1, the
	form ``python3 -m kit move grid`` takes (Python frame index = label - 1)."""
	from .font import draw_text

	names = list(names or STATE_TABLE)
	cells = []
	for name in names:
		for i in range(frame_count(name)):
			im, _, _ = pet_frame(name, i, variant, scale=scale)
			cells.append((f'{name}:{i + 1}', im))  # numbered from 1, like `kit move grid`
	cols = 10
	cw = max(im.width for _, im in cells) + 16
	ch = max(im.height for _, im in cells) + 40
	rows = (len(cells) + cols - 1) // cols
	sheet = Image.new('RGBA', (cols * cw, rows * ch), (30, 30, 30, 255))
	for k, (label, im) in enumerate(cells):
		x, y = (k % cols) * cw + 8, (k // cols) * ch + 28
		blit(sheet, im, x, y)
		draw_text(sheet, x, y - 22, label, (220, 220, 220, 255), 2)
	return sheet
