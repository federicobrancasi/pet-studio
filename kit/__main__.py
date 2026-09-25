"""Command line: ``python3 -m kit <command>``. Run ``python3 -m kit --help`` for the list."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import OUT_ROOT, REPO_ROOT, __version__

TEMPLATES = REPO_ROOT / '.claude' / 'skills' / 'pet-studio' / 'templates'


def _ok(text: str) -> None:
	print(f'  OK    {text}')


def _fail(text: str) -> None:
	print(f'  FAIL  {text}')


def cmd_doctor(args: argparse.Namespace) -> int:
	from . import media, sprites

	print(f'Pet Studio for Visual Studio Code {__version__}')
	status = 0
	if sys.version_info < (3, 9):
		_fail(f'Python {sys.version.split()[0]} is too old; use 3.9 or newer')
		status = 1
	else:
		_ok(f'Python {sys.version.split()[0]}')
	try:
		import numpy
		import PIL
		_ok(f'Pillow {PIL.__version__}, numpy {numpy.__version__}')
	except ImportError as error:
		_fail(f'{error}: run  python3 -m pip install -r requirements.txt')
		return 1
	try:
		exe = media.ffmpeg_exe()
		out = media.run(['-version'], capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.splitlines()[0]
		encoders = media.run(['-encoders'], capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
		if 'libx264' not in encoders:
			_fail(f'{exe} has no libx264 encoder')
			status = 1
		else:
			_ok(out.split(' Copyright')[0])
	except Exception as error:  # noqa: BLE001 - report anything that stops ffmpeg
		_fail(f'ffmpeg: {error}')
		status = 1
	if args.update:
		m = sprites.update_pin(args.update)
		_ok(f"re-pinned to microsoft/vscode@{m['commit'][:7]} ({len(m['files'])} sprite files)")
	try:
		if sprites.local_root() is None:
			sprites.ensure(verbose=True)
		from . import pet
		idle = pet.source_frame('idle', 0)
		_ok(f'pet sprites from {sprites.describe()}')
		_ok(f'{len(pet.STATE_TABLE)} states, idle frame {idle.size[0]}x{idle.size[1]}, typing timing {list(pet.durations("typing"))} ms')
	except Exception as error:  # noqa: BLE001
		_fail(f'pet sprites: {error}')
		status = 1
	print('Ready.' if status == 0 else 'Fix the problems above, then run doctor again.')
	return status


def cmd_poses(args: argparse.Namespace) -> int:
	from . import pet

	if args.list:
		for name, info in pet.STATE_TABLE.items():
			w, h = pet.frame_size(name)
			eyes = 'live eyes' if info.dom_eyes else 'baked eyes'
			print(f'{name:13} {pet.frame_count(name):2} frames {w}x{h}  {pet.total_ms(name):5} ms  {eyes:10}  {info.about}')
		return 0
	out = Path(args.out) if args.out else OUT_ROOT / f'poses-{args.variant}.png'
	out.parent.mkdir(parents=True, exist_ok=True)
	pet.pose_sheet(args.states or None, args.variant).save(out)
	print(out)
	return 0


def _new_from_template(kind: str, name: str) -> Path:
	import re

	if not re.match(r'^[a-z][a-z0-9-]{1,40}$', name):
		raise SystemExit(f'{kind} names use lowercase letters, digits and dashes: {name!r}')
	folder = REPO_ROOT / f'{kind}s' / name
	target = folder / f'{kind}.py'
	if target.exists():
		raise SystemExit(f'{target} already exists')
	folder.mkdir(parents=True, exist_ok=True)
	text = (TEMPLATES / f'{kind}.py').read_text(encoding='utf-8').replace('{{name}}', name)
	target.write_text(text, encoding='utf-8')
	return target


def cmd_film(args: argparse.Namespace) -> int:
	from . import film as F

	if args.action == 'new':
		print(_new_from_template('film', args.target))
		return 0
	target = Path(args.target)
	if args.action == 'review' and target.suffix.lower() in ('.mp4', '.mov'):
		from . import review
		cues = F.load(args.film).cues if args.film else []
		print(review.build(target, cues, folder=OUT_ROOT / target.stem / 'review'))
		return 0
	if args.action == 'gif' and target.suffix.lower() in ('.mp4', '.mov'):
		from . import media
		out = Path(args.out) if args.out else target.with_suffix('.gif')
		start = args.start or 0.0
		end = args.end if args.end is not None else media.probe(target).get('duration', 0.0)
		print(media.video_to_gif(target, out, start, end - start, args.fps, args.width))
		return 0
	film = F.load(target)
	if args.action == 'frame':
		for t in args.at:
			print(F.still(film, t, args.out if len(args.at) == 1 else None))
		return 0
	if args.action == 'sheet':
		return _film_sheet(film, args)
	if args.action == 'audio':
		from . import audio as A
		path = film.write_audio()
		if path is None:
			print('This film has no score(mix) function.')
			return 1
		loud = A.loudness(path)
		print(f"{path}\n  {loud['lufs']} LUFS integrated, true peak {loud['true_peak_db']} dBFS (before AAC)")
		return 0
	if args.action == 'check':
		result = F.check_determinism(film)
		print(json.dumps(result, indent=2))
		return 0 if result['ok'] else 1
	if args.action == 'render':
		out = F.export(film, args.out, 'draft' if args.draft else 'x', args.start or 0.0, args.end)
		return _print_video_report(out)
	if args.action == 'review':
		from . import review
		mp4 = film.out_dir() / (f'{film.name}-draft.mp4' if args.draft else f'{film.name}.mp4')
		if not args.reuse or not mp4.exists():
			mp4 = F.export(film, None, 'draft' if args.draft else 'x')
		print('checking determinism...')
		det = F.check_determinism(film)
		folder = review.build(mp4, film.cues, determinism=det)
		print((folder / 'report.md').read_text(encoding='utf-8'))
		print(f'Review package: {folder}')
		return 0
	if args.action == 'gif':
		print(F.gif(film, args.out, args.start or 0.0, args.end, args.fps, args.width))
		return 0
	raise SystemExit(f'unknown film action {args.action}')


def _film_sheet(film, args: argparse.Namespace) -> int:
	from PIL import Image

	from .font import draw_text

	start = args.start or 0.0
	end = args.end if args.end is not None else film.duration
	times = []
	t = start
	while t < end - 1e-9:
		times.append(round(t, 4))
		t += args.every
	cols = 5
	w, h = film.size
	tw = 384
	th = int(h * tw / w)
	rows = (len(times) + cols - 1) // cols
	sheet = Image.new('RGBA', (cols * (tw + 6) + 6, rows * (th + 28) + 6), (24, 24, 28, 255))
	for i, t in enumerate(times):
		im = film.render(t).resize((tw, th), Image.BILINEAR)
		x, y = 6 + (i % cols) * (tw + 6), 6 + (i // cols) * (th + 28)
		sheet.paste(im, (x, y + 22))
		draw_text(sheet, x + 2, y + 2, f'{t:05.2f}s', (255, 220, 90, 255), 2)
	out = Path(args.out) if args.out else film.out_dir() / f'sheet-{start:g}-{end:g}s.png'
	sheet.convert('RGB').save(out)
	print(out)
	return 0


def _print_video_report(path: Path) -> int:
	from . import audio as A
	from . import media

	info = media.probe(path)
	v = info.get('video', {})
	print(f"{path}\n  {info['bytes'] / 1e6:.1f} MB, {info.get('duration', 0):.2f} s, {v.get('width')}x{v.get('height')} @ {v.get('fps')} fps")
	if info.get('audio'):
		loud = A.loudness(path)
		print(f"  audio {loud['lufs']} LUFS, true peak {loud['true_peak_db']} dBTP")
	bad = [(n, d) for (n, ok, d) in media.x_checks(info) if not ok]
	print('  X upload checks: ' + ('all pass' if not bad else ', '.join(f'FAIL {n} ({d})' for n, d in bad)))
	return 0


def cmd_still(args: argparse.Namespace) -> int:
	from . import stills as St

	if args.action == 'new':
		print(_new_from_template('still', args.target))
		return 0
	if args.action == 'presets':
		for name, ((w, h), k, about) in St.PRESETS.items():
			print(f'{name:10} base {w}x{h} x{k}  {about}')
		return 0
	still = St.load(args.target)
	presets = list(St.PRESETS) if args.all else [args.preset or still.default_preset]
	for preset in presets:
		t0 = time.time()
		print(f'{still.save(preset, args.out if len(presets) == 1 else None)}  ({time.time() - t0:.1f}s)')
	return 0


def cmd_move(args: argparse.Namespace) -> int:
	from . import moves as M

	if args.action == 'new':
		if args.target in ('', 'all'):
			raise SystemExit('Give the new move a name: python3 -m kit move new <name>')
		print(M.new(args.target, args.source, args.frames, args.width, args.height, args.ms))
		return 0
	if args.action == 'grid':
		from . import KitError
		from . import pet as P
		state, _, frame = args.target.partition(':')
		if state not in P.state_names():
			raise KitError(f'Unknown state {state!r}. Run python3 -m kit poses --list to see them all')
		count = P.frame_count(state)
		if frame and (not frame.isdigit() or not 1 <= int(frame) <= count):
			raise KitError(f'{state} has frames 1-{count}; got {frame!r}')
		print(M.grid_text(state, int(frame) - 1 if frame else 0, args.variant))
		return 0
	if args.action == 'list':
		for name in M.all_moves():
			spec = M.parse(M.find(name))
			print(f'{name:16} {len(spec.frames):2} frames {spec.width}x{spec.height}  {spec.about}')
		return 0
	if args.action == 'gallery':
		print(M.gallery())
		return 0
	names = M.all_moves() if args.target == 'all' else [args.target]
	status = 0
	built = []
	for name in names:
		spec = M.parse(M.find(name))
		errors, warnings = M.validate(spec)
		print(f'{spec.name}: {len(spec.frames)} frames, {spec.width}x{spec.height} logical px, {sum(spec.durations)} ms, {"loops" if spec.loop else "plays once"}')
		for e in errors:
			print(f'  ERROR  {e}')
		for w in warnings:
			print(f'  warn   {w}')
		if errors:
			status = 1
			continue
		if args.action == 'build':
			result = M.build(name)
			built.append(spec.name)
			for path in result['written']:
				print(f'  wrote  {path.relative_to(REPO_ROOT) if REPO_ROOT in path.parents else path}')
	if len(built) == 1 and status == 0:
		print(f'  next   look at out/moves/{built[0]}/strip.png and moves/{built[0]}/preview.gif; add it to moves/README.md with: python3 -m kit move gallery')
	return status


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(prog='python3 -m kit', description='Pet Studio for Visual Studio Code: make videos, images and new moves with the VS Code pet.')
	parser.add_argument('--version', action='version', version=__version__)
	sub = parser.add_subparsers(dest='command', required=True)

	p = sub.add_parser('doctor', help='check the setup and download the pet sprites')
	p.add_argument('--update', nargs='?', const='main', metavar='REF', help='re-pin the sprites to a newer microsoft/vscode ref (maintainers)')
	p.set_defaults(func=cmd_doctor)

	p = sub.add_parser('poses', help='contact sheet (or --list) of every real pet state')
	p.add_argument('--list', action='store_true', help='list states, frame counts and timings')
	p.add_argument('--states', nargs='*', help='only these states')
	p.add_argument('--variant', default='stable', choices=['stable', 'insiders'])
	p.add_argument('--out')
	p.set_defaults(func=cmd_poses)

	p = sub.add_parser('film', help='videos: new, frame, sheet, audio, check, render, review, gif')
	p.add_argument('action', choices=['new', 'frame', 'sheet', 'audio', 'check', 'render', 'review', 'gif'])
	p.add_argument('target', help='film name (e.g. my-film, coding-world) or path to film.py; an .mp4 for review and gif')
	p.add_argument('--at', type=float, nargs='+', default=[0.0], help='frame: time(s) in seconds')
	p.add_argument('--from', dest='start', type=float, default=None, help='start time in seconds')
	p.add_argument('--to', dest='end', type=float, default=None, help='end time in seconds')
	p.add_argument('--every', type=float, default=0.5, help='sheet: seconds between frames')
	p.add_argument('--draft', action='store_true', help='fast low-quality encode')
	p.add_argument('--reuse', action='store_true', help='review: reuse the existing MP4')
	p.add_argument('--film', help='review of an .mp4: film.py to read CUES from')
	p.add_argument('--fps', type=float, default=20, help='gif: frames per second (default 20)')
	p.add_argument('--width', type=int, default=960, help='gif: width in px, rounded to a whole-number downscale (default 960)')
	p.add_argument('--out')
	p.set_defaults(func=cmd_film)

	p = sub.add_parser('still', help='images: new, render, presets')
	p.add_argument('action', choices=['new', 'render', 'presets'])
	p.add_argument('target', nargs='?', default='', help='still name (e.g. my-poster, lgtm-poster) or path to still.py')
	p.add_argument('--preset', help='x-post, square, x-header, wallpaper, phone or sticker')
	p.add_argument('--all', action='store_true', help='render every preset')
	p.add_argument('--out')
	p.set_defaults(func=cmd_still)

	p = sub.add_parser('move', help='new moves: new, grid, check, build, list, gallery')
	p.add_argument('action', choices=['new', 'grid', 'check', 'build', 'list', 'gallery'])
	p.add_argument('target', nargs='?', default='all', help='move name, folder or move.txt (check/build default to all moves); for grid: state[:frame], e.g. jump:2')
	p.add_argument('--from', dest='source', default='idle:1', help='new: real pose to start every frame from, e.g. idle:1')
	p.add_argument('--frames', type=int, default=4)
	p.add_argument('--width', type=int, default=12, help='new: frame width in logical px (12 = body only)')
	p.add_argument('--height', type=int, default=12, help='new: frame height in logical px')
	p.add_argument('--ms', type=int, default=120, help='new: default frame duration')
	p.add_argument('--variant', default='stable', choices=['stable', 'insiders'])
	p.set_defaults(func=cmd_move)

	for stream in (sys.stdout, sys.stderr):  # never crash on characters a console can't show
		try:
			stream.reconfigure(errors='replace')
		except (AttributeError, ValueError):
			pass
	args = parser.parse_args(argv)
	if args.command == 'move' and args.action == 'new':
		state, _, frame = args.source.partition(':')
		if frame and not frame.isdigit():
			parser.error(f'--from takes state:frame with a frame number, e.g. idle:1 (got {args.source!r})')
		args.source = f'{state}:{int(frame) - 1 if frame else 0}'
	from . import KitError
	try:
		return args.func(args)
	except KitError as error:  # the kit's own, already explained problems; other errors keep their traceback
		print(f'error: {error}', file=sys.stderr)
		return 2


if __name__ == '__main__':
	sys.exit(main())
