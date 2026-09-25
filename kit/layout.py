"""Layout for pet images that must work at every preset size.

:func:`poster` draws the classic composition: the code-city backdrop, a headline, a
line of code and one or more pets standing on it. It picks a layout from the aspect
ratio, so the same still looks right as an X post, a square, a 4K wallpaper, a phone
lock screen and a wide X header::

    from kit import layout, pet as P

    def render(width, height):
        return layout.poster(width, height, 'Happy coding!', ['hello();', 'hi();'],
                             [P.PetPose('idleTracking', 0, 0, 0, gaze=(4, -4)), ...])

Pet poses are placed automatically (their x and y are ignored); spacing, facing and the
ground line are handled for you. Use ``scale`` 2 (film size) unless the canvas is tiny.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from PIL import Image

from . import pet as P
from . import world
from .draw import TP


def pick_code(candidates: Sequence[str], max_width: int) -> tuple[str, bool]:
	"""The first code line that fits (list the longest version first), and whether it keeps
	its line number: lines drop the number before they are allowed to overflow."""
	for gutter in (True, False):
		for code in candidates:
			if world.CodeLine('x', 1, 0, 0, world.code(code), gutter=gutter).width <= max_width:
				return code, gutter
	return candidates[-1], False


def place_pets(img: Image.Image, poses: Sequence[P.PetPose], center_x: int, ground: int, spacing: int = 340) -> None:
	"""Draws pets side by side around ``center_x`` on ``ground``; the right half faces left."""
	n = len(poses)
	for i, pose in enumerate(poses):
		x = center_x + int((i - (n - 1) / 2) * spacing)
		facing = pose.facing if n == 1 else ('right' if (i + 0.5) < n / 2 else 'left')
		P.draw_pose(img, replace(pose, x=x, y=ground, facing=facing))


def poster(width: int, height: int, headline: str, code: Sequence[str], poses: Sequence[P.PetPose], subtitle: str | None = None, seed: int = 2, line_number: int = 1, tab: str | None = None) -> Image.Image:
	"""Backdrop + headline + code line + pets, laid out for the canvas shape."""
	img = Image.new('RGBA', (width, height))
	wide = width / height >= 2.2
	margin = 64
	spacing = 340 if len(poses) > 1 else 0

	if wide:
		# Header: the headline in an editor window on the left; the pets stand on a code
		# line on the right that runs off the edge of the picture.
		city = world.CodeCity((width, height), world_width=width, seed=seed, moon=None, star_band=height)
		city.draw(img, 0.0, 0, 0, clouds_fade=1.0, clouds_fade_above=height)  # the headline sits in a window
		text_w = int(width * 0.6)
		room = height - 19 * TP  # inside the window: tab bar and padding take the rest
		block_h = world.title_layout(headline, subtitle, text_w - 8 * TP, room)['height']
		win_h = min(height - 2 * TP, block_h + 17 * TP)
		wx, wy, ww, wh = world.window(img, margin, (height - win_h) // 2, text_w, win_h, tab or 'README.md')
		world.title_block(img, headline, wy + 4 * TP, subtitle, center_x=wx + ww // 2, max_width=ww - 6 * TP, max_height=room)
		left = margin + text_w + 48
		line = world.CodeLine('poster', line_number, left - 24, int(height * 0.68), world.code(code[0]))
		line.draw(img, 0.0, 0, 0, active=True)
		room = width - left
		place_pets(img, poses, left + room // 2, line.top, spacing=min(spacing, max(0, room - 220) // max(1, len(poses) - 1)))
		return img

	# Everything else: headline on top, pets on a code line below.
	top = int(height * (0.12 if height <= width else 0.2))
	max_ground = height - 2 * world.LINE_H
	pet_h = max((P.frame_size(p.name)[1] * p.scale for p in poses), default=0) + 48  # the tallest pose, plus air
	room = max(36, max_ground - top - pet_h)
	lay = world.title_layout(headline, subtitle, width - 2 * margin, room)
	title_w = max(world.text_width(text, lay['px']) for _, text in lay['lines'])
	moon = (width - 200, 40) if (width - title_w) // 2 >= 260 else None
	city = world.CodeCity((width, height), world_width=width, seed=seed, moon=moon)
	title_bottom = top + lay['height']
	clear = ((width - title_w) // 2 - 24, top - 24, (width + title_w) // 2 + 24, title_bottom + 24)
	city.draw(img, 0.0, 0, 0, clouds_fade=1.0, clouds_fade_above=title_bottom + 40, keep_clear=clear)
	world.title_block(img, headline, top, subtitle, max_width=width - 2 * margin, max_height=room)
	code_text, gutter = pick_code(code, width - 32)
	ground = int(height * (0.7 if height <= width else 0.66))
	ground = min(max(ground, title_bottom + pet_h), max_ground)  # leave the pets room under a tall title
	line = world.CodeLine('poster', line_number, 0, ground, world.code(code_text), gutter=gutter)
	line.x0 = (width - line.width) // 2
	line.draw(img, 0.0, 0, 0, active=True)
	fit_spacing = min(spacing, max(0, (width - 2 * margin - 220) // max(1, len(poses) - 1)))
	place_pets(img, poses, width // 2, line.top, spacing=fit_spacing)
	return img


def sticker(width: int, height: int, poses: Sequence[P.PetPose], scale: int | None = None) -> Image.Image:
	"""Just the pets on a transparent background (for the sticker preset).

	The pets are drawn at the largest whole-number scale that fits, unless ``scale`` is given.
	"""
	img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
	n = len(poses)
	if scale is None:
		fw = max(P.frame_size(p.name)[0] for p in poses)
		fh = max(P.frame_size(p.name)[1] for p in poses)
		scale = max(1, min((height - 24) // fh, (width // n - 8) // fw))
	spacing = int(width * 0.4) if n > 1 else 0
	for i, pose in enumerate(poses):
		x = width // 2 + int((i - (n - 1) / 2) * spacing)
		facing = pose.facing if n == 1 else ('right' if (i + 0.5) < n / 2 else 'left')
		P.draw_pose(img, replace(pose, x=x, y=height - 16, facing=facing, scale=scale))
	return img
