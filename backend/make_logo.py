"""Draw the Clear Home logo from simple shapes and write every icon the site uses.

A rounded square in the site's blue (gradient #2f55b5 → #23408f), a white house (roof chevron, walls and a
door), a soft light window, and the orange "ping" dot from the hero label as a small notification accent.

Writes: frontend/logo.svg (header mark), frontend/favicon.svg, frontend/favicon.ico (16/32/48),
frontend/apple-touch-icon.png (180x180).

Usage: python backend/make_logo.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
BLUE_TOP, BLUE_BOTTOM = (47, 85, 181), (35, 64, 143)  # #2f55b5 → #23408f, the site's primary blues
WINDOW = (226, 234, 251)                               # #e2eafb, the pale blue used for chips and tabs
ORANGE = (255, 138, 31)                                # #ff8a1f, the hero ping

# Shapes on a 64-unit grid, shared by the SVG and the PNG drawing.
ROOF = [(14, 31), (32, 16), (50, 31)]                  # chevron, drawn as a thick rounded line
WALLS = (19, 29, 45, 49)                               # x0, y0, x1, y1 (bottom corners rounded)
DOOR = (28.5, 37, 35.5, 49)                            # arched door, cut out in the background blue
WINDOW_BOX = (37.5, 33, 42, 37.5)
PING = (51, 13, 5.2)                                   # cx, cy, r


def svg():
    (rx0, ry0), (rx1, ry1), (rx2, ry2) = ROOF
    wx0, wy0, wx1, wy1 = WALLS
    dx0, dy0, dx1, dy1 = DOOR
    door_r = (dx1 - dx0) / 2
    cx, cy, r = PING
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Clear Home">
  <defs>
    <linearGradient id="ch-bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2f55b5"/><stop offset="1" stop-color="#23408f"/></linearGradient>
    <radialGradient id="ch-glow"><stop offset="0" stop-color="#ff8a1f" stop-opacity=".55"/><stop offset="1" stop-color="#ff8a1f" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="64" height="64" rx="16" fill="url(#ch-bg)"/>
  <path d="M{wx0} {wy0 + 1}L32 19L{wx1} {wy0 + 1}Z" fill="#fff"/>
  <path d="M{wx0} {wy0}H{wx1}V{wy1 - 3}a3 3 0 0 1-3 3H{wx0 + 3}a3 3 0 0 1-3-3Z" fill="#fff"/>
  <path d="M{dx0} {dy1}V{dy0 + door_r}a{door_r} {door_r} 0 0 1 {dx1 - dx0} 0V{dy1}Z" fill="#23408f"/>
  <rect x="{WINDOW_BOX[0]}" y="{WINDOW_BOX[1]}" width="{WINDOW_BOX[2] - WINDOW_BOX[0]}" height="{WINDOW_BOX[3] - WINDOW_BOX[1]}" rx="1.2" fill="#e2eafb"/>
  <path d="M{rx0} {ry0}L{rx1} {ry1}L{rx2} {ry2}" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="{cx}" cy="{cy}" r="{r * 2}" fill="url(#ch-glow)"/>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="#ff8a1f" stroke="#fff" stroke-width="1.6"/>
</svg>
'''


def png(size):
    """The same shapes drawn with Pillow at 4x and scaled down, for crisp small icons."""
    s = size * 4 / 64
    big = size * 4
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    grad = Image.new("RGBA", (big, big))
    gd = ImageDraw.Draw(grad)
    for y in range(big):  # vertical blue gradient
        t = y / (big - 1)
        gd.line([(0, y), (big, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(BLUE_TOP, BLUE_BOTTOM)) + (255,))
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, big - 1, big - 1], radius=16 * s, fill=255)
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)
    wx0, wy0, wx1, wy1 = (v * s for v in WALLS)
    d.rounded_rectangle([wx0, wy0, wx1, wy1], radius=3 * s, fill="white")
    d.rectangle([wx0, wy0, wx1, wy0 + 4 * s], fill="white")  # square top corners under the roof
    d.polygon([(wx0, wy0 + 1 * s), (32 * s, 19 * s), (wx1, wy0 + 1 * s)], fill="white")  # gable under the roof
    dx0, dy0, dx1, dy1 = (v * s for v in DOOR)
    d.rounded_rectangle([dx0, dy0, dx1, dy1], radius=(dx1 - dx0) / 2, fill=BLUE_BOTTOM)
    d.rectangle([dx0, (dy0 + dy1) / 2, dx1, dy1], fill=BLUE_BOTTOM)  # square bottom: the door meets the ground
    d.rounded_rectangle([v * s for v in WINDOW_BOX], radius=1.2 * s, fill=WINDOW)
    d.line([(x * s, y * s) for x, y in ROOF], fill="white", width=round(5 * s), joint="curve")
    for x, y in (ROOF[0], ROOF[2]):  # round line caps
        d.ellipse([x * s - 2.5 * s, y * s - 2.5 * s, x * s + 2.5 * s, y * s + 2.5 * s], fill="white")
    cx, cy, r = (v * s for v in PING)
    glow = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([cx - r * 1.9, cy - r * 1.9, cx + r * 1.9, cy + r * 1.9], fill=ORANGE + (110,))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(r * .6)))
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r - 1.6 * s, cy - r - 1.6 * s, cx + r + 1.6 * s, cy + r + 1.6 * s], fill="white")
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ORANGE)
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    mark = svg()
    (FRONTEND / "logo.svg").write_text(mark)
    (FRONTEND / "favicon.svg").write_text(mark)
    png(180).convert("RGB").save(FRONTEND / "apple-touch-icon.png")
    png(48).save(FRONTEND / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    png(512).save(FRONTEND.parent / "docs" / "logo-512.png")
    print("Wrote logo.svg, favicon.svg, favicon.ico, apple-touch-icon.png and docs/logo-512.png")
