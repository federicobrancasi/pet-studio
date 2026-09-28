"""A day in the life of the VS Code pet: a 30-second vertical (9:16) reel told with the moves in moves/.

Eleven beats, one move each, from the morning coffee to logging off, then the pet falls asleep
on the chat input. It shows how to build a reel from ready-made moves:

* ``moves.use(name)`` for each move, then ``P.frame_at(name, ms, loop=False)`` plays it once;
* a schedule that starts every move on the musical grid after the previous one has settled;
* captions and the pet inside ``layout.safe_area``, clear of the apps' buttons and captions;
* the pet at ``scale=3`` for a phone close-up, and sound effects on the moves' own frames.

    python3 -m kit film sheet pet-day
    python3 -m kit film review pet-day
"""

from __future__ import annotations

import math

from PIL import Image

from kit import fx, layout, moves, motion, world
from kit import audio as A
from kit import pet as P
from kit.pet import PetPose

TITLE = 'A day in the life of the VS Code pet'
W, H = SIZE = (1080, 1920)  # 9:16 for Reels, TikTok, Shorts and X
FPS = 60
DURATION = 30.5  # the end card holds for 2 s once its title has popped in
SAFE = layout.safe_area(SIZE)  # (60, 260, 960, 1600)
SAFE_X = (SAFE[0] + SAFE[2]) // 2
SAFE_W = SAFE[2] - SAFE[0]
SCALE = 3  # a close-up: the pet is 288 px tall, and a 24-pixel move is 576 px wide

# --------------------------------------------------------------------------------------------
# The day: (clock, caption, move), one beat each

DAY = [
	('09:00', 'coffee first', 'coffee'),
	('09:30', 'a wild idea', 'idea'),
	('10:00', 'rubber ducking', 'rubber-duck'),
	('11:00', 'found the bug', 'debug'),
	('12:00', 'merge conflict', 'zapped'),
	('12:01', 'still conflicts', 'angry'),
	('14:00', 'it works?!', 'magic'),
	('16:00', 'ship it', 'ship-it'),
	('16:01', 'all tests pass', 'trophy'),
	('17:00', 'PR approved', 'yes'),
	('18:00', 'logging off', 'cowboy'),
]
for _, _, _name in DAY:
	moves.use(_name)

T_FIRST = 2.0  # the hook holds for one bar
GRID = 0.25    # moves start on sixteenth notes at 120 BPM
GAP = 0.1      # at least this much idle between two moves


def _schedule() -> tuple[list, float]:
	beats, t = [], T_FIRST
	for clock, caption, name in DAY:
		beats.append((t, clock, caption, name))
		t = math.ceil((t + P.total_ms(name) / 1000 + GAP) / GRID - 1e-9) * GRID
	return beats, t


BEATS, T_END_CARD = _schedule()  # [(t0, clock, caption, move), ...]; the end card is at 27.75 s
START = {name: t0 for (t0, _, _, name) in BEATS}
T_ASLEEP = T_END_CARD + P.total_ms('waking') / 1000  # dozing off plays the waking animation backwards



def at(name: str, frame: int) -> float:
	"""When frame ``frame`` (1-based, as in move.txt) of a beat's move starts."""
	return START[name] + sum(P.durations(name)[:frame - 1]) / 1000


# Each beat is reviewed at its move's key frame (the one shown for reduced motion).
CUES = [
	(0.0, 'hook: a day in the life'),
	*((at(name, moves.load(name).still_index() + 1) + 0.03, f'{clock} {name}') for (_, clock, _, name) in BEATS),
	(T_ASLEEP + 0.5, 'end card, the pet dozes off'),
]


# --------------------------------------------------------------------------------------------
# Picture

PET_X, GROUND = 420, 1300  # left of center: props grow to the right and stay in the safe area
INPUT_X0, INPUT_X1 = SAFE[0] + 30, SAFE[2] - 30
BLINKS = [0.75, 1.55]
CITY = world.CodeCity(SIZE, world_width=1400, seed=4)
CAPTION_TOP = SAFE[1] + 40
CAPTION_BOX = (SAFE[0], SAFE[1], SAFE[2], SAFE[1] + 460)  # no stars or clouds behind the words


def beat_at(t: float) -> tuple | None:
	for beat in reversed(BEATS):
		if t >= beat[0]:
			return beat
	return None


def hero_pose(t: float) -> PetPose:
	beat = beat_at(t)
	if beat is not None and t < T_END_CARD:
		t0, _, _, name = beat
		ms = (t - t0) * 1000
		if ms < P.total_ms(name):
			return PetPose(name, P.frame_at(name, ms, loop=False), PET_X, GROUND, scale=SCALE)
	if t >= T_END_CARD:
		if t < T_ASLEEP:  # the waking animation, backwards: it nods off
			ms = (T_ASLEEP - t) * 1000
			return PetPose('waking', P.frame_at('waking', ms - 1, loop=False), PET_X, GROUND, scale=SCALE)
		return PetPose('sleep', P.frame_at('sleep', (t - T_ASLEEP) * 1000), PET_X, GROUND, scale=SCALE)
	gaze = (0, -4) if 0.9 <= t < T_FIRST - 0.15 else (0, 0)  # reads the hook, then faces the day
	return PetPose('idleTracking', P.frame_at('idle', t * 1000), PET_X, GROUND, gaze=gaze, blink=motion.blinking(t, BLINKS), scale=SCALE)


def caption(img: Image.Image, t: float) -> None:
	if t < T_FIRST:  # whole from the first frame: it's the thumbnail
		world.title_block(img, 'a day in the life', CAPTION_TOP, 'of the VS Code pet', center_x=SAFE_X, max_width=SAFE_W)
	elif t < T_END_CARD:
		t0, clock, text, _ = beat_at(t)
		world.title_block(img, clock, CAPTION_TOP, text, center_x=SAFE_X, max_width=SAFE_W, t=t, t0=t0, subtitle_delay=0.12)
	else:
		world.title_block(img, 'Happy coding!', CAPTION_TOP, center_x=SAFE_X, max_width=SAFE_W, t=t, t0=T_END_CARD)


def render(t: float) -> Image.Image:
	img = Image.new('RGBA', SIZE)
	CITY.draw(img, t, int(t * 14), 0, clouds_fade=1.0, clouds_fade_above=CAPTION_BOX[3], keep_clear=CAPTION_BOX)  # the city drifts by as the day goes
	world.chat_input(img, t, INPUT_X0, INPUT_X1, GROUND, 0, 0)
	P.draw_pose(img, hero_pose(t))
	if t >= T_ASLEEP:
		fx.zzz(img, t - T_ASLEEP, PET_X + 170, GROUND - 250, 0, 0)
	caption(img, t)
	return img


# --------------------------------------------------------------------------------------------
# Score: 120 BPM, so one beat = 0.5 s and one bar = 2 s. Morning, trouble, triumph, evening.

CHORDS = {
	'C': ['C3', 'E4', 'G4', 'C5'], 'Am': ['A2', 'C4', 'E4', 'A4'], 'F': ['F2', 'A3', 'C4', 'F4'],
	'G': ['G2', 'B3', 'D4', 'G4'], 'Dm': ['D3', 'F3', 'A3', 'D4'], 'E': ['E2', 'G#3', 'B3', 'E4'],
}
PROGRESSION = [  # (start beat, length in beats, chord)
	(0, 4, 'C'),
	(4, 4, 'C'), (8, 4, 'Am'), (12, 4, 'F'), (16, 4, 'G'),       # morning: coffee, idea, duck
	(20, 4, 'Am'), (24, 4, 'F'), (28, 4, 'Dm'), (32, 4, 'E'),    # trouble: bug, conflict, GRR
	(36, 4, 'F'), (40, 4, 'G'), (44, 4, 'C'), (48, 3, 'Am'),     # it works: magic, ship it, trophy, yes
	(51, 2, 'F'), (53, 2, 'G'),                                   # evening: yeehaw
	(55, 5, 'C'),                                                 # end card
]
MORNING = [
	(4, .5, 'E5'), (4.5, .5, 'G5'), (5, 1, 'C6'), (6, .5, 'G5'), (6.5, .5, 'E5'), (7, 1, 'G5'),
	(8, .5, 'A5'), (8.5, .5, 'C6'), (9, 1, 'E6'), (10, .5, 'C6'), (10.5, .5, 'B5'), (11, 1, 'A5'),
	(12, .5, 'F5'), (12.5, .5, 'A5'), (13, 1, 'C6'), (14, .5, 'A5'), (14.5, .5, 'G5'), (15, 1, 'F5'),
	(16, .5, 'D5'), (16.5, .5, 'G5'), (17, 1, 'B5'), (18, .5, 'D6'), (18.5, .5, 'B5'), (19, 1, 'G5'),
]
TROUBLE = [  # a minor-key tiptoe
	(20, .25, 'A4'), (20.5, .25, 'C5'), (21, .25, 'E5'), (21.5, .25, 'C5'), (22, .25, 'A4'), (23, .25, 'G#4'),
	(24, .25, 'F4'), (24.5, .25, 'A4'), (25, .25, 'C5'), (25.5, .25, 'A4'), (26, .25, 'F4'), (27, .25, 'E4'),
	(28, .25, 'D4'), (28.5, .25, 'F4'), (29, .25, 'A4'), (29.5, .25, 'F4'), (30, .25, 'D4'), (31, .25, 'E4'),
	(32, .25, 'E4'), (32.5, .25, 'G#4'), (33, .25, 'B4'), (33.5, .25, 'D5'), (34, .5, 'E5'), (35, .5, 'G#5'),
]
TRIUMPH = [
	(36, .5, 'A5'), (36.5, .5, 'C6'), (37, 1, 'F6'), (38, .5, 'C6'), (38.5, .5, 'A5'), (39, 1, 'C6'),
	(40, .5, 'B5'), (40.5, .5, 'D6'), (41, 1, 'G6'), (42, .5, 'D6'), (42.5, .5, 'B5'), (43, 1, 'D6'),
	(44, .5, 'C6'), (44.5, .5, 'E6'), (45, 1, 'G6'), (46, .5, 'E6'), (46.5, .5, 'D6'),
]
FANFARE = [(47, .25, 'C6'), (47.25, .25, 'C6'), (47.5, .25, 'C6'), (47.75, 1.25, 'E6'), (49, .5, 'D6'), (49.5, .5, 'E6'), (50, 1, 'G6')]  # PR approved
YEEHAW = [(51, .25, 'G5'), (51.25, .25, 'C6'), (51.5, .5, 'E6'), (52, .25, 'D6'), (52.25, .25, 'C6'), (52.5, .5, 'A5'), (53, .5, 'G5'), (53.5, .25, 'B5'), (53.75, .25, 'D6'), (54, 1, 'C6')]
LULLABY = [(56.5, 1, 'E5'), (57.5, 1, 'D5'), (58.5, 1.5, 'C5')]


def music(mix: A.Mixer) -> None:
	n, bt, put = A.n, mix.beat, mix.put
	for (b0, length, ch) in PROGRESSION:  # bass and soft arpeggios from the chords
		root = n(CHORDS[ch][0])
		tones = [n(x) for x in CHORDS[ch][1:]]
		intro, trouble, final = b0 < 4, 20 <= b0 < 36, b0 >= 55
		if intro or final:
			continue
		for k in range(int(length * 2)):
			if trouble:
				if k % 2 == 0:
					put(A.bass(root, 0.16), bt(b0 + k * 0.5), 0.26)
				continue
			put(A.bass(root if k % 2 == 0 else root + 7, 0.2), bt(b0 + k * 0.5), 0.25)
			put(A.pluck(tones[(k + 1) % 3] + 12, 0.16), bt(b0 + k * 0.5 + 0.25), 0.035, pan=0.3)
	mix.melody([(0, .5, 'E5'), (.5, .5, 'G5'), (1, .5, 'C6'), (1.5, .5, 'G5'), (2, .5, 'A5'), (2.5, .5, 'G5'), (3, 1, 'E5')], 0, 'bell', 0.09)
	mix.melody(MORNING, 0, 'lead', 0.11)
	mix.melody(TROUBLE, 0, 'pluck', 0.11)
	mix.melody(TRIUMPH, 0, 'lead', 0.12)
	mix.melody(FANFARE, 0, 'lead', 0.15)
	mix.melody([(b, length, x[:-1] + str(int(x[-1]) - 1)) for (b, length, x) in FANFARE], 0, 'lead', 0.07, pan=0.2)
	mix.melody(YEEHAW, 0, 'pluck', 0.12)
	mix.melody(LULLABY, 0, 'bell', 0.08)
	for i, nm in enumerate(['C4', 'E4', 'G4', 'C5', 'E5']):  # final chord on the end card
		put(A.lead(n(nm), 1.6, 0.125), T_END_CARD + 0.01 * i, 0.05, pan=(i - 2) * 0.25)
	put(A.bass(n('C3'), 1.4), T_END_CARD, 0.24)
	# drums: a groove in the morning, a heartbeat for the trouble, then the groove again
	A.groove(mix, 4, 20)
	for b in (20, 24, 28, 32):
		put(A.kick(0.6), bt(b))
	A.roll(mix, 34, 36, 0.08, 0.3)
	put(A.crash(0.22), bt(36), pan=0.2)
	A.groove(mix, 36, 44)
	A.groove(mix, 44, 51, hats16=True)
	A.groove(mix, 51, 55, soft=0.8)


def sound_effects(mix: A.Mixer) -> None:
	n, put = A.n, mix.put
	for (t0, _, _, _) in BEATS:  # each new clock pops in
		put(A.click(1.4, 0.6), t0, 0.08, pan=-0.2)
	put(A.click(1.6), at('coffee', 2), 0.14, pan=0.4)                         # the mug lands
	put(A.bell(n('G5'), 0.9), at('coffee', 5), 0.07, pan=0.3)                 # a blissful sip
	put(A.click(0.8), at('idea', 2), 0.14)                                    # the bulb appears
	put(A.blip(n('C6')), at('idea', 3), 0.10)                                 # it flickers
	put(A.blip(n('G5')), at('idea', 4), 0.08)
	put(A.twinkle(['C6', 'E6', 'G6', 'C7']), at('idea', 5), 0.12)             # and lights up
	put(A.land(), at('rubber-duck', 3), 0.22, pan=0.4)                        # the duck plops down
	for frame in (5, 8):                                                      # squeak!
		put(A.sweep(1400, 2300, 0.12, duty=0.25), at('rubber-duck', frame), 0.14, pan=0.4)
	put(A.boing(), at('rubber-duck', 6), 0.14)                                # jumps in surprise
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
	put(A.sweep(140, 90, 0.4, duty=0.5), at('angry', 3), 0.14)               # the anger rises
	for frame in (5, 6):                                                      # steam
		put(A.noise_burst(0.3, 6000, 7), at('angry', frame), 0.10, pan=-0.3 if frame == 5 else 0.3)
	put(A.lead(n('E3'), 0.45, 0.5, vib=0.03), at('angry', 7), 0.16)         # GRR!
	put(A.snare(0.5), at('angry', 7))
	put(A.sweep(400, 1300, 0.25, 'tri'), at('magic', 2), 0.10)               # the wand goes up
	put(A.whoosh(0.2), at('magic', 4), 0.16)                                  # swish
	put(A.twinkle(['C6', 'E6', 'G6', 'B6', 'D7']), at('magic', 5), 0.13)     # stars
	put(A.noise_burst(0.5, 90, 3), at('ship-it', 3), 0.16, pan=0.4)          # engines rumble
	put(A.sweep(200, 1600, 0.6, curve=2.0), at('ship-it', 5), 0.12, pan=0.4)  # lift-off
	put(A.whoosh(0.35), at('ship-it', 6), 0.16, pan=0.4)
	put(A.sweep(300, 900, 0.3, 'tri'), at('trophy', 2), 0.10, pan=0.4)       # the trophy rises
	put(A.coin(), at('trophy', 5), 0.16, pan=0.4)                             # shine
	put(A.twinkle(['G6', 'C7', 'E7']), at('trophy', 7), 0.10, pan=0.4)
	put(A.blip(n('C6')), at('yes', 3), 0.10)                                  # the small YES!
	put(A.crash(0.2), at('yes', 4), pan=0.1)                                  # the big one
	put(A.land(), at('cowboy', 3), 0.20)                                      # hat on
	for frame in (4, 6, 8):                                                   # lasso twirls
		put(A.whoosh(0.15), at('cowboy', frame), 0.08, pan=0.4)
	put(A.noise_burst(0.06, 3000, 40), at('cowboy', 9), 0.22, pan=0.5)       # crack!
	put(A.click(1.2), at('cowboy', 12), 0.12)                                 # tips the hat


def score(mix: A.Mixer) -> None:
	music(mix)
	sound_effects(mix)
