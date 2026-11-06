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


def get_titles(titles):
    import re, time
    for k in range(6):
        r = requests.get(API, headers=UA, timeout=30, params={
            "action": "query", "format": "json", "titles": "|".join(titles), "prop": "imageinfo",
            "iiprop": "url|extmetadata", "iiurlwidth": 1600})
        try:
            pages = r.json()["query"]["pages"].values(); break
        except Exception:
            print("api", r.status_code); time.sleep(5 + 5 * k)
    out = {}
    for p in pages:
        ii = p["imageinfo"][0]; md = ii.get("extmetadata", {})
        art = re.sub("<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip()
        for k in range(5):
            resp = requests.get(ii["thumburl"], headers=UA, timeout=60)
            if resp.ok: break
            time.sleep(5 + 5 * k)
        out[p["title"]] = {"img": Image.open(io.BytesIO(resp.content)).convert("RGB"),
                           "lic": md.get("LicenseShortName", {}).get("value", ""), "artist": art, "title": p["title"]}
        print("PICK", p["title"], "|", out[p["title"]]["lic"], "|", art)
    return out


def cover(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def fade(w, h, k=0.62):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).ellipse((w * (1 - k) / 2, h * (1 - k) / 2, w * (1 + k) / 2, h * (1 + k) / 2), fill=255)
    return m.filter(ImageFilter.GaussianBlur(min(w, h) * 0.16))


def put(base, im, box, alpha=1.0, k=0.62, bright=0.9, sat=1.25):
    x, y, w, h = box
    ph = ImageEnhance.Color(ImageEnhance.Contrast(cover(im, w, h)).enhance(1.12)).enhance(sat)
    ph = ImageEnhance.Brightness(ph).enhance(bright)
    m = fade(w, h, k)
    if alpha < 1:
        m = m.point(lambda v: int(v * alpha))
    base.paste(ph, (x, y), m)


base = Image.open(os.path.join(D, "base.png")).convert("RGB")
T = get_titles(["File:Crabs as food in Antalya.jpg", "File:Crab (1795737730).jpg",
                "File:Alaskan King Crab Legs (3241225745).jpg", "File:Beer Mug (30310981316).jpg"])
rak, rak2, legs, beer = (T[t] for t in ["File:Crabs as food in Antalya.jpg", "File:Crab (1795737730).jpg",
                                        "File:Alaskan King Crab Legs (3241225745).jpg", "File:Beer Mug (30310981316).jpg"])
put(base, rak["img"], (-380, -80, 760, 760), alpha=0.5, k=0.62, bright=0.8)
put(base, rak2["img"], (500, -220, 820, 820), alpha=0.9, k=0.66)
put(base, legs["img"], (-300, 640, 1000, 1000), k=0.7, bright=1.0)
put(base, beer["img"], (560, 720, 620, 760), k=0.7, bright=1.08, sat=1.15)

fg = Image.open(os.path.join(D, "fg.png")).convert("RGBA")
out = base.convert("RGBA")
out.alpha_composite(fg)
out = out.convert("RGB")

t = "Фото: Wikimedia Commons, CC BY — Kadı; David Pursehouse; missbossy; Victor Zolotuhin"
ImageDraw.Draw(out).text((18, 1326), t, fill=(200, 180, 160), font=ImageFont.truetype(os.path.join(D, "GolosText[wght].ttf"), 15))
out.save(os.path.join(D, "kubok_rakov_real.jpg"), quality=92)

th = out.resize((540, 675))
b = io.BytesIO(); th.save(b, "JPEG", quality=70)
print("PREVIEW_B64_START"); print(base64.b64encode(b.getvalue()).decode()); print("PREVIEW_B64_END")
