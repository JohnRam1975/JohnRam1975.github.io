from PIL import Image
import math

src = r"C:\Users\Djohn\Desktop\DeJohn System\JohnRam1975.github.io\logo-dejohn.png"
# keep original backup path if needed
bak = r"C:\Users\Djohn\Desktop\DeJohn System\JohnRam1975.github.io\logo-dejohn-original.png"
out = src

img = Image.open(src).convert("RGBA")
img.save(bak)

w, h = img.size
px = img.load()

samples = [px[2, 2], px[w - 3, 2], px[2, h - 3], px[w - 3, h - 3], px[w // 2, 2], px[2, h // 2]]
br = sum(s[0] for s in samples) / len(samples)
bg = sum(s[1] for s in samples) / len(samples)
bb = sum(s[2] for s in samples) / len(samples)
print(f"bg approx RGB=({br:.1f},{bg:.1f},{bb:.1f})")


def dist(c):
    return math.sqrt((c[0] - br) ** 2 + (c[1] - bg) ** 2 + (c[2] - bb) ** 2)


hard = 40
soft = 78
changed = 0
for y in range(h):
    for x in range(w):
        r, g, b, a = px[x, y]
        d = dist((r, g, b))
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        is_dark_navy = luminance < 38 and b >= r - 5 and b >= g - 5
        if d <= hard or (is_dark_navy and d < soft):
            px[x, y] = (r, g, b, 0)
            changed += 1
        elif d < soft:
            t = (d - hard) / (soft - hard)
            na = int(255 * t)
            px[x, y] = (r, g, b, min(a, na))
            changed += 1

img.save(out, "PNG")
print(f"saved {out}, pixels adjusted={changed}, size={w}x{h}")
