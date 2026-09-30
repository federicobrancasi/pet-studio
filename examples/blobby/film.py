"""blobby: the VS Code pet's name reveal, a 15 s vertical (9:16) reel.

The community named the pet. A golden envelope with the winning name drifts down to the pet, a
gust steals it, and the pet chases it up a sunset sky from cloud to cloud (with one jelly splat
it bounces back from). A spring cloud launches it into dusk, it catches the envelope, and BLOBBY
bursts out. It hops along its new name, one note per letter, a panel credits everyone who sent
the name in (NAMED BY YOU!, with the prize and a note that the winners will be contacted), it
says hello in a close-up, and the end card shows everything at once.

It shows how to make a reveal: a chase up a world taller than the screen with a camera that
follows (blobby_world.py), a prop that keeps getting away, a flash that bursts into a
bubble-letter logo drawn on a character grid (blobby_props.py), hops that land on the beat and
play one note per letter, a 2x close-up cropped from the same frame, and an end card that pulls
back.

    python3 -m kit film sheet blobby
    python3 -m kit film review blobby

Everything in the chase is in world coordinates (y grows downward, the camera climbs), the
reveal is in screen coordinates, and the close-up is a 2x nearest-neighbor crop of the reveal.
Text, faces and the action stay inside ``SAFE``.
"""

from __future__ import annotations

import dataclasses
import math
import random

from PIL import Image

import blobby_props as BP
import blobby_world as BW
from kit import audio as A
from kit import art, fx, layout, moves, motion
from kit import pet as P
from kit.draw import blit, catmull, clamp, ease_out, ease_out_back, fill_rect, hexc, seg, smooth, snap
from kit.font import text_width
from kit.motion import Hop
from kit.pet import PetPose

TITLE = 'Blobby: the name reveal'
W, H = SIZE = (1080, 1920)  # 9:16 vertical
FPS = 60
BPM = 120  # a beat is 0.5 s, a bar is 2 s
DURATION = 15.0
MASTER = {'fade_out': 0.5}
SAFE = layout.safe_area(SIZE)  # (60, 260, 960, 1600)
SAFE_X = (SAFE[0] + SAFE[2]) // 2

moves.use('wave')

# --------------------------------------------------------------------------------------------
# Words: change them here

NAME = 'BLOBBY'
HOOK = ('YOU NAMED', 'ME!')
CREDIT = ('NAMED BY', 'YOU!')  # many people sent in the winning name, so the credit names no one
PRIZE = ('PRIZE: 1 MONTH OF', 'GITHUB COPILOT MAX!')
NOTE = "WE'LL REACH OUT!"  # to the winners
HELLO = "HI, I'M BLOBBY!"

# --------------------------------------------------------------------------------------------
# Timeline (seconds). Big moments sit on beats: the first landing on bar 2, the reveal on bar 4.

T_WIGGLE = 0.45               # a little excited hop as the envelope drifts down
T_GUST = 1.0                  # the wind snatches the envelope (and blows the caption away)
T_H1 = (1.5, 2.0)             # hill -> first cloud
T_LUNGE = (2.4, 2.95)         # a leap at the envelope ...
T_DODGE = 2.54                # ... which zips away just before the pet reaches it
T_FLAIL = 2.64                # from here the pet flails down
T_SPLAT = T_LUNGE[1]          # jelly splat on the second cloud
T_BACK = T_SPLAT + P.total_ms('splat') / 1000  # back in shape
T_H3 = (3.62, 4.0)            # to the spring cloud
T_LAUNCH = 4.2                # the spring cloud fires it upward
T_CATCH = 5.25                # it snags the envelope at the top of the leap
T_REVEAL = 6.0                # flash: the envelope bursts and the name comes out
T_LETTER_STEP = 0.05          # the letters fly out one after another
T_LETTER_FLIGHT = 0.16
LETTER_LANDS = [6.5 + 0.5 * i for i in range(len(NAME))]  # the pet lands on each letter on a beat
T_JOY = (LETTER_LANDS[-1] + 0.1, LETTER_LANDS[-1] + 0.6)   # a big happy jump to the middle
T_CREDIT = 9.5
T_PRIZE = 9.95
T_CLOSEUP = 12.5
T_TALK = 12.62                # it says its name: the bubble types in over four babble syllables
SYLLABLES = [T_TALK + d for d in (0.0, 0.14, 0.3, 0.48)]
T_WAVE = 13.25
T_PULLBACK = 14.0             # cut back to the whole name for the end card (and the loop point)
T_BYE = 14.1                  # a second wave, goodbye

CUES = [
	(0.0, 'hook: YOU NAMED ME! and the envelope'),
	(T_GUST, 'a gust steals the envelope'),
	(T_H1[0], 'chase: hop to a cloud'),
	(T_DODGE, 'lunge; the envelope dodges'),
	(T_SPLAT, 'jelly splat'),
	(T_H3[0], 'hop to the spring cloud'),
	(T_LAUNCH, 'spring launch'),
	(T_CATCH, 'catch'),
	(T_REVEAL, 'reveal: BLOBBY'),
	(LETTER_LANDS[0], 'letter hop'),
	(T_JOY[0], 'joy jump'),
	(T_CREDIT, 'credit'),
	(T_CLOSEUP, "close-up: HI, I'M BLOBBY!"),
	(T_WAVE, 'wave'),
	(T_PULLBACK, 'end card: the whole name, the credit and the hello'),
]

# --------------------------------------------------------------------------------------------
# The chase (world coordinates, pet at scale 3)

CHASE_SCALE = 3
HEAD = 96 * CHASE_SCALE  # the pet's height, antennae included
ENV_CELL = 16  # the envelope is almost as wide as the pet, so it reads on a phone
START = (380, BW.GROUND_Y)
C1 = BW.Platform(730, 1060, 36, 14, 7, BW.CLOUD_WARM)
C2 = BW.Platform(330, 800, 34, 14, 12, BW.CLOUD_PINK)
SPRING = BW.Platform(690, 520, 30, 13, 19, BW.CLOUD_SPRING)
CATCH = (540, -700)
SPRING_ROWS = [(T_H3[1], 12), (T_H3[1] + 0.06, 11), (T_H3[1] + 0.12, 9), (T_LAUNCH, 15), (T_LAUNCH + 0.07, 14), (T_LAUNCH + 0.14, 13)]

WIGGLE = Hop(T_WIGGLE, T_WIGGLE + 0.3, *START, *START, 70)
H1 = Hop(*T_H1, *START, C1.x, C1.top, 300)
LUNGE = Hop(*T_LUNGE, C1.x, C1.top, C2.x, C2.top, 380, recover=False)
H3 = Hop(*T_H3, C2.x, C2.top, SPRING.x, SPRING.top, 250, recover=False)
CHASE_HOPS = [WIGGLE, H1, H3]
BLINKS = [0.25, 3.55, 9.9, 11.4, 12.25, 14.2]

# The envelope's flight: (t, x, y) keys through a Catmull-Rom spline.
ENVELOPE_KEYS = [
	(0.0, 520, 760), (0.5, 470, 930), (0.95, 440, 1080),
	(1.2, 640, 880), (1.5, 810, 690), (2.0, 720, 540), (2.45, 560, 350),
	(T_DODGE, 520, 300), (T_DODGE + 0.14, 690, 130), (3.0, 700, 40), (3.55, 640, -60),
	(4.2, 610, -420), (4.8, 560, -840), (T_CATCH, CATCH[0], CATCH[1] - HEAD - 40),
]


def spring_rows(t: float) -> int:
	rows = SPRING.rows
	for (tk, r) in SPRING_ROWS:
		if t >= tk:
			rows = r
	return rows


def launch_y(t: float) -> float:
	"""The rise from the spring cloud: fast off the cloud, slowing to a stop at the catch."""
	u = seg(t, T_LAUNCH, T_CATCH)
	y0 = SPRING.surface(SPRING_ROWS[3][1] - 2)
	return y0 + (CATCH[1] - y0) * (1 - (1 - u) ** 2)


def launch_x(t: float) -> float:
	return SPRING.x + (CATCH[0] - SPRING.x) * smooth(seg(t, T_LAUNCH, T_CATCH))


def hang(t: float) -> tuple:
	"""Where the pet dangles below the envelope after the catch (a tiny hit pause first)."""
	dt = max(0.0, t - T_CATCH - 0.08)
	return CATCH[0] + math.sin(dt * 7) * 10, CATCH[1] - 30 * seg(dt, 0, 0.6) + math.sin(dt * 11) * 4


def envelope_pos(t: float) -> tuple:
	if t >= T_CATCH:
		x, y = hang(t)
		k = seg(t, T_CATCH + 0.1, T_REVEAL)
		jit = 3 + 9 * k * k
		return x + math.sin(t * 91) * jit, y - HEAD - 40 + math.cos(t * 77) * jit * 0.5
	if t < T_GUST:
		x, y = catmull(ENVELOPE_KEYS, t)
		return x + math.sin(t * 5) * 18, y
	return catmull(ENVELOPE_KEYS, t)


def envelope_frame(t: float) -> str:
	if t >= T_CATCH:
		return 'front'
	if t < T_GUST:
		return ['front', 'tilt_l', 'front', 'tilt_r'][int(t / 0.2) % 4]
	return BP.FLUTTER[int((t - T_GUST) / 0.07) % len(BP.FLUTTER)]


def gaze_at(px: float, py: float, tx: float, ty: float, facing: str) -> tuple:
	gx = clamp((tx - px) / 60, -4, 4)
	gy = clamp((ty - py) / 60, -4, 4)
	return (round(-gx if facing == 'left' else gx), round(gy))


def chase_pose(t: float) -> PetPose:
	ex, ey = envelope_pos(t)
	blink = motion.blinking(t, BLINKS)
	if t >= T_CATCH:  # dangling from the envelope
		x, y = hang(t)
		return PetPose('falling', P.frame_at('falling', (t - T_CATCH) * 700), x, y, 'right', scale=CHASE_SCALE)
	if t >= T_LAUNCH:
		x, y = launch_x(t), launch_y(t)
		if t < T_LAUNCH + 0.12:
			return PetPose('jump', 2, x, y, 'left', scale=CHASE_SCALE)
		if t < T_CATCH - 0.22:
			return PetPose('jump', 3, x, y, 'left', air_offset=P.AIRBORNE_OFFSET, scale=CHASE_SCALE)
		return PetPose('falling', 0, x, y, 'left', scale=CHASE_SCALE)  # antennae up, reaching
	if T_H3[1] <= t < T_LAUNCH:  # riding the spring cloud down
		y = SPRING.surface(spring_rows(t))
		return PetPose('jump', 4 if t < T_H3[1] + 0.1 else 1, SPRING.x, y, 'left', scale=CHASE_SCALE)
	if T_LUNGE[0] - LUNGE.crouch <= t < T_SPLAT:
		if t >= T_FLAIL:
			x, y = LUNGE.pos(t)
			return PetPose('falling', P.frame_at('falling', (t - T_FLAIL) * 1000), x, y, 'left', scale=CHASE_SCALE)
		return dataclasses.replace(motion.hop_pose([LUNGE], t, facing='left'), scale=CHASE_SCALE)
	if T_SPLAT <= t < T_BACK - 0.2:
		return PetPose('splat', P.frame_at('splat', (t - T_SPLAT) * 1000, loop=False), C2.x, C2.surface() + BW.dip(t, [T_SPLAT], 18), 'left', scale=CHASE_SCALE)
	facing = 'right' if t < T_H1[1] + 0.05 or T_BACK - 0.2 <= t else 'left'
	hop = motion.hop_pose(CHASE_HOPS, t, facing=facing)
	if hop is not None:
		pose = dataclasses.replace(hop, scale=CHASE_SCALE)
		if hop.name == 'jump' and hop.frame in (4, 5) and hop.y == C1.top:
			pose = dataclasses.replace(pose, y=C1.top + BW.dip(t, [T_H1[1]]))
		return pose
	if t < T_H1[0]:
		x, y = START
	elif t < T_LUNGE[0]:
		x, y = C1.x, C1.top + BW.dip(t, [T_H1[1]])
	else:
		x, y = C2.x, C2.top
	return PetPose('idleTracking', P.frame_at('idle', t * 1000), x, y, facing, gaze=gaze_at(x, y - HEAD * 0.55, ex, ey, facing), blink=blink, scale=CHASE_SCALE)


def camera_target(t: float) -> tuple:
	if t < T_H1[0] - 0.15:
		y = 0.0
	elif t < T_LUNGE[0] - 0.1:
		y = C1.top - 1360
	elif t < T_H3[0] - 0.1:
		y = C2.top - 1360
	elif t < T_LAUNCH - 0.05:
		y = SPRING.top - 1360
	else:
		y = launch_y(min(T_CATCH, t + 0.15)) - 1150
	return 0.0, y


CAMERA = motion.FollowCamera(camera_target, T_REVEAL + 0.05, FPS, omega=(5.0, 5.5))
CHASE_LANDINGS = [(T_H1[1], C1.x, C1.top), (T_SPLAT, C2.x, C2.top), (T_H3[1], SPRING.x, SPRING.top)]


def draw_hook(img: Image.Image, t: float) -> None:
	"""The two-line hook, whole from the first frame; the gust blows it away letter by letter."""
	y = SAFE[1] + 40
	i = 0
	for line, px, color in ((HOOK[0], 16, BP.WHITE), (HOOK[1], 16, BP.GOLD)):
		x0 = snap(SAFE_X - text_width(line, px) / 2, 2)
		for j, ch in enumerate(line):
			k = seg(t, T_GUST + 0.02 * i, T_GUST + 0.02 * i + 0.5)
			i += 1
			if ch == ' ' or k >= 1:
				continue
			dx, dy = 1500 * k * k, -700 * k * k + math.sin(k * 9 + j) * 30 * k
			BP.outlined_text(img, ch, snap(x0 + j * 6 * px + dx, 2), snap(y + dy, 2), px, color)
		y += 9 * px + 24


def render_chase(t: float) -> Image.Image:
	img = Image.new('RGBA', SIZE)
	cy = int(round(CAMERA.at(min(t, T_CATCH + 0.08) if T_CATCH <= t < T_CATCH + 0.08 else t)[1]))
	BW.draw_chase_backdrop(img, t, 0, cy)
	C1.draw(img, 0, cy, dip=BW.dip(t, [T_H1[1]]))
	C2.draw(img, 0, cy, dip=BW.dip(t, [T_SPLAT], 18))
	SPRING.draw(img, 0, cy, rows=spring_rows(t))
	BW.butterfly(img, t, 0, cy, T_GUST)
	pose = chase_pose(t)
	grounded = pose.name in ('idleTracking', 'splat') or (pose.name == 'jump' and pose.frame in (1, 4, 5))
	if grounded:
		BW.shadow(img, pose.x, pose.y, 0, cy, 200)
	P.draw_pose(img, pose, 0, cy)
	fx.dust(img, t, CHASE_LANDINGS, 0, cy, color=hexc('#fff4ec'))
	BW.rise_streaks(img, t, T_LAUNCH, T_CATCH, 0, cy)
	ex, ey = envelope_pos(t)
	glow = seg(t, T_CATCH, T_REVEAL) if t >= T_CATCH else 0.0
	BP.draw_envelope(img, ex, ey, 0, cy, envelope_frame(t), ENV_CELL, glow, t)
	BP.sparkle_ring(img, t, T_CATCH, ex, ey, 0, cy, n=10, radius=190, inner=70)
	if t >= T_CATCH + 0.2:  # light leaking out of the envelope as the drumroll builds
		rng = random.Random(int(t * 12))
		for _ in range(2 + int(4 * seg(t, T_CATCH, T_REVEAL))):
			a = rng.uniform(0, math.tau)
			r = rng.uniform(90, 170)
			BP.sparkle(img, ex + math.cos(a) * r, ey + math.sin(a) * r * 0.7 - cy, 10, (255, 240, 170, 230))
	BW.wind(img, t, T_GUST, 0, cy, (430, 1120))
	if T_GUST + 0.02 <= t < T_GUST + 0.55:  # a big "!" above the antennae as the envelope flies off
		bang = art.bang(24)
		lift = int((1 - ease_out_back(seg(t, T_GUST + 0.02, T_GUST + 0.14))) * 3) * 24
		blit(img, bang, START[0] - bang.width // 2, START[1] - HEAD - bang.height - 24 + lift - cy)
	if t < T_GUST + 0.7:
		draw_hook(img, t)
	return img


# --------------------------------------------------------------------------------------------
# The reveal (screen coordinates, pet at scale 2)

LOGO = BP.Logo(NAME, SAFE_X, 1008)
BURST = (510, 520)
LETTER_ARRIVALS = [T_REVEAL + 0.02 + T_LETTER_STEP * i + T_LETTER_FLIGHT for i in range(len(NAME))]
CENTER = (SAFE_X, LOGO.top(2))
FIREWORKS = [(6.25, 250, 440, '#ffd35c'), (6.55, 830, 380, '#ff7eb6'), (6.95, 520, 330, '#7fe0ff'),
	(9.25, 300, 400, '#ffd35c'), (9.5, 790, 360, '#b7f171')]
CONFETTI = [
	(T_REVEAL, fx.confetti_burst(1, BURST[0], BURST[1] + 40, 70, 1.5)),
	(T_REVEAL + 0.03, fx.confetti_burst(2, 110, 1560, 36, 0.45)),
	(T_REVEAL + 0.03, fx.confetti_burst(3, 930, 1560, 36, 0.45)),
	(T_JOY[0], fx.confetti_burst(4, LOGO.centers[-1], 760, 26, 0.9)),
]
LETTER_HOPS = [Hop(LETTER_LANDS[i] + 0.2, LETTER_LANDS[i + 1], LOGO.centers[i], LOGO.top(i), LOGO.centers[i + 1], LOGO.top(i + 1), 110)
	for i in range(len(NAME) - 1)]
ENTRY = Hop(T_REVEAL + 0.04, LETTER_LANDS[0], BURST[0] - 40, BURST[1] + 150, LOGO.centers[0], LOGO.top(0), 150, crouch=0.0)
JOY = Hop(*T_JOY, LOGO.centers[-1], LOGO.top(len(NAME) - 1), CENTER[0], CENTER[1], 300)
WIDE_HOPS = [ENTRY] + LETTER_HOPS + [JOY]


def letter_touches(i: int) -> list:
	"""Times the letter gets hit: when it lands, and whenever the pet lands on it."""
	times = [LETTER_ARRIVALS[i], LETTER_LANDS[i]]
	if i in (2, 3):
		times.append(T_JOY[1])  # the pet lands on the middle two at the end of the joy jump
	return times


def letter_state(i: int, t: float) -> tuple:
	"""(x, baseline, cell size, lit) of letter ``i`` at ``t``; None before it flies out."""
	t_out = T_REVEAL + 0.02 + T_LETTER_STEP * i
	if t < t_out:
		return None
	x1, base1 = LOGO.centers[i], LOGO.baseline
	if t < LETTER_ARRIVALS[i]:
		u = ease_out(seg(t, t_out, LETTER_ARRIVALS[i]))
		x = BURST[0] + (x1 - BURST[0]) * u
		base = BURST[1] + 100 + (base1 - BURST[1] - 100) * u - 160 * math.sin(math.pi * u)
		return x, base, (BP.LOGO_CELL, BP.LOGO_CELL), True
	last = max(tt for tt in letter_touches(i) if tt <= t)
	cell = BP.squash_cell(t - last)
	bob = snap(math.sin((t - 6.5) * 4.4 + i * 0.9) * 5, 2) if t > LETTER_ARRIVALS[-1] + 0.3 else 0
	lit = t - last < 0.22
	return x1, base1 + bob, cell, lit


def letter_top(i: int, t: float) -> float:
	s = letter_state(i, t)
	if s is None:
		return LOGO.top(i)
	x, base, cell, _ = s
	return base - BP.letter_size(NAME[i])[1] * cell[1]


def standing_letter(t: float) -> int | None:
	"""Which letter the pet stands on (the last one it landed on), if any."""
	idx = None
	for i, tl in enumerate(LETTER_LANDS):
		if t >= tl:
			idx = i
	return idx


def wide_pose(t: float) -> PetPose:
	blink = motion.blinking(t, BLINKS)
	hop = motion.hop_pose(WIDE_HOPS, t, facing='right')
	if t >= T_JOY[1] + 0.18:  # in the middle of its name, straddling O and B
		x, y = CENTER[0], min(letter_top(2, t), letter_top(3, t))
		if t >= T_BYE:
			return PetPose('wave', P.frame_at('wave', (t - T_BYE) * 1000, loop=False), x, y, 'right')
		if t >= T_WAVE:
			return PetPose('wave', P.frame_at('wave', (t - T_WAVE) * 1000, loop=False), x, y, 'right')
		if t >= T_TALK:
			# Talking: the pet's own "thinking" state (live eyes, bouncing antennae) with a
			# little squash on every syllable.
			if any(ts <= t < ts + 0.08 for ts in SYLLABLES):
				return PetPose('jump', 1, x, y, 'right')
			return PetPose('rendering', P.frame_at('rendering', (t - T_TALK) * 1000), x, y, 'right', gaze=(0, 0), blink=blink)
		if 9.75 <= t < 11.1 or 11.6 <= t < 12.3:
			return PetPose('clapping', P.frame_at('clapping', (t - 9.75) * 1000), x, y, 'right', gaze=(0, 2), blink=blink)
		return PetPose('idleTracking', P.frame_at('idle', t * 1000), x, y, 'right', gaze=(0, 4) if t < T_CLOSEUP else (0, 0), blink=blink)
	if hop is not None:
		if hop.frame in (4, 5):  # squash and recover ride the letter's own squash
			i = standing_letter(t)
			if i is not None and t < T_JOY[0]:
				hop = dataclasses.replace(hop, y=letter_top(i, t))
			elif t >= T_JOY[1]:
				hop = dataclasses.replace(hop, y=min(letter_top(2, t), letter_top(3, t)))
		return hop
	i = standing_letter(t)
	if i is None:
		return PetPose('falling', 0, ENTRY.x0, ENTRY.y0, 'right')
	gaze = (4, -3) if i < len(NAME) - 1 else (0, -4)
	return PetPose('idleTracking', P.frame_at('idle', t * 1000), LOGO.centers[i], letter_top(i, t), 'right', gaze=gaze, blink=blink)


def paper_bits(img: Image.Image, t: float) -> None:
	"""Gold scraps of the envelope flying out of the burst."""
	dt = t - T_REVEAL
	if not (0 <= dt < 0.9):
		return
	rng = random.Random(3)
	for _ in range(14):
		a = rng.uniform(0, math.tau)
		v = rng.uniform(380, 820)
		x = BURST[0] + math.cos(a) * v * dt
		y = BURST[1] + math.sin(a) * v * dt + 900 * dt * dt
		s = 16 if dt < 0.4 else 8
		fill_rect(img, snap(x, 4), snap(y, 4), s, s, BP.ENV_PAL['Y'] if rng.random() < 0.6 else BP.ENV_PAL['L'])


def logo_sparkles(img: Image.Image, t: float) -> None:
	for k, (i, dx, dy) in enumerate(((0, -40, -150), (2, 30, -170), (5, 20, -150), (3, -30, -60), (1, 40, -40))):
		t0 = LETTER_ARRIVALS[-1] + 0.05 + k * 0.09
		dt = t - t0
		if 0 <= dt < 0.3:
			size = 20 if dt < 0.15 else 12
			BP.sparkle(img, LOGO.centers[i] + dx, LOGO.baseline + dy, size, (255, 255, 255, 255))


def draw_credit(img: Image.Image, t: float) -> None:
	if t < T_CREDIT:
		return
	rise = (1 - ease_out_back(seg(t, T_CREDIT, T_CREDIT + 0.3))) * 360
	top = max(1048, 1072 + snap(rise, 8))  # a small overshoot that never touches the name
	BP.rounded_panel(img, SAFE[0] + 30, top, SAFE[2] - 30, top + 440, (27, 20, 64, 215), BP.GOLD)
	BP.text_centered(img, CREDIT[0], SAFE_X, top + 32, 7, hexc('#d9d0ff'))
	BP.text_centered(img, CREDIT[1], SAFE_X, top + 110, 12, BP.GOLD)
	if t >= T_PRIZE:
		BP.text_centered(img, PRIZE[0], SAFE_X, top + 223, 7, BP.WHITE)
		BP.text_centered(img, PRIZE[1], SAFE_X, top + 288, 7, BP.GOLD)
		BP.text_centered(img, NOTE, SAFE_X, top + 360, 7, hexc('#d9d0ff'))


def render_wide(t: float, closeup: bool = False) -> Image.Image:
	img = Image.new('RGBA', SIZE)
	BW.draw_reveal_backdrop(img, t, seg(t, T_REVEAL, T_REVEAL + 0.4), T_REVEAL)
	fx.fireworks(img, t, FIREWORKS, 0, 0)
	if t < T_REVEAL + 0.1:
		BP.draw_envelope(img, BURST[0], BURST[1], 0, 0, 'open', BW.WIDE_CELL)
	paper_bits(img, t)
	order = sorted(range(len(NAME)), key=lambda i: (letter_state(i, t) or (0, 0, (16, 16)))[2][0])
	for i in order:  # squashed (wider) letters on top of their neighbors
		s = letter_state(i, t)
		if s is not None:
			BP.draw_letter(img, NAME[i], s[0], s[1], s[2], s[3])
	logo_sparkles(img, t)
	fx.floating_hearts(img, t, T_JOY[1] + 0.1, CENTER[0] + 150, CENTER[1] - 150, 0, 0, count=5, every=0.14, life=1.0)
	P.draw_pose(img, wide_pose(t))
	fx.dust(img, t, [(tl, LOGO.centers[i], LOGO.top(i)) for i, tl in enumerate(LETTER_LANDS)], 0, 0, color=hexc('#fff4ec'))
	fx.confetti(img, t, CONFETTI, 0, 0)
	if closeup:
		return img
	draw_credit(img, t)
	if t >= T_PULLBACK:  # the end card keeps the hello; sparkles first, so they pass behind the bubble
		BP.sparkle_ring(img, t, T_PULLBACK, CENTER[0], CENTER[1] - 96, 0, 0, n=10, radius=300, life=0.5, color=(255, 255, 255, 255), inner=150)
		BP.speech_bubble(img, HELLO, SAFE_X, CENTER[1] - 192 - 32, SAFE_X - 40, px=8)
	BP.flash(img, t, T_REVEAL)
	return img


# --------------------------------------------------------------------------------------------
# The close-up: the reveal frame cropped around the pet and doubled, then the speech bubble

CROP = (SAFE_X - 270, 180)


def render_closeup(t: float) -> Image.Image:
	wide = render_wide(t, closeup=True)
	x0, y0 = CROP
	img = wide.crop((x0, y0, x0 + W // 2, y0 + H // 2)).resize(SIZE, Image.NEAREST)
	head_y = (CENTER[1] - 192 - y0) * 2
	if t >= T_WAVE + 0.2:  # hearts first, so they pass behind the bubble
		fx.floating_hearts(img, t, T_WAVE + 0.2, (CENTER[0] - x0) * 2 + 170, head_y + 60, 0, 0, count=4, every=0.18, life=0.9)
	pop = ease_out_back(seg(t, T_TALK - 0.06, T_TALK + 0.12))
	if t >= T_TALK - 0.06:
		bottom = head_y - 70 + snap((1 - pop) * 60, 8)
		BP.speech_bubble(img, HELLO, SAFE_X, bottom, SAFE_X - 40, px=9, reveal=seg(t, T_TALK, SYLLABLES[-1] + 0.1))
	return img


def render(t: float) -> Image.Image:
	if t < T_REVEAL:
		return render_chase(t)
	if T_CLOSEUP <= t < T_PULLBACK:
		return render_closeup(t)
	return render_wide(t)


# --------------------------------------------------------------------------------------------
# Score: C major at 120 BPM. Music first, then the sound effects, all on the timeline above.

LETTER_NOTES = ['E5', 'G5', 'C6', 'E6', 'E6', 'G6']  # the B-L-O-B-B-Y tune the pet plays by hopping
CLAP_TIMES = [t0 + k * 0.68 + off for (t0, t1) in ((9.75, 11.1), (11.6, 12.3)) for k in range(3) for off in (0.2, 0.6) if t0 + k * 0.68 + off < t1]


def music(mix: A.Mixer) -> None:
	n, put, bt = A.n, mix.put, mix.beat
	# Bar 1: a music-box sparkle while the envelope drifts down, over a soft chord.
	for i, nm in enumerate(['C6', 'E6', 'G6', 'C7', 'G6', 'E6']):
		put(A.bell(n(nm), 0.7), 0.05 + i * 0.13, 0.07, pan=(i - 2.5) * 0.15)
	for i, nm in enumerate(['C4', 'E4', 'G4']):
		put(A.lead(n(nm), 1.4, 0.125, 0.006), 0.0, 0.03, pan=(i - 1) * 0.3)
	put(A.bass(n('C3'), 0.9), 0.0, 0.18)
	for i in range(4):  # a snare pickup into the chase
		put(A.snare(0.5 + 0.12 * i), T_H1[0] + 0.25 + i * 0.0625, 0.14)
	# Bars 2-3: the chase groove, until the spring launch takes over with a drumroll.
	A.groove(mix, 4, 8.4, hats16=True)
	for i, nm in enumerate(['C3', 'C3', 'G3', 'C3', 'A2', 'A2', 'E3', 'A2', 'F2']):
		put(A.bass(n(nm), 0.2), bt(4 + i * 0.5), 0.24)
	mix.melody([(4, .5, 'E5'), (4.5, .5, 'G5'), (5, .5, 'A5'), (5.5, .25, 'G5'), (5.75, .25, 'A5')], 0, 'lead', 0.11)
	for i, nm in enumerate(['G4', 'F#4', 'F4', 'E4']):  # the splat: a comic slide down ...
		put(A.lead(n(nm), 0.1 if i < 3 else 0.28, 0.25, 0.01), T_SPLAT + 0.02 + i * 0.1, 0.10)
	mix.melody([(7.0, .25, 'C5'), (7.25, .25, 'E5'), (7.5, .5, 'G5')], 0, 'lead', 0.11)  # ... and back up, determined
	A.roll(mix, 8.4, 12, 0.10, 0.40)
	for i in range(7):  # a bass pedal climbing with the pet
		put(A.bass(n('G2') + i, 0.2), bt(8.5 + i * 0.5), 0.2)
	for i in range(9):  # the envelope shimmers while the pet dangles from it
		put(A.bell(n(['G6', 'A6', 'B6', 'D7'][i % 4]), 0.3), T_CATCH + 0.1 + i * 0.075, 0.035 + 0.004 * i, pan=0.4 * math.sin(i))
	# Bar 4: the reveal fanfare, then the letter hop over a happy groove.
	put(A.crash(0.3), T_REVEAL, 1.0, pan=0.1)
	for i, nm in enumerate(['C4', 'E4', 'G4', 'C5', 'E5']):
		put(A.lead(n(nm), 1.1, 0.25, 0.006), T_REVEAL + 0.005 * i, 0.055, pan=(i - 2) * 0.25)
	put(A.bass(n('C3'), 0.9), T_REVEAL, 0.3)
	A.groove(mix, 13, 19)
	for i, nm in enumerate(['C3', 'C3', 'C3', 'G3', 'F3', 'F3', 'A3', 'F3', 'G3', 'G3', 'B3', 'G3']):
		put(A.bass(n(nm), 0.2), bt(13 + i * 0.5), 0.22)
	for i, tl in enumerate(LETTER_LANDS):
		put(A.bell(n(LETTER_NOTES[i]), 0.7), tl, 0.12, pan=(i - 2.5) * 0.2)
		put(A.lead(n(LETTER_NOTES[i]), 0.22, 0.125), tl, 0.045, pan=(i - 2.5) * 0.2)
	put(A.twinkle(['C7', 'E7', 'G7', 'C8']), T_JOY[0] + 0.05, 0.1)
	# The credit: a softer groove, the B-L-O-B-B-Y tune again on bells.
	A.groove(mix, 19, 25, soft=0.6)
	for i, nm in enumerate(['C3', 'G3', 'A2', 'E3', 'F2', 'C3', 'G2', 'D3', 'C3', 'G3', 'G2', 'B2']):
		put(A.bass(n(nm), 0.22), bt(19 + i * 0.5), 0.18)
	mix.melody([(19.5, .5, 'E5'), (20, .5, 'G5'), (20.5, .5, 'C6'), (21, .5, 'E6'), (21.5, .5, 'E6'), (22, 1.5, 'G6'),
		(23.5, .5, 'E6'), (24, 1, 'D6')], 0, 'bell', 0.075)
	# The close-up: the pet says its name over a light groove, then the final chord lands on the
	# pull-back to the end card.
	A.groove(mix, 25, 28, soft=0.45)
	for i, nm in enumerate(['C3', 'G3', 'F3', 'G3', 'C3', 'G3']):
		put(A.bass(n(nm), 0.2), bt(25 + i * 0.5), 0.16)
	for ts, (nm, d) in zip(SYLLABLES, (('C6', 0.09), ('D6', 0.09), ('G5', 0.14), ('E5', 0.24))):
		put(A.lead(n(nm), d, 0.25, 0.012), ts, 0.10)
	for i, nm in enumerate(['C4', 'E4', 'G4', 'C5']):
		put(A.lead(n(nm), 1.3, 0.125, 0.006), T_PULLBACK + 0.01 * i, 0.05, pan=(i - 1.5) * 0.3)
	for i, nm in enumerate(['C6', 'E6', 'G6', 'C7']):
		put(A.bell(n(nm), 1.0), T_PULLBACK + i * 0.08, 0.06, pan=(i - 1.5) * 0.2)
	put(A.bass(n('C3'), 1.2), T_PULLBACK, 0.22)
	put(A.crash(0.18), T_PULLBACK, 0.5, pan=-0.1)


def sound_effects(mix: A.Mixer) -> None:
	n, put = A.n, mix.put
	put(A.boing(), WIGGLE.t0, 0.08)
	put(A.land(), WIGGLE.t1, 0.18)
	put(A.whoosh(0.5), T_GUST - 0.05, 0.32, pan=0.3)
	put(A.whoosh(0.3), T_GUST + 0.1, 0.18, pan=0.6)
	put(A.blip(n('E6'), 0.06), T_GUST + 0.02, 0.10)
	put(A.blip(n('A6'), 0.16), T_GUST + 0.09, 0.10)
	for h in (H1, LUNGE, H3):
		put(A.boing(), h.t0, 0.16 if h is LUNGE else 0.13)
	put(A.land(), H1.t1, 0.28)
	put(A.whoosh(0.2), T_DODGE, 0.2, pan=0.4)
	put(A.uh_oh(), T_FLAIL + 0.02, 0.18)
	put(A.sweep(420, 70, 0.2, 'sine') * 0.9, T_SPLAT, 0.34)  # squelch
	put(A.noise_burst(0.12, 300, 30), T_SPLAT, 0.16)
	put(A.sweep(300, 950, 0.1, 'sine'), T_BACK - 0.08, 0.16)  # pop! back in shape
	put(A.land(), H3.t1, 0.24)
	put(A.sweep(650, 240, 0.2, 'tri') * 0.7, H3.t1 + 0.02, 0.12)  # the spring cloud squeaks down
	put(A.spring(), T_LAUNCH, 0.26)
	put(A.boing(), T_LAUNCH, 0.14)
	put(A.whoosh(0.7), T_LAUNCH + 0.05, 0.22)
	put(A.sweep(180, 900, T_CATCH - T_LAUNCH, 'tri') * 0.5, T_LAUNCH, 0.07)
	put(A.coin(), T_CATCH, 0.2)
	put(A.bell(n('B6'), 0.4), T_CATCH + 0.02, 0.08)
	put(A.click(1.4, 0.8), T_CATCH, 0.12)
	put(A.kick(1.0), T_REVEAL, 0.45)
	put(A.noise_burst(0.2, 1500, 16), T_REVEAL, 0.2)  # the envelope bursts
	for i, ta in enumerate(LETTER_ARRIVALS):  # the letters slam into place
		put(A.blip(n(['C6', 'D6', 'E6', 'F6', 'G6', 'A6'][i]), 0.05), ta, 0.08, pan=(i - 2.5) * 0.25)
		put(A.land(), ta, 0.12, pan=(i - 2.5) * 0.25)
	for (tb, x, _, _) in FIREWORKS:
		whistle, boom = A.firework()
		pan = (x - SAFE_X) / 600
		put(whistle, tb - 0.35, 0.05, pan=pan)
		put(boom, tb, 0.14, pan=pan)
	for h in WIDE_HOPS:
		if h is not ENTRY:
			put(A.boing(), h.t0, 0.07 if h is not JOY else 0.13)
	put(A.whoosh(0.25), T_CREDIT, 0.14)
	put(A.coin(), T_CREDIT + 0.12, 0.10)
	put(A.blip(n('G6'), 0.08), T_PRIZE, 0.09)
	put(A.blip(n('C7'), 0.12), T_PRIZE + 0.07, 0.09)
	for i, tc in enumerate(CLAP_TIMES):
		put(A.noise_burst(0.05, 1800, 60), tc, 0.10, pan=0.2 if i % 2 else -0.2)
	put(A.blip(n('C7'), 0.05), T_CLOSEUP, 0.06)
	put(A.twinkle(['E7', 'G7', 'C8']), T_WAVE + 0.2, 0.07)
	put(A.twinkle(['G7', 'C8']), T_BYE + 0.2, 0.05)


def score(mix: A.Mixer) -> None:
	music(mix)
	sound_effects(mix)
