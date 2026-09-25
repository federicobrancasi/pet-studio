# Teaching the pet a new move

A move is a text file of frames, one letter per logical pixel. The kit turns it into sprite
sheets for both colorways, in the same format as the pet's own, plus a GIF and a preview. Moves
work in films and stills too.

## Steps

1. **Design it.** Work out the trigger, the peak pose and the result, and whether it loops or
   plays once. Aim for 4-10 frames lasting 0.6-2 s.
2. **Start from the real pet.** Never draw the body from memory:

   ```sh
   python3 -m kit move new juggle --frames 6 --height 16   # every frame starts as the idle pose
   python3 -m kit move grid jump:3                         # print any real pose as text
   ```

   `--height 16` adds headroom for props above the pet, and `--width 16` adds room on the right.
3. **Edit `moves/<name>/move.txt`.** Change only what the move needs, and paste in real poses where
   they fit.
4. **Build and look.** Run `python3 -m kit move build juggle`, then read every warning and look at
   `out/moves/juggle/strip.png` and `moves/juggle/preview.gif`. Iterate, show the user the strip,
   and then run `python3 -m kit move gallery`.

Frames are numbered from 1 on the command line and in move files (`jump:2` is the second frame).
In Python they're indexed from 0.

| Recipe | Frames |
| --- | --- |
| Nod yes | `idle:1` 160 ms, `jump:2` 110 ms, `idle:1` 160 ms, `jump:2` 110 ms, `idle:1` 300 ms |
| Bounce | `jump:2` crouch, `jump:3` stretch, `jump:4` air, `jump:5` squash, `jump:6` recover |
| Blink | `idle:1`, then the same grid with the top `E` of each eye set to `C`, for 80 ms |
| Wave | move one antenna outward and up over two frames (`moves/wave`) |
| Hearts, shades, sweat | start from `love:6`, `cool:9` or `worry:1`, keeping their colors |
| Prop overhead | `--height 16`, with the prop in the top rows in its own letters (`moves/lgtm`) |

## Format

```text
name: juggle
about: Juggles curly braces with its antennae.
loop: yes            # yes = loops; no = plays once and holds the last frame
still: 3             # optional: the frame used as the static image
colors: Y=#ffd700 W=#ffffff
fixed: Y             # optional: prop letters that must not mirror (text, checks, notes)

frame 120            # duration in ms (the pet's own frames run 40-600 ms)
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

- **Letters:**
  - `.` is transparent.
  - `C`, `A` and `B` are the body's light, mid and dark colors; they become blue or green
    automatically.
  - `E` is an eye.
  - Any other letter is a prop and must be declared in `colors:`.
- **Frames:** every frame has the same size, at least 12 x 12.
- **Comments:** start a line with `#`, or add ` #` after a value.
- **Names:** built-in state names such as `jump` are taken.

## Good moves

- Use big, simple shapes. Change as few pixels as possible, and make every frame count:
  anticipation, peak, settle.
- Start and end on the idle pose so the move doesn't pop in or out.
- Keep the body in the bottom-left 12 x 12 box, touching the bottom row except in the air. Props go
  above or to the right.
- Hold the peak for 200-600 ms, and keep fast frames at 60-120 ms.
- The pet faces left by mirroring. Put text, checks and notes in `fixed:` so they stay readable.

## Using and sharing

```python
moves.use('juggle')
P.draw_pose(img, P.PetPose('juggle', P.frame_at('juggle', ms), x, y), cx, cy)
```

`moves/<name>/` holds:
- `move.txt`: the whole move, which you can share as it is
- the previews
- `vscode/`: the sprite sheets, the static images, `timing.ts` and `move.json`

Visual Studio Code only plays its built-in animations, so a new move won't appear in the editor.
The `vscode/` files let you try it in a local build.
