"""Ship it: the pet celebrates a push with its friend. The default layout, one call.

    python3 -m kit still render ship-it --all
"""

from __future__ import annotations

from PIL import Image

from kit import layout
from kit import pet as P

TITLE = 'Ship it'
PETS = [
	P.PetPose('love', 5, 0, 0),  # both pets are in love with the push
	P.PetPose('love', 5, 0, 0, variant='insiders'),
]


def render(width: int, height: int) -> Image.Image:
	if width <= 512:
		return layout.sticker(width, height, PETS[:1])
	return layout.poster(width, height, 'Ship it!', ['git push origin main', 'git push'], PETS, line_number=7, tab='deploy.md')
