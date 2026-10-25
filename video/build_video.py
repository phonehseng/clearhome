"""Build the Clear Home explainer: two self-contained HTML players and a voiceover script.

  out/clear-home-explainer.html         plays with the recorded narration (voice track drives the clock)
  out/clear-home-explainer-silent.html  same timing, no voice, for someone to narrate live or record over
  out/voiceover-script.md                every line with its exact start time, for a manual voiceover

Inputs: storyboard.json (scenes), timings.json (from the narration), out/narration.m4a, out/*.woff2 fonts.
Usage: python video/build_video.py
"""
import base64
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
CHAPTERS = [("Intro", 0), ("The problem", 2), ("Checked data", 5), ("Finding a home", 9),
            ("Gemma 4 on Google Cloud", 13), ("Safe and honest AI", 19), ("Recap", 23)]


def b64(path):
    return base64.b64encode(Path(path).read_bytes()).decode()


def page(voice):
    story, timings = json.loads((HERE / "storyboard.json").read_text()), json.loads((HERE / "timings.json").read_text())
    chapters = [{"title": t, "scene": i} for t, i in CHAPTERS]
    audio = f'<audio id="voice" preload="auto" src="data:audio/mp4;base64,{b64(OUT / "narration.m4a")}"></audio>' if voice else '<audio id="voice"></audio>'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clear Home: how it works{'' if voice else ' (silent)'}</title>
<style>
  @font-face {{ font-family: 'Google Sans'; src: url(data:font/woff2;base64,{b64(OUT / "googlesans.woff2")}) format('woff2'); font-weight: 100 900; }}
  html, body {{ margin: 0; height: 100%; background: #0b1020; color: #fff; font-family: 'Google Sans', system-ui, sans-serif; }}
  .wrap {{ height: 100%; display: grid; grid-template-rows: 1fr auto; place-items: center; }}
  canvas {{ width: min(100vw, calc((100vh - 64px) * 16 / 9)); aspect-ratio: 16 / 9; display: block; }}
  .bar {{ display: flex; gap: 10px; padding: 12px; }}
  button {{ font: 700 16px 'Google Sans', system-ui; padding: 10px 20px; border-radius: 999px; border: 0; background: #1a73e8; color: #fff; cursor: pointer; }}
  button.ghost {{ background: transparent; border: 1px solid #5f6f95; }}
  body.recording .bar {{ display: none; }}
</style></head>
<body><div class="wrap"><canvas id="stage" width="1920" height="1080" aria-label="Animated explainer of how Clear Home works"></canvas>
<div class="bar"><button id="play">Play</button><button id="export" class="ghost">Export video file</button></div></div>
{audio}
<!-- Sound direction: a calm, warm synth pad in the key of the chapter mood, ducked under the voice; a soft whoosh on each
     scene change and a light impact on every big number and recap check. Narration: a calm British professor. -->
<script>
const STORYBOARD = {json.dumps(story, ensure_ascii=False)};
const TIMINGS = {json.dumps(timings)};
const CHAPTERS = {json.dumps(chapters)};
const HAS_VOICE = {str(voice).lower()};
window.UPLOAD_URL = new URLSearchParams(location.search).get('upload');
</script>
<script>
{(HERE / "player.js").read_text()}
</script></body></html>
"""


def script_md():
    story, timings = json.loads((HERE / "storyboard.json").read_text()), json.loads((HERE / "timings.json").read_text())
    mm = lambda s: f"{int(s // 60)}:{s % 60:04.1f}"
    out = ["# Clear Home explainer: voiceover script", "",
           f"Long form, 16:9, {mm(timings['total'])} total. Narrator: calm, warm British professor. Read each line when its start time comes up;",
           "the silent player shows the same line as a subtitle, so you can read along while recording.", ""]
    chapter_at = {i: t for t, i in CHAPTERS}
    for i, (s, tm) in enumerate(zip(story, timings["scenes"])):
        if i in chapter_at:
            out += [f"## {chapter_at[i]}", ""]
        out += [f"**Scene {i + 1} · {s['kicker']} · “{s['headline']}”** ({mm(tm['start'])}–{mm(tm['end'])})", ""]
        out += [f"- `{mm(c['start'])}` {c['text']}" for c in tm["cues"]] + [""]
    return "\n".join(out)


if __name__ == "__main__":
    (OUT / "clear-home-explainer.html").write_text(page(True))
    (OUT / "clear-home-explainer-silent.html").write_text(page(False))
    (HERE / "voiceover-script.md").write_text(script_md())
    for f in ["clear-home-explainer.html", "clear-home-explainer-silent.html"]:
        print(f, (OUT / f).stat().st_size // 1024, "KB")
    print("voiceover-script.md written")
