"""Teach the pet a new move.

A move is a plain-text file (``moves/<name>/move.txt``): a few header lines and a list of
frames drawn as grids, one character per pet *logical pixel*. Because it is just text, a
move can be written in a chat, pasted into Slack or reviewed in a pull request, and
anyone can build it back into real sprites::

    name: wave
    about: Waves hello with an antenna.
    loop: yes
    colors: Y=#ffe780

    frame 140
    ..A......A..
    ...A....A...
    ...

Letters:

``.``  transparent
``C``  body light   (blue in Stable, green in Insiders)
``A``  body mid
``B``  body dark / shadow
``E``  eye (#191a1b); a normal open eye is 1 wide and 2 tall
other letters must be declared in ``colors:`` and look the same in both variants.

Letters listed in ``fixed:`` keep their screen orientation when the pet faces left:
use it for text, check marks, arrows and musical notes, which would read backwards if
mirrored (VS Code does the same for the sing animation's note).

Every frame has the same size, at least 12 x 12. The pet's body lives in the bottom-left
12 x 12 box; extra columns on the right and extra rows on top are room for props, just
like the typing terminal or the musical note in VS Code's own sprites.

``python3 -m kit move build <name>`` writes, next to ``move.txt``:

* ``vscode/buddy-<name>-{stable,insiders}-<height>.spritesheet.png`` horizontal sheets in
  exactly the format VS Code uses, plus the reduced-motion ``.png`` stills and
  ``vscode/timing.ts`` with the frame durations
* ``preview.gif`` (for Slack and X) and ``preview.png`` (animated PNG for READMEs)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from . import MOVES_ROOT, OUT_ROOT, KitError
from . import pet as P
from .draw import blit, hexc
from .font import draw_text
from .media import save_animation

CELL = 8  # source pixels per logical pixel
HOME = 12  # the body's home box is 12 x 12 logical pixels
RESERVED = {'.': None, 'C': 'body light', 'A': 'body mid', 'B': 'body dark', 'E': 'eye'}
NAME_RE = re.compile(r'^[a-z][a-z0-9-]{1,30}$')


@dataclass
class Frame:
	ms: int
	rows: list
	line: int  # line number in the file, for error messages


@dataclass
class MoveSpec:
	path: Path
	name: str = ''
	about: str = ''
	loop: bool = True
	still: int | None = None
	colors: dict = field(default_factory=dict)
	fixed: str = ''
	frames: list = field(default_factory=list)

	@property
	def width(self) -> int:
		return len(self.frames[0].rows[0]) if self.frames else 0

	@property
	def height(self) -> int:
		return len(self.frames[0].rows) if self.frames else 0

	@property
	def durations(self) -> list:
		return [f.ms for f in self.frames]

	@property
	def folder(self) -> Path:
		return self.path.parent

	def still_index(self) -> int:
		if self.still is not None:
			return self.still
		longest = max(self.durations)
		return max(i for i, d in enumerate(self.durations) if d == longest)


class MoveError(KitError, ValueError):
	pass


def find(name_or_path: str | Path) -> Path:
	"""Resolves a move name (``wave``), folder or ``move.txt`` path."""
	p = Path(name_or_path)
	if p.is_file():
		return p.resolve()
	if p.is_dir() and (p / 'move.txt').exists():
		return (p / 'move.txt').resolve()
	candidate = MOVES_ROOT / str(name_or_path) / 'move.txt'
	if candidate.exists():
		return candidate
	raise MoveError(f'No move called {name_or_path!r} (looked for {candidate})')


_TRAILING_COMMENT = re.compile(r'\s+#.*$')  # ' # note' after a value; '=#rrggbb' colors are kept


def reserved_names() -> set:
	"""Names a move can't take: the real states and effects, and the word 'all'."""
	names = {name.lower() for name in list(P.STATE_TABLE) + list(P.EFFECT_TABLE) + list(P.STATIC_ONLY)}
	names |= {'all', 'press-button', 'wall-impact', 'idle-tracking'}
	return names


def parse(path: str | Path) -> MoveSpec:
	"""Reads a move file. Lines starting with ``#`` are comments, and so is anything after
	`` #`` (space, then ``#``) at the end of a line."""
	path = Path(path)
	spec = MoveSpec(path=path)
	current: Frame | None = None
	for number, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
		stripped = raw.strip()
		if stripped.startswith('#'):
			continue
		stripped = _TRAILING_COMMENT.sub('', stripped)
		m = re.match(r'^frame\s+(\d+)\s*(?:ms)?\s*$', stripped)
		if m:
			current = Frame(int(m.group(1)), [], number)
			spec.frames.append(current)
			continue
		if current is None:
			if not stripped:
				continue
			key, sep, value = stripped.partition(':')
			if not sep:
				raise MoveError(f'{path.name}:{number}: expected "key: value" or "frame <ms>", got {stripped!r}')
			key, value = key.strip().lower(), value.strip()
			if key == 'name':
				spec.name = value
			elif key == 'about':
				spec.about = value
			elif key == 'loop':
				choice = value.lower()
				if choice not in ('yes', 'no', 'true', 'false', 'on', 'off', '1', '0'):
					raise MoveError(f'{path.name}:{number}: loop must be yes or no, got {value!r}')
				spec.loop = choice in ('yes', 'true', 'on', '1')
			elif key == 'still':
				if not value.isdigit():
					raise MoveError(f'{path.name}:{number}: still must be a frame number (1, 2, ...), got {value!r}')
				spec.still = int(value) - 1
			elif key == 'colors':
				for item in value.replace(',', ' ').split():
					letter, eq, color = item.partition('=')
					if not eq or len(letter) != 1 or not re.match(r'^#[0-9a-fA-F]{6}$', color):
						raise MoveError(f'{path.name}:{number}: bad color {item!r}; use X=#rrggbb')
					spec.colors[letter] = color.lower()
			elif key == 'fixed':
				spec.fixed = ''.join(value.replace(',', ' ').split())
			else:
				raise MoveError(f'{path.name}:{number}: unknown header {key!r} (use name, about, loop, still, colors, fixed)')
			continue
		if not stripped:
			continue
		current.rows.append(stripped)
	if not spec.name:
		spec.name = path.parent.name
	return spec


def validate(spec: MoveSpec) -> tuple[list, list]:
	"""Returns ``(errors, warnings)``. Errors stop a build; warnings are worth a look."""
	errors: list = []
	warnings: list = []
	if not NAME_RE.match(spec.name):
		errors.append(f'name {spec.name!r} must be lowercase letters, digits and dashes (2-31 chars)')
	elif spec.name in reserved_names():
		errors.append(f'name {spec.name!r} is taken by a built-in state; choose another (e.g. {spec.name}-2 or my-{spec.name})')
	for letter in spec.colors:
		if letter in RESERVED:
			errors.append(f'color letter {letter!r} is reserved ({RESERVED[letter] or "transparent"})')
	for letter in spec.fixed:
		if letter not in spec.colors:
			errors.append(f'fixed: {letter!r} is not declared in colors: (only prop colors can keep their orientation)')
	if not spec.frames:
		errors.append('no frames: add "frame <ms>" followed by grid rows')
		return errors, warnings
	w, h = spec.width, spec.height
	allowed = set(RESERVED) | set(spec.colors)
	for i, f in enumerate(spec.frames, start=1):
		if f.ms < 20:
			errors.append(f'frame {i}: {f.ms} ms is too short (minimum 20 ms)')
		if len(f.rows) != h:
			errors.append(f'frame {i} (line {f.line}): {len(f.rows)} rows, expected {h} like frame 1')
		for r, row in enumerate(f.rows):
			if len(row) != w:
				errors.append(f'frame {i} (line {f.line + 1 + r}): row is {len(row)} wide, expected {w}')
			bad = sorted(set(row) - allowed)
			if bad:
				errors.append(f'frame {i} (line {f.line + 1 + r}): unknown letters {"".join(bad)}; declare them in colors:')
	if w < HOME or h < HOME:
		errors.append(f'frames are {w}x{h}; they must be at least {HOME}x{HOME} (the body box)')
	if spec.still is not None and not (0 <= spec.still < len(spec.frames)):
		errors.append(f'still: {spec.still + 1} is not a frame number (1-{len(spec.frames)})')
	if errors:
		return errors, warnings
	if not spec.about or spec.about.startswith('('):
		warnings.append('about: is still the placeholder; describe the move in one line (it shows in the gallery)')
	if len(spec.frames) == 1:
		warnings.append('only one frame: this is a pose, not an animation')
	total = sum(spec.durations)
	if total > 10_000:
		warnings.append(f'the move lasts {total / 1000:.1f} s; VS Code reactions are usually 0.5-3 s')
	idle_rows, _ = P.grid('idle', 0)
	for label, frame in (('first', spec.frames[0]), ('last', spec.frames[-1])):
		if home_box(frame.rows) != idle_rows:
			warnings.append(f'the {label} frame is not the idle pose, so switching between idle and this move will pop (fine for deliberate entrances or exits)')
	for i, f in enumerate(spec.frames, start=1):
		home = home_box(f.rows)
		if not any(ch in 'CAB' for ch in home[-1]):
			warnings.append(f'frame {i}: the body does not touch the ground row (fine for a hop)')
		outside = [(x, y) for y, row in enumerate(f.rows) for x, ch in enumerate(row) if ch in 'CAB' and (x >= HOME or y < h - HOME)]
		if outside:
			warnings.append(f'frame {i}: {len(outside)} body-colored pixels are outside the 12x12 body box (props should use their own colors)')
		for (ex, ey, ew, eh) in eye_blobs(f.rows):
			if (ew, eh) != (1, 2):
				warnings.append(f'frame {i}: an eye is {ew}x{eh} at column {ex + 1}, row {ey + 1}; normal open eyes are 1x2 (fine for a special expression)')
	for i in range(1, len(spec.frames)):
		if spec.frames[i].rows == spec.frames[i - 1].rows:
			warnings.append(f'frames {i} and {i + 1} are identical; merge them into one longer frame')
	return errors, warnings


def home_box(rows: list) -> list:
	"""The bottom-left 12 x 12 part of a frame, where the body lives."""
	return [row[:HOME] for row in rows[-HOME:]]


def eye_blobs(rows: list) -> list:
	"""Bounding boxes ``(x, y, w, h)`` of connected ``E`` areas."""
	seen = set()
	blobs = []
	for y, row in enumerate(rows):
		for x, ch in enumerate(row):
			if ch != 'E' or (x, y) in seen:
				continue
			stack = [(x, y)]
			cells = []
			seen.add((x, y))
			while stack:
				cx, cy = stack.pop()
				cells.append((cx, cy))
				for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
					if 0 <= ny < len(rows) and 0 <= nx < len(rows[ny]) and rows[ny][nx] == 'E' and (nx, ny) not in seen:
						seen.add((nx, ny))
						stack.append((nx, ny))
			xs = [c[0] for c in cells]
			ys = [c[1] for c in cells]
			blobs.append((min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
	return blobs


def palette(spec: MoveSpec, variant: str) -> dict:
	pal = dict(P.BODY_PALETTES[variant])
	pal['E'] = P.EYE_COLOR
	pal.update({k: hexc(v) for k, v in spec.colors.items()})
	return pal


def frame_image(spec: MoveSpec, index: int, variant: str, only: str | None = None) -> Image.Image:
	"""One frame at source scale (8 px per logical pixel), like VS Code's sprite files.

	``only`` limits drawing to the given letters (used for the fixed-orientation layer).
	"""
	pal = palette(spec, variant)
	rows = spec.frames[index].rows
	im = Image.new('RGBA', (spec.width, spec.height), (0, 0, 0, 0))
	px = im.load()
	for y, row in enumerate(rows):
		for x, ch in enumerate(row):
			if ch != '.' and (only is None or ch in only):
				px[x, y] = pal[ch]
	return im.resize((spec.width * CELL, spec.height * CELL), Image.NEAREST)


def load(name_or_path: str | Path, strict: bool = True) -> MoveSpec:
	spec = parse(find(name_or_path))
	errors, _ = validate(spec)
	if errors and strict:
		raise MoveError(f'{spec.path}:\n  ' + '\n  '.join(errors))
	return spec


def use(name_or_path: str | Path) -> P.Move:
	"""Registers a move so films and stills can use it like a built-in state::

	    moves.use('wave')
	    pet.draw_pose(img, pet.PetPose('wave', pet.frame_at('wave', ms), x, y))
	"""
	spec = load(name_or_path)
	frames = {v: [frame_image(spec, i, v) for i in range(len(spec.frames))] for v in P.VARIANTS}
	fixed = {v: [frame_image(spec, i, v, only=spec.fixed) for i in range(len(spec.frames))] for v in P.VARIANTS} if spec.fixed else None
	move = P.Move(spec.name, frames, spec.durations, spec.loop, spec.about, fixed)
	P.register_move(move)
	return move


# --------------------------------------------------------------------------------------------
# Build outputs


def _ts_name(name: str) -> str:
	return re.sub(r'[^A-Z0-9]', '_', name.upper())


def build(name_or_path: str | Path) -> dict:
	"""Validates and writes the VS Code sprites and the previews. Returns what was written."""
	spec = load(name_or_path)
	_, warnings = validate(spec)
	folder = spec.folder
	vs = folder / 'vscode'
	vs.mkdir(exist_ok=True)
	fw, fh = spec.width * CELL, spec.height * CELL
	written = []
	for variant in P.VARIANTS:
		frames = [frame_image(spec, i, variant) for i in range(len(spec.frames))]
		sheet = Image.new('RGBA', (fw * len(frames), fh), (0, 0, 0, 0))
		for i, f in enumerate(frames):
			sheet.paste(f, (i * fw, 0))
		base = vs / f'buddy-{spec.name}-{variant}-{fh}'
		sheet.save(f'{base}.spritesheet.png', optimize=True)
		frames[spec.still_index()].save(f'{base}.png', optimize=True)
		written += [Path(f'{base}.spritesheet.png'), Path(f'{base}.png')]
	const = _ts_name(spec.name)
	ts = [
		f'// {spec.name}: {spec.about}'.rstrip(': '),
		f'// {len(spec.frames)} frames, {fw}x{fh} source px each; {"loops" if spec.loop else "plays once and holds the last frame"}.',
		f'const {const}_FRAME_DURATIONS = [{", ".join(str(d) for d in spec.durations)}];',
	]
	if fw != 96:
		ts.append(f'const CHAT_PET_{const}_SOURCE_WIDTH = {fw};')
	if fh != 96:
		ts.append(f'const CHAT_PET_{const}_SOURCE_HEIGHT = {fh};')
	(vs / 'timing.ts').write_text('\n'.join(ts) + '\n', encoding='utf-8')
	fixed_bounds = None
	if spec.fixed:
		fixed_bounds = [frame_image(spec, i, 'stable', only=spec.fixed).getbbox() for i in range(len(spec.frames))]
		fixed_bounds = [list(b) if b else None for b in fixed_bounds]
	(vs / 'move.json').write_text(json.dumps({
		'name': spec.name, 'about': spec.about, 'loop': spec.loop, 'frameWidth': fw, 'frameHeight': fh,
		'frameDurations': spec.durations, 'staticFrame': spec.still_index(),
		# Per-frame [left, top, right, bottom] source-px bounds of pixels that must keep their
		# screen orientation when mirrored (VS Code: IChatPetFixedOrientationDecoration).
		'fixedOrientationBounds': fixed_bounds,
		'files': {v: {'spritesheet': f'buddy-{spec.name}-{v}-{fh}.spritesheet.png', 'static': f'buddy-{spec.name}-{v}-{fh}.png'} for v in P.VARIANTS},
	}, indent='\t') + '\n', encoding='utf-8')
	written += [vs / 'timing.ts', vs / 'move.json']
	frames, durations = preview_frames(spec)
	written.append(save_animation(frames, durations, folder / 'preview.gif', loop=True))
	written.append(save_animation(frames, durations, folder / 'preview.png', loop=True))
	strip_path = OUT_ROOT / 'moves' / spec.name / 'strip.png'
	strip(spec).save(_mkdir(strip_path))
	written.append(strip_path)
	return {'spec': spec, 'warnings': warnings, 'written': written}


def _mkdir(path: Path) -> Path:
	path.parent.mkdir(parents=True, exist_ok=True)
	return path


PREVIEW_BG = hexc('#181818')
INPUT_FILL = hexc('#1f1f1f')
INPUT_EDGE = hexc('#3c3c3c')


def _stage(width: int, height: int, baseline: int) -> Image.Image:
	"""A dark stage with the chat input box the pet sits on."""
	im = Image.new('RGBA', (width, height), PREVIEW_BG)
	im.paste(INPUT_EDGE, (8, baseline, width - 8, height - 8))
	im.paste(INPUT_FILL, (12, baseline + 4, width - 12, height - 12))
	return im


def preview_frames(spec: MoveSpec, scale: int = 2) -> tuple[list, list]:
	"""Both colorways side by side on a chat-input stage. One-shot moves are shown between
	idle holds, the way they play in VS Code."""
	fw, fh = spec.width * CELL * scale, spec.height * CELL * scale
	gap, margin, floor = 48, 32, 40
	width = margin * 2 + fw * 2 + gap
	height = margin + fh + floor
	baseline = margin + fh
	sequence: list = []
	if not spec.loop:
		sequence.append(('idle', 0, 500))
	sequence += [('move', i, d) for i, d in enumerate(spec.durations)]
	if not spec.loop:
		sequence.append(('idle', 0, 800))
	frames, durations = [], []
	for kind, index, ms in sequence:
		im = _stage(width, height, baseline)
		for k, variant in enumerate(P.VARIANTS):
			x = margin + k * (fw + gap)
			if kind == 'idle':
				body = P.source_frame('idle', 0, variant)
				body = body.resize((body.width * scale, body.height * scale), Image.NEAREST)
				blit(im, body, x, baseline - body.height)
			else:
				f = frame_image(spec, index, variant)
				blit(im, f.resize((f.width * scale, f.height * scale), Image.NEAREST), x, baseline - fh)
		frames.append(im)
		durations.append(ms)
	return frames, durations


def strip(spec: MoveSpec, scale: int = 2) -> Image.Image:
	"""Every frame of both colorways in a row, labelled with its number and duration."""
	fw, fh = spec.width * CELL * scale, spec.height * CELL * scale
	pad = 16
	n = len(spec.frames)
	sheet = Image.new('RGBA', (pad + n * (fw + pad), 2 * (fh + 40) + pad), (30, 30, 34, 255))
	for row, variant in enumerate(P.VARIANTS):
		for i in range(n):
			x = pad + i * (fw + pad)
			y = pad + row * (fh + 40) + 24
			sheet.paste((44, 44, 50, 255), (x, y, x + fw, y + fh))
			sheet.paste((70, 70, 80, 255), (x, y + fh - (HOME * CELL * scale), x + HOME * CELL * scale, y + fh - (HOME * CELL * scale) + 2))
			f = frame_image(spec, i, variant)
			blit(sheet, f.resize((fw, fh), Image.NEAREST), x, y)
			draw_text(sheet, x, y - 22, f'{i + 1}: {spec.frames[i].ms}ms', (230, 230, 230, 255), 2)
	return sheet


# --------------------------------------------------------------------------------------------
# Authoring helpers


def grid_text(state: str, frame: int = 0, variant: str = 'stable') -> str:
	"""A real pose as move-file rows, plus any extra colors it uses."""
	rows, extra = P.grid(state, frame, variant)
	lines = [f'# {state} frame {frame + 1} of {P.frame_count(state)} ({P.durations(state)[frame]} ms)']
	if extra:
		lines.append('# extra colors: ' + ' '.join(f'{k}={v}' for k, v in extra.items()))
	return '\n'.join(lines + rows)


def new(name: str, source: str = 'idle:0', frames: int = 4, width: int = HOME, height: int = HOME, ms: int = 120) -> Path:
	"""Creates ``moves/<name>/move.txt`` pre-filled with a real pose on every frame."""
	if not NAME_RE.match(name):
		raise MoveError(f'name {name!r} must be lowercase letters, digits and dashes')
	if name in reserved_names():
		raise MoveError(f'name {name!r} is taken by a built-in state; choose another (e.g. my-{name})')
	folder = MOVES_ROOT / name
	path = folder / 'move.txt'
	if path.exists():
		raise MoveError(f'{path} already exists')
	state, _, index = source.partition(':')
	if state not in P.state_names():
		raise MoveError(f'--from: unknown state {state!r}. Run python3 -m kit poses --list to see them all')
	if not 0 <= int(index or 0) < P.frame_count(state):
		raise MoveError(f'--from: {state} has frames 1-{P.frame_count(state)}')
	rows, extra = P.grid(state, int(index or 0))
	rows = [row + '.' * (width - len(row)) for row in rows]
	rows = ['.' * width] * max(0, height - len(rows)) + rows
	colors = ' '.join(f'{k}={v}' for k, v in extra.items())
	label = f'{state} frame {int(index or 0) + 1}'
	lines = [
		f'# A new move for the VS Code pet. Each frame starts as the real {label} pose:',
		'# edit the grids, then run: python3 -m kit move build ' + name,
		'# Letters: . clear, C/A/B body light/mid/dark, E eye, others declared in colors:',
		f'name: {name}',
		'about: (one line: what the pet does)',
		'loop: yes',
		f'colors: {colors}',
		'',
	]
	for _ in range(frames):
		lines.append(f'frame {ms}')
		lines += rows
		lines.append('')
	folder.mkdir(parents=True, exist_ok=True)
	path.write_text('\n'.join(lines), encoding='utf-8')
	return path


def all_moves() -> list:
	return sorted(p.parent.name for p in MOVES_ROOT.glob('*/move.txt'))


def gallery() -> Path:
	"""Regenerates ``moves/README.md`` from every move folder."""
	lines = [
		'# Moves gallery',
		'',
		'New moves taught to the VS Code pet. Each folder has the move as text (`move.txt`), previews',
		'and `vscode/` sprite sheets in the exact format VS Code uses. To add yours, see the main',
		'[README](../README.md#teach-the-pet-a-new-move).',
		'',
		'| Move | What it does | Preview |',
		'| --- | --- | --- |',
	]
	for name in all_moves():
		spec = parse(MOVES_ROOT / name / 'move.txt')
		preview = f'![{spec.name} in Stable and Insiders colors]({name}/preview.png)' if (MOVES_ROOT / name / 'preview.png').exists() else '(run `python3 -m kit move build ' + name + '`)'
		lines.append(f'| [`{name}`]({name}/move.txt) | {spec.about} | {preview} |')
	path = MOVES_ROOT / 'README.md'
	path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
	return path
