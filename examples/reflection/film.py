"""reflection: "WATCH THE REFLECTION", a 17 s vertical (9:16) reel.

A night pond. The Stable (blue) pet sits on a lily pad, and its reflection copies it perfectly...
until it doesn't: the reflection waves first, then hops before the pet does. It's early. The
reflection glitches green, leaps out of the water and lands on the next lily pad: it's the
Insiders pet, and it puts on its sunglasses: "I'M FROM INSIDERS. I GET EVERY UPDATE FIRST."
The end card asks the comments: which team are you?

It shows how to make a "wait for it" reel: water that mirrors one layer of everything above it
(pond.py), a reflection with its own timeline that drifts out of sync with the pet, a glitch
from sliced bands and noise, a character climbing out through the surface, and two pets as two
teams.

    python3 -m kit film sheet reflection
    python3 -m kit film review reflection
"""

from __future__ import annotations

import math
import random

import numpy as np
from PIL import Image

import pond
from kit import art, layout, moves, motion, world
from kit import audio as A
from kit import pet as P
from kit.draw import blit, ease_out_back, fill_rect, hexc, seg, snap
from kit.font import text_width
from kit.motion import Hop
from kit.pet import PetPose

TITLE = 'Watch the reflection'
W, H = SIZE = (1080, 1920)
FPS = 60
BPM = 120
DURATION = 17.0
MASTER = {'ceiling': 0.72, 'drive': 2.4, 'fade_out': 0.6}  # true peak under -1 dBTP after AAC
SAFE = layout.safe_area(SIZE)  # (60, 260, 960, 1600)
SAFE_X = (SAFE[0] + SAFE[2]) // 2
SAFE_W = SAFE[2] - SAFE[0]
SCALE = 3

moves.use('wave')

# --------------------------------------------------------------------------------------------
# Timeline (seconds, on a 120 BPM grid once the Insiders pet is out)

T_ODD_BLINK = 0.85        # a rewatch easter egg: the reflection blinks on its own
T_LOOK = (1.0, 1.5)       # the pet looks left, then right; the reflection copies
T_REF_WAVE = 1.8          # the reflection waves... first
T_NOTICE = 2.5            # the pet notices: "?"
T_PET_WAVE = 3.4          # the pet waves, late; the reflection just watches
T_REF_HOP = 4.9           # the reflection hops... early
T_PET_HOP = 5.75          # the pet hops; the reflection doesn't
T_LEAN = 6.4              # the pet leans in; the reflection stops copying and stares
T_GLITCH = 7.0            # the reflection glitches green
T_LEAP = 7.5              # splash: the Insiders pet leaps out
T_LAND = 8.0              # and lands on the other lily pad (the beat drops)
T_COOL = 8.3              # sunglasses on
T_SAY1 = 9.5
T_SAY2 = 11.0
T_END = 13.5              # the end card
SUNGLASSES_ON = T_COOL + sum(P.durations('cool')[:4]) / 1000

SAY1 = "I'M FROM\nINSIDERS!"
SAY2 = 'I GET EVERY\nUPDATE FIRST'

CUES = [
	(0.0, 'hook: WATCH THE REFLECTION'),
	(T_REF_WAVE + 0.5, 'the reflection waves first'),
	(T_PET_WAVE + 0.6, 'the pet waves, late'),
	(T_REF_HOP + 0.25, 'the reflection hops early'),
	(T_PET_HOP + 0.3, "the pet hops: IT'S... EARLY?!"),
	(T_LEAN + 0.3, 'the pet leans in; the reflection stares'),
	(T_GLITCH + 0.25, 'glitch: WHO ARE YOU?!'),
	(T_LEAP + 0.25, 'splash: the Insiders pet leaps out'),
	(SUNGLASSES_ON + 0.1, 'sunglasses on'),
	(T_SAY1 + 0.7, "I'M FROM INSIDERS!"),
	(T_SAY2 + 0.9, 'I GET EVERY UPDATE FIRST'),
	(T_END + 1.0, 'end card: WHICH TEAM ARE YOU?'),
]

# --------------------------------------------------------------------------------------------
# The pets

PX1, PX2 = 300, 680                  # the two lily pads
FEET = pond.PAD_TOP
HEAD = 96 * SCALE
T_OWN_BLINK = 6.55  # the pet blinks as it leans in; the reflection doesn't
BLINKS = [1.85, 4.55, T_OWN_BLINK, 9.2, 12.0, 14.3, 15.6]
PET_HOP = Hop(T_PET_HOP, T_PET_HOP + 0.45, PX1, FEET, PX1, FEET, 110)
REF_HOP = Hop(T_REF_HOP, T_REF_HOP + 0.45, PX1, FEET, PX1, FEET, 110)
LEAP = Hop(T_LEAP, T_LAND, PX1 + 150, FEET + 170, PX2, FEET, 520, crouch=0.0)
END_HOP = Hop(15.0, 15.45, PX1, FEET, PX1, FEET, 110)


def _scaled(pose: PetPose | None, variant: str = 'stable') -> PetPose | None:
	if pose is not None:
		pose.scale = SCALE
		pose.variant = variant
	return pose


def stable_pose(t: float) -> PetPose:
	"""The Stable (blue) pet on the left lily pad."""
	blink = motion.blinking(t, BLINKS)
	hop = _scaled(motion.hop_pose([PET_HOP, END_HOP], t))
	if hop is not None:
		return hop
	idle = lambda gaze, facing='right': PetPose('idleTracking', P.frame_at('idle', t * 1000), PX1, FEET, facing, gaze=gaze, blink=blink, scale=SCALE)
	if t < T_LOOK[0]:
		return idle((0, 0))
	if t < T_LOOK[1]:
		return idle((-4, 0))
	if t < T_REF_WAVE:
		return idle((4, 0))
	if t < T_NOTICE:
		return idle((0, 0))  # it hasn't noticed yet
	if t < T_PET_WAVE:
		return idle((0, 4))  # looks down at the water
	if t < T_PET_WAVE + P.total_ms('wave') / 1000:
		return PetPose('wave', P.frame_at('wave', (t - T_PET_WAVE) * 1000, loop=False), PX1, FEET, scale=SCALE)
	if t < T_LEAN:
		return idle((0, 4))
	if t < T_LEAP:
		return idle((0, 4))  # peers down at the water, while the reflection stares out at you
	if t < T_LEAP + 0.25:
		return PetPose('worry', P.frame_at('worry', (t - T_LEAP) * 1000), PX1, FEET, scale=SCALE)
	if t < T_LAND + 0.5:
		return idle((4, -4))  # follows the Insiders pet through the air
	if T_SAY2 + 0.5 <= t < T_END:
		return PetPose('speechless', P.frame_at('speechless', (t - T_SAY2 - 0.5) * 1000, loop=False), PX1, FEET, scale=SCALE)
	if T_END + 0.2 <= t < T_END + 0.2 + P.total_ms('wave') / 1000:
		return PetPose('wave', P.frame_at('wave', (t - T_END - 0.2) * 1000, loop=False), PX1, FEET, scale=SCALE)
	return idle((4, 0) if t < T_END else (0, 0))


def reflection_pose(t: float) -> tuple:
	"""What the water shows under the Stable pet: ``(pose, variant)``. Until the leap, it's the
	Insiders pet pretending to be a reflection, and it's a little early."""
	if t >= T_LEAP:
		return stable_pose(t), 'stable'
	blink = motion.blinking(t, [b for b in BLINKS if b != T_OWN_BLINK]) or (T_ODD_BLINK <= t < T_ODD_BLINK + 0.13)
	idle = lambda gaze: PetPose('idleTracking', P.frame_at('idle', t * 1000), PX1, FEET, gaze=gaze, blink=blink, scale=SCALE)
	if T_GLITCH <= t:
		k = t - T_GLITCH
		variant = 'insiders' if k > 0.3 or int(k * 12) % 2 else 'stable'
		return idle((0, 0)), variant
	if T_LEAN <= t:
		return idle((0, 0)), 'stable'  # it stops copying and stares at you
	if T_REF_WAVE <= t < T_REF_WAVE + P.total_ms('wave') / 1000:
		return PetPose('wave', P.frame_at('wave', (t - T_REF_WAVE) * 1000, loop=False), PX1, FEET, scale=SCALE), 'stable'
	if T_PET_WAVE <= t < T_REF_HOP - REF_HOP.crouch:
		return idle((0, 4)), 'stable'  # watches the pet wave (it did that already)
	hop = motion.hop_pose([REF_HOP], t)
	if hop is not None:
		hop.scale = SCALE
		return hop, 'stable'
	if T_REF_HOP <= t < T_LEAN:
		return idle((0, 4)), 'stable'  # already hopped: it just watches the pet hop
	pose = stable_pose(t)
	pose.blink = blink if pose.name == 'idleTracking' else pose.blink
	return pose, 'stable'


def insiders_pose(t: float) -> PetPose | None:
	"""The Insiders (green) pet, once it's out of the water."""
	if t < T_LEAP:
		return None
	hop = _scaled(motion.hop_pose([LEAP], t, variant='insiders'), 'insiders')
	if hop is not None:
		if t >= T_LAND:
			hop.facing = 'left'
		return hop
	if t < T_COOL:
		return PetPose('idleTracking', P.frame_at('idle', t * 1000), PX2, FEET, 'left', gaze=(4, 0), blink=motion.blinking(t, [8.15]), variant='insiders', scale=SCALE)
	ms = (t - T_COOL) * 1000
	if ms < P.total_ms('cool') or t < T_END:
		return PetPose('cool', P.frame_at('cool', ms, loop=False), PX2, FEET, 'left', variant='insiders', scale=SCALE)
	glint = P.durations('cool')[4:]  # the end card: the glint keeps sweeping across the shades
	k = ((t - T_END) * 1000) % sum(glint)
	frame = 4
	for d in glint:
		if k < d:
			break
		k -= d
		frame += 1
	return PetPose('cool', min(frame, 8), PX2, FEET, 'left', variant='insiders', scale=SCALE)


# --------------------------------------------------------------------------------------------
# Picture


def draw_glitched(layer: Image.Image, pose: PetPose, t: float) -> None:
	"""The fake reflection during the glitch: sliced into bands that jump sideways, with noise."""
	tmp = Image.new('RGBA', SIZE)
	P.draw_pose(tmp, pose)
	arr = np.asarray(tmp).copy()
	rng = random.Random(int(t * 30))
	top = FEET - HEAD
	for y0 in range(top, FEET, 24):
		if rng.random() < 0.45:
			arr[y0:y0 + 24] = np.roll(arr[y0:y0 + 24], rng.choice((-36, -24, -12, 12, 24, 36)), axis=1)
	layer.alpha_composite(Image.fromarray(arr))
	for _ in range(6):
		x = PX1 + rng.randrange(-190, 170)
		y = rng.randrange(top, FEET)
		fill_rect(layer, snap(x, 12), snap(y, 12), rng.choice((12, 24, 48)), 12, hexc(rng.choice(('#24bfa5', '#23a8f2', '#9affe6'))))


def draw_insiders(img: Image.Image, t: float, reflected: bool) -> None:
	pose = insiders_pose(t)
	if pose is None:
		return
	if t < T_LEAP + 0.12:  # still coming out of the water: only the part above the surface shows
		tmp = Image.new('RGBA', SIZE)
		P.draw_pose(tmp, pose)
		tmp.paste((0, 0, 0, 0), (0, pond.WATER_Y, W, H))
		if not reflected:
			img.alpha_composite(tmp)
		return
	P.draw_pose(img, pose)


def caption(img: Image.Image, t: float) -> None:
	top = SAFE[1] + 40
	if t < T_REF_WAVE + 0.3:  # whole from the first frame: the thumbnail
		bottom = world.caption(img, 'WATCH THE REFLECTION', top, SAFE_X, SAFE_W, sizes=(16, 12))
		world.caption(img, '(wait for it)', bottom + 28, SAFE_X, SAFE_W, color=hexc('#ffe070'), sizes=(8,))
	elif t < T_REF_HOP - 0.2:
		world.caption(img, 'IT WAVED FIRST?!', top, SAFE_X, SAFE_W, sizes=(16, 12))
	elif t < T_PET_HOP - 0.2:
		world.caption(img, 'AND AGAIN?!', top, SAFE_X, SAFE_W, sizes=(16, 12))
	elif T_PET_HOP - 0.2 <= t < T_LEAN + 0.25:
		world.caption(img, "IT'S... EARLY?!", top, SAFE_X, SAFE_W, sizes=(16, 12))
	elif T_LEAN + 0.25 <= t < T_LEAP:
		glitching = t >= T_GLITCH and int((t - T_GLITCH) * 6) % 2 == 1  # a jolt every third of a second
		world.caption(img, 'WHO ARE YOU?!', top, SAFE_X + (12 if glitching else 0), SAFE_W, color=hexc('#9affe6'), sizes=(16, 12))
	elif t >= T_END:
		pop = snap((1 - ease_out_back(seg(t, T_END, T_END + 0.25))) * -40, 4)
		world.caption(img, 'WHICH TEAM ARE YOU?', top + pop, SAFE_X, SAFE_W, sizes=(16, 12))


def team_tag(img: Image.Image, x: float, y: float, text: str, color: tuple, pop: float, px: int = 9) -> None:
	"""A team tag: the team's name on a dark panel with a border in its color."""
	w = text_width(text, px) + 64
	lift = snap((1 - pop) * 40, 4)
	world.panel(img, x - w / 2, y + lift, x + w / 2, y + 9 * px + 40 + lift, (14, 16, 44, 235), color)
	world.outlined_text(img, text, snap(x - text_width(text, px) / 2, 2), y + 24 + lift, px, color, width=3)


def end_labels(img: Image.Image, t: float) -> None:
	"""The team tags under each pet's reflection, and the call to comment."""
	if t < T_END + 0.3:
		return
	team_tag(img, 262, 1290, 'STABLE', hexc('#23a8f2'), ease_out_back(seg(t, T_END + 0.3, T_END + 0.5)), px=8)
	team_tag(img, 712, 1290, 'INSIDERS', hexc('#24bfa5'), ease_out_back(seg(t, T_END + 0.45, T_END + 0.65)), px=8)
	if t >= T_END + 0.9:
		world.caption(img, 'COMMENT BELOW!', 1440, SAFE_X, SAFE_W, sizes=(10, 8))


def bubbles(img: Image.Image, t: float) -> None:
	head = FEET - HEAD
	if T_SAY1 <= t < T_SAY2:
		world.say(img, SAY1, 600, head - 48, PX2 - 20, px=12, reveal=seg(t, T_SAY1, T_SAY1 + 0.5))
	elif T_SAY2 <= t < T_END:
		world.say(img, SAY2, 560, head - 48, PX2 - 20, px=10, reveal=seg(t, T_SAY2, T_SAY2 + 0.6))


def render(t: float) -> Image.Image:
	top = pond.above(t)
	# What the water reflects: the scenery, the reflection under the Stable pet, and the Insiders pet.
	mirror = top.copy()
	ref, variant = reflection_pose(t)
	ref.variant = variant
	if T_GLITCH <= t < T_LEAP:
		draw_glitched(mirror, ref, t)
	else:
		P.draw_pose(mirror, ref)
	draw_insiders(mirror, t, reflected=True)
	stir = 18 * math.exp(-(t - T_LEAP) * 2.2) if t >= T_LEAP else 0.0
	water = pond.reflect(mirror, t, stir)
	img = top
	img.paste(water, (0, pond.WATER_Y))
	pond.moon_glints(img, t)
	pond.ripple_ring(img, t, T_LEAP, PX1 + 150, big=True)
	pond.ripple_ring(img, t, T_LEAP + 0.25, PX1 + 150, big=True)
	pond.ripple_ring(img, t, T_LAND, PX2)
	for (tl, x) in ((PET_HOP.t1, PX1), (REF_HOP.t1, PX1), (END_HOP.t1, PX1)):
		pond.ripple_ring(img, t, tl, x, life=0.8)
	# On the surface: the lily pads and a lotus, then the pets.
	pond.pad(img, 130, small=True)
	blit(img, pond.sprite('lotus'), 130 - pond.sprite('lotus').width // 2, pond.WATER_Y - 2 * pond.CELL - pond.sprite('lotus').height + 12)
	pond.pad(img, PX1, dip=pad_dip(t, [PET_HOP.t1, END_HOP.t1]))
	pond.pad(img, PX2, dip=pad_dip(t, [T_LAND]))
	pond.pad(img, 1000, small=True)
	emerging = t < T_LEAP + 0.12
	if emerging:  # it bursts up right behind the Stable pet
		draw_insiders(img, t, reflected=False)
	pond.splash(img, t, T_LEAP, PX1 + 150)
	P.draw_pose(img, stable_pose(t))
	if not emerging:
		draw_insiders(img, t, reflected=False)
	if T_NOTICE <= t < T_PET_WAVE - 0.1:  # "?" beside its head
		k = seg(t, T_NOTICE, T_NOTICE + 0.12)
		world.outlined_text(img, '?', PX1 + 160, FEET - HEAD + 20 + snap((1 - k) * 30, 4), 16, hexc('#ffe070'))
	if T_LEAP + 0.02 <= t < T_LEAP + 0.6:  # "!" beside its head
		bang = art.bang(24)
		lift = int((1 - ease_out_back(seg(t, T_LEAP + 0.02, T_LEAP + 0.14))) * 3) * 24
		blit(img, bang, PX1 - 150 - bang.width // 2, FEET - HEAD - 40 + lift)
	if T_GLITCH + 0.05 <= t < T_GLITCH + 0.45 and int((t - T_GLITCH) * 20) % 3 == 0:  # static on the water
		rng = random.Random(int(t * 60))
		for _ in range(5):
			fill_rect(img, snap(rng.randrange(80, 1000), 12), snap(rng.randrange(pond.WATER_Y + 20, 1600), 12), rng.choice((48, 96, 144)), 6, (150, 255, 230, 120))
	if t < T_REF_WAVE + 0.5:  # thumbnail-style "look here" circle and arrow on the reflection
		pond.red_ring(img, PX1, pond.WATER_Y + 170, 220, 150)
		arrow = pond.sprite('arrow_big')
		blit(img, arrow, PX1 + 200, pond.WATER_Y + 280)
	bubbles(img, t)
	caption(img, t)
	end_labels(img, t)
	return img


def pad_dip(t: float, landings: list) -> float:
	"""A lily pad bobbing down and back up after each landing."""
	d = 0.0
	for tl in landings:
		dt = t - tl
		if 0 <= dt < 0.6:
			d += 14 * math.exp(-dt * 7.0) * math.sin(dt * 16)
	return d


# --------------------------------------------------------------------------------------------
# Score: a spooky music box in A minor, then the Insiders pet brings the beat (C major).


def crickets(mix: A.Mixer, t0: float, t1: float) -> None:
	t, k = t0, 0
	while t < t1:
		for j in range(3):
			mix.put(A.sweep(4300, 4100, 0.03, 'sine'), t + j * 0.045, 0.025, pan=0.6 if k % 2 else -0.6)
		t += 0.9 + 0.13 * (k % 3)
		k += 1


def music(mix: A.Mixer) -> None:
	n, put, bt = A.n, mix.put, mix.beat
	# The mystery: music box arpeggios, Am - F - G - E, one chord per second.
	for i, (chord, root) in enumerate(((('A5', 'C6', 'E6', 'C6'), 'A2'), (('F5', 'A5', 'C6', 'A5'), 'F2'), (('G5', 'B5', 'D6', 'B5'), 'G2'),
			(('E5', 'G#5', 'B5', 'G#5'), 'E2'), (('A5', 'C6', 'E6', 'C6'), 'A2'), (('F5', 'A5', 'C6', 'A5'), 'F2'), (('E5', 'G#5', 'B5', 'D6'), 'E2'))):
		t0 = i * 1.0
		for j, nm in enumerate(chord):
			if i == 2 and j == 0:
				nm = 'G#5'  # a wrong note: something's off (just as the reflection waves first)
			put(A.bell(n(nm), 0.6), t0 + j * 0.25, 0.10, pan=-0.2 + 0.13 * j)
		put(A.lead(n(root) + 12, 0.95, 0.125, 0.008), t0, 0.045)
		put(A.bass(n(root), 0.9), t0, 0.10)
	crickets(mix, 0.2, T_GLITCH)
	for tk in (T_LEAN, T_LEAN + 0.3):  # a heartbeat as it leans in
		put(A.kick(0.5), tk)
	A.roll(mix, T_GLITCH * 2, T_LEAP * 2, 0.06, 0.32)
	put(A.sweep(180, 1800, T_LEAP - T_GLITCH, 'pulse', 0.25, curve=2.0), T_GLITCH, 0.05)
	# The drop: the Insiders pet brings a groove, C - Am - F - G.
	put(A.crash(0.28), T_LEAP, 0.9)
	A.groove(mix, T_LAND * 2, DURATION * 2, hats16=True)
	chords = ['C3', 'A2', 'F2', 'G2']
	b = T_LAND * 2
	k = 0
	while b < DURATION * 2 - 0.5:
		root = n(chords[(k // 8) % 4])  # a chord per bar, eighth-note bass
		put(A.bass(root if k % 2 == 0 else root + 12, 0.2), bt(b), 0.24)
		b += 0.5
		k += 1
	hook = [(0, .5, 'E5'), (.5, .25, 'G5'), (.75, .75, 'C6'), (2, .5, 'A5'), (2.5, .25, 'C6'), (2.75, .75, 'E6'),
		(4, .5, 'F5'), (4.5, .25, 'A5'), (4.75, .75, 'C6'), (6, .5, 'G5'), (6.5, .25, 'B5'), (6.75, 1.25, 'D6')]
	start = math.ceil(T_END * 2 / 4) * 4  # the hook tune starts on the first bar of the end card
	mix.melody([(start + nb, d, nm) for (nb, d, nm) in hook if start + nb < DURATION * 2 - 1], 0, 'lead', 0.10)
	for i, nm in enumerate(['C5', 'E5', 'G5', 'C6']):  # the drop: a bright chord as the Insiders pet lands
		put(A.lead(n(nm), 0.5, 0.25, 0.006), T_LAND + 0.01 * i, 0.04, pan=(i - 1.5) * 0.3)
	for i, nm in enumerate(['C4', 'E4', 'G4', 'C5']):  # a stinger on the end card
		put(A.lead(n(nm), 1.2, 0.125, 0.006), T_END + 0.01 * i, 0.05, pan=(i - 1.5) * 0.3)


def babble(mix: A.Mixer, text: str, t0: float, length: float, base: str) -> None:
	letters = [c for c in text if c.isalpha()]
	for i in range(len(letters)):
		if i % 2 == 0:
			mix.put(A.blip(A.n(base) + (i * 5) % 7, 0.04, 0.25), t0 + length * i / len(letters), 0.05, pan=0.3)


def sound_effects(mix: A.Mixer) -> None:
	n, put = A.n, mix.put
	put(A.bell(n('E7'), 0.3), T_ODD_BLINK, 0.02)                           # the odd blink (listen closely)
	put(A.sweep(900, 500, 0.25, 'tri') * 0.8, T_REF_WAVE + 0.2, 0.07)      # a wobbly "hm?"
	put(A.blip(n('E6'), 0.07), T_NOTICE, 0.08)                              # "?"
	put(A.blip(n('A6'), 0.12), T_NOTICE + 0.08, 0.08)
	put(A.twinkle(['C6', 'E6', 'G6']), T_PET_WAVE + 0.2, 0.05)              # the pet waves back
	put(A.boing()[::-1].copy(), T_REF_HOP - 0.12, 0.13)                      # a backwards boing: it's early
	put(A.land(), REF_HOP.t1, 0.12)
	put(A.boing(), T_PET_HOP, 0.13)                                           # the pet's own hop, late
	put(A.land(), PET_HOP.t1, 0.16)
	rng = random.Random(5)
	for k in range(10):                                                       # glitch: bzzt
		put(A.blip(n('C5') + rng.randrange(-12, 12), 0.04, 0.5), T_GLITCH + 0.05 * k, 0.06, pan=rng.uniform(-0.6, 0.6))
	put(A.noise_burst(0.45, 800, 8), T_GLITCH + 0.02, 0.06)
	put(A.noise_burst(0.5, 300, 6), T_LEAP, 0.34)                            # SPLASH
	put(A.sweep(900, 180, 0.3, 'sine'), T_LEAP, 0.2)
	put(A.kick(1.0), T_LEAP, 0.5)
	put(A.whoosh(0.4), T_LEAP + 0.05, 0.2, pan=0.4)
	put(A.land(), T_LAND, 0.3, pan=0.3)
	for k in range(8):                                                        # droplets falling back
		put(A.blip(n('C7') + k * 2, 0.03, 0.5), T_LEAP + 0.45 + k * 0.06, 0.03, pan=-0.4 + k * 0.1)
	put(A.whoosh(0.3), T_COOL + 0.55, 0.12, pan=0.3)                         # the shades come down
	put(A.bass(n('C2'), 0.4), SUNGLASSES_ON, 0.3)                            # ... and they're on
	put(A.coin(), SUNGLASSES_ON + 0.02, 0.10, pan=0.3)
	put(A.snare(0.5), SUNGLASSES_ON)
	babble(mix, SAY1, T_SAY1, 0.5, 'G5')
	babble(mix, SAY2, T_SAY2, 0.6, 'A5')
	put(A.sweep(600, 300, 0.35, 'tri') * 0.8, T_SAY2 + 0.9, 0.06, pan=-0.3)  # the Stable pet: "..."
	put(A.twinkle(['C6', 'E6', 'G6', 'C7']), T_END + 0.2, 0.07)


def score(mix: A.Mixer) -> None:
	music(mix)
	sound_effects(mix)
