"""Sticker pack: eight real pet reactions on one sheet, each labelled.

    python3 -m kit still render sticker-pack --all
"""

from __future__ import annotations

from PIL import Image

from kit import pet as P
from kit.font import draw_text, text_width

TITLE = 'Sticker pack'
DEFAULT_PRESET = 'x-post'
# (state, frame index, variant, label): pick the frame that reads best on its own
STICKERS = [
	('love', 5, 'stable', 'love'),
	('cool', 8, 'insiders', 'cool'),
	('sing', 2, 'stable', 'sing'),
	('worry', 0, 'insiders', 'worry'),
	('dizzy', 3, 'stable', 'dizzy'),
	('typing', 0, 'insiders', 'typing'),
	('press', 5, 'stable', 'ship it'),
	('sleep', 5, 'insiders', 'sleep'),
]
LABEL = (200, 210, 225, 255)


def render(width: int, height: int) -> Image.Image:
	transparent = width <= 512  # the sticker preset: no background, no labels
	img = Image.new('RGBA', (width, height), (0, 0, 0, 0) if transparent else (24, 26, 34, 255))
	cols = 4 if width >= height else 2
	rows = (len(STICKERS) + cols - 1) // cols
	label_h = 0 if transparent else 48
	cell_w, cell_h = width // cols, height // rows
	widest = max(P.frame_size(state)[0] for state, *_ in STICKERS)
	tallest = max(P.frame_size(state)[1] for state, *_ in STICKERS)
	scale = max(1, min((cell_w - 32) // widest, (cell_h - label_h - 32) // tallest))
	for i, (state, frame, variant, label) in enumerate(STICKERS):
		cx = (i % cols) * cell_w + cell_w // 2
		top = (i // cols) * cell_h
		ground = top + (cell_h - label_h + tallest * scale) // 2
		P.draw_pose(img, P.PetPose(state, frame, cx, ground, variant=variant, scale=scale))
		if not transparent:
			px = 8 if cell_w >= 400 else 4
			draw_text(img, cx - text_width(label, px) // 2, ground + 12, label, LABEL, px)
	return img
