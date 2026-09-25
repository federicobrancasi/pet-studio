# Coding World

A 30-second one-shot of the VS Code pet in a night-time city made of editor windows. It fixes a
bug, builds a bridge out of code, ships the app, and celebrates with a friend. Directed by
Federico Brancasi, built by Claude Opus 5.5, and signed off by Opus 5.5 after three review
rounds.

![Coding World poster](../../docs/media/coding-world-poster.png)

- **Watch:** the MP4 is on the [v1.0 release](https://github.com/federicobrancasi/pet-studio/releases/tag/v1.0).
- **Rebuild:** `python3 -m kit film render coding-world`, which writes
  `out/coding-world/coding-world.mp4` in about two minutes, with exactly the published film's
  frames and soundtrack.

## Beats

| Time | What happens |
| --- | --- |
| 0.0-2.4 s | Title "Coding World". The pet sleeps on the chat input; "fix the bug & ship it" is typed; the first key wakes it and it types along at its tiny terminal |
| 2.4-3.5 s | Prompt sent: it thinks with its speech bubble, then gets an idea (!) |
| 3.5-7.0 s | Hops across `while (awake) hop();` and `let joy = Infinity;`, collecting four stars |
| 7.0-10.0 s | Lands on `ship(app);`, which has a red squiggle. A ladybug approaches, the pet worries, then takes a big hop |
| 10.0-12.0 s | BONK: a pink poof, the bug becomes a butterfly, `// it's a feature!` types itself, and the pet sings |
| 12.0-18.0 s | Follows the butterfly to `// TODO: bridge`, types `new Bridge();` across the gap, and hops over |
| 18.0-22.0 s | The butterfly perches on its antenna; button-press celebration; a terminal shows `42 tests passed` and `shipped!`, with confetti and fireworks |
| 22.0-24.0 s | The green Insiders pet respawns in the sky, falls and lands beside it |
| 24.0-30.0 s | Both show hearts, the end card "Happy coding!" appears, and they hop together on the final chord |

The end card's small "Visual Studio Code" line is part of the film exactly as it was signed off.
New work made with the kit should leave product names and logos off end cards (see the brand
rules in the skill's style guide).

## Techniques worth reusing

| Technique | Where in `film.py` |
| --- | --- |
| One continuous tracking shot that holds still for key moments | `camera_target`, `FollowCamera` |
| A pet whose state changes over time, with hops, blinks and gaze | `hero_pose`, `HOPS`, `BLINKS_HERO` |
| Typing into the chat input, then a code line that types itself | `world.chat_input` + `world.typed`; `CodeLine` characters with `appear` times |
| A bug fix gag: squash, poof and transformation | `draw_bug`, `fx.poof`, `draw_butterfly` |
| A prop that lands on the pet and follows its breathing bob | `draw_butterfly` (the perch) |
| A second pet entering: portal, fall and splat | `friend_pose`, `fx.respawn` |
| Music whose sections follow the story, and SFX read from the same timeline | `music`, `sound_effects` |
