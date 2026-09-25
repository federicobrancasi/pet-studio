"""Coding World: a 30 second one-shot of the VS Code pet fixing a bug and shipping code.

A complete example that uses most of the kit: a follow camera (``motion.FollowCamera``), real
pet states and hops (``pet``, ``motion.hop_pose``), code-line platforms and the chat input
(``world``), effects (``fx``) and a chiptune score with synced sound effects (``audio``).

    python3 -m kit film render coding-world
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image

from kit import art, fx, motion, world
from kit import audio as A
from kit import pet as P
from kit.draw import LP, TP, blit, catmull, ease_out_back, fill_rect, hexc, seg, snap
from kit.motion import Hop
from kit.pet import PetPose
from kit.world import BR1, CH, CMT, CTRL, FG, FN, KW, NUM, OK, PUNC, STR, TYPE, VAR, WHITE, CodeLine, tokens

TITLE = 'Coding World'
W, H = SIZE = (1920, 1080)
FPS = 60
DURATION = 30.0

# --------------------------------------------------------------------------------------------
# Timeline (seconds)

INPUT_X0, INPUT_X1, INPUT_TOP = 160, 1400, 800
PROMPT = 'fix the bug & ship it'
T_KEYS0, T_KEY_STEP, T_SEND = 0.50, 0.055, 2.40
T_THINK0, T_THINK1 = 2.40, 3.30
T_BANG0, T_BANG1 = 3.28, 3.52
T_COMMENT, COMMENT, COMMENT_STEP = 10.70, " // it's a feature!", 0.047
T_BRIDGE_GUTTER, T_BRIDGE0, BRIDGE_STEP = 14.10, 14.25, 0.125
T_PRESS, T_SUCCESS = 19.20, 20.00
T_FRIEND, T_LOVE, T_TITLE = 22.00, 24.04, 26.00
T_TERM_CLOSE, TERM_TOP, TERM_CX = 24.00, 64, 7700

CUES = [
	(0.0, 'asleep on the chat input'),
	(0.5, 'first key wakes it'),
	(2.4, 'prompt sent, thinking'),
	(3.28, 'idea!'),
	(3.5, 'hops into Coding World'),
	(7.45, 'worried: a bug'),
	(10.0, 'BONK'),
	(10.3, 'bug becomes a feature'),
	(14.0, 'types a bridge'),
	(18.35, 'butterfly perches'),
	(19.2, 'button press'),
	(20.0, 'shipped!'),
	(22.0, 'friend respawns'),
	(25.0, 'hearts'),
	(26.0, 'end card'),
	(28.0, 'final hop'),
]

# --------------------------------------------------------------------------------------------
# The world: code lines are floating platforms

LINES = [
	CodeLine('l3', 3, 1540, 700, tokens(('while', CTRL), (' ', PUNC), ('(', BR1), ('awake', VAR), (')', BR1), (' ', PUNC), ('hop', FN), ('()', BR1), (';', PUNC))),
	CodeLine('l7', 7, 2860, 600, tokens(('let', KW), (' ', PUNC), ('joy', VAR), (' = ', PUNC), ('Infinity', TYPE), (';', PUNC))),
	CodeLine('l12', 12, 4060, 720, tokens(('ship', FN), ('(', BR1), ('app', VAR), (')', BR1), (';', PUNC)) + tokens((COMMENT, CMT), appear=T_COMMENT, step=COMMENT_STEP)),
	CodeLine('l23', 23, 5820, 650, tokens(('// TODO: bridge', CMT))),
	CodeLine('l24', 24, 6750, 650, tokens(('new', KW), (' ', PUNC), ('Bridge', TYPE), ('()', BR1), (';', PUNC), appear=T_BRIDGE0, step=BRIDGE_STEP, pop=True), appear=T_BRIDGE_GUTTER),
	CodeLine('l42', 42, 7584, 650, tokens(('export', CTRL), (' ', PUNC), ('default', CTRL), (' ', PUNC), ('joy', VAR), (';', PUNC))),
]
LINE = {line.key: line for line in LINES}
WORLD_W = LINES[-1].x1 + 1400
CITY = world.CodeCity(SIZE, WORLD_W, seed=0)

# --------------------------------------------------------------------------------------------
# Choreography

BUG_X0, BUG_T0, BUG_SPEED, BUG_STOP = 5010.0, 5.0, 92.0, 9.35


def bug_x(t: float) -> float:
	return BUG_X0 - BUG_SPEED * (min(max(t, BUG_T0), BUG_STOP) - BUG_T0)


BONK_X = round(bug_x(BUG_STOP))
T_BONK = 10.0
START_X = 1180
HOPS = [
	Hop(3.50, 4.00, START_X, INPUT_TOP, 1720, 700, 190),
	Hop(4.25, 4.75, 1720, 700, 2280, 700, 170, star=True),
	Hop(5.00, 5.50, 2280, 700, 2960, 600, 200, star=True),
	Hop(5.75, 6.25, 2960, 600, 3560, 600, 170, star=True),
	Hop(6.50, 7.00, 3560, 600, 4200, 720, 170, star=True),
	Hop(9.50, T_BONK, 4200, 720, BONK_X, 720 - 40, 300, recover=False),  # the bonk
	Hop(T_BONK + 0.10, T_BONK + 0.42, BONK_X, 720 - 40, 4480, 720, 120, crouch=0.0),
	Hop(12.00, 12.50, 4480, 720, 5040, 720, 170),
	Hop(12.75, 13.25, 5040, 720, 5540, 720, 150),
	Hop(13.50, 14.00, 5540, 720, 6060, 650, 180),
	Hop(16.00, 16.50, 6060, 650, 6600, 650, 150),
	Hop(16.75, 17.25, 6600, 650, 7160, 650, 150),
	Hop(17.50, 18.00, 7160, 650, 7860, 650, 210),
	Hop(28.00, 28.36, 7860, 650, 7860, 650, 70),  # final hop with the friend
]
HERO_FINAL_X, FRIEND_X, FINALE_Y = 7860, 8300, 650
LANDINGS = motion.landings(HOPS)
STARS = [((h.t0 + h.t1) / 2, h.pos((h.t0 + h.t1) / 2)[0], h.pos((h.t0 + h.t1) / 2)[1] - 96) for h in HOPS if h.star]
BLINKS_HERO = [1.62, 3.05, 5.0, 7.3, 8.9, 11.95, 15.2, 18.62, 21.9, 23.86, 27.25, 29.2]
BLINKS_FRIEND = [23.86, 27.6, 29.4]


def idle_frame(t: float, phase: float = 0.0) -> int:
	return P.frame_at('idle', (t + phase) * 1000.0)


def hero_ground(t: float) -> tuple[float, float]:
	return motion.ground_at(HOPS, t, (START_X, INPUT_TOP))


def hero_pose(t: float) -> PetPose:
	hp = motion.hop_pose(HOPS, t)
	if hp is not None:
		return hp
	x, y = hero_ground(t)
	blink = motion.blinking(t, BLINKS_HERO)
	if t < T_KEYS0:
		return PetPose('sleep', P.frame_at('sleep', (t + 0.62) * 1000), x, y)
	if t < T_KEYS0 + 0.88:
		return PetPose('waking', P.frame_at('waking', (t - T_KEYS0) * 1000, loop=False), x, y)
	if t < T_SEND:
		return PetPose('typing', P.frame_at('typing', (t - T_KEYS0 - 0.88) * 1000), x, y, gaze=(4, 0), blink=blink)
	if t < T_THINK1:
		return PetPose('rendering', idle_frame(t), x, y, gaze=(4, -4), blink=blink)
	if t < 3.40:
		return PetPose('idleTracking', idle_frame(t), x, y, gaze=(4, 0), blink=blink)
	if 7.0 <= t < 9.40:
		if 7.45 <= t < 8.75:
			return PetPose('worry', int((t - 7.45) / 0.26) % 2, x, y)
		return PetPose('idleTracking', idle_frame(t), x, y, gaze=(4, 0) if t < 7.45 else (4, 4), blink=blink)
	if T_BONK + 0.42 <= t < 12.0:
		if 10.95 <= t < 11.80:
			return PetPose('sing', P.frame_at('sing', (t - 10.95) * 1000), x, y)
		return PetPose('idleTracking', idle_frame(t), x, y, gaze=(4, -4), blink=blink)
	if 14.0 <= t < 15.90:
		return PetPose('typing', P.frame_at('typing', (t - 14.0) * 1000), x, y, gaze=(4, 0), blink=blink)
	if 18.0 <= t < T_PRESS:
		return PetPose('idleTracking', idle_frame(t), x, y, gaze=(0, 0) if t < 18.55 else (4, -4), blink=blink)
	if T_PRESS <= t < T_PRESS + 2.85:
		return PetPose('press', P.frame_at('press', (t - T_PRESS) * 1000, loop=False), x, y, gaze=(4, 0), blink=blink)
	if T_LOVE <= t < T_LOVE + 2.94:
		return PetPose('love', P.frame_at('love', (t - T_LOVE) * 1000, loop=False), x, y, gaze=(4, 0), blink=blink)
	if T_PRESS + 2.85 <= t < T_LOVE:
		return PetPose('idleTracking', idle_frame(t), x, y, gaze=(4, -4) if t < T_FRIEND + 0.9 else (4, 0), blink=blink)
	return PetPose('idleTracking', idle_frame(t), x, y, gaze=(4, 0) if t > 22 else (0, 0), blink=blink)


# The Insiders friend respawns at the top, falls and lands next to the hero.
FRIEND_SPAWN_Y = 330.0
T_FRIEND_FALL = T_FRIEND + 0.80
FALL_G = 3200.0
T_FRIEND_LAND = T_FRIEND_FALL + math.sqrt(2 * (FINALE_Y - (FRIEND_SPAWN_Y + 96)) / FALL_G)


def friend_pose(t: float) -> PetPose | None:
	if t < T_FRIEND_FALL:
		return None
	blink = motion.blinking(t, BLINKS_FRIEND)
	if t < T_FRIEND_LAND:
		dt = t - T_FRIEND_FALL
		return PetPose('falling', P.frame_at('falling', dt * 1000), FRIEND_X, FRIEND_SPAWN_Y + 96 + 0.5 * FALL_G * dt * dt, 'left', variant='insiders')
	if t < T_FRIEND_LAND + 0.52:
		return PetPose('splat', P.frame_at('splat', (t - T_FRIEND_LAND) * 1000, loop=False), FRIEND_X, FINALE_Y, 'left', variant='insiders')
	if 27.9 <= t < 28.6:
		hp = motion.hop_pose(HOPS, t, 'insiders', 'left')
		if hp is not None:
			hp.x = FRIEND_X
			return hp
	if T_LOVE <= t < T_LOVE + 2.94:
		return PetPose('love', P.frame_at('love', (t - T_LOVE) * 1000, loop=False), FRIEND_X, FINALE_Y, 'left', gaze=(4, 0), blink=blink, variant='insiders')
	return PetPose('idleTracking', idle_frame(t, 0.7), FRIEND_X, FINALE_Y, 'left', gaze=(4, 0), blink=blink, variant='insiders')


# --------------------------------------------------------------------------------------------
# Camera: one continuous tracking shot

GROUND_RATIO = 0.72
FINALE_CX = (HERO_FINAL_X + FRIEND_X) / 2 - W / 2 - 32
FINALE_CY = FINALE_Y - GROUND_RATIO * H


def camera_target(t: float) -> tuple[float, float]:
	if t < 3.4:
		return 0.0, INPUT_TOP - GROUND_RATIO * H
	if 13.9 <= t < 16.2:
		return 5740.0, 650 - GROUND_RATIO * H
	if t >= 17.4:
		return FINALE_CX, FINALE_CY
	gx, gy = hero_ground(t)
	return hero_pose(t).x - 0.28 * W, motion.heading_y(HOPS, t, gy) - GROUND_RATIO * H


CAMERA = motion.FollowCamera(camera_target, DURATION, FPS, omega=(5.0, 3.0))


def camera(t: float) -> tuple[int, int]:
	cx, cy = CAMERA.at(t)
	sx, sy = motion.shake(t, T_BONK)
	return int(round(cx + sx)), int(round(cy + sy))


# --------------------------------------------------------------------------------------------
# Scene pieces


def active_line(t: float) -> str | None:
	x, y = hero_ground(t)
	for line in LINES:
		if line.contains(x, y):
			return line.key
	return None


def draw_lines(img: Image.Image, t: float, cx: int, cy: int) -> None:
	active = active_line(t)
	for line in LINES:
		def dip(x: float, line: CodeLine = line) -> int:
			d = world.landing_dip(t, LANDINGS, line.top, x)
			if not d and line.key == 'l12' and T_BONK <= t < T_BONK + 0.16 and abs(BONK_X - x) < 150:
				d = TP
			return d
		line.draw(img, t, cx, cy, active=line.key == active, dip=dip)
		if line.key == 'l12' and t < T_BONK + 0.5 and not (t >= T_BONK + 0.2 and int((t - T_BONK) * 20) % 2):
			world.squiggle(img, line.char_x(0), line.char_x(9) - TP, line.top + 10 * TP, cx, cy)


def draw_bug(img: Image.Image, t: float, cx: int, cy: int) -> None:
	if t >= T_BONK + 0.12:
		return
	x = bug_x(t)
	if x - cx > W + 200 or x - cx < -300:
		return
	top = LINE['l12'].top
	if t >= T_BONK:
		im = art.bug(0, 'left', squish=True)
	else:
		im = art.bug(int(t * 8) if t < BUG_STOP else 0, 'left')
	bob = 0 if (t >= BUG_STOP or int(t * 8) % 2 == 0) else -4
	blit(img, im, round(x) - im.width // 2 - cx, top - im.height + bob - cy)
	if 8.05 <= t < 8.9:
		k = seg(t, 8.05, 8.17)
		blit(img, art.bang(8), round(x) - 60 - cx, top - 150 + int((1 - ease_out_back(k)) * 2) * TP - cy)


# The butterfly perches on the tip of the pet's right antenna while it waits to press its button.
PERCH_X, PERCH_Y = HERO_FINAL_X + 60, FINALE_Y - 192 - 40
T_PERCH0, T_PERCH1 = 18.35, 19.15
FLY_KEYS = [
	(10.30, BONK_X, 650), (10.9, BONK_X + 120, 470), (11.8, 4980, 420), (12.8, 5480, 440),
	(13.6, 6000, 430), (14.4, 6620, 430), (15.4, 7200, 470), (16.4, 7400, 420),
	(17.4, 7700, 330), (18.35, PERCH_X, PERCH_Y), (19.15, PERCH_X, PERCH_Y), (19.9, 8420, 500), (20.6, 8640, 420),
	(21.6, 8700, 500), (22.6, 8620, 540), (23.6, 8560, 470), (24.6, 8600, 360),
	(25.6, 8420, 328), (26.6, 8140, 318), (27.6, 7990, 328), (28.6, 8150, 308), (29.6, 8230, 328), (30.5, 8110, 318),
]


def draw_butterfly(img: Image.Image, t: float, cx: int, cy: int) -> None:
	if t < 10.30:
		return
	if T_PERCH0 <= t < T_PERCH1:
		frame = 2 if int((t - T_PERCH0) * 2.5) % 3 else 1  # wings mostly folded, a slow lazy flap
		# the folded frame's body sits one logical pixel higher in the art; align bodies so it doesn't hop
		x, y = PERCH_X, PERCH_Y + (8 if idle_frame(t) >= 20 else 0) + (LP if frame == 2 else 0)
		im = art.butterfly(frame)
		blit(img, im, snap(x - im.width / 2 - cx, 4), snap(y - im.height / 2 - cy, 4))
		if 0 <= t - T_PERCH0 < 0.3:
			fx.sparks(img, t, T_PERCH0, x, y - 20, cx, cy, [hexc('#ffe780'), hexc('#ff7ac8')], 6, 50, 0.3)
		return
	x, y = catmull(FLY_KEYS, t)
	settle = min(seg(t, T_PERCH0 - 0.35, T_PERCH0), 1 - seg(t, T_PERCH1, T_PERCH1 + 0.35)) if T_PERCH0 - 0.35 <= t < T_PERCH1 + 0.35 else 0.0
	y += math.sin(t * 7.5) * 14 * (1 - settle)
	im = art.butterfly(int(t * 13) % 4)
	blit(img, im, snap(x - im.width / 2 - cx, 4), snap(y - im.height / 2 - cy, 4))
	for j in range(1, 4):  # sparkle trail
		tt = t - j * 0.09
		if tt < 10.3:
			break
		px, py = catmull(FLY_KEYS, tt)
		py += math.sin(tt * 7.5) * 14
		if (int(t * 12) + j) % 3 == 0:
			fill_rect(img, snap(px - cx, 4), snap(py + 30 - cy, 4), TP // 2, TP // 2, hexc('#ffe780'))


def draw_bridge_sparkles(img: Image.Image, t: float, cx: int, cy: int) -> None:
	line = LINE['l24']
	done = T_BRIDGE0 + (len(line.chars) - 1) * BRIDGE_STEP + 0.18
	for i, c in enumerate(line.chars):
		if c.appear >= 0:
			fx.sparks(img, t, c.appear, line.char_x(i) + CH / 2, line.top + 40, cx, cy, [hexc('#ffe780'), hexc('#9cdcfe')], 4, 40, 0.22)
	if done <= t < done + 0.45:
		for j in range(10):
			if (j + int(t * 16)) % 3 == 0:
				fill_rect(img, snap(line.x0 + 80 + j * 72 - cx, 4), snap(line.top - 30 - (j % 3) * 20 - cy, 4), TP, TP, hexc('#ffe780'))


CONFETTI = [
	(T_SUCCESS, fx.confetti_burst(1, 8010, FINALE_Y - 40, 70, 0.75)),
	(T_SUCCESS + 0.15, fx.confetti_burst(2, 7300, FINALE_Y + 40, 40, 0.35)),
	(T_SUCCESS + 0.15, fx.confetti_burst(3, 8760, FINALE_Y + 40, 40, 0.35)),
	(T_LOVE + 0.96, fx.confetti_burst(4, (HERO_FINAL_X + FRIEND_X) / 2, FINALE_Y - 120, 36, 0.9)),
]
FIREWORKS = [
	(20.35, 7250, 20, '#ffbe30'), (20.80, 8700, -20, '#ff7ac8'), (21.30, 8420, 60, '#24bfa5'),
	(21.85, 8820, 150, '#23a8f2'), (22.60, 7160, 150, '#c586c0'), (26.10, 7350, 330, '#ffbe30'),
	(26.60, 8820, 360, '#23a8f2'), (27.20, 7250, 420, '#24bfa5'), (28.00, 8700, 330, '#ff7ac8'),
	(28.70, 7400, 380, '#dcdcaa'), (29.30, 8850, 420, '#24bfa5'),
]
TERMINAL_LINES = [
	(T_SUCCESS + 0.22, [('$ ', OK), ('npm run ship', FG)], 0.03),
	(T_SUCCESS + 0.85, [('\u2713 ', OK), ('42 tests passed', OK)], 0.0),
	(T_SUCCESS + 1.35, [('\u2713 ', OK), ('shipped! ', WHITE), ('\u2728', BR1)], 0.0),
]
OPEN_TITLE = 'Coding World'
OPEN_TITLE_COLORS = [KW, VAR, TYPE, FN, STR, CTRL, None, NUM, BR1, KW, VAR, TYPE]
END_TITLE = 'Happy coding!'
END_TITLE_COLORS = [KW, VAR, TYPE, FN, STR, None, CTRL, NUM, BR1, KW, VAR, TYPE, FN]


def draw_open_title(img: Image.Image, t: float, cx: int, cy: int) -> None:
	f = 0.55  # parallax: the title lives in the sky and drifts away as the camera moves
	x0 = (W - world.text_width(OPEN_TITLE, LP)) // 2 - int(cx * f)
	y0 = 150 - int((cy - (INPUT_TOP - GROUND_RATIO * H)) * f)
	if x0 + world.text_width(OPEN_TITLE, LP) >= -50:
		world.bob_title(img, t, OPEN_TITLE, OPEN_TITLE_COLORS, x0, y0)


def render(t: float) -> Image.Image:
	img = Image.new('RGBA', SIZE)
	cx, cy = camera(t)
	CITY.draw(img, t, cx, cy, clouds_fade=seg(t, T_SUCCESS + 0.2, T_SUCCESS + 0.5))
	fx.fireworks(img, t, FIREWORKS, cx, cy)
	draw_open_title(img, t, cx, cy)
	typing = T_KEYS0 <= t < T_SEND
	world.chat_input(
		img, t, INPUT_X0, INPUT_X1, INPUT_TOP, cx, cy,
		text=world.typed(PROMPT, t, T_KEYS0, T_KEY_STEP, T_SEND),
		placeholder='Ask anything' if t < T_KEYS0 else None,
		focused=T_KEYS0 - 0.05 <= t < T_SEND + 0.25, typing=typing, send_flash=T_SEND <= t < T_SEND + 0.18,
	)
	draw_lines(img, t, cx, cy)
	draw_bridge_sparkles(img, t, cx, cy)
	world.terminal_panel(img, t, TERM_CX, TERM_TOP, cx, cy, world.open_amount(t, T_SUCCESS, T_TERM_CLOSE), TERMINAL_LINES)
	fx.collectible_stars(img, t, STARS, cx, cy)
	draw_bug(img, t, cx, cy)
	fx.poof(img, t, T_BONK + 0.08, BONK_X, LINE['l12'].top - 96, cx, cy)
	hero = hero_pose(t)
	if t < T_KEYS0 + 0.1:
		fx.zzz(img, t, START_X + 70, INPUT_TOP - 200, cx, cy)
	P.draw_pose(img, hero, cx, cy)
	if T_THINK0 + 0.05 <= t < T_THINK1:
		fx.speech_bubble(img, t - T_THINK0, hero, cx, cy)
	fx.bang(img, t, T_BANG0, T_BANG1, hero.x, hero.y - 192, cx, cy)
	if T_FRIEND <= t < T_FRIEND_FALL + 0.05:
		fx.respawn(img, t - T_FRIEND, FRIEND_X, FRIEND_SPAWN_Y, cx, cy, 'insiders')
	friend = friend_pose(t)
	if friend is not None:
		P.draw_pose(img, friend, cx, cy)
	fx.dust(img, t, LANDINGS, cx, cy)
	fx.sparks(img, t, T_BONK, BONK_X, LINE['l12'].top - 30, cx, cy, [hexc('#ffffff'), hexc('#ffe780'), hexc('#ff9da0')], 10, 120, 0.3)
	fx.floating_hearts(img, t, T_LOVE + 0.96, (HERO_FINAL_X + FRIEND_X) / 2, FINALE_Y - 140, cx, cy)
	draw_butterfly(img, t, cx, cy)
	fx.confetti(img, t, CONFETTI, cx, cy)
	world.pop_title(img, t, END_TITLE, END_TITLE_COLORS, T_TITLE, 96)
	if t >= T_TITLE + 0.9:
		world.centered_text(img, 96 + 11 * LP + 8, 'Visual Studio Code', hexc('#9aa3b5'), TP)
	return img


# --------------------------------------------------------------------------------------------
# Score: 120 BPM, one bar = 2 s, sections follow the story beats

CHORDS = {
	'C': ['C3', 'E4', 'G4', 'C5'], 'Am': ['A2', 'C4', 'E4', 'A4'], 'F': ['F2', 'A3', 'C4', 'F4'],
	'G': ['G2', 'B3', 'D4', 'G4'], 'Dm': ['D3', 'F3', 'A3', 'D4'], 'E': ['E2', 'G#3', 'B3', 'E4'],
}
PROGRESSION = [  # (start beat, length in beats, chord)
	(0, 2, 'C'), (2, 2, 'Am'), (4, 2, 'F'), (6, 2, 'G'), (8, 2, 'C'), (10, 2, 'G'), (12, 2, 'Am'),
	(14, 2, 'F'), (16, 2, 'Dm'), (18, 2, 'E'), (20, 2, 'C'), (22, 1, 'F'), (23, 1, 'G'),
	(24, 2, 'C'), (26, 2, 'G'), (28, 2, 'Am'), (30, 2, 'F'), (32, 2, 'C'), (34, 2, 'G'),
	(36, 2, 'Am'), (38, 1, 'F'), (39, 1, 'G'), (40, 2, 'C'), (42, 1, 'F'), (43, 1, 'G'),
	(44, 2, 'F'), (46, 2, 'G'), (48, 2, 'C'), (50, 2, 'Am'), (52, 2, 'F'), (54, 2, 'G'), (56, 4, 'C'),
]
THEME_A1 = [(0, .5, 'C5'), (.5, .5, 'E5'), (1, .75, 'G5'), (1.75, .25, 'E5'), (2, .5, 'D5'), (2.5, .5, 'G5'), (3, .5, 'B4'), (3.5, .5, 'D5')]
THEME_A2 = [(0, .5, 'C5'), (.5, .5, 'E5'), (1, 1, 'A5'), (2, .5, 'A5'), (2.5, .5, 'G5'), (3, .5, 'F5'), (3.5, .5, 'D5')]


def music(mix: A.Mixer) -> None:
	n, bt, put = A.n, mix.beat, mix.put
	for (b0, length, ch) in PROGRESSION:  # bass and soft arpeggios from the chords
		root = n(CHORDS[ch][0])
		tones = [n(x) for x in CHORDS[ch][1:]]
		intro, tension, final = b0 < 8, 14 <= b0 < 20, b0 >= 56
		for k in range(int(length * 2)):
			bb = b0 + k * 0.5
			if final:
				break
			if intro and b0 < 4:
				continue
			if tension:
				if k % 2 == 0:
					put(A.bass(root, 0.16), bt(bb), 0.26)
				continue
			put(A.bass(root if k % 2 == 0 else root + 7, 0.2), bt(bb), 0.26 if not intro else 0.16)
		if (28 <= b0 < 32) or (40 <= b0 < 44):
			for k in range(int(length * 4)):
				put(A.pluck(tones[k % 3] + 12, 0.1), bt(b0 + k * 0.25), 0.05, pan=0.35 if k % 2 else -0.35)
		elif not intro and not tension and not final:
			for k in range(int(length * 2)):
				put(A.pluck(tones[(k + 1) % 3] + 12, 0.16), bt(b0 + k * 0.5 + 0.25), 0.035, pan=0.3)
	for i, nm in enumerate(['C4', 'E4', 'G4', 'C5', 'E5']):  # final chord
		put(A.lead(n(nm), 1.6, 0.125), bt(56) + 0.01 * i, 0.05, pan=(i - 2) * 0.25)
	put(A.bass(n('C3'), 1.4), bt(56), 0.24)
	for i, nm in enumerate(['C5', 'E5', 'G5', 'C6', 'E6', 'G6', 'C7']):
		put(A.bell(n(nm), 1.6), bt(56) + i * 0.07, 0.06, pan=(i - 3) * 0.15)
	# lullaby while asleep, thinking plucks, then the main theme on the hops
	mix.melody([(0, .5, 'E5'), (.5, .5, 'G5'), (1, .5, 'C6'), (1.5, .5, 'G5'), (2, .5, 'A5'), (2.5, .5, 'E5'), (3, .5, 'C6'), (3.5, .5, 'B5')], 0, 'bell', 0.10)
	mix.melody([(4, .5, 'A5'), (5, .5, 'C6'), (5.5, .5, 'A5'), (6, .5, 'B5'), (6.5, .25, 'D6'), (6.75, .25, 'G6')], 0, 'pluck', 0.07)
	mix.melody(THEME_A1, 8)
	mix.melody(THEME_A2[:3], 12)
	mix.melody([(14, .25, 'A4'), (14.5, .25, 'G#4'), (15, .25, 'A4'), (16, .25, 'F4'), (16.5, .25, 'E4'), (17, .25, 'F4'), (18, .25, 'E4'), (18.5, .25, 'G#4'), (19, .25, 'B4'), (19.5, .25, 'D5')], 0, 'pluck', 0.11)
	for i, nm in enumerate(['C5', 'E5', 'G5', 'C6', 'E6', 'G6', 'C7']):  # bonk sparkle
		put(A.bell(n(nm), 0.8), bt(20) + 0.1 + i * 0.06, 0.07, pan=(i - 3) * 0.2)
	mix.melody([(21, .5, 'E6'), (21.5, .5, 'G6'), (22, .5, 'A6'), (22.5, .5, 'F6'), (23, .5, 'G6'), (23.5, .5, 'B5')], 0, 'bell', 0.09)
	mix.melody([(21, .5, 'E5'), (21.5, .5, 'G5'), (22, .75, 'A5'), (22.75, .25, 'F5'), (23, .5, 'G5'), (23.5, .5, 'B4')], 0, 'lead', 0.08)
	mix.melody(THEME_A1, 24)
	mix.melody([(28, .5, 'E5'), (29, .5, 'A5'), (30, .5, 'C6'), (31, .5, 'A5')], 0, 'lead', 0.07)
	mix.melody(THEME_A1, 32)
	mix.melody([(36, .5, 'A4'), (36.5, .5, 'B4'), (37, .5, 'C5'), (37.5, .5, 'D5'), (38, .5, 'E5'), (38.5, .5, 'F5'), (39, .5, 'G5'), (39.5, .5, 'B5')], 0, 'lead', 0.15)
	fanfare = [(40, .25, 'C6'), (40.25, .25, 'C6'), (40.5, .25, 'C6'), (40.75, 1.25, 'E6'), (42, .5, 'D6'), (42.5, .5, 'E6'), (43, 1, 'G6')]
	mix.melody(fanfare, 0, 'lead', 0.15)
	mix.melody([(b, length, x[:-1] + str(int(x[-1]) - 1)) for (b, length, x) in fanfare], 0, 'lead', 0.07, pan=0.2)
	mix.melody([(44, .5, 'A5'), (44.5, .5, 'G5'), (45, .5, 'F5'), (45.5, .5, 'A5'), (46, 1, 'G5'), (47, .5, 'B5'), (47.5, .5, 'D6')], 0, 'lead', 0.09)
	mix.melody([(48, 1, 'E5'), (49, 1, 'G5'), (50, 1.5, 'C6'), (51.5, .5, 'B5')], 0, 'lead', 0.11)
	mix.melody([(48, 1, 'E6'), (49, 1, 'G6'), (50, 1.5, 'C7'), (51.5, .5, 'B6')], 0, 'bell', 0.05)
	mix.melody([(52, .5, 'A5'), (52.5, .5, 'C6'), (53, 1, 'F6'), (54, .5, 'D6'), (54.5, .5, 'B5'), (55, .5, 'G5'), (55.5, .5, 'B5')], 0, 'lead', 0.10)
	# drums
	A.roll(mix, 7, 8, 0.12, 0.3)
	A.groove(mix, 8, 14)
	for b in (14, 16, 18):
		put(A.kick(0.6), bt(b))
	A.roll(mix, 19, 20, 0.08, 0.34)
	put(A.crash(0.22), bt(20), pan=0.2)
	put(A.kick(1.0), bt(20))
	A.groove(mix, 21, 24, soft=0.8)
	A.groove(mix, 24, 28)
	A.groove(mix, 28, 32, hats16=True)
	A.groove(mix, 32, 36)
	for i in range(8):
		put(A.kick(0.8), bt(36 + i * 0.5))
	A.roll(mix, 38, 40, 0.1, 0.36)
	put(A.crash(0.26), bt(40), pan=-0.2)
	A.groove(mix, 40, 44, hats16=True)
	A.groove(mix, 44, 48, soft=0.7)
	A.groove(mix, 48, 52, soft=0.6)
	A.groove(mix, 52, 56, soft=0.75)
	put(A.crash(0.2), bt(56), pan=0.15)
	put(A.kick(1.0), bt(56))


def sound_effects(mix: A.Mixer) -> None:
	n, put = A.n, mix.put
	put(A.sweep(300, 520, 0.18, 'sine') * 0.5, 0.12, 0.12)  # sleepy bubble
	for i, ch in enumerate(PROMPT):
		put(A.click(1.0 + 0.08 * ((i * 7) % 5 - 2) if ch != ' ' else 0.7), T_KEYS0 + i * T_KEY_STEP, 0.20, pan=-0.3)
	put(A.sweep(500, 1300, 0.08, 'sine'), T_KEYS0 + 0.02, 0.22)  # wake
	put(A.spring(), T_KEYS0 + 0.36, 0.10)
	t = T_KEYS0 + 0.9
	while t < T_SEND - 0.05:  # the pet types along
		put(A.click(1.6, 0.8), t, 0.10, pan=0.25)
		t += 0.13
	put(A.whoosh(0.3), T_SEND - 0.02, 0.28, pan=0.1)
	put(A.blip(n('A5'), 0.06), T_SEND, 0.10)
	put(A.blip(n('E6'), 0.09), T_SEND + 0.06, 0.10)
	for i, m in enumerate(['E6', 'G6', 'B6']):
		put(A.blip(n(m), 0.05, 0.125), T_THINK0 + i * 0.22, 0.07, pan=0.4)
	put(A.blip(n('E6'), 0.07), T_BANG0, 0.12)
	put(A.blip(n('A6'), 0.16), T_BANG0 + 0.07, 0.12)
	for h in HOPS:
		put(A.boing(), h.t0, 0.16 if h.h > 100 else 0.12)
		put(A.land(), h.t1, 0.30)
	for (tc, _x, _y) in STARS:
		put(A.coin(), tc, 0.11, pan=0.2)
	put(A.uh_oh(), 7.45, 0.20)
	put(A.blip(n('B6'), 0.05), 8.05, 0.08, pan=0.4)
	put(A.blip(n('B6'), 0.05), 8.12, 0.08, pan=0.4)
	put(A.bonk(), T_BONK, 0.45)
	put(A.noise_burst(0.25, 2000, 16) * 0.6, T_BONK + 0.08, 0.35)
	put(A.twinkle(['C7', 'E7', 'G7', 'C8'], 0.04), T_BONK + 0.30, 0.12, pan=0.2)
	for i in range(len(COMMENT)):
		put(A.click(1.3, 0.6), T_COMMENT + i * COMMENT_STEP, 0.08, pan=0.2)
	t = 14.02
	while t < 15.85:
		put(A.click(1.6, 0.7), t, 0.08, pan=-0.2)
		t += 0.12
	bridge = LINE['l24']
	for i, c in enumerate(bridge.chars):
		put(A.pluck(n(A.PENTA[min(i, len(A.PENTA) - 1)]), 0.1, 0.25), c.appear, 0.09, pan=-0.4 + 0.8 * i / len(bridge.chars))
	put(A.twinkle(['G6', 'C7', 'E7', 'G7'], 0.05), T_BRIDGE0 + (len(bridge.chars) - 1) * BRIDGE_STEP + 0.18, 0.10)
	put(A.sweep(400, 900, 0.06, 'sine'), T_PRESS, 0.15)
	put(A.click(0.5, 1.0), T_SUCCESS, 0.5)
	put(A.bonk() * 0.5, T_SUCCESS, 0.2)
	for i in range(len('$ npm run ship')):
		put(A.click(1.4, 0.6), T_SUCCESS + 0.22 + i * 0.03, 0.06)
	put(A.coin(), T_SUCCESS + 0.85, 0.10)
	put(A.twinkle(['C7', 'G7', 'C8'], 0.05), T_SUCCESS + 1.35, 0.10)
	for (t0, _parts) in CONFETTI:
		for k in range(8):
			put(A.noise_burst(0.02, 3000, 200), t0 + k * 0.035, 0.15, pan=float(A.rng().uniform(-0.6, 0.6)))
	for (tb, x, _y, _c) in FIREWORKS:
		whistle, boom = A.firework()
		pan = float(np.clip((x - 8030) / 900, -0.8, 0.8))
		put(whistle, tb - 0.35, 0.10, pan)
		put(boom, tb, 0.20, pan)
	put(A.twinkle(['C6', 'E6', 'G6', 'B6', 'D7', 'G7'], 0.1, 1.0), T_FRIEND, 0.09, pan=0.3)
	put(A.sweep(1200, 300, 0.36, 'tri'), T_FRIEND_FALL, 0.08, pan=0.3)
	put(A.spring(), T_FRIEND_LAND, 0.14, pan=0.3)
	put(A.land(), T_FRIEND_LAND, 0.26, pan=0.3)
	put(A.twinkle(['E6', 'G6', 'C7'], 0.09), T_LOVE + 0.96, 0.12)
	for i in range(14):
		put(A.blip(n(A.PENTA[5 + i % 5]), 0.04, 0.125), T_LOVE + 0.96 + i * 0.22, 0.03, pan=float(np.sin(i)) * 0.4)
	for i, ch in enumerate(END_TITLE):
		if ch != ' ':
			put(A.pluck(n(A.PENTA[i % len(A.PENTA)]), 0.08, 0.25), T_TITLE + i * 0.055, 0.07, pan=-0.6 + 1.2 * i / len(END_TITLE))


def score(mix: A.Mixer) -> None:
	music(mix)
	sound_effects(mix)
