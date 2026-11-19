"""Blobby On Air: avatars and Slack emoji for the bot that posts the daily video.

Everything is the real pet (``kit.pet``) plus the camera and other props in ``props.py``,
drawn on the pet's logical-pixel grid and scaled by whole numbers. The backgrounds stay
transparent; a light outline keeps the dark edges readable on dark themes.

    python3 -m kit still render blobby-on-air --preset sticker   # avatar a, 512 x 512
    python3 stills/blobby-on-air/export.py                       # every avatar and emoji
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kit import moves  # noqa: E402
from kit import pet as P  # noqa: E402
from kit.draw import blit, grid_sprite, hexc  # noqa: E402

import props  # noqa: E402

TITLE = 'Blobby On Air'
DEFAULT_PRESET = 'sticker'
moves.use('on-air')
moves.use('wave')

PAL = {k: hexc(v) for k, v in props.PALETTE.items()}
OUTLINE = hexc('#e6edf3')
PAD = 4  # logical px of working margin around a scene


def mirror(rows: list) -> list:
	return [row[::-1] for row in rows]


def pet(state: str, frame: int, col: int, row: int, **kw) -> tuple:
	return ('pet', state, frame, col, row, kw)


def prop(rows: list, col: int, row: int) -> tuple:
	return ('prop', rows, col, row)


def compose(layers: list, u: int, size: tuple = (24, 24)) -> Image.Image:
	"""Draws layers on a transparent canvas at ``u`` screen px per logical pixel."""
	img = Image.new('RGBA', ((size[0] + 2 * PAD) * u, (size[1] + 2 * PAD) * u), (0, 0, 0, 0))
	for layer in layers:
		if layer[0] == 'pet':
			_, state, frame, col, row, kw = layer
			im, _, _ = P.pet_frame(state, frame, kw.get('variant', 'stable'), kw.get('facing', 'right'),
								   tuple(kw.get('gaze', (0, 0))), kw.get('blink', False), True, u // 8)
		else:
			_, rows, col, row = layer
			im = grid_sprite(rows, PAL, u)
		blit(img, im, (col + PAD) * u, (row + PAD) * u)
	return img


def outline(img: Image.Image, t: int, diagonal: bool = False) -> Image.Image:
	"""Adds a ``t`` px light outline around everything opaque, on the grid.

	4-neighbour by default; ``diagonal`` also grows across corners, which wraps the pet's
	diagonal antennae in one smooth band instead of a staircase.
	"""
	a = np.array(img)[:, :, 3] > 0
	grown = a.copy()
	shifts = [(t, 0), (-t, 0), (0, t), (0, -t)]
	if diagonal:
		shifts += [(t, t), (t, -t), (-t, t), (-t, -t)]
	for dy, dx in shifts:
		grown |= np.roll(np.roll(a, dy, axis=0), dx, axis=1)
	under = np.zeros(a.shape + (4,), np.uint8)
	under[grown & ~a] = OUTLINE
	out = Image.fromarray(under, 'RGBA')
	out.alpha_composite(img)
	return out


def place(img: Image.Image, size: int, bbox: tuple | None = None) -> Image.Image:
	"""Crops to ``bbox`` (default: the content) and centers it on a transparent square."""
	piece = img.crop(bbox or img.getbbox())
	if piece.width > size or piece.height > size:
		raise ValueError(f'scene is {piece.size}, larger than {size}')
	out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
	out.alpha_composite(piece, ((size - piece.width) // 2, (size - piece.height) // 2))
	return out


# --------------------------------------------------------------------------------------------
# Avatars: four poses with the camera

AVATARS = {
	# a: the camera rests on its head and the right antenna holds it, filming to the right
	'a': [pet('on-air', 0, 0, 0)],
	# b: peeking into a camera on a tripod, the left antenna on the camera's back
	'b': [
		prop(props.TRIPOD, 1, 9),
		prop(mirror(props.CAMERA), 0, 2),
		pet('idleTracking', 0, 6, 3, facing='left', gaze=(3, -2)),
	],
	# c: in love with filming, holding the camera out toward you
	'c': [pet('love', 5, 0, 0, gaze=(1, 0)), prop(props.CAMERA_FRONT, 9, 4)],
	# d: Insiders in sunglasses, the camera in the foreground filming to the left
	'd': [pet('cool', 8, 3, 0, variant='insiders', facing='left'), prop(mirror(props.CAMERA), 0, 9)],
	# e: holding the clapperboard open over its head, about to snap it
	'e': [pet('idleTracking', 0, 0, 3, gaze=(3, -3)), prop(props.CLAPPER_OPEN, 7, 0)],
	# f: Insiders sitting on a big shut clapperboard, looking at you
	'f': [prop(props.CLAPPER_BIG, 0, 12), pet('idleTracking', 0, 1, 0, variant='insiders', gaze=(1, 1))],
	# --- second set: one pet, at most one prop, clean silhouettes
	# g: the cleaner camera on its head, the right antenna holding it
	'g': [pet('idleTracking', 0, 0, 5, gaze=(1, 0)), prop(props.CAMERA_CLEAN, 6, 0)],
	# h: a small clapperboard standing against its side
	'h': [pet('idleTracking', 0, 0, 0, gaze=(3, 1)), prop(props.CLAPBOARD, 11, 5)],
	# i: the clapperboard held up beside its head
	'i': [pet('idleTracking', 0, 0, 4, gaze=(2, -3)), prop(props.CLAPBOARD, 9, 0)],
	# j: minimal, just the pet and a red recording dot by its antenna
	'j': [pet('idleTracking', 0, 0, 3), prop(props.REC_DOT_BIG, 10, 0)],
	# k: a speech bubble with a play button: today's video is in
	'k': [pet('idleTracking', 0, 0, 6, gaze=(2, -2)), prop(props.PLAY_BUBBLE, 10, 0)],
	# l: Insiders sitting on a big clean clapperboard
	'l': [prop(props.CLAPBOARD_BIG, 0, 12), pet('idleTracking', 0, 1, 0, variant='insiders')],
}


SECOND_SET = 'ghijkl'


def avatar(key: str, size: int = 1024, safe: float = 0.8) -> Image.Image:
	"""The largest whole-number scale whose outlined scene fits the central ``safe`` share."""
	for scale in range(16, 0, -1):
		u = 8 * scale
		img = outline(compose(AVATARS[key], u), u, diagonal=key in SECOND_SET)
		bbox = img.getbbox()
		if max(bbox[2] - bbox[0], bbox[3] - bbox[1]) <= size * safe:
			return place(img, size)
	raise ValueError(key)


# --------------------------------------------------------------------------------------------
# Emoji: 128 x 128 loops at 8 px per logical pixel with a half-pixel (4 px) outline


STEP = 250  # ms per frame of the idle-based loops: 8 frames = one 2 s breath


def breath(i: int) -> int:
	"""The real idle breathing frame at loop frame `i`, so the loop never stands still."""
	return P.frame_at('idleTracking', i * STEP)


GLOW = [[(7, 2), (14, 2), (10, 0), (11, 0)], [(7, 0), (14, 0), (7, 4), (14, 4)]]  # lamp rays
ON_AIR_GAZE = {4: (3, -3), 5: (3, -3), 6: (0, 0), 7: (3, -3)}


def _on_air(i: int) -> list:
	lit = i < 4
	layers = [
		pet('idleTracking', breath(i), 0, 3, gaze=ON_AIR_GAZE.get(i, (3, -3)), blink=(i == 5)),
		prop(props.LAMP_ON if lit else props.LAMP_OFF, 8, 1),
	]
	if lit:
		layers += [prop(['R'], c, r) for c, r in GLOW[i % 2]]
	return layers


def _cam(i: int) -> list:
	return [pet('on-air', i, 0, 0)]


# (stick, gaze, blink) per frame: raise, snap, clack, look at you, lift again
CLAP = [
	('open', (3, -3), False), ('half', (3, -3), False), ('shut', (3, -2), True), ('shut', (3, -2), False),
	('shut', (0, 0), False), ('half', (3, -3), False), ('open', (3, -3), False), ('open', (3, -3), True),
]
CLAPPERS = {'open': props.CLAPPER_OPEN, 'half': props.CLAPPER_HALF, 'shut': props.CLAPPER_SHUT}


def _clapper(i: int) -> list:
	stick, gaze, blink = CLAP[i]
	layers = [pet('idleTracking', breath(i), 0, 3, gaze=gaze, blink=blink), prop(CLAPPERS[stick], 7, 0)]
	if i == 2:  # clack!
		layers += [prop(['Y'], 9, 0), prop(['Y'], 12, 0)]
	return layers


KERNELS = [  # (col, row) of popped kernels per frame, rising over the bucket
	[(11, 6)], [(11, 5), (13, 7)], [(11, 4), (13, 6)], [(13, 5), (10, 7)],
	[(13, 4), (10, 6)], [(10, 5), (12, 7)], [(10, 4), (12, 6)], [(12, 5)],
]


def _popcorn(i: int) -> list:
	layers = [pet('love', 5, 0, 3, gaze=(3, 1)), prop(props.POPCORN, 9, 8)]
	for n, (c, r) in enumerate(KERNELS[i]):
		layers.append(prop(['W' if n % 2 == 0 else 'y'], c, r))
	return layers


# (REC dot on, gaze, blink) per frame: the dot blinks every two frames while the eyes look around
REC = [
	(True, (0, 0), False), (True, (2, 0), False), (False, (2, 0), False), (False, (0, 0), True),
	(True, (0, 0), False), (True, (-2, 0), False), (False, (-2, 0), False), (False, (0, 0), False),
]


def _rec(i: int) -> list:
	_, gaze, blink = REC[i]
	return [pet('idleTracking', breath(i), 0, 0, gaze=gaze, blink=blink)]


WRAP_FRAMES = [0, 1, 2, 3, 4, 5, 6, 6]  # the wave move, holding its last pose


def _wrap(i: int) -> list:
	layers = [pet('wave', WRAP_FRAMES[i], 0, 3)]
	layers.append(prop(props.SPARKLE, 12, 0 if i % 4 < 2 else 5))
	if i % 2 == 0:
		layers.append(prop(['Y'], 13, 9))
	return layers


EMOJI = {
	# name: (layers for frame i, frame durations in ms)
	'blobby-on-air': (_on_air, [STEP] * 8),
	'blobby-cam': (_cam, [160] * 8),
	'blobby-clapper': (_clapper, [STEP] * 8),
	'blobby-popcorn': (_popcorn, [140] * 8),
	'blobby-rec': (_rec, [STEP] * 8),
	'blobby-thats-a-wrap': (_wrap, [200, 110, 130, 110, 130, 110, 280, 280]),
}


def emoji_frames(name: str, size: int = 128) -> tuple:
	"""Returns ``(frames, durations)`` for one emoji; each frame is ``size`` square and transparent."""
	build, durations = EMOJI[name]
	if name == 'blobby-rec':
		# close-up: the pet at 16 px per logical pixel, cropped to its face, with a blinking REC dot
		frames = []
		for i in range(len(durations)):
			big = outline(compose(build(i), 16), 8)
			x0, y0 = (PAD + 3) * 16, (PAD + 4) * 16  # columns 3-10, rows 4-11: the face and the base
			frame = big.crop((x0, y0, x0 + size, y0 + size))
			if REC[i][0]:
				blit(frame, grid_sprite(props.REC_DOT, PAL, 8), size - 36, 4)
			frames.append(frame)
		return frames, durations
	raw = [outline(compose(build(i), 8), 4) for i in range(len(durations))]
	boxes = [im.getbbox() for im in raw]
	union = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
	return [place(im, size, union) for im in raw], durations


def render(width: int, height: int) -> Image.Image:
	img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
	side = min(width, height)
	img.alpha_composite(avatar('a', side), ((width - side) // 2, (height - side) // 2))
	return img
