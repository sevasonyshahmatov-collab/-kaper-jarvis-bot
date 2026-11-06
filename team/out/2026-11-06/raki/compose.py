"""Кубок раков 2026: реальные фото раков и пива (Wikimedia Commons) под карточками ставок.
Запускается в Actions (там есть сеть): python team/out/2026-11-06/raki/compose.py
Фон base.png и передний план fg.png нарисованы заранее (Playwright, banner.html)."""
import base64, io, os, sys
import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

D = os.path.dirname(os.path.abspath(__file__))
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "jarvibet-banner/1.0 (team script)"}
OK = ("cc0", "public domain", "pd")


def search(q, n=25):
    r = requests.get(API, headers=UA, timeout=30, params={
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"{q} filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": n, "prop": "imageinfo", "iiprop": "url|size|extmetadata|mime",
        "iiurlwidth": 1400})
    pages = r.json().get("query", {}).get("pages", {}).values()
    out = []
    for p in sorted(pages, key=lambda p: p.get("index", 99)):
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("mime") != "image/jpeg" or ii.get("width", 0) < 1000:
            continue
        md = ii.get("extmetadata", {})
        lic = md.get("LicenseShortName", {}).get("value", "")
        art = md.get("Artist", {}).get("value", "")
        out.append({"title": p["title"], "url": ii.get("thumburl") or ii["url"], "lic": lic,
                    "artist": __import__("re").sub("<[^>]+>", "", art).strip(), "w": ii["width"], "h": ii["height"]})
    return out


def pick(queries, skip=()):
    free, other = [], []
    for q in queries:
        for c in search(q):
            if c["title"] in skip:
                continue
            (free if c["lic"].lower().startswith(OK) else other).append(c)
    for c in free + other:
        if c["lic"].lower().startswith(OK) or "cc by" in c["lic"].lower():
            try:
                im = Image.open(io.BytesIO(requests.get(c["url"], headers=UA, timeout=60).content)).convert("RGB")
                c["img"] = im
                print("PICK", c["title"], "|", c["lic"], "|", c["artist"])
                return c
            except Exception as e:  # noqa
                print("skip", c["title"], e)
    sys.exit("no photo for " + str(queries))


def cover(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def fade(w, h, k=0.62):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).ellipse((w * (1 - k) / 2, h * (1 - k) / 2, w * (1 + k) / 2, h * (1 + k) / 2), fill=255)
    return m.filter(ImageFilter.GaussianBlur(min(w, h) * 0.16))


def put(base, im, box, alpha=1.0, k=0.62, bright=0.9):
    x, y, w, h = box
    ph = ImageEnhance.Brightness(cover(im, w, h)).enhance(bright)
    m = fade(w, h, k)
    if alpha < 1:
        m = m.point(lambda v: int(v * alpha))
    base.paste(ph, (x, y), m)


base = Image.open(os.path.join(D, "base.png")).convert("RGB")
rak = pick(["boiled crayfish", "cooked crayfish plate", "crayfish party"])
rak2 = pick(["crayfish dish", "boiled crawfish", "kräftskiva"], skip={rak["title"]})
beer = pick(["beer mug foam", "glass of beer lager", "beer stein"])

put(base, rak2["img"], (560, -160, 720, 720), alpha=0.75)
put(base, rak["img"], (-200, 700, 900, 900), k=0.7)
put(base, beer["img"], (560, 640, 680, 860), k=0.7, bright=0.95)
put(base, rak2["img"], (-260, 120, 620, 620), alpha=0.55)

fg = Image.open(os.path.join(D, "fg.png")).convert("RGBA")
out = base.convert("RGBA")
out.alpha_composite(fg)
out = out.convert("RGB")

credits = [c for c in (rak, rak2, beer) if not c["lic"].lower().startswith(OK)]
if credits:
    t = "Фото: " + "; ".join(f"{c['artist'][:30]}, {c['lic']}" for c in credits) + " · Wikimedia Commons"
    ImageDraw.Draw(out).text((18, 1326), t[:160], fill=(200, 180, 160), font=ImageFont.truetype(os.path.join(D, "GolosText[wght].ttf"), 15))
out.save(os.path.join(D, "kubok_rakov_real.jpg"), quality=92)

th = out.resize((432, 540))
b = io.BytesIO(); th.save(b, "JPEG", quality=55)
print("PREVIEW_B64_START"); print(base64.b64encode(b.getvalue()).decode()); print("PREVIEW_B64_END")
