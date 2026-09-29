# Making a video

A film is one file, `films/<name>/film.py`, that draws any frame from its time. The template is
a working 10 s film:

```sh
python3 -m kit film new surf-the-branch
python3 -m kit film sheet surf-the-branch
```

| Name | Meaning |
| --- | --- |
| `DURATION`, `FPS` | length in seconds; 60 fps for X |
| `SIZE` | `(1920, 1080)` for X, `(1080, 1080)` square, `(1080, 1920)` vertical (see [Vertical](#vertical-916)) |
| `render(t)` | a PIL image of `SIZE`, pure in `t` |
| `score(mix)` | the music and effects ([sound.md](sound.md)) |
| `CUES` | `[(t, 'beat'), ...]`; each beat gets a frame and a motion strip in the review |

## Plan

- **One idea, told in beats.** For X, aim for 15-30 s.
  - The first second already shows the pet doing something: it's the thumbnail.
  - End on a clear pose or end card held for 2-3 s, with no logos or bylines.
- **Readable with the sound off.** Every action has a visible result. Text stays on screen at least
  0.8 s after it finishes typing.
- **Keep it moving.** The pet travels: it hops from place to place, climbs, chases, falls, and
  the camera follows it (`motion.FollowCamera`). A pet that stands in one spot for the whole film
  feels static, however good its moves are. Hold the camera still for the moments that matter,
  and while there's text to read.
- **Space.** Keep the pet in the lower-middle third, with room to look ahead of it. Keep props and
  titles clear of heads.
- **Timing.** At 120 BPM a beat is 0.5 s, so put big actions on beats. Hops take about 0.5 s, and
  reactions need a moment to breathe.

## Worlds

Pick the world from the brief, and make each film look like itself: the templates and examples
show the mechanics, not the world to reuse.

| Brief | A world to try | Built with |
| --- | --- | --- |
| about code: a bug, a merge, a deploy | a city or a stairway of code | `world.CodeCity`, `world.CodeLine`, `world.terminal_panel` |
| a day, a trip, a season | a landscape through the hours: meadow, field, desert | `land.Ground` with biomes, `land.Ridge`, `land.prop`, `sky.day_keys`, `sky.day_light` |
| a big moment, a wish, a reveal | the clouds at sunset, then the stars | `sky.gradient`, `sky.CloudPlatform`, `sky.rays`, `letters.BubbleWord` |
| a dev joke, a challenge, a versus | a retro game: a boss, a HUD, banners and power-ups | see `examples/boss-fight` |
| anything else | the beach, space, snow, underwater, a candy land, inside a computer | the pieces above, new props as letter grids (`draw.grid_sprite`) |

- **Vary the look.** Choose a palette, a time of day and a way of travelling (hops, a climb, a
  slide, a chase) that suit the story, rather than the ones of the last film.
- **Vary the sound.** Change the key, the tempo, the instruments and the drum pattern too.
- **Light the world, not the pet.** Tint the scenery for the time of day (`sky.day_light`), and
  keep the pet in its real colors.

## Vertical (9:16)

For Reels, TikTok, Shorts and phone-first posts on X, start from the vertical template, a
working 8 s film in which the pet hops up the clouds from a sunny hill to the stars:

```sh
python3 -m kit film new my-reel --vertical
```

- **Safe area.** The apps draw buttons, captions and profile bars over the top 260 px, the
  bottom 320 px, the left 60 px and the right 120 px of a 1080x1920 frame.
  `layout.safe_area(SIZE)` returns the box that stays clear, x 60-960 and y 260-1600. Keep
  text, faces and the action inside it, centered on its middle (x 510).
- **Hook.** A short caption in the top of the safe area, whole from the first frame. It's the
  thumbnail, and it reads with the sound off. `world.caption` outlines it, so it reads on a
  bright sky too.
- **Motion.** Tall frames suit climbing, falling and stacking: a `FollowCamera` that tracks `y`
  keeps the pet in the lower-middle while the world scrolls, and showing only the next platform
  keeps the frame calm. For a journey sideways, track `x` and keep the pet on the left third, so
  its moves have room on the right (as `pet-day` does).
- **Size.** At 1080 px wide, the pet at `scale=2` is a fifth of the screen. Use `scale=3` for
  close-ups: moves up to 24 logical pixels wide still fit.
- **Check.** `film review` adds `safe-zones.png`, with the covered parts shaded red, and
  vertical checks (1080x1920, up to 60 fps, up to 3 min) to the report. `film gif` sizes by
  the long side, so a vertical film gives a vertical GIF.
- **Cover.** Render a still at the `story` preset (1080x1920) for the cover.

## Building blocks

```python
GROUND = land.Ground(lambda x: 900 + 30 * math.sin(x / 500))          # a path, in world px
STEP = sky.CloudPlatform(x=1500, top=620, cols=28, rows=11, seed=3)   # a cloud to land on
HOPS = [Hop(3.0, 3.5, 900, GROUND.y(900), 1500, STEP.top, 220)]       # t0, t1, x0, y0, x1, y1, height
CLOUDS = sky.CloudLayer(seed=1, count=6, y=(150, 500), parallax=(0.3, 0.3))

def render(t):
    img = Image.new('RGBA', SIZE)
    cx, cy = CAMERA.at(t)
    hour = 9 + t / 4                                                   # the morning goes by
    img.paste(sky.gradient(SIZE, sky.day_keys(hour)), (0, 0))
    CLOUDS.draw(img, t, cx, cy, sky.day_light(hour))
    GROUND.draw(img, cx, cy, sky.day_light(hour))
    STEP.draw(img, cx, cy, dip=sky.bounce(t, [3.5]))
    x, y = motion.ground_at(HOPS, t, (900, GROUND.y(900)))
    pose = motion.hop_pose(HOPS, t) or PetPose('idleTracking', P.frame_at('idle', t * 1000), x, y, gaze=(4, 0))
    P.draw_pose(img, pose, cx, cy)
    return img
```

- **One-shot states:** `P.frame_at(state, ms, loop=False)` plays once and holds the last frame.
  `P.total_ms(state)` gives the length.
- **A code world:** `world.CodeCity` for the backdrop, `world.CodeLine` platforms, and
  `world.typed` with `world.chat_input` or `world.code('...', appear=t0, step=0.1)` for typing.
- **Celebration:** the `press` state, `fx.confetti` and `fx.fireworks`, or `world.terminal_panel`.
- **A reveal:** `fx.flash` hides a cut, `sky.rays` turn behind it and `fx.sparkle_ring` bursts
  around it. For a hit, a partial flash (`strength=0.4`) punches it up without whiting out.
- **A friend arrives:** `fx.respawn`, then `falling` and `splat`.
- **Talking:** `world.say` draws a speech bubble with text; the `rendering` state keeps the
  pet's live eyes while it talks.
- **A close-up:** `draw.zoom(frame, x0, y0, 2)` blows up part of a rendered frame with whole
  pixels; draw text after zooming.
- **Titles:** `world.title_block` (fits and wraps), `world.pop_title`, `world.caption` (outlined,
  for bright skies) or `letters.BubbleWord` (big bubble letters that drop in and squash).
- **New props:** letter grids with `draw.grid_sprite`, as in `kit/art.py` and `kit/land.py`.

## Check

```sh
python3 -m kit film frame my-film --at 3.2 3.4
python3 -m kit film sheet my-film --from 3 --to 5 --every 0.1
python3 -m kit film render my-film --draft
python3 -m kit film review my-film            # final MP4 + review package
python3 -m kit film gif my-film --from 3 --to 6
```

Look for:
- props covering faces
- text cut off at an edge
- poses that pop
- dead air
- the camera moving while the viewer should be reading
- a pet that stands in one spot the whole time
- the world, palette or beats of an example, when the brief didn't ask for them

The final MP4 is 1080p60 H.264 with AAC and faststart, which suits X uploads of up to 140 s;
vertical films suit Reels, TikTok and Shorts too.
