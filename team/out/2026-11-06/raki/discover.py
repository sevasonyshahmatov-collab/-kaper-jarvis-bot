"""Кандидаты фото крабов и пива с Wikimedia Commons: список + контактные листы в лог (base64)."""
import base64, io, re
import requests
from PIL import Image, ImageDraw

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "jarvibet-banner/1.0 (team script)"}
GROUPS = {
    "crab": (["Cooked crabs", "Crabs as food", "Boiled crabs", "Steamed crabs", "Crab dishes",
              "Paralithodes camtschaticus as food", "Cancer pagurus as food", "Callinectes sapidus as food"],
             ["intitle:crab boiled", "intitle:crab steamed", "intitle:crab cooked", "intitle:crabs plate"], "crab"),
    "beer": (["Beer mugs", "Glasses of beer", "Beer in glasses", "Beer steins", "Lager beer in glasses"],
             ["intitle:beer mug", "intitle:beer glass foam", "intitle:pint lager"], "beer|pint|stein|lager|bier|pivo"),
}


def info(titles):
    out = []
    for i in range(0, len(titles), 40):
        r = requests.get(API, headers=UA, timeout=30, params={
            "action": "query", "format": "json", "titles": "|".join(titles[i:i + 40]), "prop": "imageinfo",
            "iiprop": "url|size|extmetadata|mime", "iiurlwidth": 300}).json()
        for p in r.get("query", {}).get("pages", {}).values():
            ii = (p.get("imageinfo") or [{}])[0]
            if ii.get("mime") != "image/jpeg" or ii.get("width", 0) < 1200:
                continue
            lic = ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")
            out.append((p["title"], lic, ii["width"], ii["height"], ii.get("thumburl")))
    return out


for g, (cats, qs, rx) in GROUPS.items():
    titles = []
    for c in cats:
        r = requests.get(API, headers=UA, timeout=30, params={"action": "query", "format": "json", "list": "categorymembers",
                         "cmtitle": "Category:" + c, "cmtype": "file", "cmlimit": 40}).json()
        titles += [m["title"] for m in r.get("query", {}).get("categorymembers", [])]
    for q in qs:
        r = requests.get(API, headers=UA, timeout=30, params={"action": "query", "format": "json", "list": "search",
                         "srsearch": q + " filetype:bitmap", "srnamespace": 6, "srlimit": 30}).json()
        titles += [m["title"] for m in r.get("query", {}).get("search", [])]
    titles = [t for t in dict.fromkeys(titles) if re.search(rx, t, re.I)]
    cand = [c for c in info(titles) if re.search(r"cc0|public domain|^pd|cc by", c[1], re.I)][:30]
    sheet = Image.new("RGB", (6 * 200, 5 * 200), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for i, (t, lic, w, h, u) in enumerate(cand):
        print(f"CAND {g} {i} | {t} | {lic} | {w}x{h}")
        try:
            im = Image.open(io.BytesIO(requests.get(u, headers=UA, timeout=30).content)).convert("RGB")
            im.thumbnail((196, 196))
            x, y = (i % 6) * 200, (i // 6) * 200
            sheet.paste(im, (x + 2, y + 2))
            d.rectangle((x + 2, y + 2, x + 30, y + 22), fill=(0, 0, 0)); d.text((x + 6, y + 6), str(i), fill=(255, 255, 0))
        except Exception as e:  # noqa
            print("thumb fail", t, e)
    b = io.BytesIO(); sheet.save(b, "JPEG", quality=60)
    print(f"SHEET_{g}_START"); print(base64.b64encode(b.getvalue()).decode()); print(f"SHEET_{g}_END")
