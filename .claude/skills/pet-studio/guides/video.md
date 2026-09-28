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
- **Camera.** A `FollowCamera` glides after the pet; hold it still for important moments. A fixed
  frame works too.
- **Space.** Keep the pet in the lower-middle third, with room to look ahead of it. Keep props and
  titles clear of heads.
- **Timing.** At 120 BPM a beat is 0.5 s, so put big actions on beats. Hops take about 0.5 s, and
  reactions need a moment to breathe.

## Vertical (9:16)

For Reels, TikTok, Shorts and phone-first posts on X, start from the vertical template, a
working 10 s film in which the pet climbs a stack of code lines:

```sh
python3 -m kit film new my-reel --vertical
```

- **Safe area.** The apps draw buttons, captions and profile bars over the top 260 px, the
  bottom 320 px, the left 60 px and the right 120 px of a 1080x1920 frame.
  `layout.safe_area(SIZE)` returns the box that stays clear, x 60-960 and y 260-1600. Keep
  text, faces and the action inside it, centered on its middle (x 510).
- **Hook.** A short caption in the top of the safe area, whole from the first frame. It's the
  thumbnail, and it reads with the sound off.
- **Motion.** Tall frames suit climbing, falling and stacking. A `FollowCamera` that tracks
  `y` keeps the pet in the lower-middle while the world scrolls. Only show the next platform,
  so the frame stays calm.
- **Size.** At 1080 px wide, the pet at `scale=2` is a fifth of the screen. Use `scale=3` for
  close-ups: moves up to 24 logical pixels wide still fit.
- **Check.** `film review` adds `safe-zones.png`, with the covered parts shaded red, and
  vertical checks (1080x1920, up to 60 fps, up to 3 min) to the report. `film gif` sizes by
  the long side, so a vertical film gives a vertical GIF.
- **Cover.** Render a still at the `story` preset (1080x1920) for the cover.

## Building blocks

```python
LINE = world.CodeLine('fix', 12, 1200, 700, world.code('ship(app);'))  # a platform
HOPS = [Hop(3.0, 3.5, 900, 800, 1400, LINE.top, 200)]                  # t0, t1, x0, y0, x1, y1, height
CITY = world.CodeCity(SIZE, world_width=4000, seed=1)                   # the backdrop

def render(t):
    img = Image.new('RGBA', SIZE)
    cx, cy = CAMERA.at(t)
    CITY.draw(img, t, cx, cy)
    LINE.draw(img, t, cx, cy)
    x, y = motion.ground_at(HOPS, t, (900, 800))
    pose = motion.hop_pose(HOPS, t) or PetPose('idleTracking', P.frame_at('idle', t * 1000), x, y, gaze=(4, 0))
    P.draw_pose(img, pose, cx, cy)
    return img
```

- **One-shot states:** `P.frame_at(state, ms, loop=False)` plays once and holds the last frame.
  `P.total_ms(state)` gives the length.
- **Typing:** `world.typed` with `world.chat_input`, or `world.code('...', appear=t0, step=0.1)`
  on a `CodeLine`.
- **Celebration:** the `press` state, `fx.confetti` and `fx.fireworks`, or `world.terminal_panel`.
- **A friend arrives:** `fx.respawn`, then `falling` and `splat`.
- **Titles:** `world.title_block` (fits and wraps) or `world.pop_title`.
- **New props:** letter grids with `draw.grid_sprite`, as in `kit/art.py`.

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

The final MP4 is 1080p60 H.264 with AAC and faststart, which suits X uploads of up to 140 s;
vertical films suit Reels, TikTok and Shorts too.
