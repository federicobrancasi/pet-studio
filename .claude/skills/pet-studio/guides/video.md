# Making a video

A film is one Python file, `films/<name>/film.py`, that draws any frame from its time. Start from
the template; it is a complete 10 s film you can change:

```sh
python3 -m kit film new surf-the-branch          # creates films/surf-the-branch/film.py
python3 -m kit film sheet surf-the-branch        # films can be given by name or by path
```

## The film contract

| Name | Meaning |
| --- | --- |
| `DURATION` | length in seconds |
| `FPS` | 60 for X (30 also works) |
| `SIZE` | `(1920, 1080)` for X; `(1080, 1080)` square; `(1080, 1920)` vertical |
| `render(t)` | returns a PIL image of `SIZE`; pure in `t` |
| `score(mix)` | fills a `kit.audio.Mixer`; see [sound.md](sound.md) |
| `CUES` | `[(t, 'beat'), ...]`: every beat gets a cue frame and a motion strip in the review |

## Plan like an animator

- **One idea, told in beats.** 15-30 s for X. The first second must already show the pet doing
  something (it is the thumbnail and the autoplay hook). End on a clear final pose or an end
  card that holds for 2-3 seconds. Keep end cards free of logos and product bylines (see the
  brand rules in [style.md](style.md)).
- **Readable muted.** Each beat is an action and a visible consequence: pet types, code appears;
  pet bonks bug, bug turns into a butterfly. On-screen text is short and holds for at least
  0.8 s after it finishes typing.
- **One continuous shot works well.** A `FollowCamera` glides after the pet; hold it still
  (return a fixed target) while something important happens. A fixed frame is also fine.
- **Space.** Keep the pet in the lower-middle third, with room to see where it is going
  (`x - 0.28 * W` look-ahead). Keep titles and important props clear of the pets' heads.
- **Timing.** At 120 BPM one beat is 0.5 s: put big actions on beats so the music can hit them.
  Hops take 0.5 s with a 0.25 s pause between. Let a reaction breathe before the next action.

## Building blocks

```python
from kit import fx, motion, world, pet as P
from kit.motion import Hop
from kit.pet import PetPose

LINE = world.CodeLine('fix', 12, 1200, 700, world.code('ship(app);'))  # a platform
HOPS = [Hop(3.0, 3.5, 900, 800, 1400, LINE.top, 200)]                  # t0, t1, x0, y0, x1, y1, height
CITY = world.CodeCity(SIZE, world_width=4000, seed=1)                   # the backdrop

def render(t):
    img = Image.new('RGBA', SIZE)
    cx, cy = CAMERA.at(t)                         # camera top-left in world px
    CITY.draw(img, t, cx, cy)
    LINE.draw(img, t, cx, cy)
    pose = motion.hop_pose(HOPS, t) or PetPose('idleTracking', P.frame_at('idle', t * 1000), *motion.ground_at(HOPS, t, (900, 800)), gaze=(4, 0))
    P.draw_pose(img, pose, cx, cy)
    return img
```

- `P.frame_at(state, ms, loop=False)` plays one-shot states once and holds the last frame.
  `P.total_ms(state)` gives the length.
- Typing: `world.typed(text, t, start, step)` + `world.chat_input(...)` or a `CodeLine` whose
  characters have `appear` times (`world.code('...', appear=t0, step=0.1, pop=True)`).
- Celebration: the `press` state, then `fx.confetti` with `fx.confetti_burst(seed, x, y, n, spread)`
  and `fx.fireworks`, or `world.terminal_panel(...)` with lines that type in.
- A friend arrives: `fx.respawn` (portal), then the `falling` state under gravity and `splat` on
  landing (see Coding World, 22-24 s).
- Text: `world.pop_title` (letters pop in), `world.title_block` (title + subtitle that fits),
  `world.bob_title` (gentle wave), `world.centered_text`.
- New props: letter grids with `kit.draw.grid_sprite(rows, palette, 16)`, like `kit/art.py`.

## Check as you go

```sh
python3 -m kit film frame my-film --at 3.2 3.4                   # full frames
python3 -m kit film sheet my-film --from 3 --to 5 --every 0.1    # dense contact sheet
python3 -m kit film render my-film --draft                       # fast MP4 to watch
python3 -m kit film check my-film                                # determinism
python3 -m kit film review my-film                               # final MP4 + review package
python3 -m kit film gif my-film --from 3 --to 6                  # a GIF clip for Slack
```

Look at every frame you render. Common problems to catch: a prop covering the pet's face or
antennae, text cut off at an edge, a pose that pops between frames, dead air with nothing
happening, the camera moving while the viewer should be reading, and effects hiding the story.

## Deliverable

`out/<name>/<name>.mp4`: 1080p60 H.264 High (CRF 12) with AAC 192k, BT.709 and faststart, which
suits X uploads (up to 140 s). The review's report checks this and prints loudness.
