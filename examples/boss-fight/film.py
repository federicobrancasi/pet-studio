"""boss-fight: "POV: the bug only happens in prod", a 20.5 s vertical (9:16) reel.

A retro video-game boss fight in a server room. The VS Code pet dodges the prod bug's error
rain, takes a "WORKS ON MY MACHINE!" to the face (the ready-made `zapped` move), gets a rubber
duck from an item box (the `rubber-duck` move; its squeak finds the weak spot), and when the
Insiders pet joins as player 2, they double-stomp it for a -9999 critical hit. The bug shrinks
into a butterfly: it's not a bug, it's a feature. The end card asks for comments.

It shows how to make a game-style reel: a boss drawn from shapes on the pet's grid (arena.py),
a HUD (health bar, hearts, floating damage numbers), banners that slide in on the beat, moves
used as story beats, two pets playing together, whole-pixel squash and shrink, screen shake and
partial flashes on the hits.

    python3 -m kit film sheet boss-fight
    python3 -m kit film review boss-fight
"""

from __future__ import annotations

import math
import random

from PIL import Image

import arena as AR
from kit import art, fx, layout, moves, motion, world
from kit import audio as A
from kit import pet as P
from kit.draw import blit, clamp, ease_out, ease_out_back, fill_rect, hexc, seg, smooth, snap
from kit.motion import Hop
from kit.pet import PetPose

TITLE = 'Boss fight: the bug only happens in prod'
W, H = SIZE = (1080, 1920)
FPS = 60
BPM = 120
DURATION = 20.5
MASTER = {'ceiling': 0.64, 'drive': 2.4, 'fade_out': 0.5}  # true peak under -1 dBTP after AAC
SAFE = layout.safe_area(SIZE)  # (60, 260, 960, 1600)
SAFE_X = (SAFE[0] + SAFE[2]) // 2
SAFE_W = SAFE[2] - SAFE[0]
SCALE = 2
FLOOR = AR.FLOOR

for _name in ('zapped', 'rubber-duck'):
	moves.use(_name)

# --------------------------------------------------------------------------------------------
# Timeline (seconds, on a 120 BPM grid: a beat is 0.5 s)

T_FIGHT = 1.8
T_CHARGE = 2.3
T_BLOCKS = (3.0, 3.5, 4.0)             # error blocks smash on the beat
T_SPECIAL = 4.3                         # "PROD BUG USED WORKS ON MY MACHINE!"
T_STRIKE = 5.5                          # the lightning hits, on the beat ...
T_ZAP = T_STRIKE - sum(P.durations('zapped')[:5]) / 1000   # ... so the zapped move starts here
T_EFFECTIVE = T_STRIKE + 0.1
T_BOX = 7.15                            # an item box drops in
T_BOX_LAND = 7.45
T_DUCK = 7.7                            # the rubber-duck move starts ...
T_DUCK_OUT = T_DUCK + sum(P.durations('rubber-duck')[:2]) / 1000  # ... the duck pops out of the box
T_WEAK = T_DUCK + sum(P.durations('rubber-duck')[:7]) / 1000     # the second squeak finds the weak spot
T_DUCK_GONE = T_DUCK + sum(P.durations('rubber-duck')[:10]) / 1000
T_P2 = 10.0                             # player 2 joins
T_JUMP = 11.45
T_HIT = 12.0                            # the double stomp, on the beat
T_BOUNCE = 12.5
T_POOF = 13.0                           # the bug turns into a butterfly
T_NOT_BUG = 13.25
T_FEATURE = 14.25
T_FIXED = 15.5
T_END = 17.0

CUES = [
	(0.0, 'hook: POV: THE BUG ONLY HAPPENS IN PROD'),
	(T_FIGHT + 0.2, 'FIGHT!'),
	(T_BLOCKS[0] + 0.05, 'error rain: MISS!'),
	(T_SPECIAL + 0.4, 'PROD BUG USED WORKS ON MY MACHINE!'),
	(T_STRIKE + 0.2, "zapped: IT'S SUPER EFFECTIVE!"),
	(T_DUCK_OUT + 0.3, 'ITEM GET: RUBBER DUCK!'),
	(T_WEAK + 0.5, 'WEAK SPOT FOUND!'),
	(T_P2 + 0.6, 'PLAYER 2 HAS JOINED!'),
	(T_HIT + 0.08, 'double stomp: CRITICAL HIT! -9999'),
	(T_POOF + 0.2, 'poof'),
	(T_FEATURE + 0.5, "IT'S A FEATURE"),
	(T_FIXED + 0.5, 'BUG FIXED! +1000 XP'),
	(T_END + 1.5, "end card: WHAT'S YOUR FINAL BOSS BUG?"),
]

# --------------------------------------------------------------------------------------------
# The boss

BOSS_X0 = SAFE_X - AR.BOSS_W // 2   # its sprite's left edge
BOSS_TOP = 690


def boss_top(t: float) -> float:
	calm = 1 - seg(t, T_WEAK, T_WEAK + 0.4)  # locked on: it stops bobbing once the weak spot is found
	return BOSS_TOP + snap(math.sin(t * 2.6) * 12 * calm, 4)


def boss_look(t: float) -> dict:
	"""How the boss looks at ``t``: wings, mood, flash, charge and the squash of its cells."""
	charge = T_CHARGE <= t < T_BLOCKS[-1] or T_SPECIAL <= t < T_STRIKE
	dazed = t >= T_HIT + 0.12
	wing = None if dazed else int(t * (16 if charge else 9)) % 2
	mood = 'dazed' if dazed else 'roar' if (T_SPECIAL <= t < T_STRIKE + 0.3 or T_P2 <= t < T_P2 + 0.5) else 'angry'
	cell_h = AR.CELL
	if T_HIT <= t < T_HIT + 0.06:
		cell_h = 19
	elif T_HIT + 0.06 <= t < T_HIT + 0.14:
		cell_h = 22
	return dict(wing=wing, mood=mood, flash=T_HIT <= t < T_HIT + 0.12, charge=charge, cell_h=cell_h)


def boss_bottom(t: float) -> float:
	return boss_top(min(t, T_HIT)) + AR.BOSS_H


def boss_frame_top(t: float) -> float:
	"""The sprite's top edge: a squash keeps the bottom where it was."""
	look = boss_look(t)
	return boss_bottom(t) - 16 * look['cell_h']


def surface(x: float, t: float) -> float:
	"""The world y of the top of the boss's head or shell under ``x`` (where a pet's feet go)."""
	col = int((x - BOSS_X0) // AR.CELL) - 1
	col = max(0, min(AR.BW - 1, col))
	body = AR.SHELL | AR.HEAD
	rows = [r for r in range(AR.BH) if body[r, col]]
	row = rows[0] if rows else AR.BH - 1
	cell_h = boss_look(t)['cell_h']
	return boss_frame_top(t) + row * cell_h  # the outline row sits above: feet stand on it


T_SHRINK = T_POOF - 0.18


def draw_boss(img: Image.Image, t: float, sx: float, sy: float) -> None:
	if t >= T_POOF + 0.04:
		return
	if t >= T_SHRINK:  # it glows and shrinks into the poof, in whole-pixel steps
		cell = (20, 16, 12, 8, 4)[min(4, int((t - T_SHRINK) / 0.045))]
		spr = AR.boss_sprite(None, 'dazed', True, False, cell, cell)
		cx, cy = SAFE_X, boss_bottom(t) - AR.BOSS_H / 2
		blit(img, spr, snap(cx - spr.width / 2, 4) - sx, snap(cy - spr.height / 2, 4) - sy)
		return
	look = boss_look(t)
	spr = AR.boss_sprite(look['wing'], look['mood'], look['flash'], look['charge'], look['cell_h'])
	top = boss_frame_top(t)
	jitter = snap(math.sin(t * 70) * 6, 4) if T_HIT + 0.12 <= t < T_POOF else 0  # dazed wobble
	blit(img, spr, BOSS_X0 + jitter - sx, top - sy)
	if T_BOUNCE + 0.05 <= t < T_POOF:  # dizzy stars circling its head
		for k in range(3):
			a = t * 7 + k * math.tau / 3
			star = art.star(8)
			blit(img, star, snap(SAFE_X + math.cos(a) * 170 - star.width / 2 - sx, 4), snap(top - 10 + math.sin(a) * 30 - sy, 4))


# --------------------------------------------------------------------------------------------
# The pets

P1_START = 300
STARTLED = Hop(0.5, 0.78, 300, FLOOR, 230, FLOOR, 80, crouch=0.06)   # it sees the boss and hops back
T_WORRY = (0.9, 1.65)
READY = Hop(1.85, 2.15, 230, FLOOR, 300, FLOOR, 90)                     # FIGHT!: it steps up
DODGES = [Hop(2.62, 3.0, 300, FLOOR, 560, FLOOR, 130), Hop(3.12, 3.5, 560, FLOOR, 820, FLOOR, 130),
	Hop(3.62, 4.0, 820, FLOOR, 430, FLOOR, 170)]
ZAP_X = 430
DUCK_X = ZAP_X
BOX_X = DUCK_X + 190                    # the rubber-duck move's duck sits here
P1_READY = Hop(10.25, 10.65, 430, FLOOR, 220, FLOOR, 110)
P2_X = 860
STOMP_X = (SAFE_X - 100, SAFE_X + 100)
P1_JUMP = Hop(T_JUMP, T_HIT, 220, FLOOR, STOMP_X[0], 0, 0, crouch=0.14, recover=False)  # y1 and h set below
P2_JUMP = Hop(T_JUMP, T_HIT, P2_X, FLOOR, STOMP_X[1], 0, 0, crouch=0.14, recover=False)
for _hop, _x in ((P1_JUMP, STOMP_X[0]), (P2_JUMP, STOMP_X[1])):
	_hop.y1 = surface(_x, T_HIT)
	_hop.h = (FLOOR - _hop.y1) * 0.5 + 170
P1_BACK = Hop(T_BOUNCE, T_BOUNCE + 0.45, STOMP_X[0], P1_JUMP.y1, 220, FLOOR, 140, crouch=0.08)
P2_BACK = Hop(T_BOUNCE, T_BOUNCE + 0.45, STOMP_X[1], P2_JUMP.y1, P2_X, FLOOR, 140, crouch=0.08)
P1_END_X, P2_END_X = 380, 660
T_WIN = (T_FIXED, T_FIXED + 0.5)
P1_WIN = [Hop(tw, tw + 0.38, 220, FLOOR, 220, FLOOR, 200) for tw in T_WIN]
P2_WIN = [Hop(tw, tw + 0.38, P2_X, FLOOR, P2_X, FLOOR, 200) for tw in T_WIN]
P1_MEET = Hop(T_END + 0.15, T_END + 0.55, 220, FLOOR, P1_END_X, FLOOR, 120)
P2_MEET = Hop(T_END + 0.15, T_END + 0.55, P2_X, FLOOR, P2_END_X, FLOOR, 120)
P1_HOPS = [STARTLED, READY] + DODGES + [P1_READY, P1_JUMP, P1_BACK] + P1_WIN + [P1_MEET]
P2_HOPS = [P2_JUMP, P2_BACK] + P2_WIN + [P2_MEET]
BLINKS = [0.6, 1.5, 6.6, 9.9, 14.4, 17.2, 18.9]
BUTTERFLY_T0 = T_POOF + 0.2


T_PERCH = T_END + 1.3


def _flying(t: float) -> tuple:
	dt = t - BUTTERFLY_T0
	return SAFE_X + math.sin(dt * 1.7) * 220, 880 - 40 * min(1.0, dt / 1.2) + 40 * math.sin(dt * 3.4)


PERCH = (P1_END_X + 36, FLOOR - 192 - 70)  # on the Stable pet's head, between its antennae


def butterfly_pos(t: float) -> tuple:
	"""The butterfly flies out of the poof in loops, then glides down and perches on the Stable pet."""
	if t < T_END + 0.6:
		return _flying(t)
	x0, y0 = _flying(T_END + 0.6)
	u = smooth(seg(t, T_END + 0.6, T_PERCH))
	x = x0 + (PERCH[0] - x0) * u
	y = y0 + (PERCH[1] - y0) * u - math.sin(u * math.pi) * 90
	return x, y


def butterfly_wing(t: float) -> int:
	return int(t * (5 if t >= T_PERCH else 12)) % 4


def _gaze_at(px: float, py: float, tx: float, ty: float, facing: str) -> tuple:
	gx = clamp((tx - px) / 50, -4, 4)
	gy = clamp((ty - py) / 50, -4, 4)
	return (round(-gx if facing == 'left' else gx), round(gy))


def p1_pose(t: float) -> PetPose:
	blink = motion.blinking(t, BLINKS)
	facing = 'left' if (DODGES[2].t0 - DODGES[2].crouch <= t < DODGES[2].t1 + 0.15) or (P1_READY.t0 - 0.1 <= t < P1_READY.t1) else 'right'
	hop = motion.hop_pose(P1_HOPS, t, facing=facing)
	if hop is not None:
		hop.scale = SCALE
		if T_HIT <= t < T_BOUNCE and hop.name == 'jump':
			hop.y = surface(STOMP_X[0], t)
		return hop
	x, y = motion.ground_at(P1_HOPS, t, (P1_START, FLOOR))
	if T_HIT <= t < T_BOUNCE:
		y = surface(STOMP_X[0], t)
	if T_ZAP <= t < T_ZAP + P.total_ms('zapped') / 1000:
		return PetPose('zapped', P.frame_at('zapped', (t - T_ZAP) * 1000, loop=False), x, y, 'right', scale=SCALE)
	if T_DUCK <= t < T_DUCK + P.total_ms('rubber-duck') / 1000:
		return PetPose('rubber-duck', P.frame_at('rubber-duck', (t - T_DUCK) * 1000, loop=False), x, y, 'right', scale=SCALE)
	if T_WORRY[0] <= t < T_WORRY[1]:
		return PetPose('worry', P.frame_at('worry', (t - T_WORRY[0]) * 1000), x, y, 'right', scale=SCALE)
	if T_WIN[1] + 0.45 <= t < T_END - 0.05:
		return PetPose('clapping', P.frame_at('clapping', (t - T_FIXED) * 1000), x, y, 'right', gaze=(0, -2), blink=blink, scale=SCALE)
	target = (SAFE_X, boss_top(t) + 200)
	if T_BOX <= t < T_DUCK:
		target = box_pos(t)
	elif t >= BUTTERFLY_T0:
		target = butterfly_pos(t)
	return PetPose('idleTracking', P.frame_at('idle', t * 1000), x, y, facing, gaze=_gaze_at(x, y - 120, *target, facing), blink=blink, scale=SCALE)


def p2_pose(t: float) -> PetPose | None:
	if t < T_P2 + 0.35:
		return None
	blink = motion.blinking(t, [b + 0.4 for b in BLINKS])
	hop = motion.hop_pose(P2_HOPS, t, facing='left', variant='insiders')
	if hop is not None:
		hop.scale = SCALE
		if T_HIT <= t < T_BOUNCE and hop.name == 'jump':
			hop.y = surface(STOMP_X[1], t)
		return hop
	x, y = motion.ground_at(P2_HOPS, t, (P2_X, FLOOR))
	if T_HIT <= t < T_BOUNCE:
		y = surface(STOMP_X[1], t)
	if T_WIN[1] + 0.45 <= t < T_END - 0.05:
		return PetPose('clapping', P.frame_at('clapping', (t - T_FIXED) * 1000), x, y, 'left', gaze=(0, -2), blink=blink, variant='insiders', scale=SCALE)
	target = butterfly_pos(t) if t >= BUTTERFLY_T0 else (SAFE_X, boss_top(t) + 200)
	return PetPose('idleTracking', P.frame_at('idle', t * 1000), x, y, 'left', gaze=_gaze_at(x, y - 120, *target, 'left'), blink=blink, variant='insiders', scale=SCALE)


# --------------------------------------------------------------------------------------------
# Props and effects


def box_pos(t: float) -> tuple:
	"""The item box: it drops in from above and bounces once on the floor."""
	h = AR.prop('box').height
	rest = FLOOR - h
	if t < T_BOX_LAND:
		u = seg(t, T_BOX, T_BOX_LAND)
		return BOX_X, -120 + (rest + 120) * u * u
	dt = t - T_BOX_LAND
	return BOX_X, rest - (60 * math.sin(min(1.0, dt / 0.22) * math.pi) if dt < 0.22 else 0)


def error_blocks(img: Image.Image, t: float, sx: float, sy: float) -> None:
	spr = AR.prop('error')
	targets = [h.x0 for h in DODGES]  # each block falls where the pet was standing
	for t_hit, x in zip(T_BLOCKS, targets):
		t0 = t_hit - 0.42
		if t0 <= t < t_hit:
			u = seg(t, t0, t_hit)
			y0 = boss_top(t0) + AR.BOSS_H - 60
			y = y0 + (FLOOR - spr.height - y0) * u * u
			blit(img, spr, snap(x - spr.width / 2 - sx, 4), snap(y - sy, 4))
		dt = t - t_hit
		if 0 <= dt < 0.45:  # it shatters
			rng = random.Random(int(t_hit * 10))
			for _ in range(8):
				vx, vy = rng.uniform(-520, 520), rng.uniform(-620, -260)
				px, py = x + vx * dt, FLOOR - 40 + vy * dt + 1500 * dt * dt
				if py < FLOOR:
					fill_rect(img, snap(px - sx, 4), snap(py - sy, 4), 24, 24, hexc('#e5484d') if rng.random() < 0.6 else hexc('#ffffff'))


def draw_box(img: Image.Image, t: float, sx: float, sy: float) -> None:
	if not (T_BOX <= t < T_DUCK_OUT):
		return
	x, y = box_pos(t)
	spr = AR.prop('box')
	blit(img, spr, snap(x - spr.width / 2 - sx, 4), snap(y - sy, 4))


_BUTTERFLIES: dict = {}


def butterfly_sprite(frame: int) -> Image.Image:
	"""The kit's butterfly at twice its size (whole pixels), so the payoff reads on a phone."""
	if frame not in _BUTTERFLIES:
		im = art.butterfly(frame)
		_BUTTERFLIES[frame] = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
	return _BUTTERFLIES[frame]


def big_poof(img: Image.Image, t: float, t0: float, x: float, y: float, scale: int, sx: float, sy: float) -> None:
	"""The kit's transformation poof (pink and gold) at any whole scale."""
	if not (t0 <= t < t0 + sum(fx.POOF_STEPS)):
		return
	acc = t0
	for i, d in enumerate(fx.POOF_STEPS):
		if t < acc + d:
			im = fx.poof_frame(5 - i, scale)
			blit(img, im, round(x) - im.width // 2 - sx, round(y) - im.height // 2 - sy)
			return
		acc += d


def shake(t: float) -> tuple:
	dx, dy = 0.0, 0.0
	for (t0, amp) in ((T_BLOCKS[0], 8), (T_BLOCKS[1], 8), (T_BLOCKS[2], 8), (T_STRIKE, 16), (T_HIT, 26), (T_POOF, 10)):
		ox, oy = motion.shake(t, t0, 0.3, (amp, amp * 0.7))
		dx, dy = dx + ox, dy + oy
	return snap(dx, 4), snap(dy, 4)


CONFETTI = [(T_FIXED, fx.confetti_burst(5, SAFE_X, 1000, 60, 1.2))]

# --------------------------------------------------------------------------------------------
# Words

WHITE, GOLD, RED, CYAN = hexc('#ffffff'), hexc('#ffe14d'), hexc('#ff5a5f'), hexc('#6fe6cc')
BAND = (14, 8, 30, 205)
BANNERS = [  # (t0, t1, [(text, px, color)], band)
	(T_FIGHT, T_FIGHT + 0.55, [('FIGHT!', 16, GOLD)], BAND),
	(T_SPECIAL, T_STRIKE - 0.02, [('PROD BUG USED', 7, GOLD), ('WORKS ON MY', 11, WHITE), ('MACHINE!', 11, WHITE)], BAND),
	(T_EFFECTIVE, T_EFFECTIVE + 1.1, [("IT'S SUPER", 12, RED), ('EFFECTIVE!', 12, RED)], BAND),
	(T_DUCK_OUT, T_WEAK + 0.02, [('ITEM GET:', 8, GOLD), ('RUBBER DUCK!', 12, WHITE)], BAND),
	(T_WEAK + 0.05, T_P2 + 0.25, [('WEAK SPOT', 12, GOLD), ('FOUND!', 12, GOLD)], BAND),
	(T_P2 + 0.25, T_JUMP - 0.05, [('PLAYER 2', 12, CYAN), ('HAS JOINED!', 12, WHITE)], BAND),
	(T_HIT, T_HIT + 0.9, [('CRITICAL HIT!', 11, GOLD)], BAND),
	(T_NOT_BUG, T_FEATURE, [("IT'S NOT", 12, WHITE), ('A BUG...', 12, WHITE)], BAND),
	(T_FEATURE, T_FIXED, [("IT'S A", 12, CYAN), ('FEATURE ✨', 12, CYAN)], BAND),
	(T_FIXED, T_END, [('BUG FIXED!', 12, GOLD), ('+1000 XP', 8, WHITE)], BAND),
]


def banners(img: Image.Image, t: float) -> None:
	for (t0, t1, lines, band) in BANNERS:
		if not (t0 <= t < t1):
			continue
		k = min(1.0, (t - t0) / 0.1)
		offset = snap((1 - ease_out(k)) * -700, 8)
		height = sum(9 * px + 24 for (_, px, _) in lines) + 32
		top = 388
		fill_rect(img, offset, top - 16, W, height, band)
		for edge in (top - 16, top - 16 + height - 6):
			fill_rect(img, offset, edge, W, 6, lines[0][2])
		y = top
		for (text, px, color) in lines:
			world.outlined_text(img, text, snap(SAFE_X + offset - world.text_width(text, px) / 2, 2), y, px, color, width=max(3, px // 2))
			y += 9 * px + 24


def hud(img: Image.Image, t: float) -> None:
	if t < T_END:
		hp = 1 - smooth(seg(t, T_HIT + 0.05, T_HIT + 0.45))
		ghost = 1 - smooth(seg(t, T_HIT + 0.5, T_HIT + 0.9))
		slide = seg(t, T_POOF + 0.3, T_POOF + 0.6) * 200 + (1 - ease_out(seg(t, T_FIGHT - 0.1, T_FIGHT + 0.15))) * 200
		if slide < 200:
			AR.boss_bar(img, hp, ghost, 'PROD BUG', 'FINAL BOSS', slide)
		AR.hearts(img, 84, 'P1', hexc('#23a8f2'), 2 if t >= T_STRIKE else 3, broken_at=T_STRIKE, t=t)
		if t >= T_P2 + 0.35:
			AR.hearts(img, 560, 'P2', hexc('#24bfa5'), 3)
	if t < T_FIGHT:  # the hook, whole from the first frame
		y = SAFE[1] + 36
		for (text, color) in (('POV: THE BUG', WHITE), ('ONLY HAPPENS', WHITE), ('IN PROD', RED)):
			y = world.caption(img, text, y, SAFE_X, SAFE_W, color=color, sizes=(12,)) + 24
	for t_hit, hop in zip(T_BLOCKS, DODGES):
		AR.pop(img, t, t_hit, 'MISS!', hop.x0, FLOOR - 250, WHITE, px=8)
	AR.pop(img, t, T_STRIKE, '-1', ZAP_X + 150, FLOOR - 300, RED, px=10)
	AR.pop(img, t, T_HIT + 0.08, '-9999', SAFE_X, boss_top(T_HIT) + AR.BOSS_H + 40, GOLD, px=14, life=1.1, rise=110)
	if t >= T_END:
		y = world.caption(img, "WHAT'S YOUR", SAFE[1] + 60, SAFE_X, SAFE_W, sizes=(14, 12))
		world.caption(img, 'FINAL BOSS BUG?', y + 28, SAFE_X, SAFE_W, color=GOLD, sizes=(9,))
		if t >= T_END + 0.5:
			pop_in = ease_out_back(seg(t, T_END + 0.5, T_END + 0.7))
			world.caption(img, 'COMMENT BELOW!', 1470 + snap((1 - pop_in) * 30, 4), SAFE_X, SAFE_W, sizes=(10,))


# --------------------------------------------------------------------------------------------
# Picture


def render(t: float) -> Image.Image:
	img = Image.new('RGBA', SIZE)
	sx, sy = shake(t)
	healthy = 1.0 if t >= T_POOF + 0.1 else 0.0
	AR.room(img, t, sx, sy, alarm=0.0 if healthy else 1.0, healthy=healthy)
	draw_boss(img, t, sx, sy)
	if T_WEAK + 0.05 <= t < T_HIT:  # the weak spot, pulsing on its head
		ret = AR.reticle(int(t * 4) % 2 == 0)
		blit(img, ret, SAFE_X - ret.width // 2 - sx, snap(boss_frame_top(t) + 50 - ret.height / 2, 4) - sy)
	big_poof(img, t, T_POOF, SAFE_X, BOSS_TOP + AR.BOSS_H / 2, 5, sx, sy)
	error_blocks(img, t, sx, sy)
	draw_box(img, t, sx, sy)
	big_poof(img, t, T_DUCK_OUT - 0.04, BOX_X, FLOOR - 60, 2, sx, sy)
	big_poof(img, t, T_DUCK_GONE, BOX_X, FLOOR - 70, 2, sx, sy)
	if T_P2 <= t < T_P2 + P.total_ms('respawn') / 1000:
		fx.respawn(img, t - T_P2, P2_X, FLOOR - 96, sx, sy, 'insiders', 2)
	for pose in (p2_pose(t), p1_pose(t)):
		if pose is not None:
			P.draw_pose(img, pose, sx, sy)
	fx.dust(img, t, motion.landings([STARTLED, READY] + DODGES + [P1_READY, P1_BACK, P2_BACK] + P1_WIN + P2_WIN + [P1_MEET, P2_MEET]), sx, sy, color=hexc('#c9cde6'))
	for (t0, strength) in ((T_JUMP, 1.0),):
		if t0 <= t < T_HIT:
			AR.speed_lines(img, t, STOMP_X[0], P1_JUMP.pos(t)[1], 'right', strength)
	if t >= BUTTERFLY_T0:
		bx, by = butterfly_pos(t)
		spr = butterfly_sprite(butterfly_wing(t))
		blit(img, spr, snap(bx - spr.width / 2 - sx, 4), snap(by - spr.height / 2 - sy, 4))
		if t < T_PERCH:  # a sparkle trail
			for k in range(1, 5):
				px, py = butterfly_pos(t - k * 0.07)
				fx.sparkle(img, px - sx, py + 40 - sy, 12 - 2 * k, (255, 240, 170, 230 - 45 * k))
	fx.confetti(img, t, CONFETTI, sx, sy)
	fx.flash(img, t, T_HIT, 0.12, (255, 214, 140), strength=0.4)    # partial flashes: a punch, not a white-out
	fx.flash(img, t, T_STRIKE, 0.1, (220, 228, 255), strength=0.4)
	banners(img, t)
	hud(img, t)
	return img


# --------------------------------------------------------------------------------------------
# Score: an E minor boss battle, then a C major victory.


def music(mix: A.Mixer) -> None:
	n, put, bt = A.n, mix.put, mix.beat
	# The hook: an alarm and a low drone.
	for k in range(4):
		put(A.lead(n('A5') if k % 2 == 0 else n('E5'), 0.22, 0.5), k * 0.45, 0.05, pan=-0.3 if k % 2 else 0.3)
	put(A.bass(n('E2'), 1.7), 0.0, 0.2)
	# The battle: Em - C - D - B, eighth-note bass, sixteenth hats.
	chords = [('E2', 'E5'), ('C2', 'E5'), ('D2', 'F#5'), ('B1', 'D#5')]
	riff = [0, 12, 0, 10, 0, 12, 7, 10]
	def battle(b0: float, b1: float, gain: float = 1.0) -> None:
		b, k = b0, 0
		while b < b1 - 1e-6:
			root = n(chords[int((b - b0) // 4) % 4][0])
			put(A.bass(root + riff[k % 8], 0.2), bt(b), 0.22 * gain)
			b += 0.5
			k += 1
		A.groove(mix, b0, b1, hats16=True, soft=gain)
	battle(T_FIGHT * 2 + 0.4, T_SPECIAL * 2)
	theme = [(0, .5, 'E5'), (.5, .5, 'G5'), (1, .5, 'B5'), (1.5, .5, 'A5'), (2, 1, 'G5'), (3, .5, 'F#5'), (3.5, .5, 'E5'),
		(4, .5, 'C5'), (4.5, .5, 'E5'), (5, 1, 'G5'), (6, .5, 'F#5'), (6.5, .5, 'D5'), (7, 1, 'B4')]
	mix.melody([(T_FIGHT * 2 + 0.4 + b, d, nm) for (b, d, nm) in theme], 0, 'lead', 0.10)
	# The special attack: a tense pedal and a roll.
	for k in range(4):
		put(A.bass(n('E2'), 0.2), T_SPECIAL + k * 0.2, 0.2)
	A.roll(mix, T_SPECIAL * 2, T_SPECIAL * 2 + 1.5, 0.05, 0.25)
	# After the zap: a low heartbeat groove, waiting for a plan.
	A.groove(mix, T_STRIKE * 2 + 1, T_DUCK * 2 + 1, soft=0.7)
	b, k = T_STRIKE * 2 + 1, 0
	while b < T_DUCK * 2 + 1:
		put(A.bass(n(['E2', 'E2', 'C2', 'D2'][(k // 2) % 4]), 0.3), bt(b), 0.22)
		b += 0.5
		k += 1
	mix.melody([(T_STRIKE * 2 + 1.5, 1, 'B4'), (T_STRIKE * 2 + 2.5, .5, 'G4'), (T_STRIKE * 2 + 3, 1, 'F#4')], 0, 'pluck', 0.10)
	# Item get and the rubber duck: lighter, then the battle again.
	for i, nm in enumerate(['C6', 'E6', 'G6', 'C7']):
		put(A.bell(n(nm), 0.5), T_DUCK_OUT + i * 0.09, 0.09)
	battle(T_DUCK * 2 + 1, T_P2 * 2, 0.7)
	# Player 2: the battle comes back fuller, a rising roll into the jump.
	battle(T_P2 * 2, T_JUMP * 2)
	mix.melody([(T_P2 * 2 + b, d, nm) for (b, d, nm) in theme[:6]], 0, 'lead', 0.11)
	A.roll(mix, T_JUMP * 2 - 0.1, T_HIT * 2, 0.1, 0.4)
	put(A.sweep(200, 1600, T_HIT - T_JUMP, 'pulse', 0.25, curve=2.0), T_JUMP, 0.05)
	# The hit: a crash, then silence while the health drains.
	put(A.crash(0.35), T_HIT + 0.02, 0.6)
	put(A.sweep(900, 120, 0.45, 'tri'), T_HIT + 0.05, 0.12)
	# The butterfly: magic bells in C over a soft pad; "it's a feature"; the victory fanfare and a happy groove.
	for i, nm in enumerate(['C4', 'E4', 'G4']):
		put(A.lead(n(nm), T_FIXED - T_POOF, 0.125, 0.006), T_POOF + 0.1, 0.022, pan=(i - 1) * 0.3)
	put(A.bass(n('C3'), T_FIXED - T_POOF), T_POOF + 0.1, 0.10)
	for i, nm in enumerate(['C6', 'E6', 'G6', 'B6', 'C7', 'E7']):
		put(A.bell(n(nm), 0.9), T_POOF + 0.05 + i * 0.08, 0.08, pan=(i - 2.5) * 0.15)
	for i, nm in enumerate(['C5', 'E5', 'G5', 'C6']):
		put(A.bell(n(nm), 1.2), T_FEATURE + i * 0.12, 0.08)
	fanfare = [(0, .25, 'C6'), (.25, .25, 'C6'), (.5, .25, 'C6'), (.75, .75, 'E6'), (1.5, .5, 'D6'), (2, .5, 'E6'), (2.5, 1.5, 'G6')]
	mix.melody([(T_FIXED * 2 + b, d, nm) for (b, d, nm) in fanfare], 0, 'lead', 0.14)
	mix.melody([(T_FIXED * 2 + b, d, nm[:-1] + str(int(nm[-1]) - 1)) for (b, d, nm) in fanfare], 0, 'lead', 0.07, pan=0.2)
	b, k = T_FIXED * 2, 0
	happy = ['C3', 'C3', 'A2', 'A2', 'F2', 'F2', 'G2', 'G2']
	while b < DURATION * 2 - 1:
		root = n(happy[(k // 4) % 8])
		put(A.bass(root if k % 2 == 0 else root + 12, 0.2), bt(b), 0.2)
		b += 0.5
		k += 1
	A.groove(mix, T_FIXED * 2, DURATION * 2 - 1, soft=0.8)
	outro = [(0, .5, 'E5'), (.5, .5, 'G5'), (1, .5, 'C6'), (1.5, .5, 'G5'), (2, .5, 'A5'), (2.5, .5, 'C6'), (3, 1, 'E6'),
		(4, .5, 'D6'), (4.5, .5, 'C6'), (5, .5, 'A5'), (5.5, .5, 'G5'), (6, 1.5, 'C6')]
	mix.melody([(T_END * 2 + b, d, nm) for (b, d, nm) in outro], 0, 'lead', 0.10)


def sound_effects(mix: A.Mixer) -> None:
	n, put = A.n, mix.put
	put(A.boing(), STARTLED.t0, 0.08)                                     # startled!
	put(A.blip(n('E6'), 0.06), STARTLED.t0, 0.06)
	put(A.land(), STARTLED.t1, 0.10)
	put(A.boing(), READY.t0, 0.08)
	put(A.land(), READY.t1, 0.12)
	put(A.crash(0.25), T_FIGHT, 0.6)
	put(A.blip(n('E6'), 0.08), T_FIGHT, 0.12)
	put(A.blip(n('B6'), 0.18), T_FIGHT + 0.08, 0.12)
	put(A.sweep(300, 1200, 0.6, 'pulse', 0.25), T_CHARGE, 0.05)       # the boss charges up
	for h, t_hit in zip(DODGES, T_BLOCKS):
		put(A.boing(), h.t0, 0.10)
		put(A.land(), h.t1, 0.12)
		put(A.sweep(1500, 500, 0.4, 'sine') * 0.6, t_hit - 0.42, 0.05)  # the block whistles down
		put(A.kick(0.8), t_hit, 0.3)
		put(A.noise_burst(0.15, 1200, 18), t_hit, 0.18)
		put(A.blip(n('A6'), 0.05), t_hit + 0.05, 0.07)                  # MISS!
	put(A.whoosh(0.4), T_SPECIAL, 0.14)
	put(A.lead(n('E3'), 0.35, 0.5, vib=0.03), T_SPECIAL + 0.05, 0.12)   # the boss roars
	put(A.noise_burst(0.35, 150, 9), T_STRIKE, 0.34)                   # the lightning (the zapped move's own strike)
	put(A.crash(0.25), T_STRIKE, 0.8)
	put(A.sweep(95, 120, 0.3, duty=0.5), T_STRIKE + 0.1, 0.10)
	for i, nm in enumerate(['E5', 'C5', 'A4']):                          # a heart lost
		put(A.blip(n(nm), 0.08), T_STRIKE + 0.2 + i * 0.09, 0.08)
	put(A.whoosh(0.3), T_BOX, 0.12)
	put(A.land(), T_BOX_LAND, 0.24)
	put(A.coin(), T_DUCK_OUT - 0.04, 0.12)
	for frame in (5, 8):                                                   # squeak!
		put(A.sweep(1400, 2300, 0.12, duty=0.25), T_DUCK + sum(P.durations('rubber-duck')[:frame - 1]) / 1000, 0.14, pan=0.3)
	put(A.bell(n('E7'), 0.6), T_WEAK + 0.05, 0.10)                        # weak spot found
	put(A.twinkle(['E6', 'G6', 'B6', 'E7']), T_WEAK + 0.1, 0.07)
	put(A.whoosh(0.5), T_P2, 0.18)                                          # player 2 joins
	put(A.twinkle(['C6', 'E6', 'G6', 'C7']), T_P2 + 0.15, 0.10)
	put(A.boing(), P1_READY.t0, 0.09)
	put(A.land(), P1_READY.t1, 0.12)
	put(A.spring(), T_JUMP, 0.2)
	put(A.boing(), T_JUMP, 0.14)
	put(A.kick(1.0), T_HIT, 0.42)                                           # CRITICAL HIT
	put(A.bonk(), T_HIT + 0.012, 0.34)
	put(A.noise_burst(0.3, 400, 10), T_HIT + 0.024, 0.2)
	for h in (P1_BACK, P2_BACK):
		put(A.boing(), h.t0, 0.08)
		put(A.land(), h.t1, 0.14)
	put(A.sweep(300, 2400, T_POOF - T_SHRINK, 'pulse', 0.25, curve=2.0), T_SHRINK, 0.06)  # it glows and shrinks ...
	put(A.noise_burst(0.4, 1500, 6), T_POOF, 0.10)                          # ... poof
	put(A.twinkle(['C7', 'E7', 'G7', 'C8']), T_POOF + 0.1, 0.08)
	put(A.coin(), T_FIXED + 0.1, 0.12)                                      # +1000 XP
	put(A.coin(), T_FIXED + 0.22, 0.10)
	for h in P1_WIN:                                                          # victory hops
		put(A.boing(), h.t0, 0.10)
		put(A.land(), h.t1, 0.14)
	for k in range(4):                                                        # claps
		put(A.noise_burst(0.05, 1800, 60), T_WIN[1] + 0.5 + k * 0.12, 0.06, pan=0.3 if k % 2 else -0.3)
	for h in (P1_MEET,):
		put(A.boing(), h.t0, 0.09)
		put(A.land(), h.t1, 0.12)
	put(A.twinkle(['C6', 'E6', 'G6', 'C7']), T_END, 0.08)


def score(mix: A.Mixer) -> None:
	music(mix)
	sound_effects(mix)
