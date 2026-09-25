"""LGTM poster: both pets approve your pull request, using the custom lgtm move.

Shows how a move taught in ``moves/`` works in any image or film once registered with
``moves.use('lgtm')``.

    python3 -m kit still render lgtm-poster --all
"""

from __future__ import annotations

from PIL import Image

from kit import layout, moves
from kit import pet as P

TITLE = 'LGTM'
DEFAULT_PRESET = 'x-post'
moves.use('lgtm')
APPROVED = 7  # the frame of the lgtm move where the check shines
PETS = [P.PetPose('lgtm', APPROVED, 0, 0), P.PetPose('lgtm', APPROVED, 0, 0, variant='insiders')]


def render(width: int, height: int) -> Image.Image:
	if width <= 512:
		return layout.sticker(width, height, PETS[:1])
	return layout.poster(
		width, height, 'Looks good to me!',
		['merge(pullRequest);  // LGTM!', 'merge(pr);  // LGTM!', 'merge(pr);'],
		PETS, line_number=42, tab='pull-request.md',
	)
