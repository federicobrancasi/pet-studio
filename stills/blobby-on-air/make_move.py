"""Writes ``moves/on-air/move.txt``: the pet films with a movie camera on its head.

Composed from layers like the ready-made moves: the real idle pose (``kit move grid idle:1``)
and the camera from ``props.py``. Run from the repo root, then build the move:

    python3 stills/blobby-on-air/make_move.py
    python3 -m kit move build on-air
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(HERE)]

from kit import pet as P  # noqa: E402

import props  # noqa: E402

W, H = 15, 15
PET_AT = (0, 3)     # column, row of the 12 x 12 body box
CAMERA_AT = (6, 0)  # the camera rests on the head and the right antenna holds it
LETTERS = 'KDGHSRhrLN'


def overlay(canvas: list, rows: list, col: int, row: int) -> None:
	for y, line in enumerate(rows):
		for x, ch in enumerate(line):
			if ch != '.':
				canvas[row + y][col + x] = ch


def frame(spin: bool, rec: bool, blink: bool) -> list:
	canvas = [['.'] * W for _ in range(H)]
	body, _ = P.grid('idle', 0)
	if blink:  # the top pixel of each eye closes
		body = [line.replace('E', 'C') if i == 8 else line for i, line in enumerate(body)]
	overlay(canvas, body, *PET_AT)
	cam = props.CAMERA_SPIN if spin else props.CAMERA
	if not rec:
		cam = [line.replace('R', 'r') for line in cam]
	overlay(canvas, cam, *CAMERA_AT)
	return [''.join(line) for line in canvas]


def main() -> None:
	frames = [
		(160, frame(False, True, False)),
		(160, frame(True, True, False)),
		(160, frame(False, True, False)),
		(160, frame(True, True, False)),
		(160, frame(False, False, False)),
		(160, frame(True, False, False)),
		(100, frame(False, False, True)),
		(160, frame(True, False, False)),
	]
	colors = ' '.join(f'{k}={props.PALETTE[k]}' for k in LETTERS)
	lines = [
		'# Films with a movie camera resting on its head: the reels turn and the record light blinks.',
		'# Composed from the real idle pose and the camera in stills/blobby-on-air/props.py.',
		'name: on-air',
		'about: Films with a movie camera on its head; the reels turn and the red record light blinks.',
		'loop: yes',
		'still: 1',
		f'colors: {colors}',
		'',
	]
	for ms, rows in frames:
		lines.append(f'frame {ms}')
		lines.extend(rows)
		lines.append('')
	out = ROOT / 'moves' / 'on-air' / 'move.txt'
	out.parent.mkdir(parents=True, exist_ok=True)
	out.write_text('\n'.join(lines))
	print(out)


if __name__ == '__main__':
	main()
