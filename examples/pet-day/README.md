# A day in the life

A 30-second vertical (9:16) reel for Reels, TikTok, Shorts and X. The VS Code pet goes through a
coding day, from the morning coffee to logging off, told with the ready-made moves in
[`moves/`](../../moves/README.md), and falls asleep on the chat input.

<img src="../../docs/media/pet-day.gif" width="270" alt="The reel: a clock and a caption at the top, the pet playing one move per beat on the chat input">

- **Watch:** the MP4 (with sound) is on the [v1.1 release](https://github.com/federicobrancasi/pet-studio/releases/tag/v1.1).
- **Rebuild:** `python3 -m kit film review pet-day` (the MP4 and its review package, with
  `safe-zones.png`).

| Time | Beat | Move |
| --- | --- | --- |
| 0-2 s | The hook: "a day in the life of the VS Code pet" | |
| 2 s | 09:00 coffee first | `coffee` |
| 4.75 s | 09:30 a wild idea | `idea` |
| 7 s | 10:00 rubber ducking | `rubber-duck` |
| 9.5 s | 11:00 found the bug | `debug` |
| 12.5 s | 12:00 merge conflict | `zapped` |
| 15 s | 12:01 still conflicts | `angry` |
| 17.75 s | 14:00 it works?! | `magic` |
| 20 s | 16:00 ship it | `ship-it` |
| 21.5 s | 16:01 all tests pass | `trophy` |
| 23.5 s | 17:00 PR approved | `yes` |
| 25.5 s | 18:00 logging off | `cowboy` |
| 27.75-30.5 s | "Happy coding!" while the pet dozes off | `waking` backwards, then `sleep` |

Routines worth reusing from `film.py`:

| Technique | Where |
| --- | --- |
| A reel from ready-made moves: change `DAY` and the timings follow | `DAY`, `_schedule` |
| Moves that start on the musical grid after the previous one settles | `_schedule` (`GRID`, `GAP`) |
| Captions and the pet inside the vertical safe area | `layout.safe_area`, `caption` |
| A close-up pet (`scale=3`) placed so wide moves still fit | `PET_X`, `hero_pose` |
| Sound effects on a move's own frames | `at(name, frame)`, `sound_effects` |
| Reviewing each beat at its move's key frame | `CUES` |
