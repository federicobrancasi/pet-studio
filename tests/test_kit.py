"""Smoke tests for the kit. Run from the repository root:

    python3 -m unittest discover -s tests -v

They download the pinned pet sprites on first run (about 1 MB).
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from kit import audio as A  # noqa: E402
from kit import film as F  # noqa: E402
from kit import media, moves, sprites, stills  # noqa: E402
from kit import pet as P  # noqa: E402


class SpritesTest(unittest.TestCase):
	def test_pinned_sprites_verify(self) -> None:
		folder = sprites.ensure()
		manifest = sprites.manifest()
		for name, digest in manifest['files'].items():
			self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), digest, name)

	def test_states_load_with_runtime_timings(self) -> None:
		self.assertEqual(list(P.durations('typing')), [320, 480])
		self.assertEqual(P.frame_size('typing'), (168, 96))
		for name in P.STATE_TABLE:
			frames = P.frame_count(name)
			self.assertGreater(frames, 0, name)
			P.source_frame(name, frames - 1, 'insiders')

	def test_live_eyes_and_mirroring(self) -> None:
		right, ax_r, _ = P.pet_frame('idleTracking', 0, gaze=(4, -4))
		left, ax_l, _ = P.pet_frame('idleTracking', 0, facing='left', gaze=(4, -4))
		self.assertEqual(right.size, left.size)
		self.assertEqual(ax_r + ax_l, right.width)
		self.assertEqual(right.getpixel((44 * 2, 60 * 2 + 4)), P.EYE_COLOR)


class MovesTest(unittest.TestCase):
	def test_gallery_moves_validate_and_build(self) -> None:
		for name in moves.all_moves():
			spec = moves.parse(moves.find(name))
			errors, _ = moves.validate(spec)
			self.assertEqual(errors, [], name)
			sheet = moves.frame_image(spec, 0, 'stable')
			self.assertEqual(sheet.size, (spec.width * 8, spec.height * 8))

	def test_new_move_starts_from_the_real_idle_pose(self) -> None:
		folder = Path(tempfile.mkdtemp())
		try:
			original = moves.MOVES_ROOT
			moves.MOVES_ROOT = folder
			path = moves.new('smoke-test', 'idle:0', frames=2)
			spec = moves.parse(path)
			self.assertEqual(moves.validate(spec)[0], [])
			self.assertEqual(moves.home_box(spec.frames[0].rows), P.grid('idle', 0)[0])
		finally:
			moves.MOVES_ROOT = original
			shutil.rmtree(folder)

	def test_validator_catches_mistakes(self) -> None:
		folder = Path(tempfile.mkdtemp())
		try:
			bad = folder / 'move.txt'
			bad.write_text('name: Bad Name\nframe 10\n' + '\n'.join(['Z' * 12] * 11))
			errors, _ = moves.validate(moves.parse(bad))
			text = ' '.join(errors)
			self.assertIn('name', text)
			self.assertIn('too short', text)
			self.assertIn('unknown letters', text)
			self.assertIn('at least 12x12', text)
		finally:
			shutil.rmtree(folder)

	def test_parser_ignores_trailing_comments_and_rejects_bad_values(self) -> None:
		folder = Path(tempfile.mkdtemp())
		try:
			body = '\n'.join(P.grid('idle', 0)[0])
			good = folder / 'move.txt'
			good.write_text(f'name: my-nod  # a comment\nabout: nods\nloop: yes  # loops\nstill: 1  # frame\ncolors: Y=#ffd700  # prop\n\nframe 120  # ms\n{body}\n', encoding='utf-8')
			spec = moves.parse(good)
			self.assertEqual((spec.name, spec.loop, spec.still, spec.colors, spec.durations), ('my-nod', True, 0, {'Y': '#ffd700'}, [120]))
			bad = folder / 'bad.txt'
			bad.write_text(f'name: my-nod\nloop: maybe\nframe 120\n{body}\n', encoding='utf-8')
			with self.assertRaises(moves.MoveError):
				moves.parse(bad)
		finally:
			shutil.rmtree(folder)

	def test_moves_cannot_take_built_in_names(self) -> None:
		with self.assertRaises(moves.MoveError):
			moves.new('jump')
		with self.assertRaises(ValueError):
			P.register_move(P.Move('love', {}, [100]))

	def test_used_move_plays_like_a_state(self) -> None:
		moves.use('lgtm')
		image, _, _ = P.pet_frame('lgtm', 7, facing='left')
		self.assertEqual(image.size, (96 * 2, 128 * 2))

	def test_montage_plays_every_move_at_its_own_timing(self) -> None:
		frames, durations = moves.montage(['yes', 'wave', 'cowboy'], cols=2)
		yes, wave, cowboy = (moves.load(name) for name in ('yes', 'wave', 'cowboy'))
		changes = {sum(spec.durations[:i]) for spec in (yes, wave, cowboy) for i in range(len(spec.frames) + 1)}
		self.assertEqual(len({f.size for f in frames}), 1)
		self.assertEqual(len(frames), len(changes) + 1)  # plus the idle lead-in
		self.assertEqual(sum(durations), 500 + max(sum(s.durations) for s in (yes, wave, cowboy)) + 900)


class WorldsTest(unittest.TestCase):
	"""Worlds that aren't code: skies, landscapes, bubble letters, captions and the close-up zoom."""

	def test_day_sky_and_light_follow_the_clock(self) -> None:
		from kit import sky

		brightness = [sum(sky.day_keys(hour)[0][1][:3]) for hour in (5.0, 12.0, 21.0)]
		self.assertEqual(
			(brightness[1] > brightness[0], brightness[1] > brightness[2], sky.day_light(12.0)[1], sky.day_light(21.0)[1] > 0.5),
			(True, True, 0.0, True))
		self.assertIs(sky.gradient((64, 64), sky.day_keys(9.0)), sky.gradient((64, 64), sky.day_keys(9.01)))

	def test_cloud_platforms_hold_the_pet_on_their_surface(self) -> None:
		from PIL import Image
		from kit import sky

		step = sky.CloudPlatform(200, 300, 26, 11, seed=4)
		img = Image.new('RGBA', (400, 500))
		step.draw(img, 0, 0)
		column = [img.getpixel((200, y))[3] for y in range(250, 320, 4)]
		first_solid = 250 + 4 * next(i for i, a in enumerate(column) if a)
		self.assertEqual((step.surface(), step.surface(8) > step.surface(), abs(first_solid - (step.top - step.sink)) <= 4), (300, True, True))

	def test_ground_and_props_stand_on_the_surface(self) -> None:
		from PIL import Image
		from kit import land

		ground = land.Ground(lambda x: 300 + x / 10, biomes=((0, 'meadow'), (200, 'sand')))
		img = Image.new('RGBA', (400, 600))
		ground.draw(img, 0, 0)
		land.prop(img, 'rock', 300, ground.y(300), 0, 0, cell=12)
		y = ground.y(6)
		self.assertEqual((y % 12, img.getpixel((6, y - 13))[3], img.getpixel((6, y + 1))[3], img.getpixel((300, ground.y(300) - 6))[3]), (0, 0, 255, 255))

	def test_bubble_words_fit_and_squash_on_whole_pixels(self) -> None:
		from kit import letters

		word = letters.BubbleWord('HELLO WORLD', 540, 1000, max_width=880)
		hits = {0: [1.0]}
		self.assertEqual(
			(word.cell in letters.CELLS, word.width <= 880, word.cells(0, 1.0, hits), word.cells(0, 1.5, hits), word.top(0, 1.0, hits) > word.top(0)),
			(True, True, letters.squash(0.0, word.cell), (word.cell, word.cell), True))

	def test_zoom_keeps_every_pixel_whole(self) -> None:
		from PIL import Image
		from kit import draw

		img = Image.new('RGB', (8, 6))
		img.putpixel((1, 1), (255, 0, 0))
		big = draw.zoom(img, 0, 0, 2)
		self.assertEqual((big.size, [big.getpixel(xy) for xy in ((2, 2), (3, 3), (4, 4))]), ((8, 6), [(255, 0, 0), (255, 0, 0), (0, 0, 0)]))

	def test_captions_and_bubbles_stay_inside_the_safe_area(self) -> None:
		from PIL import Image
		from kit import layout, world

		img = Image.new('RGBA', (1080, 1920))
		x0, y0, x1, y1 = layout.safe_area(img.size)
		box = world.say(img, "HI, I'M HERE!", (x0 + x1) // 2, 900, 500)
		bottom = world.caption(img, 'a caption long enough that it has to wrap', y0 + 40, (x0 + x1) // 2, x1 - x0)
		left, top, right, _ = img.getbbox()
		self.assertEqual((left >= x0 - 12, right <= x1 + 12, top >= y0 + 30, bottom < box[1], box[2] <= x1), (True, True, True, True, True))


class FilmTest(unittest.TestCase):
	film = F.load(REPO / 'examples' / 'coding-world' / 'film.py')

	def test_frames_are_deterministic(self) -> None:
		a = self.film.frame(612).tobytes()
		self.film.frame(1500)
		b = self.film.frame(612).tobytes()
		self.assertEqual(hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest())

	def test_short_export_passes_x_checks(self) -> None:
		out = Path(tempfile.mkdtemp()) / 'clip.mp4'
		try:
			F.export(self.film, out, preset='draft', start=10.0, end=11.0, progress=False)
			info = media.probe(out)
			failed = [name for (name, ok, _) in media.x_checks(info) if not ok]
			self.assertEqual(failed, [])
			self.assertAlmostEqual(info['duration'], 1.0, delta=0.05)
		finally:
			shutil.rmtree(out.parent)

	def test_gif_is_rendered_from_the_film(self) -> None:
		from PIL import Image

		out = Path(tempfile.mkdtemp()) / 'clip.gif'
		try:
			F.gif(self.film, out, start=10.0, end=10.5, fps=10, width=480)
			with Image.open(out) as im:  # close it before cleanup: Windows can't delete open files
				self.assertEqual((im.size, im.n_frames), ((480, 270), 5))
		finally:
			shutil.rmtree(out.parent)

	def test_score_is_deterministic(self) -> None:
		mixer = A.Mixer(2.0)
		mixer.melody([(0, 0.5, 'C5'), (0.5, 0.5, 'E5')])
		A.groove(mixer, 0, 4)
		first = mixer.master().tobytes()
		mixer = A.Mixer(2.0)
		mixer.melody([(0, 0.5, 'C5'), (0.5, 0.5, 'E5')])
		A.groove(mixer, 0, 4)
		self.assertEqual(first, mixer.master().tobytes())


class VerticalTest(unittest.TestCase):
	"""9:16 films: the template, the safe area, the review package and GIFs."""

	@classmethod
	def setUpClass(cls) -> None:
		cls.folder = Path(tempfile.mkdtemp())
		template = REPO / '.claude' / 'skills' / 'pet-studio' / 'templates' / 'film-vertical.py'
		path = cls.folder / 'vertical-smoke' / 'film.py'
		path.parent.mkdir()
		path.write_text(template.read_text(encoding='utf-8').replace('{{name}}', 'vertical-smoke'), encoding='utf-8')
		cls.film = F.load(path)

	@classmethod
	def tearDownClass(cls) -> None:
		shutil.rmtree(cls.folder)

	def test_safe_area_leaves_room_for_the_apps(self) -> None:
		from kit import layout

		self.assertEqual(layout.safe_area((1080, 1920)), (60, 260, 960, 1600))
		self.assertEqual(layout.safe_area((720, 1280)), (40, 173, 640, 1067))
		self.assertEqual(layout.safe_area((1920, 1080)), (54, 54, 1866, 1026))

	def test_template_exports_a_clip_that_passes_every_check(self) -> None:
		from kit import review

		self.assertEqual(self.film.render(0.0).size, (1080, 1920))
		out = self.folder / 'clip.mp4'
		F.export(self.film, out, preset='draft', start=2.6, end=3.2, progress=False)
		info = media.probe(out)
		failed = [name for (name, ok, _) in media.x_checks(info) + media.vertical_checks(info) if not ok]
		self.assertEqual(failed, [])
		folder = review.build(out, [(0.3, 'hop')], folder=self.folder / 'review')
		self.assertTrue((folder / 'safe-zones.png').exists())
		self.assertIn('## Vertical checks', (folder / 'report.md').read_text(encoding='utf-8'))
		from PIL import Image

		with Image.open(folder / 'contact-01.png') as sheet:  # 10 narrow tiles a row
			self.assertEqual(sheet.width, 10 * (216 + 6) + 6)

	def test_gif_keeps_the_vertical_shape(self) -> None:
		from PIL import Image

		out = self.folder / 'clip.gif'
		F.gif(self.film, out, start=3.0, end=3.5, fps=10, width=480)
		with Image.open(out) as im:
			self.assertEqual((im.size, im.n_frames), ((270, 480), 5))


class StillTest(unittest.TestCase):
	def test_names_resolve_like_paths(self) -> None:
		self.assertEqual(F.resolve('coding-world', 'film'), (REPO / 'examples' / 'coding-world' / 'film.py').resolve())
		self.assertEqual(stills.load('lgtm-poster').path, (REPO / 'examples' / 'lgtm-poster' / 'still.py').resolve())
		with self.assertRaises(FileNotFoundError):
			F.resolve('no-such-film', 'film')

	def test_long_text_wraps_inside_the_canvas(self) -> None:
		from kit import world

		lay = world.title_layout('Hello!', 'the VS Code pets say hello to everyone', 457)
		widths = [world.text_width(line, lay['spx']) for _, line in lay['sub_lines']]
		self.assertGreater(len(widths), 1)
		self.assertLessEqual(max(widths), 457)

	def test_titles_fit_the_height_they_are_given(self) -> None:
		from kit import world

		for headline in ('Looks good to me!', 'Ship it on Friday!', 'It works on my machine!'):
			for (width, height) in ((836, 348), (457, 300), (952, 300)):
				lay = world.title_layout(headline, None, width, height)
				self.assertLessEqual(lay['height'], height, (headline, width, height))

	def test_cli_explains_kit_errors_and_keeps_other_tracebacks(self) -> None:
		import subprocess
		run = lambda *a: subprocess.run([sys.executable, '-m', 'kit', *a], cwd=REPO, capture_output=True, text=True)
		for args in (('move', 'new', 'jump'), ('move', 'grid', 'jump:9'), ('film', 'frame', 'no-such-film')):
			result = run(*args)
			self.assertEqual(result.returncode, 2, args)
			self.assertTrue(result.stderr.startswith('error: '), (args, result.stderr))

	def test_every_preset_renders_at_its_size(self) -> None:
		still = stills.load(REPO / 'examples' / 'lgtm-poster' / 'still.py')
		for preset, ((w, h), k, _) in stills.PRESETS.items():
			self.assertEqual(still.render(preset).size, (w * k, h * k), preset)


if __name__ == '__main__':
	unittest.main()
