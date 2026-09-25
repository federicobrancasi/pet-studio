"""{{name}}: a short VS Code pet film.

Made from the Pet Studio film template. Preview and export with:

    python3 -m kit film sheet {{name}}          # quick contact sheet
    python3 -m kit film frame {{name}} --at 4   # one frame
    python3 -m kit film review {{name}}         # MP4 + review package

Every frame is a pure function of time: ``render(t)`` must not remember anything between
calls, and any randomness must be seeded. Keep all timings in the timeline block so the
picture and the score stay in sync.
"""

from __future__ import annotations

from PIL import Image

from kit import fx, motion, world
from kit import audio as A
from kit import pet as P
from kit.draw import seg
from kit.motion import Hop
from kit.pet import PetPose

TITLE = '{{name}}'
W, H = SIZE = (1920, 1080)  # 16:9 for X; (1080, 1080) square or (1080, 1920) vertical also work
FPS = 60
DURATION = 10.0

# --------------------------------------------------------------------------------------------
# Timeline (seconds): change the story here

PROMPT = 'make it happen'
T_KEYS0, T_KEY_STEP, T_SEND = 1.2, 0.07, 2.6
T_HOP = 3.2
T_PRESS = 5.0          # button-press celebration starts
T_SUCCESS = T_PRESS + 0.8  # the press lands (frame 3 of the press sheet)
T_TITLE = 7.6
END_TITLE = 'Happy coding!'

CUES = [  # story beats: reviews show a full frame and a motion strip for each
	(0.0, 'resting on the chat input'),
	(T_KEYS0, 'types the prompt'),
	(T_HOP, 'hops onto the code'),
	(T_SUCCESS, 'celebration'),
	(T_TITLE, 'end card'),
]

# --------------------------------------------------------------------------------------------
# The world

INPUT_X0, INPUT_X1, INPUT_TOP = 200, 1300, 780
LINE = world.CodeLine('done', 7, 1380, 680, world.code('celebrate();'))
CITY = world.CodeCity(SIZE, world_width=3000, seed=1)
START_X = 1100
HOPS = [Hop(T_HOP, T_HOP + 0.5, START_X, INPUT_TOP, 1640, LINE.top, 200)]
LANDINGS = motion.landings(HOPS)
BLINKS = [0.9, 3.9, 6.4, 8.8]
CONFETTI = [(T_SUCCESS, fx.confetti_burst(1, 1640, LINE.top - 60, 60, 0.8))]


def hero_pose(t: float) -> PetPose:
	hop = motion.hop_pose(HOPS, t)
	if hop is not None:
		return hop
	x, y = motion.ground_at(HOPS, t, (START_X, INPUT_TOP))
	blink = motion.blinking(t, BLINKS)
	idle = P.frame_at('idle', t * 1000)
	if T_KEYS0 <= t < T_SEND:
		return PetPose('typing', P.frame_at('typing', (t - T_KEYS0) * 1000), x, y, gaze=(4, 0), blink=blink)
	if T_PRESS <= t < T_PRESS + P.total_ms('press') / 1000:
		return PetPose('press', P.frame_at('press', (t - T_PRESS) * 1000, loop=False), x, y, gaze=(4, 0), blink=blink)
	gaze = (-4, -4) if t < 0.8 else (4, 0) if t < T_KEYS0 else (4, -4)  # look around, then at the input
	return PetPose('idleTracking', idle, x, y, gaze=gaze, blink=blink)


def camera_target(t: float) -> tuple[float, float]:
	x, y = motion.ground_at(HOPS, t + 0.3, (START_X, INPUT_TOP))
	return max(0.0, x - 0.45 * W), motion.heading_y(HOPS, t, y) - 0.72 * H


CAMERA = motion.FollowCamera(camera_target, DURATION, FPS)


def render(t: float) -> Image.Image:
	img = Image.new('RGBA', SIZE)
	cx, cy = (int(round(v)) for v in CAMERA.at(t))
	CITY.draw(img, t, cx, cy, clouds_fade=seg(t, T_TITLE - 0.6, T_TITLE - 0.2))  # keep the title area clean
	typing = T_KEYS0 <= t < T_SEND
	world.chat_input(img, t, INPUT_X0, INPUT_X1, INPUT_TOP, cx, cy,
		text=world.typed(PROMPT, t, T_KEYS0, T_KEY_STEP, T_SEND),
		placeholder='Ask anything' if t < T_KEYS0 else None,
		focused=T_KEYS0 - 0.05 <= t < T_SEND + 0.25, typing=typing, send_flash=T_SEND <= t < T_SEND + 0.18)
	LINE.draw(img, t, cx, cy, active=t >= T_HOP + 0.5, dip=lambda x: world.landing_dip(t, LANDINGS, LINE.top, x))
	P.draw_pose(img, hero_pose(t), cx, cy)
	fx.dust(img, t, LANDINGS, cx, cy)
	fx.confetti(img, t, CONFETTI, cx, cy)
	world.title_block(img, END_TITLE, 120, t=t, t0=T_TITLE)  # pass subtitle='...' for a second line
	return img


# --------------------------------------------------------------------------------------------
# Score: 120 BPM, so one beat = 0.5 s and one bar = 2 s. Put hits on the story beats.

THEME = [(0, .5, 'C5'), (.5, .5, 'E5'), (1, .75, 'G5'), (1.75, .25, 'E5'), (2, .5, 'D5'), (2.5, .5, 'G5'), (3, .5, 'B4'), (3.5, .5, 'D5')]


def score(mix: A.Mixer) -> None:
	n = A.n
	mix.melody([(0, .5, 'E5'), (.5, .5, 'G5'), (1, .5, 'C6'), (1.5, .5, 'G5')], 0, 'bell', 0.09)
	mix.melody(THEME, 6)            # beat 6 = 3.0 s, just before the hop
	A.groove(mix, 6, 10)
	mix.melody([(10, .25, 'C6'), (10.25, .25, 'C6'), (10.5, .25, 'C6'), (10.75, 1.25, 'E6'), (12, 1, 'G6')], 0, 'lead', 0.14)
	A.groove(mix, 10, 15, soft=0.8)
	for i, nm in enumerate(['C4', 'E4', 'G4', 'C5']):  # final chord on the end card
		mix.put(A.lead(n(nm), 1.6, 0.125), T_TITLE + 0.01 * i, 0.05, pan=(i - 1.5) * 0.3)
	for i, ch in enumerate(PROMPT):  # sound effects follow the same timeline
		if ch != ' ':
			mix.put(A.click(1.0 + 0.06 * (i % 4)), T_KEYS0 + i * T_KEY_STEP, 0.18, pan=-0.3)
	mix.put(A.whoosh(0.3), T_SEND, 0.25)
	for h in HOPS:
		mix.put(A.boing(), h.t0, 0.16)
		mix.put(A.land(), h.t1, 0.30)
	mix.put(A.click(0.5, 1.0), T_SUCCESS, 0.5)
	mix.put(A.twinkle(['C7', 'E7', 'G7', 'C8']), T_SUCCESS + 0.1, 0.12)
	for k in range(8):
		mix.put(A.noise_burst(0.02, 3000, 200), T_SUCCESS + k * 0.035, 0.15, pan=float(A.rng().uniform(-0.6, 0.6)))
