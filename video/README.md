# Clear Home explainer video

A long-form (16:9, about 6 minutes) explainer of how Clear Home works, drawn entirely with code.

## The look

- **Title:** Clear Home: how one site finds you a home
- **Mood:** calm, with a warm cinematic story style (full-bleed illustrated scenes, a vignette and soft light)
- **Accent color:** `#1a73e8` (Google blue); **good** `#188038` / `#34a853` (Google green); **bad** `#c5221f` / `#ea4335` (Google red); highlight `#fbbc04` (Google yellow); the logo's orange ping `#ff8a1f`
- **Font:** Google Sans for everything (headlines, captions, labels and subtitles), matching the site. It's embedded in the file.
- **Narrator:** a calm British professor (macOS voice "Daniel" for the voiced version)
- **Character:** Sam, a student with a round face, dot eyes and a navy cap with the orange ping
- **Sound direction:** a calm, warm synth pad that follows each chapter's mood, ducked under the voice; a soft whoosh on every scene change and a light impact on each big number and recap check

## Files

| File | What it is |
|---|---|
| `storyboard.json` | The 24 scenes, one per line (kicker, headline, narration cues, and each scene's data) |
| `timings.json` | When every line starts and ends, measured from the recorded narration |
| `voiceover-script.md` | The script for a manual voiceover, with a start time for every line |
| `player.js` | Draws any moment of the video as a pure function of time `t` (canvas, flat shapes, no images) |
| `build_video.py` | Builds `out/clear-home-explainer.html` (with voice) and `out/clear-home-explainer-silent.html` |
| `out/` (not in git) | The built players, the narration audio and the exported video files |

## Rebuild

```bash
python video/build_video.py
```

Open either HTML file and press **Play**. **Export video file** records the canvas (and voice) in real time and downloads an MP4 or WebM. Add `?t=95` to the URL to jump to a moment.

## Accuracy

All numbers come from Clear Home's own data and measurements on 2026-10-24: 409 checked resources (309 homes and floor plans, 33 shelters, 31 help programs), 2 regions, Reston distances from a real "near" answer, and about 72 s vs about 3 s to the first word (hosted API vs our Cloud Run GPU, measured). "Cost burdened" uses the standard 30%-of-income definition.
