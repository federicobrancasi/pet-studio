# Blobby: the name reveal

A 15-second vertical (9:16) reel for Reels, TikTok, Shorts and X. The community picked a name for
the VS Code pet, and this is how the pet finds out: a golden envelope with the winning name
drifts down to it, a gust steals it, and the pet chases it up a sunset sky from cloud to cloud
until a spring cloud launches it high enough to catch it. BLOBBY bursts out, the pet hops along
its new name one note per letter, everyone who sent the name in is credited, and it says hello.

<img src="../../docs/media/blobby.gif" width="270" alt="The reel: the pet chases a golden envelope up a sunset sky, catches it, and BLOBBY bursts out in big bubble letters; the pet hops along its name and says hello">

- **Watch:** the MP4 (with sound) is on the [v1.5.1 release](https://github.com/federicobrancasi/pet-studio/releases/tag/v1.5.1).
- **Rebuild:** `python3 -m kit film review blobby` (the MP4 and its review package, with
  `safe-zones.png`).
- **The credit:** more than ten people sent in "Blobby", so the credit panel names no one:
  "NAMED BY YOU!", the prize, and "WE'LL REACH OUT!" for the winners. The words are at the top
  of `film.py`. The credit and the prize belong to the real naming contest, so leave them out of
  your own films.

| Time | Beat | States and moves |
| --- | --- | --- |
| 0-1 s | The hook: "YOU NAMED ME!" as the envelope drifts down, and an excited hop | `jump` |
| 1 s | A gust snatches the envelope and blows the caption away | |
| 1.5-2.95 s | The chase: a hop to a cloud, a lunge... and the envelope zips away | `jump`, `falling` |
| 2.95 s | A jelly splat on the next cloud, and the pet bounces back | `splat` |
| 3.6-4.2 s | A spring cloud squashes under it and fires it up into dusk | `jump` |
| 5.25 s | It catches the envelope and dangles from it | `falling` |
| 6 s | Flash: the envelope bursts and BLOBBY flies out, letter by letter | |
| 6.5-9.6 s | It hops along its name on the beat, one note per letter, then a big joy jump | `jump` |
| 9.5 s | The credit: NAMED BY YOU!, the prize, and WE'LL REACH OUT! for the winners | `clapping` |
| 12.5 s | Close-up: "HI, I'M BLOBBY!", then a wave | `rendering`, `wave` |
| 14-15 s | The end card pulls back to the name, the credit and the hello | `wave` |

Routines worth reusing from `film.py`, `blobby_world.py` and `blobby_props.py`:

| Technique | Where |
| --- | --- |
| A chase up a world taller than the screen, with a camera that follows the pet | `camera_target`, `CAMERA`, `render_chase` |
| Cloud platforms that dip under a landing, and a spring cloud that squashes and fires | `BW.Platform`, `BW.dip`, `spring_rows` |
| A prop on its own path that keeps getting away, and eyes that follow it | `envelope_pos`, `gaze_at` |
| A flash that bursts into bubble letters, each squashing when the pet lands on it | `BP.flash`, `BP.Logo`, `letter_state` |
| One note per letter, on the beat | `LETTER_LANDS`, `LETTER_NOTES` |
| A pet that talks without a mouth: its `rendering` state, squashing on every syllable | `wide_pose` (`SYLLABLES`) |
| A 2x close-up cropped from the same frame, then an end card that pulls back | `render_closeup`, `render` |

This film came before `kit.sky` and `kit.letters`, which grew out of its helpers. For a new
film, start from those (`sky.CloudPlatform`, `sky.rays`, `letters.BubbleWord`, `draw.zoom`).
