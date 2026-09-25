# Style rules

These rules keep the pet looking like itself. They're adapted from the pet's own sprite
guidelines in microsoft/vscode.

## The character

- The pet lives on the chat input and reacts to chat:
  - It types along while you type.
  - It thinks in a speech bubble while a request runs.
  - It claps when the agent needs you.
  - It sleeps when things are quiet.
  - It celebrates when a response finishes.
- Call it "the VS Code pet". Don't invent a name or backstory. The pet is experimental and may
  change.
- Stable is blue and Insiders is green: one character in two colorways. Two pets make good
  friends, one of each.
- It's cheerful, curious and a little clumsy, and never mean.

## Pixels

- The pet is 12 x 12 logical pixels. One logical pixel is 8 px in the sprite files and 16 px in
  films (`scale=2`, which makes the pet 192 px tall).
- Use integer scales and nearest-neighbor only. For a bigger pet, use `scale=3` or `4`, not a
  resize.
- Draw props on the same grid. Small effects may use 8 px or 4 px steps, as long as you're
  consistent.
- Poses are anchored at the body's bottom center, so a pet on a code line has `y = line.top`.

| Letter | Stable | Insiders | Use |
| --- | --- | --- | --- |
| `C` | `#23a8f2` | `#24bfa5` | body light |
| `A` | `#0077b8` | `#009a7c` | body mid (antennae, edge) |
| `B` | `#004e7c` | `#004538` | body dark |
| `E` | `#191a1b` | `#191a1b` | eyes |

Scenes use the Dark Modern syntax colors (`kit/world.py`).

## Eyes and motion

- An open eye is 1 x 2 logical pixels.
- These states have live eyes: `idleTracking`, `rendering`, `typing`, `press`, `love` and
  `clapping`. Give them `gaze=(dx, dy)` in the range -4..4, and add a blink every 2-4 s on quiet
  beats (`motion.blinking`).
- Special faces (worry, sleep, dizzy, love) are baked into their states. Use those states rather
  than drawing new faces.
- Use the real states and their timings (`python3 -m kit poses`).
  - Hops use `motion.Hop`: about 0.5 s in the air and 150-300 px high.
  - Move the pet by moving the pose. Change its shape only with frames.
- Hold key poses: give each action a clear start, a peak, and a result that stays on screen for
  0.5-1 s.

## Brand

This is an unofficial fan project, so follow https://code.visualstudio.com/brand:

- No Visual Studio Code logo or icon, no "Visual Studio Code" byline, and nothing that looks like
  official Microsoft content.
- Write "Visual Studio Code" (or "VS Code" after the first mention), never "vscode" or "VSCode".
- Don't name your work in a way that implies endorsement.

## Never

- Name the pet, or present fan content as an announcement.
- Show the pet hurt, sad for long, or unkind.
- Use real people, other companies' mascots, or copyrighted characters, music or art.
- Redraw the body from memory. Start from a real state or from `kit move grid`.
- Mix baked eyes and live eyes in the same frame.
