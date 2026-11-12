"""Draw the Maybe daily cards (1080×1350 JPEGs) from posts.json.

    python scripts/render_cards.py            # every card
    python scripts/render_cards.py q001 t004  # just these

Fonts: uses Zodiak and Satoshi from fonts/ when they're there (the Build cards
workflow downloads them from Fontshare), otherwise Fraunces and Manrope.
"""
import json, os, sys, base64, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"
posts = json.load(open(ROOT / "posts.json"))

NAVY, CREAM, RED, INK = "#15213B", "#F6F0E6", "#C42B32", "#0E1729"

def font_face(family, file, weight="400", style="normal"):
    p = FONTS / file
    if not p.exists(): return ""
    b64 = base64.b64encode(p.read_bytes()).decode()
    fmt = "woff2" if file.endswith("woff2") else "truetype" if file.endswith("ttf") else "woff"
    return (f"@font-face{{font-family:'{family}';src:url(data:font/{fmt};base64,{b64}) format('{fmt}');"
            f"font-weight:{weight};font-style:{style};}}")

FACES = "".join([
    font_face("Zodiak", "Zodiak-Regular.woff2"), font_face("Zodiak", "Zodiak-Italic.woff2", style="italic"),
    font_face("Satoshi", "Satoshi-Medium.woff2", "500"), font_face("Satoshi", "Satoshi-Bold.woff2", "700"),
    font_face("Fraunces", "fraunces-latin-400-normal.woff2"),
    font_face("Fraunces", "fraunces-latin-400-italic.woff2", style="italic"),
    font_face("Manrope", "manrope-latin-500-normal.woff2", "500"),
    font_face("Manrope", "manrope-latin-700-normal.woff2", "700"),
])

def card_html(kind, item, n):
    if kind == "quote":
        bg, fg, accent = (CREAM, NAVY, RED) if n % 2 else (NAVY, CREAM, "#E2575C")
        label = item["stage"]
        foot = "maybeproject.com"
        body = f"<div class='mark'>“</div><div class='txt quote'>{item['text']}</div>"
    elif kind == "tuesday":
        bg, fg, accent = RED, CREAM, NAVY
        label = "Tuesday experiment"
        foot = "Týr’s day · the bravest day of the week"
        body = f"<div class='txt prompt'>{item['text']}</div>"
    else:
        bg, fg, accent = NAVY, CREAM, "#E2575C"
        label = "Spot the maybe"
        foot = "Write it down before you edit it"
        body = f"<div class='txt prompt'>{item['text']}</div>"
    big_label = kind != "quote"
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
{FACES}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1350px;background:{bg};color:{fg}}}
.card{{position:absolute;inset:0;padding:96px 100px 92px;display:flex;flex-direction:column}}
.serif{{font-family:'Zodiak','Fraunces',Georgia,serif}}
.sans{{font-family:'Satoshi','Manrope',Helvetica,Arial,sans-serif}}
.top{{display:flex;align-items:baseline;justify-content:space-between}}
.word{{font-family:'Zodiak','Fraunces',Georgia,serif;font-size:58px;letter-spacing:-.5px;line-height:1}}
.dots{{display:inline-flex;gap:9px;margin-left:8px;transform:translateY(-4px)}}
.dots i{{width:11px;height:11px;border-radius:50%;background:{accent};display:block}}
.label{{font-family:'Satoshi','Manrope',sans-serif;font-weight:700;font-size:{30 if big_label else 22}px;
  letter-spacing:{4 if big_label else 3}px;text-transform:uppercase;color:{accent if big_label else fg};opacity:{1 if big_label else .72}}}
.mid{{flex:1;display:flex;flex-direction:column;justify-content:center;padding:40px 0}}
.mark{{font-family:'Zodiak','Fraunces',Georgia,serif;font-size:220px;line-height:.6;height:96px;color:{accent}}}
.txt{{font-family:'Zodiak','Fraunces',Georgia,serif;letter-spacing:-.4px;text-wrap:pretty}}
.quote{{font-size:76px;line-height:1.16}}
.prompt{{font-size:80px;line-height:1.14}}
.rule{{height:2px;background:{fg};opacity:.25;margin-bottom:30px}}
.foot{{display:flex;justify-content:space-between;font-family:'Satoshi','Manrope',sans-serif;font-weight:500;
  font-size:24px;letter-spacing:.5px;opacity:.85}}
</style></head><body><div class="card">
<div class="top"><div class="word">Maybe<span class="dots"><i></i><i></i><i></i></span></div>
{'' if big_label else ''}</div>
<div class="mid">{('<div class="label" style="margin-bottom:44px">'+label+'</div>') if big_label else ''}{body}</div>
<div class="rule"></div>
<div class="foot"><span>{foot if big_label else label}</span><span>{'' if big_label else foot}</span></div>
</div>
<script>
// shrink the text until the card's middle fits
window.fit=()=>{{const mid=document.querySelector('.mid'), t=document.querySelector('.txt');
let s=parseFloat(getComputedStyle(t).fontSize);
while((mid.scrollHeight>mid.clientHeight) && s>34){{s-=2;t.style.fontSize=s+'px';}}
return s;}};
</script></body></html>"""

def main(only):
    jobs = [(k, it, i) for k in ("quote", "tuesday", "friday") for i, it in enumerate(posts[k], 1)
            if not only or it["id"] in only]
    exe = os.environ.get("CHROME_PATH")
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for kind, it, i in jobs:
            pg.set_content(card_html(kind, it, i), wait_until="load")
            size = pg.evaluate("document.fonts.ready.then(() => fit())")
            if float(size) <= 34: print(f"warning: {it['id']} text is very long")
            pg.screenshot(path=str(ROOT / it["image"]), type="jpeg", quality=90)
        b.close()
    print(f"Rendered {len(jobs)} cards.")

if __name__ == "__main__":
    main(set(sys.argv[1:]))
