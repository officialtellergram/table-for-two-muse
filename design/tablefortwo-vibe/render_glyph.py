from PIL import Image, ImageDraw

GOLD = (201, 168, 106, 255)
BLACK = (10, 10, 11, 255)


def glyph(size, stroke_units=7):
    ss = 4
    S = size * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=BLACK)
    cx = cy = S / 2
    rad = S * 0.26
    w = max(1, int(S * stroke_units / 100))
    bbox = [cx - rad, cy - rad, cx + rad, cy + rad]
    d.arc(bbox, start=192, end=348, fill=GOLD, width=w)
    d.arc(bbox, start=12, end=168, fill=GOLD, width=w)
    return im.resize((size, size), Image.LANCZOS)


for name, size in [("icon-512.png", 512), ("icon-192.png", 192),
                   ("apple-touch-icon.png", 180), ("favicon.png", 64), ("mark.png", 256)]:
    glyph(size).save(f"icons/{name}", optimize=True)
    print(name, size)

open("icons/source.txt", "w").write(
    "icons/favicon.svg + icons/glyph.svg - notched table glyph, gold #c9a86a on "
    "#0a0a0b, gap 24deg, favicon optical stroke 7 (master stroke 4). PNGs rendered with PIL.\n")
