# Teaching the pet a new move

A move is a text file of frames, one letter per logical pixel. The kit turns it into sprite
sheets in the exact format VS Code uses (Stable and Insiders), plus a GIF and an animated PNG to
share. Moves can also be used in any film or still.

## Steps

1. **Understand the move.** What triggers it, what the peak pose is, what the result looks like,
   and whether it loops (a dance) or plays once (a reaction). Aim for 4-10 frames and 0.6-2 s.
2. **Start from the real pet.** Never draw the body from memory:

   ```sh
   python3 -m kit move new juggle --frames 6 --height 16     # every frame starts as idle
   python3 -m kit move grid jump:3                           # print any real pose as text
   python3 -m kit poses --list                               # all states and frame counts
   ```

   `--height 16` gives 4 rows of headroom for props above the pet; `--width 16` gives room on
   the right (props on the right side only: the body keeps its home in the bottom-left 12 x 12).
3. **Edit `moves/<name>/move.txt`.** Change only what the move needs. Reuse real poses by copying
   their grids (the jump frames for any bounce, `love` for hearts, `worry` for sweat drops).
4. **Build and look.**

   ```sh
   python3 -m kit move build juggle
   ```

   Read every error and warning, then open `out/moves/juggle/strip.png` (every frame, both colors)
   and `moves/juggle/preview.gif`. Fix and rebuild until it reads clearly. Then show the user the
   strip and the preview. To list the move in `moves/README.md`, run `python3 -m kit move gallery`.

## Recipes

Most moves are a few real poses in a new order, plus a small change. Print any pose with
`python3 -m kit move grid <state>:<frame>` and paste it in. On the command line and in move
files, frames are numbered from 1 (`jump:2` is the second frame); in Python code, frame indexes
start at 0 (`PetPose('jump', 1, ...)` is that same frame).

| Move | Frames |
| --- | --- |
| Nod yes | `idle:1` 160 ms, `jump:2` 110 ms (the crouch: head squashed down, eyes one row lower), `idle:1` 160 ms, `jump:2` 110 ms, `idle:1` 300 ms |
| Happy bounce | `jump:2` (crouch), `jump:3` (stretch), `jump:4` (in the air), `jump:5` (squash), `jump:6` (recover, same as idle) |
| Blink | `idle:1`, then the same grid with the top pixel of each eye (`E`) turned into `C` for 80 ms |
| Wave | move one antenna's pixels outward and up over two frames (see `moves/wave`) |
| Hearts, sunglasses, sweat | start from `love:6`, `cool:9` or `worry:1` and keep their extra colors |
| A prop above the head | `--height 16` and draw the prop in the top rows with its own letters (see `moves/lgtm`) |

## The format

```text
name: juggle
about: Juggles curly braces with its antennae.
loop: yes            # yes = loops; no = plays once and holds its last frame
still: 3             # optional: frame used for the reduced-motion image (default: the longest)
colors: Y=#ffd700 W=#ffffff
fixed: Y             # optional: prop letters that must not mirror (text, checks, notes)

frame 120            # duration in ms (the pet's own moves use 40-600 ms per frame)
..A......A..
...A....A...
....A..A....
.....BA.....
....BACC....
...BACCCC...
..BACCCCCC..
.BACCCCCCCC.
BAACCECCECCC
BAACCECCECCC
BAACCCCCCCCC
.BAAACCCCCC.
```

| Letter | Meaning |
| --- | --- |
| `.` | transparent |
| `C` `A` `B` | body light, mid, dark: blue in Stable, green in Insiders automatically |
| `E` | eye; the normal open eye is 1 wide and 2 tall |
| others | props, declared in `colors:`; the same in both colorways |

All frames must have the same size, at least 12 x 12. A line starting with `#` is a comment, and
so is anything after ` #` (a space, then `#`) at the end of a line. Names of built-in states
(`jump`, `love`, ...) are taken.

## Good moves

- **Readable at 12 x 12.** Big, simple shapes. Change as few pixels as possible between frames,
  and make every frame count: an anticipation, a peak you can recognize, a settle.
- **Start and end on the idle pose** so VS Code can switch into and out of it without a pop (the
  validator warns if not; deliberate entrances or exits are fine).
- **Keep the body's footprint.** The body stays in the bottom-left 12 x 12 box and touches the
  bottom row except while airborne. Props go above or to the right, in their own colors.
- **Timing is part of the art.** Hold the peak (200-600 ms) and keep fast frames at 60-120 ms.
  Merge identical frames into one longer frame.
- **Mirror-safe props.** The pet faces left by mirroring. Letters listed in `fixed:` keep their
  orientation, so use it for text, check marks, arrows and musical notes.

## Using a move

```python
from kit import moves, pet as P
moves.use('juggle')                                  # register once, at import
P.draw_pose(img, P.PetPose('juggle', P.frame_at('juggle', ms), x, y), cx, cy)
```

## What you get

```text
moves/juggle/
  move.txt                        the move (share this: it is the whole move)
  preview.gif, preview.png        both colors on a chat input, for Slack/X and READMEs
  vscode/buddy-juggle-{stable,insiders}-<h>.spritesheet.png   VS Code sprite sheets
  vscode/buddy-juggle-{stable,insiders}-<h>.png               reduced-motion stills
  vscode/timing.ts, vscode/move.json                          frame durations and sizes
```

Visual Studio Code only plays the pet animations that ship with it (the pet is an experimental
feature), so a new move does not appear in your editor. The `vscode/` folder has the move in the
same format as the pet's own sprites, which makes it easy to try in a local build. Share the
move itself as `move.txt`, the preview GIF, or a pull request to this repo's `moves/` gallery.
