"""Props and characters drawn on the pet's logical-pixel grid (``LP`` = 16 screen px).

Every sprite here is a character grid, so new art can be added the same way: pick a
palette, draw rows of letters, and build it with :func:`kit.draw.grid_sprite`.
"""

from __future__ import annotations

from functools import lru_cache
from PIL import Image

from .draw import LP, TP, grid_sprite, hexc

# ---------------------------------------------------------------------------------------------
# Ladybug (faces left). Legs alternate between two frames.
BUG_PAL = {
	'R': hexc('#e5484d'),
	'H': hexc('#ff9da0'),
	'D': hexc('#a3262c'),
	'K': hexc('#24242b'),
	'W': hexc('#ffffff'),
	'P': hexc('#24242b'),
	'L': hexc('#6a6a78'),
}

_BUG_BODY = [
	'K.K......',
	'.KK..RRR.',
	'KKK.RRHRR',
	'WKWRRRRKR',
	'KKKRKRRRR',
	'.KKDDDDDD',
]
_BUG_LEGS_A = '.L..L..L.'
_BUG_LEGS_B = '..L..L..L'

_BUG_SQUISH = [
	'.........',
	'.........',
	'.........',
	'.........',
	'.....RHR.',
	'KKKRRKRRR',
	'LKLDDDDDD',
]

# ---------------------------------------------------------------------------------------------
# Butterfly (front view) - the fixed bug becomes a "feature".
FLY_PAL = {
	'A': hexc('#ff7ac8'),
	'a': hexc('#c94f9b'),
	'Y': hexc('#ffe780'),
	'B': hexc('#a98bff'),
	'b': hexc('#7a5cd6'),
	'K': hexc('#4a3b6b'),
}
_FLY_OPEN = [
	'.K...K.',
	'AAK.KAA',
	'AYAKAYA',
	'aAAKAAa',
	'.BBKBB.',
	'.BYKYB.',
	'..b.b..',
]
_FLY_MID = [
	'.K...K.',
	'.AK.KA.',
	'.AAKAA.',
	'.aAKAa.',
	'..BKB..',
	'..BKB..',
	'.......',
]
_FLY_CLOSED = [
	'..K.K..',
	'..AKA..',
	'..AKA..',
	'..aKa..',
	'..bKb..',
	'.......',
	'.......',
]

# ---------------------------------------------------------------------------------------------
# Gold star collectible, drawn exactly like the dizzy stars in the pet sheets.
STAR_PAL = {'A': hexc('#ffbe30'), 'B': hexc('#ffe780')}
_STAR = ['...A...', '..AAA..', 'AAABAAA', '.AABAA.', '..AAA..', '.AA.AA.', '.A...A.']
_SPARK = ['A']

HEART_PAL = {'R': hexc('#ed1c24'), 'H': hexc('#ff8a8f'), 'D': hexc('#b0141b')}
_HEART = [
	'.RR.RR.',
	'RHRRRRR',
	'RRRRRRR',
	'.RRRRD.',
	'..RRD..',
	'...D...',
]
_HEART_SMALL = [
	'R.R',
	'RRR',
	'.R.',
]

BANG_PAL = {'Y': hexc('#ffbe30'), 'W': hexc('#fff3c4'), 'O': hexc('#8a5a00')}
_BANG = [
	'WY',
	'WY',
	'YY',
	'YY',
	'..',
	'YY',
]


@lru_cache(maxsize=None)
def bug(frame: int = 0, facing: str = 'left', squish: bool = False) -> Image.Image:
	rows = list(_BUG_SQUISH) if squish else list(_BUG_BODY) + [_BUG_LEGS_A if frame % 2 == 0 else _BUG_LEGS_B]
	im = grid_sprite(rows, BUG_PAL, LP)
	if facing == 'right':
		im = im.transpose(Image.FLIP_LEFT_RIGHT)
	return im


@lru_cache(maxsize=None)
def butterfly(frame: int) -> Image.Image:
	seq = [_FLY_OPEN, _FLY_MID, _FLY_CLOSED, _FLY_MID]
	return grid_sprite(seq[frame % 4], FLY_PAL, LP)


@lru_cache(maxsize=None)
def star(scale: int = TP) -> Image.Image:
	return grid_sprite(_STAR, STAR_PAL, scale)


@lru_cache(maxsize=None)
def spark(color: str = 'A', scale: int = TP) -> Image.Image:
	return grid_sprite(['A'], {'A': STAR_PAL[color]}, scale)


@lru_cache(maxsize=None)
def heart(scale: int = TP, small: bool = False) -> Image.Image:
	return grid_sprite(_HEART_SMALL if small else _HEART, HEART_PAL, scale)


@lru_cache(maxsize=None)
def bang(scale: int = LP) -> Image.Image:
	return grid_sprite(_BANG, BANG_PAL, scale)
