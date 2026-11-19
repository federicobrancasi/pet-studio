"""Exports the Blobby On Air avatars and emoji, with previews on Slack's light and dark themes.

    python3 stills/blobby-on-air/export.py [out_dir]     # default: out/blobby-on-air
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from kit import stills  # noqa: E402
from kit.font import draw_text  # noqa: E402

LIGHT = (255, 255, 255, 255)
DARK = (0x1A, 0x1D, 0x21, 255)
INK = {LIGHT: (90, 90, 90, 255), DARK: (200, 200, 200, 255)}


def on(img: Image.Image, bg: tuple, size: int | None = None) -> Image.Image:
	out = Image.new('RGBA', img.size, bg)
	out.alpha_composite(img)
	if size and size != img.width:
		out = out.resize((size, size), Image.LANCZOS)  # what Slack does when it shows it small
	return out


def save_gif(frames: list, durations: list, path: Path) -> None:
	"""A looping GIF with one shared palette; index 0 is transparent."""
	arrays = [np.array(f) for f in frames]
	colors = sorted({tuple(px[:3]) for a in arrays for px in a[a[:, :, 3] > 127]})
	if len(colors) > 255:
		raise ValueError(f'{path.name}: {len(colors)} colors')
	index = {c: i + 1 for i, c in enumerate(colors)}
	palette = [0, 0, 0] + [v for c in colors for v in c]
	palette += [0] * (768 - len(palette))
	pims = []
	for a in arrays:
		idx = np.zeros(a.shape[:2], np.uint8)
		ys, xs = np.nonzero(a[:, :, 3] > 127)
		for y, x in zip(ys, xs):
			idx[y, x] = index[tuple(a[y, x, :3])]
		im = Image.fromarray(idx, 'P')
		im.putpalette(palette)
		pims.append(im)
	pims[0].save(path, save_all=True, append_images=pims[1:], duration=durations, loop=0,
				 disposal=2, transparency=0, background=0, optimize=False)


def preview(avatars: list, first: int, path: Path) -> None:
	"""One row per avatar: on white and on #1A1D21 at 320 px, then at a true 48 px (and that 48 px enlarged 3x)."""
	big, small, gap = 320, 48, 24
	cell_w = big + gap + small + gap + 3 * small + gap
	sheet = Image.new('RGBA', (200 + 2 * cell_w + gap, gap + 48 + len(avatars) * (big + gap)), (128, 128, 128, 255))
	for j, bg in enumerate((LIGHT, DARK)):
		draw_text(sheet, 200 + j * cell_w, gap, 'on white' if bg == LIGHT else 'on #1A1D21', (255, 255, 255, 255), 4)
	for i, img in enumerate(avatars):
		y = gap + 48 + i * (big + gap)
		draw_text(sheet, gap, y + big // 2 - 8, f'avatar-{first + i}', (255, 255, 255, 255), 4)
		for j, bg in enumerate((LIGHT, DARK)):
			x = 200 + j * cell_w
			sheet.alpha_composite(on(img, bg, big), (x, y))
			x += big + gap
			sheet.alpha_composite(on(img, bg, small), (x, y + big // 2 - small // 2))  # true 48 px
			zoom = on(img, bg, small).resize((small * 3, small * 3), Image.NEAREST)  # the same 48 px, enlarged
			sheet.alpha_composite(zoom, (x + small + gap, y + big // 2 - small * 3 // 2))
	sheet.convert('RGB').save(path, optimize=True)


def main() -> None:
	out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'out' / 'blobby-on-air'
	(out / 'avatars').mkdir(parents=True, exist_ok=True)
	(out / 'emoji').mkdir(parents=True, exist_ok=True)
	still = stills.load(ROOT / 'stills' / 'blobby-on-air' / 'still.py').module

	# Avatars: 1024 px transparent, plus 48 px checks
	avatars = []
	for n, key in enumerate(still.AVATARS, 1):
		img = still.avatar(key, 1024)
		assert img.size == (1024, 1024)
		img.save(out / 'avatars' / f'avatar-{n}.png', optimize=True)
		img.resize((48, 48), Image.LANCZOS).save(out / 'avatars' / f'avatar-{n}-48.png')
		avatars.append(img)
		bbox = img.getbbox()
		print(f'avatar-{n}: content {bbox[2] - bbox[0]}x{bbox[3] - bbox[1]} at {bbox[:2]}')
	# one sheet per set of six: avatars-preview.png (1-6), avatars-preview-2.png (7-12)
	for s in range(0, len(avatars), 6):
		name = 'avatars-preview.png' if s == 0 else f'avatars-preview-{s // 6 + 1}.png'
		preview(avatars[s:s + 6], s + 1, out / 'avatars' / name)

	# Emoji: 128 px looping GIFs
	rows = []
	for name in still.EMOJI:
		frames, durations = still.emoji_frames(name)
		path = out / 'emoji' / f'{name}.gif'
		save_gif(frames, durations, path)
		kb = path.stat().st_size / 1024
		print(f'{name}: {len(frames)} frames, {sum(durations)} ms, {kb:.1f} KB')
		assert kb < 128 and all(f.size == (128, 128) for f in frames)
		rows.append((name, frames))
	cell, tiny, gap = 128, 22, 24
	width = gap + 220 + 8 * (cell + 8) + 2 * (tiny * 4 + gap) + gap
	sheet = Image.new('RGBA', (width, gap + len(rows) * 2 * (cell + 8) + gap), (128, 128, 128, 255))
	for r, (name, frames) in enumerate(rows):
		for j, bg in enumerate((LIGHT, DARK)):
			y = gap + (2 * r + j) * (cell + 8)
			draw_text(sheet, gap, y + 56, name, (255, 255, 255, 255), 4)
			for k, f in enumerate(frames):
				sheet.alpha_composite(on(f, bg), (gap + 220 + k * (cell + 8), y))
			x = gap + 220 + 8 * (cell + 8) + gap
			t = on(frames[0], bg, tiny)
			sheet.alpha_composite(t, (x, y + 8))  # true 22 px
			sheet.alpha_composite(t.resize((tiny * 4, tiny * 4), Image.NEAREST), (x + tiny + 8, y + 8))
	sheet.convert('RGB').save(out / 'emoji' / 'emoji-frames.png', optimize=True)

	# The deliverable preview: each emoji at 128 and 22 px, on white and on #1A1D21
	col = 300
	pv = Image.new('RGBA', (gap + len(rows) * col, gap + 32 + 2 * (cell + gap) + 2 * (tiny + gap)), (128, 128, 128, 255))
	for i, (name, frames) in enumerate(rows):
		x = gap + i * col
		draw_text(pv, x, gap, name.replace('blobby-', ''), (255, 255, 255, 255), 4)
		key = frames[0]
		for j, bg in enumerate((LIGHT, DARK)):
			pv.alpha_composite(on(key, bg), (x, gap + 32 + j * (cell + gap)))
			pv.alpha_composite(on(key, bg, tiny), (x, gap + 32 + 2 * (cell + gap) + j * (tiny + gap)))
	pv.convert('RGB').save(out / 'emoji' / 'emoji-preview.png', optimize=True)
	print(out)


if __name__ == '__main__':
	main()
