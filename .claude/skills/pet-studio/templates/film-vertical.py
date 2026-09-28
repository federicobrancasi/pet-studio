"""{{name}}: a short vertical (9:16) VS Code pet film for Reels, TikTok, Shorts and X.

Made from the Pet Studio vertical film template: the pet hops up a stairway of clouds from a
sunny hill to the stars, and the camera follows it. Keep the mechanics (a journey, a camera
that follows, the safe area, a hook and an end title) and replace the world with the one your
brief needs: a beach, a snowy mountain, space, a city, inside a computer (see guides/video.md).

    python3 -m kit film sheet {{name}}          # quick contact sheet
    python3 -m kit film frame {{name}} --at 5   # one frame
    python3 -m kit film review {{name}}         # MP4 + review package, with safe-zones.png

Reels, TikTok and Shorts draw buttons, captions and profile bars over vertical video, so
keep text, faces and the action inside ``SAFE`` (x 60-960, y 260-1600). Every frame is a
pure function of time: ``render(t)`` must not remember anything between calls, and any
randomness must be seeded. Keep all timings in the timeline block so the picture and the
score stay in sync.
"""

from __future__ import annotations

from PIL import Image

from kit import art, fx, land, layout, letters, motion, sky, world
from kit import audio as A
from kit import pet as P
from kit.draw import blit, seg, snap
from kit.motion import Hop
from kit.pet import PetPose

TITLE = '{{name}}'
W, H = SIZE = (1080, 1920)  # 9:16 vertical
FPS = 60
DURATION = 8.0
SAFE = layout.safe_area(SIZE)  # (60, 260, 960, 1600): visible on every app
SAFE_X = (SAFE[0] + SAFE[2]) // 2  # the safe area's center, a little left of the frame's
SAFE_W = SAFE[2] - SAFE[0]

# --------------------------------------------------------------------------------------------
# Timeline (seconds): change the story here

CAPTION = 'to the stars!'  # the hook: vertical videos autoplay muted, so say it in text
T_HOPS = (1.6, 2.6, 3.6)   # three hops up the clouds, on the beat
HOP_TIME = 0.5
T_GRAB = (4.5, 4.9)        # a jump in place to grab the star at the top
T_STAR = T_GRAB[0] + 0.2   # the top of that jump
T_CHEER = 5.05             # it claps
T_TITLE = 5.4              # the end title drops in, letter by letter
END_TITLE = 'YAY!'

CUES = [  # story beats: reviews show a full frame and a motion strip for each
	(0.0, 'caption; the pet on a hill looks up'),
	(T_HOPS[0], 'hops up the clouds'),
	(T_STAR, 'grabs the star'),
	(T_TITLE, 'end title'),
]

# --------------------------------------------------------------------------------------------
# The world: y shrinks as the pet climbs, and the camera starts at cy = 0

SCALE = 3                  # a phone-sized pet: 288 px tall
GROUND_Y = 1450            # the hilltop, where the pet starts
START_X = 300
HILL = land.Ground(lambda x: GROUND_Y + ((x - START_X) / 560) ** 2 * 330)
STEP = 440                 # between clouds: more than the pet's height plus its hop
STEPS = [sky.CloudPlatform(x, GROUND_Y - STEP * (i + 1), 26, 11, seed=11 + i, palette='day') for i, x in enumerate((780, 260, 640))]
SPOTS = [(START_X, GROUND_Y)] + [(c.x, c.top) for c in STEPS]
HOPS = [Hop(t0, t0 + HOP_TIME, *SPOTS[i], *SPOTS[i + 1], 240) for i, t0 in enumerate(T_HOPS)]
TOP = SPOTS[-1]
GRAB = Hop(*T_GRAB, *TOP, *TOP, 170)
LANDINGS = motion.landings(HOPS + [GRAB])
# Each cloud fades in as the pet lands on the one below it, so only the next step shows.
T_APPEAR = [0.9] + [h.t1 for h in HOPS[:-1]]
STAR = (TOP[0], TOP[1] - 96 * SCALE - 150)   # just above its antennae at the top of the jump
BLINKS = [0.5, 2.3, 6.3, 7.4]

# A sky as tall as the climb: bright day at the bottom, night with stars at the top.
SKY_TOP = TOP[1] - 1700
SKY = sky.gradient((W, GROUND_Y + H - SKY_TOP), ((0.0, '#0b0f30'), (0.22, '#232a70'), (0.38, '#3f64c8'), (0.5, '#6fb0f0'), (0.7, '#a8dcff'), (1.0, '#eaf8ff')))
CLOUDS = sky.CloudLayer(seed=5, count=9, y=(-700, 1250), palette='day', alpha=150, parallax=(0.0, 0.45), drift=14, span=1400)
HILLS = land.Ridge(seed=3, color='#8cbfa6', y=GROUND_Y - 120, amp=70, parallax=0.6, rim='#aad6bd')
TITLE_WORD = letters.BubbleWord(END_TITLE, SAFE_X, SAFE[1] + 330, max_width=SAFE_W, palette='gold')


def facing(t: float) -> str:
	"""The pet faces the way it is about to hop."""
	direction = 'right'
	for h in HOPS:
		if t >= h.t0 - h.crouch:
			direction = 'right' if h.x1 >= h.x0 else 'left'
	return direction


def hero_pose(t: float) -> PetPose:
	hop = motion.hop_pose(HOPS + [GRAB], t, facing=facing(t))
	x, y = motion.ground_at(HOPS, t, SPOTS[0])
	blink = motion.blinking(t, BLINKS)
	if hop is not None:
		pose = hop
	elif T_CHEER <= t < T_TITLE + 1.2:
		pose = PetPose('clapping', P.frame_at('clapping', (t - T_CHEER) * 1000), x, y, facing(t), gaze=(0, -2), blink=blink)
	else:
		gaze = (4, -4) if t < T_GRAB[0] else (0, -4)  # look up at the next step, then at the title
		pose = PetPose('idleTracking', P.frame_at('idle', t * 1000), x, y, facing(t), gaze=gaze, blink=blink)
	pose.scale = SCALE
	return pose


def camera_target(t: float) -> tuple[float, float]:
	# Keep the ground the pet stands on, or is about to land on, at y 1300 on screen.
	ground = motion.ground_at(HOPS, t, SPOTS[0])[1]
	return 0.0, motion.heading_y(HOPS, t, ground) - 1300


CAMERA = motion.FollowCamera(camera_target, DURATION, FPS, omega=(5.0, 4.0))


def render(t: float) -> Image.Image:
	img = Image.new('RGBA', SIZE)
	cx, cy = (int(round(v)) for v in CAMERA.at(t))
	img.paste(SKY.crop((0, cy - SKY_TOP, W, cy - SKY_TOP + H)), (0, 0))
	sky.stars(img, t, cx, cy, strength=seg(-cy, 300, 1100), area=(0, 0, W, 1300))
	CLOUDS.draw(img, t, cx, cy)
	HILLS.draw(img, cx, cy)
	HILL.draw(img, cx, cy)
	for (name, x) in (('flower_pink', 120), ('flower_white', 470), ('flower_violet', 560)):
		land.prop(img, name, x, HILL.y(x), cx, cy)
	for step, t_in in zip(STEPS, T_APPEAR):
		step.draw(img, cx, cy, dip=sky.bounce(t, [tl for (tl, lx, _) in LANDINGS if lx == step.x]), alpha=seg(t, t_in, t_in + 0.25))
	if t < T_STAR:  # the star to grab bobs above the top cloud
		star = art.star(24)
		blit(img, star, snap(STAR[0] - star.width / 2 - cx, 4), snap(STAR[1] - star.height / 2 + 12 * (t % 1 < 0.5) - cy, 4))
	P.draw_pose(img, hero_pose(t), cx, cy)
	fx.dust(img, t, LANDINGS, cx, cy, color=(255, 255, 255, 255))
	fx.sparkle_ring(img, t, T_STAR, STAR[0], STAR[1], cx, cy, n=10, radius=220, inner=60)
	# Text stays inside the safe area: the hook (whole from the first frame, the thumbnail) until
	# the climb is under way, then the end title.
	if t < T_HOPS[1]:
		world.caption(img, CAPTION.upper(), SAFE[1] + 40, SAFE_X, SAFE_W)
	if t >= T_TITLE:
		TITLE_WORD.draw(img, t, drop=(T_TITLE, 0.1))
	return img


# --------------------------------------------------------------------------------------------
# Score: 120 BPM, so one beat = 0.5 s and one bar = 2 s. Put hits on the story beats.

THEME = [(0, .5, 'C5'), (.5, .5, 'E5'), (1, .75, 'G5'), (1.75, .25, 'E5'), (2, .5, 'D5'), (2.5, .5, 'G5'), (3, .5, 'B4'), (3.5, .5, 'D5')]


def score(mix: A.Mixer) -> None:
	n = A.n
	mix.melody([(0, .5, 'E5'), (.5, .5, 'G5'), (1, .5, 'C6'), (1.5, .5, 'G5')], 0, 'bell', 0.09)
	mix.melody(THEME, 3)            # beat 3 = 1.5 s, as the climb starts
	A.groove(mix, 3, 9)  # until the star (beat 9 = 4.5 s)
	mix.melody([(9, .25, 'C6'), (9.25, .25, 'C6'), (9.5, .25, 'C6'), (9.75, 1.25, 'E6'), (11, 1, 'G6')], 0, 'lead', 0.14)
	A.groove(mix, 9, 16, soft=0.8)
	for i, nm in enumerate(['C4', 'E4', 'G4', 'C5']):  # final chord on the end title
		mix.put(A.lead(n(nm), 1.6, 0.125), T_TITLE + 0.01 * i, 0.05, pan=(i - 1.5) * 0.3)
	for k, t_in in enumerate(T_APPEAR):  # sound effects follow the same timeline
		mix.put(A.twinkle([['C6', 'E6'], ['E6', 'G6'], ['G6', 'C7']][k]), t_in, 0.05)
	for h in HOPS + [GRAB]:
		mix.put(A.boing(), h.t0, 0.16)
		mix.put(A.land(), h.t1, 0.30)
	mix.put(A.coin(), T_STAR, 0.16)
	mix.put(A.twinkle(['C7', 'E7', 'G7', 'C8']), T_STAR + 0.05, 0.12)
	for i in range(len(END_TITLE)):  # each title letter lands with a blip
		mix.put(A.blip(n(['C6', 'E6', 'G6', 'C7', 'E7', 'G7'][i % 6]), 0.05), T_TITLE + 0.1 * i + 0.14, 0.08)
