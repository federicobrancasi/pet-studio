"""A day in the life of the VS Code pet: a vertical (9:16) reel in which the pet travels through its
coding day, from a sunny morning to a starry night, stopping to play the moves in moves/.

Coffee, an idea, rubber ducking, then it builds a rocket; a bug and a merge conflict get in the
way, it finally merges, ships the rocket, logs off and goes home to sleep. It hops from stop to
stop across a meadow, a golden field and a desert at sunset. It shows how to make a journey reel:

* a world that isn't code: ``kit.sky`` for a sky that follows the clock, ``kit.land`` for the
  hills, the ground and the props, all lit by the time of day;
* a ``FollowCamera`` that keeps the pet on the left third while it travels, so the props of
  its moves have room on the right;
* a schedule built from ``DAY``: change the list and the stops, hops, clock and music follow;
* outlined captions inside ``layout.safe_area``, readable on a bright sky.

    python3 -m kit film sheet pet-day
    python3 -m kit film review pet-day
"""

from __future__ import annotations

import math

from PIL import Image

from kit import fx, land, layout, letters, moves, motion, sky, world
from kit import audio as A
from kit import pet as P
from kit.draw import blit, clamp, fill_rect, seg, snap
from kit.motion import Hop
from kit.pet import PetPose

TITLE = 'A day in the life of the VS Code pet'
W, H = SIZE = (1080, 1920)  # 9:16 for Reels, TikTok, Shorts and X
FPS = 60
SAFE = layout.safe_area(SIZE)  # (60, 260, 960, 1600)
SAFE_X = (SAFE[0] + SAFE[2]) // 2
SAFE_W = SAFE[2] - SAFE[0]
SCALE = 3  # a phone-sized pet: 288 px tall, and a 24-pixel move is 576 px wide
MASTER = {'ceiling': 0.6, 'drive': 2.2}  # keeps the true peak under -1 dBTP after AAC

# --------------------------------------------------------------------------------------------
# The day: (clock, caption, move, hops to get there), one stop each

DAY = [
	('09:00', 'coffee first', 'coffee', 0),
	('09:30', 'a wild idea', 'idea', 2),
	('10:00', 'rubber ducking', 'rubber-duck', 1),
	('11:00', 'building it', 'build', 2),         # it builds a rocket ...
	('13:00', 'oh no, a bug!', 'debug', 1),
	('14:00', 'merge conflict', 'zapped', 1),
	('15:00', 'finally merged!', 'lgtm', 1),
	('16:00', 'ship it!', 'ship-it', 2),          # ... and here it blasts off
	('18:00', 'logging off', 'cowboy', 1),
]
HOME_HOPS = 2        # back home at night, a longer way (so home stays off screen until then)
HOME_STRIDE = 1000
for _, _, _name, _ in DAY:
	moves.use(_name)

T_FIRST = 2.0        # the hook holds for one bar while the sun comes up
GRID = 0.25          # moves and hops start on sixteenth notes at 120 BPM
GAP = 0.1            # idle after a move before hopping on
SETTLE = 0.12        # idle after landing before the next move
STRIDE = 820         # px between stops
HOME_X = 400         # where the pet sleeps on its chat input


def _ground(x: float) -> float:
	return 1330 + 34 * math.sin(x / 700) + 18 * math.sin(x / 290 + 1.3)


GROUND = land.Ground(_ground)  # its biomes are set between the stops, below
INPUT_W, INPUT_H = 680, 160


def _input_box(x: float) -> tuple:
	"""The chat input the pet sleeps on, around spot ``x``: ``(x0, x1, top)``, lying on the grass."""
	x0, x1 = x - 270, x - 270 + INPUT_W
	return x0, x1, max(GROUND.y(v) for v in range(int(x0), int(x1), 12)) - INPUT_H + 24


def _clock(text: str) -> float:
	h, m = text.split(':')
	return int(h) + int(m) / 60


def _on_grid(t: float) -> float:
	return math.ceil(t / GRID - 1e-9) * GRID


def _schedule() -> tuple:
	"""Stops ``[(t0, clock, caption, move, x)]``, the hops between them, and when it gets home."""
	stops, hops = [], []
	t, x = T_FIRST, float(HOME_X)
	y = _input_box(HOME_X)[2]
	legs = [(clock, caption, name, n) for (clock, caption, name, n) in DAY] + [(None, None, None, HOME_HOPS)]
	for (clock, caption, name, n) in legs:
		if n:
			t = _on_grid(t + GAP)
			stride = HOME_STRIDE if name is None else STRIDE
			x1 = x + stride
			air, height = (0.56, 300) if n == 1 else (0.42, 200)
			for k in range(n):
				xa, xb = x + stride * k / n, x + stride * (k + 1) / n
				ya = y if k == 0 else GROUND.y(xa)
				yb = _input_box(x1)[2] if (name is None and k == n - 1) else GROUND.y(xb)
				hops.append(Hop(t, t + air, xa, ya, xb, yb, height))
				t += air + 0.2
			x, y = x1, hops[-1].y1
			t = _on_grid(t - 0.2 + SETTLE)
		if name is None:
			return stops, hops, hops[-1].t1, x
		stops.append((t, clock, caption, name, x))
		t += P.total_ms(name) / 1000


STOPS, HOPS, T_HOME, END_X = _schedule()
START = {name: t0 for (t0, _, _, name, _) in STOPS}
_X = {name: x for (_, _, _, name, x) in STOPS}
# The ground changes between stops: meadow, a golden field after the bug, sand for the ranch, and
# grass again at home.
GROUND.biomes = ((0, 'meadow'), ((_X['debug'] + _X['zapped']) / 2 + 60, 'field'),
	((_X['ship-it'] + _X['cowboy']) / 2 + 60, 'sand'), ((_X['cowboy'] + END_X) / 2 + 40, 'meadow'))
T_LEAVE = HOPS[-HOME_HOPS].t0                          # it sets off for home: the caption says so
T_DOZE = T_HOME + 0.45                                 # it nods off: the waking animation, backwards
T_ASLEEP = T_DOZE + P.total_ms('waking') / 1000
T_END = T_HOME + 0.4                                   # the end title drops in
DURATION = round(T_ASLEEP + 2.4, 2)
LANDINGS = motion.landings(HOPS)
HOMES = (HOME_X, END_X)


def at(name: str, frame: int) -> float:
	"""When frame ``frame`` (1-based, as in move.txt) of a stop's move starts."""
	return START[name] + sum(P.durations(name)[:frame - 1]) / 1000


# The clock through the film, for the sky and the light: dawn during the hook, each stop's time
# while it's there, sliding between stops, and night once it's home.
HOURS = [(0.0, 7.0), (T_FIRST, 9.0)] + [(t0, _clock(clock)) for (t0, clock, _, _, _) in STOPS[1:]] + [(T_HOME, 20.6), (DURATION, 21.0)]


def hour_at(t: float) -> float:
	for (t0, h0), (t1, h1) in zip(HOURS, HOURS[1:]):
		if t <= t1:
			return h0 + (h1 - h0) * seg(t, t0, t1)
	return HOURS[-1][1]


CUES = [  # each stop is reviewed at its move's key frame (the one shown for reduced motion)
	(0.0, 'hook: a day in the life'),
	*((at(name, moves.load(name).still_index() + 1) + 0.03, f'{clock} {name}') for (_, clock, _, name, _) in STOPS),
	(HOPS[1].t0, 'on the way'),
	(T_ASLEEP + 0.5, 'end card: home, asleep'),
]

# --------------------------------------------------------------------------------------------
# Picture

PET_SCREEN_X = 350   # the pet's place on screen: props of its moves grow to the right
SLEEP_FROM = sum(P.durations('sleep')[:3])  # the sleep loop starts on its bubble, like the last waking frame
BLINKS = [0.35, 1.45, 5.3, 12.2, 20.2, 26.6]
FAR = land.Ridge(seed=3, color='#8fb4dc', y=1050, amp=110, parallax=0.2, rim='#a9c7e8')
NEAR = land.Ridge(seed=8, color='#79ad86', y=1170, amp=70, parallax=0.45, rim='#93c49c')
CLOUDS = sky.CloudLayer(seed=3, count=7, y=(760, 1080), palette='day', alpha=210, parallax=(0.15, 0.0), drift=10, span=1600)
STORM = ((58, 62, 92), 0.42)  # the merge-conflict storm dims the world ...
STORM_SKY = (93, 99, 120)     # ... greys the sky and the sun ...
STORM_CLOUDS = [sky.CloudLayer(seed=21, count=8, y=(700, 1000), palette='storm', alpha=a, sizes=(18, 30), cell=12,
	parallax=(0.15, 0.0), drift=22, span=1500) for a in (70, 120, 170, 210, 235)]  # ... and rolls clouds in, in steps


def _stop_x(name: str) -> float:
	return next(x for (_, _, _, n, x) in STOPS if n == name)


# Props along the way: (name, x, cell size, cells sunk into the ground). Big ones are 24 px cells.
SCENERY = [
	('pine', HOME_X - 280, 24, 0), ('flower_white', HOME_X + 560, 12, 0), ('bush', HOME_X + 700, 24, 1),
	('tree', _stop_x('idea') - 150, 24, 0), ('flower_pink', _stop_x('idea') + 330, 12, 0), ('flower_violet', _stop_x('idea') + 380, 12, 0),
	('pond', _stop_x('rubber-duck') + 300, 24, 5), ('rock', _stop_x('rubber-duck') + 580, 24, 1),
	('rock', _stop_x('build') - 210, 24, 1), ('flower_violet', _stop_x('build') + 500, 12, 0),
	('bush', _stop_x('debug') - 190, 24, 1), ('flower_pink', _stop_x('debug') + 420, 12, 0), ('flower_white', _stop_x('debug') + 470, 12, 0),
	('rock', _stop_x('zapped') - 210, 24, 1),
	('bush', _stop_x('lgtm') - 200, 24, 1), ('flower_pink', _stop_x('lgtm') + 300, 12, 0), ('flower_violet', _stop_x('lgtm') + 360, 12, 0),
	('flower_white', _stop_x('lgtm') + 420, 12, 0),
	('cactus', _stop_x('ship-it') + 470, 24, 0),
	('fence', _stop_x('cowboy') - 230, 24, 0), ('fence', _stop_x('cowboy') + 420, 24, 0), ('cactus', _stop_x('cowboy') + 560, 24, 0),
	('pine', END_X + 500, 24, 0), ('flower_white', END_X - 280, 12, 0),
]


def storm(t: float) -> float:
	"""How stormy it is (0-1, in eighths) during the merge-conflict gag."""
	t0, t1 = START['zapped'], START['zapped'] + P.total_ms('zapped') / 1000
	return round(seg(t, t0 - 0.2, t0 + 0.3) * (1 - seg(t, t1 - 0.3, t1 + 0.3)) * 8) / 8


def light_at(t: float) -> tuple:
	rgb, amount = sky.day_light(hour_at(t))
	k = storm(t)
	if k > 0:
		(sr, sg, sb), sa = STORM
		rgb = tuple(int(round(c + (s - c) * k)) for c, s in zip(rgb, (sr, sg, sb)))
		amount = amount + (sa - amount) * k
	return rgb, round(amount, 3)


def sky_keys(t: float) -> tuple:
	keys, k = sky.day_keys(hour_at(t)), storm(t)
	if k <= 0:
		return keys
	grey = STORM_SKY + (255,)
	return tuple((f, tuple(int(round(a + (b - a) * 0.6 * k)) for a, b in zip(c, grey))) for (f, c) in keys)


def _prop_pops() -> list:
	"""``(t, x, y)`` where each move's props vanish on its last frames, for a small pop of sparkles."""
	pops = []
	for (_, _, _, name, x) in STOPS:
		if name in ('build', 'ship-it'):  # build pops its rocket itself, and ship-it's flies off
			continue
		last = None
		for f in range(1, P.frame_count(name)):
			before, now = (_props_box(name, g) for g in (f - 1, f))
			if before is not None and now is None:
				last = (f, before)
		if last is not None:
			f, (x0, y0, x1, y1) = last
			pops.append((at(name, f + 1), x + (x0 + x1) / 2, GROUND.y(x) + (y0 + y1) / 2))
	return pops


def _props_box(name: str, frame: int) -> tuple | None:
	"""The box of a move frame's props (anything outside the pet's own 12 x 12 body), relative to its feet."""
	im, ax, ay = P.pet_frame(name, frame, scale=SCALE)
	alpha = im.getchannel('A')
	alpha.paste(0, (ax - 48 * SCALE, ay - 96 * SCALE, ax + 48 * SCALE, ay))
	box = alpha.getbbox()
	return None if box is None else (box[0] - ax, box[1] - ay, box[2] - ax, box[3] - ay)


def _rocket() -> tuple:
	"""The ship-it rocket from its last frame with the rocket (frame 7), and where it sits relative to the feet."""
	im, ax, ay = P.pet_frame('ship-it', 6, scale=SCALE)
	x0, y0, x1, y1 = _props_box('ship-it', 6)
	return im.crop((ax + x0, ay + y0, ax + x1, ay + y1)), x0, y0


def rocket_off(img: Image.Image, t: float, cx: float) -> None:
	"""After the move's frame 7 the rocket keeps going, faster and faster, off the top of the frame."""
	t0 = at('ship-it', 8)
	dt = t - t0
	if not (0 <= dt < 0.45):
		return
	spr, rx, ry = ROCKET
	x = _X['ship-it'] + rx
	y = GROUND.y(_X['ship-it']) + ry
	lift = lambda d: 1400 * d + 5200 * d * d
	DRIFT = 0.7  # it arcs to the right, clear of the caption
	for k in range(int(dt / 0.035)):  # smoke puffs left behind, fading
		d = k * 0.035
		age = dt - d
		if age < 0.3:
			s = 24 if age < 0.15 else 12
			fill_rect(img, snap(x + DRIFT * lift(d) + spr.width / 2 - s / 2 - cx + (k % 3 - 1) * 10, 4), snap(y + spr.height - lift(d), 4), s, s,
				(236, 236, 244, int(230 * (1 - age / 0.3))))
	blit(img, spr, snap(x + DRIFT * lift(dt) - cx, 4), snap(y - lift(dt), 4))


def stop_at(t: float) -> tuple | None:
	for stop in reversed(STOPS):
		if t >= stop[0]:
			return stop
	return None


def hero_pose(t: float) -> PetPose:
	blink = motion.blinking(t, BLINKS)
	hop = motion.hop_pose(HOPS, t)
	if hop is not None:
		hop.scale = SCALE
		return hop
	x, y = motion.ground_at(HOPS, t, (HOME_X, _input_box(HOME_X)[2]))
	if t < 1.0:  # it wakes up with the sun
		return PetPose('waking', P.frame_at('waking', t * 1000 + 40, loop=False), x, y, scale=SCALE)
	if t >= T_DOZE:
		if t < T_ASLEEP:
			return PetPose('waking', P.frame_at('waking', (T_ASLEEP - t) * 1000 - 1, loop=False), x, y, scale=SCALE)
		return PetPose('sleep', P.frame_at('sleep', (t - T_ASLEEP) * 1000 + SLEEP_FROM), x, y, scale=SCALE)
	stop = stop_at(t)
	if stop is not None and t < T_HOME:
		t0, _, _, name, _ = stop
		ms = (t - t0) * 1000
		if ms < P.total_ms(name):
			return PetPose(name, P.frame_at(name, ms, loop=False), x, y, scale=SCALE)
	gaze = (0, -4) if t < T_FIRST - 0.2 else (4, 0)  # reads the hook, then looks where it's going
	return PetPose('idleTracking', P.frame_at('idle', t * 1000), x, y, gaze=gaze, blink=blink, scale=SCALE)


def camera_target(t: float) -> tuple:
	x = motion.ground_at(HOPS, t, (HOME_X, 0))[0]
	for h in HOPS:  # move early toward where it's landing
		if h.t0 - 0.05 <= t < h.t1:
			x = h.x1
	return x - PET_SCREEN_X, 0.0


CAMERA = motion.FollowCamera(camera_target, DURATION, FPS, omega=(4.2, 4.0))


def sun_and_moon(img: Image.Image, t: float, hour: float) -> None:
	"""The sun crosses the right third of the sky, away from the pet and below the captions."""
	if hour < 19.4:
		u = clamp((hour - 6.5) / 12.5, 0, 1)
		spr = sky.lit(sky.sun(120, 12, stripes=hour > 16.5), (STORM_SKY, 0.7 * storm(t)))
		x, y = 820 + 120 * u, 1230 - math.sin(math.pi * u) * 300  # low on the right, clear of the moves' props
		blit(img, spr, snap(x - spr.width / 2, 4), snap(y - spr.height / 2, 4))
	if hour > 18.8:
		k = seg(hour, 18.8, 21.0)
		spr = sky.moon(72, 12)
		blit(img, spr, snap(840 - 70 * k - spr.width / 2, 4), snap(1120 - 330 * k - spr.height / 2, 4))


def caption(img: Image.Image, t: float) -> None:
	top = SAFE[1] + 40
	if t < T_FIRST:  # whole from the first frame: it's the thumbnail
		bottom = world.caption(img, 'A DAY IN THE LIFE', top, SAFE_X, SAFE_W, sizes=(16,))
		world.caption(img, 'of the VS Code pet', bottom + 32, SAFE_X, SAFE_W, sizes=(12, 8))
		return
	if t >= T_END:
		return
	stop = stop_at(t)
	clock, text = (stop[1], stop[2]) if t < T_LEAVE else ('21:00', 'home sweet home')
	t0 = stop[0] if t < T_LEAVE else T_LEAVE
	clock = clock.replace('0', 'O')  # the font's slashed zero fills in under the outline
	pop = snap((1 - seg(t, t0, t0 + 0.12)) * -24, 4)
	bottom = world.caption(img, clock, top + pop, SAFE_X, SAFE_W, color=(255, 211, 92, 255), sizes=(16,))
	if t >= t0 + 0.12:
		world.caption(img, text, bottom - pop + 32, SAFE_X, SAFE_W, sizes=(12,))


ROCKET = _rocket()
POPS = _prop_pops()
_B = _props_box('ship-it', 1)  # where the rocket stands in ship-it's frame 2
ROCKET_BACK = (_X['ship-it'] + (_B[0] + _B[2]) / 2, GROUND.y(_X['ship-it']) + (_B[1] + _B[3]) / 2)
MERGED_CONFETTI = [(at('lgtm', 5), fx.confetti_burst(9, _X['lgtm'] + 60, GROUND.y(_X['lgtm']) - 520, 40, 0.9))]
END_WORDS = [letters.BubbleWord(word, SAFE_X, SAFE[1] + 200 + 170 * k, max_width=SAFE_W, cell=8, palette='gold') for k, word in enumerate(('HAPPY', 'CODING!'))]


def render(t: float) -> Image.Image:
	img = Image.new('RGBA', SIZE)
	cx = int(round(CAMERA.at(t)[0]))
	hour = hour_at(t)
	light = light_at(t)
	img.paste(sky.gradient(SIZE, sky_keys(t)), (0, 0))
	sky.stars(img, t, cx, 0, strength=seg(hour, 19.4, 20.6), area=(0, 0, W, 1000))
	sun_and_moon(img, t, hour)
	CLOUDS.draw(img, t, cx, 0, light)
	if storm(t) > 0:
		STORM_CLOUDS[max(0, min(4, round(storm(t) * 5) - 1))].draw(img, t, cx, 0)
	FAR.draw(img, cx, 0, light)
	NEAR.draw(img, cx, 0, light)
	GROUND.draw(img, cx, 0, light)
	for (name, x, cell, sink) in SCENERY:
		if -400 < x - cx < W + 400:
			land.prop(img, name, x, GROUND.y(x), cx, 0, light, cell, sink)
	for home in HOMES:
		x0, x1, top = _input_box(home)
		if -INPUT_W < x0 - cx < W:
			world.chat_input(img, t, x0, x1, top, cx, 0, placeholder='Ask anything' if home == HOME_X else None, height=INPUT_H)
	P.draw_pose(img, hero_pose(t), cx, 0)
	rocket_off(img, t, cx)
	for (tp, px, py) in POPS:
		fx.sparkle_ring(img, t, tp, px, py, cx, 0, n=6, radius=110, inner=30, life=0.3, color=(255, 255, 255, 255))
	fx.sparkle_ring(img, t, at('ship-it', 2), *ROCKET_BACK, cx, 0, n=8, radius=190, inner=100, life=0.35)  # the rocket it built is back
	fx.confetti(img, t, MERGED_CONFETTI, cx, 0)
	fx.dust(img, t, LANDINGS, cx, 0, color=land.lit('#f3ead2', light))
	if t >= T_ASLEEP:
		fx.zzz(img, t - T_ASLEEP, END_X + 170, _input_box(END_X)[2] - 250, cx, 0)
	fx.flash(img, t, at('zapped', 6), 0.12, (235, 240, 255))  # the lightning strike
	caption(img, t)
	if t >= T_END:
		for k, word in enumerate(END_WORDS):
			word.draw(img, t, drop=(T_END + 0.35 * k, 0.07), bob=4 if t > T_END + 1.4 else 0)
	return img


# --------------------------------------------------------------------------------------------
# Score: 120 BPM, so one beat = 0.5 s and one bar = 2 s. Morning, trouble, triumph, evening, night.

CHORDS = {
	'C': ['C3', 'E4', 'G4', 'C5'], 'Am': ['A2', 'C4', 'E4', 'A4'], 'F': ['F2', 'A3', 'C4', 'F4'],
	'G': ['G2', 'B3', 'D4', 'G4'], 'Dm': ['D3', 'F3', 'A3', 'D4'], 'E': ['E2', 'G#3', 'B3', 'E4'],
}
B_TROUBLE = round(START['debug'] * 2)       # sections start on the beat of their first stop
B_TRIUMPH = round(START['lgtm'] * 2)
B_EVENING = round(START['cowboy'] * 2)
B_NIGHT = round(T_HOME * 2)
SECTIONS = [  # (first beat, last beat, chords per 4 beats, melody, instrument)
	(4, B_TROUBLE, ['C', 'Am', 'F', 'G'], [(0, .5, 'E5'), (.5, .5, 'G5'), (1, 1, 'C6'), (2, .5, 'G5'), (2.5, .5, 'E5'), (3, 1, 'G5'),
		(4, .5, 'A5'), (4.5, .5, 'C6'), (5, 1, 'E6'), (6, .5, 'C6'), (6.5, .5, 'B5'), (7, 1, 'A5')], 'lead'),
	(B_TROUBLE, B_TRIUMPH, ['Am', 'F', 'Dm', 'E'], [(0, .25, 'A4'), (.5, .25, 'C5'), (1, .25, 'E5'), (1.5, .25, 'C5'), (2, .25, 'A4'), (3, .25, 'G#4'),
		(4, .25, 'F4'), (4.5, .25, 'A4'), (5, .25, 'C5'), (5.5, .25, 'A4'), (6, .25, 'F4'), (7, .25, 'E4')], 'pluck'),
	(B_TRIUMPH, B_EVENING, ['F', 'G', 'C', 'Am'], [(0, .5, 'A5'), (.5, .5, 'C6'), (1, 1, 'F6'), (2, .5, 'C6'), (2.5, .5, 'A5'), (3, 1, 'C6'),
		(4, .5, 'B5'), (4.5, .5, 'D6'), (5, 1, 'G6'), (6, .5, 'D6'), (6.5, .5, 'B5'), (7, 1, 'D6')], 'lead'),
	(B_EVENING, B_NIGHT, ['F', 'G'], [(0, .25, 'G5'), (.25, .25, 'C6'), (.5, .5, 'E6'), (1, .25, 'D6'), (1.25, .25, 'C6'), (1.5, .5, 'A5'),
		(2, .5, 'G5'), (2.5, .25, 'B5'), (2.75, .25, 'D6'), (3, 1, 'C6')], 'pluck'),
]


def music(mix: A.Mixer) -> None:
	n, bt, put = A.n, mix.beat, mix.put
	mix.melody([(0, .5, 'E5'), (.5, .5, 'G5'), (1, .5, 'C6'), (1.5, .5, 'G5'), (2, .5, 'A5'), (2.5, .5, 'G5'), (3, 1, 'E5')], 0, 'bell', 0.09)
	for (b0, b1, chords, phrase, inst) in SECTIONS:
		trouble = inst == 'pluck' and b0 == B_TROUBLE
		for b in range(b0, b1):
			ch = CHORDS[chords[((b - b0) // 4) % len(chords)]]
			root, tones = n(ch[0]), [n(x) for x in ch[1:]]
			if trouble:
				if b % 2 == 0:
					put(A.bass(root, 0.16), bt(b), 0.26)
				continue
			for half in (0, 0.5):
				put(A.bass(root if (b * 2 + half * 2) % 2 == 0 else root + 7, 0.2), bt(b + half), 0.24)
			put(A.pluck(tones[b % 3] + 12, 0.16), bt(b + 0.25), 0.035, pan=0.3)
		length = 8 if inst == 'lead' or trouble else 4
		for start in range(b0, b1, length):
			mix.melody([(start + nb, d, nm) for (nb, d, nm) in phrase if start + nb < b1], 0, inst, 0.11)
	A.groove(mix, 4, B_TROUBLE)
	A.groove(mix, B_TROUBLE, B_TRIUMPH - 2, soft=0.35)  # the trouble: a soft beat under a heartbeat
	for b in range(B_TROUBLE, B_TRIUMPH, 4):
		put(A.kick(0.6), bt(b))
	A.roll(mix, B_TRIUMPH - 2, B_TRIUMPH, 0.08, 0.3)
	put(A.crash(0.22), bt(B_TRIUMPH), pan=0.2)
	A.groove(mix, B_TRIUMPH, B_EVENING, hats16=True)
	A.groove(mix, B_EVENING, B_NIGHT, soft=0.8)
	for i, nm in enumerate(['C4', 'E4', 'G4', 'C5', 'E5']):  # the final chord as it gets home
		put(A.lead(n(nm), 1.6, 0.125), T_HOME + 0.01 * i, 0.05, pan=(i - 2) * 0.25)
	put(A.bass(n('C3'), 1.4), T_HOME, 0.24)
	mix.melody([(B_NIGHT + 2, 1, 'E5'), (B_NIGHT + 3, 1, 'D5'), (B_NIGHT + 4, 2, 'C5')], 0, 'bell', 0.08)  # lullaby


def sound_effects(mix: A.Mixer) -> None:
	n, put = A.n, mix.put
	for (t0, _, _, _, _) in STOPS[1:]:  # each new clock pops in
		put(A.click(1.4, 0.6), t0, 0.08, pan=-0.2)
	for h in HOPS:  # the journey
		put(A.boing(), h.t0, 0.13 if h.h > 250 else 0.09)
		put(A.land(), h.t1, 0.22)
	put(A.sweep(300, 700, 0.3, 'sine') * 0.5, 0.2, 0.08)                       # a sleepy stretch at sunrise
	put(A.click(1.6), at('coffee', 2), 0.14, pan=0.4)                         # the mug lands
	put(A.bell(n('G5'), 0.9), at('coffee', 5), 0.07, pan=0.3)                 # a blissful sip
	put(A.click(0.8), at('idea', 2), 0.14)                                    # the bulb appears
	put(A.blip(n('C6')), at('idea', 3), 0.10)                                 # it flickers
	put(A.blip(n('G5')), at('idea', 4), 0.08)
	put(A.twinkle(['C6', 'E6', 'G6', 'C7']), at('idea', 5), 0.12)             # and lights up
	put(A.land(), at('rubber-duck', 3), 0.22, pan=0.4)                        # the duck plops into the pond
	for frame in (5, 8):                                                      # squeak!
		put(A.sweep(1400, 2300, 0.12, duty=0.25), at('rubber-duck', frame), 0.14, pan=0.4)
	put(A.boing(), at('rubber-duck', 6), 0.14)                                # jumps in surprise
	for frame, part in ((2, 'fins'), (4, 'body'), (6, 'nose')):              # the rocket's parts drop in ...
		put(A.sweep(1400, 500, 0.1, 'tri') * 0.6, at('build', frame), 0.07, pan=0.4)
		put(A.click(0.9 if part == 'fins' else 1.1 if part == 'body' else 1.3, 1.0), at('build', frame + 1), 0.22, pan=0.4)  # ... click!
	put(A.land(), at('build', 3), 0.16, pan=0.4)
	put(A.blip(n('E6'), 0.06), at('build', 5), 0.06, pan=0.4)
	put(A.blip(n('G6'), 0.08), at('build', 7), 0.07, pan=0.4)
	put(A.sweep(500, 1200, 0.18, 'sine'), at('build', 8), 0.10, pan=0.4)    # the window lights up
	put(A.boing(), at('build', 9), 0.12)                                      # a hop for joy
	put(A.twinkle(['C6', 'E6', 'G6', 'C7']), at('build', 11), 0.11, pan=0.3)  # ta-da!
	put(A.sweep(300, 1500, 0.08, 'sine'), at('build', 14), 0.10, pan=0.4)   # pop
	put(A.twinkle(['G6', 'C7', 'E7']), at('build', 15), 0.06, pan=0.4)
	for frame in (2, 3):                                                      # the bug scuttles in
		put(A.click(1.8, 0.5), at('debug', frame), 0.10, pan=0.6)
	put(A.blip(n('E6'), 0.1), at('debug', 4), 0.10, pan=0.5)                  # "!": it spots the bug
	put(A.whoosh(0.25), at('debug', 5), 0.18)                                 # hammer back
	put(A.bonk(), at('debug', 6), 0.40, pan=0.3)                              # bonk: the one big hit
	put(A.twinkle(['E6', 'G6', 'C7']), at('debug', 10), 0.12)                 # fixed
	put(A.whoosh(0.4), at('zapped', 2), 0.14)                                 # the cloud rolls in
	for k in range(10):                                                       # rain
		put(A.noise_burst(0.05, 5000, 60), at('zapped', 3) + k * 0.04, 0.05, pan=float(A.rng().uniform(-0.5, 0.5)))
	put(A.noise_burst(0.35, 150, 9), at('zapped', 6), 0.34)                  # lightning strikes
	put(A.crash(0.25), at('zapped', 6), pan=-0.1)
	put(A.sweep(95, 120, 0.3, duty=0.5), at('zapped', 7), 0.10)              # electrified buzz
	put(A.noise_burst(0.3, 1500, 8), at('zapped', 11), 0.12)                 # a puff of smoke
	put(A.boing(), at('lgtm', 4), 0.12)                                       # a happy hop ...
	put(A.blip(n('C6'), 0.06), at('lgtm', 4), 0.10)                          # ... the check pops in ...
	put(A.bell(n('G6'), 0.8), at('lgtm', 5), 0.10)                            # ... ding: merged
	put(A.land(), at('lgtm', 6), 0.16)                                        # lands
	put(A.twinkle(['C7', 'E7', 'G7']), at('lgtm', 8), 0.09)
	put(A.noise_burst(0.5, 90, 3), at('ship-it', 3), 0.16, pan=0.4)          # engines rumble
	put(A.sweep(200, 1600, 0.6, curve=2.0), at('ship-it', 5), 0.12, pan=0.4)  # lift-off
	put(A.twinkle(['E6', 'G6', 'C7']), at('ship-it', 2), 0.06, pan=0.4)      # the rocket it built is back
	put(A.whoosh(0.35), at('ship-it', 6), 0.16, pan=0.4)
	put(A.land(), at('cowboy', 3), 0.20)                                      # hat on
	for frame in (4, 6, 8):                                                   # lasso twirls
		put(A.whoosh(0.15), at('cowboy', frame), 0.08, pan=0.4)
	put(A.noise_burst(0.06, 3000, 40), at('cowboy', 9), 0.22, pan=0.5)       # crack!
	put(A.click(1.2), at('cowboy', 12), 0.12)                                 # tips the hat
	for k, word in enumerate(END_WORDS):                                      # the end title lands
		for i in range(len(word.text)):
			put(A.blip(n(['C6', 'D6', 'E6', 'G6', 'A6', 'C7', 'D7'][i]), 0.04), T_END + 0.35 * k + 0.07 * i + 0.14, 0.05)


def score(mix: A.Mixer) -> None:
	music(mix)
	sound_effects(mix)
