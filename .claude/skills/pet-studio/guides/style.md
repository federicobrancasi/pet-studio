# The VS Code pet: style rules

These rules keep the pet looking like itself. Most come from VS Code's own sprite guidelines
(the `chat-pet-sprite-creation` skill in microsoft/vscode), adapted for videos and images.

## Who the pet is

- A small pixel creature that lives on top of the VS Code chat input. It reacts to chat: it
  types along at a tiny terminal while you type, thinks with a speech bubble while a request
  runs, claps when the agent needs you, falls asleep after 20 quiet seconds, and does a
  button-press celebration when a response finishes.
- Call it "the VS Code pet". Never make up a name, gender or backstory that could be read as
  official. The pet is an experimental Visual Studio Code feature and may change.
- **Stable** is blue, **Insiders** is green. It is one character in two colorways. Two pets
  together work well as friends: one blue, one green.
- It is cheerful, curious and a little clumsy, never mean. Its problems get solved with charm:
  a bug gets bonked into a butterfly and becomes a feature.

## The pixel grid

- The pet is 12 x 12 **logical pixels**. In the sprite files one logical pixel is 8 source
  pixels; in films the kit draws the pet at `scale=2`, so one logical pixel is **16 screen px**
  and the pet is 192 px tall.
- Only whole-number scales, nearest-neighbor, hard edges. Never blur, rotate, skew, smooth or
  resize pet art by fractions. To make the pet bigger, use `scale=3` or `4`, not a resize.
- Props and new art are drawn on the same grid (whole logical pixels). Small effects such as
  sparks and confetti may use half steps (8 px) or quarter steps (4 px), consistently.
- Keep the pet's feet on its ground: poses are anchored at the body's bottom center, so a pet
  standing on a code line has `y = line.top`.

## Palette

| Letter | Stable | Insiders | Use |
| --- | --- | --- | --- |
| `C` | `#23a8f2` | `#24bfa5` | body, light |
| `A` | `#0077b8` | `#009a7c` | body, mid (antennae, edge) |
| `B` | `#004e7c` | `#004538` | body, dark (shadow side) |
| `E` | `#191a1b` | `#191a1b` | eyes |

Other colors in the official sprites: heart red `#ed1c24`, star gold `#ffbe30` and `#ffe780`,
portal cyan `#a3ebe6`. Scenes use VS Code's Dark Modern syntax colors (see `kit/world.py`).

## Eyes

- The normal open eye is **1 x 2 logical pixels**, black, two of them with a 2-pixel gap.
- States with live eyes (`idleTracking`, `rendering`, `typing`, `press`, `love`, `clapping`) take
  a `gaze=(dx, dy)` in source px (-4 to 4) and `blink=True`. Look at what matters: the input
  box while typing, up at a butterfly, at the friend. Blink by hand on quiet beats, about every
  2-4 seconds (`motion.blinking(t, [times])`), never in the middle of an action.
- Special expressions (worried, sleeping, dizzy, love) are baked into their sprites: use those
  states rather than inventing new faces. New moves may add expressions; keep them readable at
  12 x 12.

## Motion

- Use the real states (`python3 -m kit poses --list`, sheet: `python3 -m kit poses`). Their
  timings come from VS Code, so they already feel right.
- Hops use `motion.Hop`: crouch, stretch, airborne, squash and recover are the real jump frames.
  Give each hop a readable arc (height 150-300 px) and about 0.5 s of air.
- Moving the pet around (walking, falling, being thrown) is done by moving the pose, not by
  drawing new frames. Changes to the body's shape are frames, not transforms.
- Hold important poses. An action needs a readable start, a clear peak, and a result that stays
  on screen long enough to register (0.5-1 s).

## Brand

This is a personal, unofficial project. Follow the Visual Studio Code brand guidelines
(https://code.visualstudio.com/brand):

- Don't put the Visual Studio Code logo or icon in outputs, and don't add a "Visual Studio Code"
  byline or anything else that makes a video or image look like official Microsoft content.
- Write "Visual Studio Code" (or "VS Code" after first use), never "vscode" or "VSCode", in text
  people will read.
- Don't use the product name in the name of your film, image or project in a way that implies
  endorsement.

## Never

- Never name the pet, or imply that a fan video is an official Microsoft announcement.
- Never show the pet hurt, sad for long, or doing anything unkind. Bugs become butterflies.
- Never use real people's likenesses, other companies' mascots or trademarks, or copyrighted
  characters, music or art.
- Never redraw the body from memory: start from `pet.grid(...)`, `kit move grid`, or a real state.
- Never put baked eyes and live eyes on the same frame.
