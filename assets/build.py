#!/usr/bin/env python3
"""Builds the profile README's monochrome sections as SVGs, each in a dark and a light version
(assets/dark/*.svg, assets/light/*.svg). The README shows the one that matches the viewer's GitHub theme.

Run:  python3 assets/build.py
Needs internet: each SVG embeds a tiny subset of Inter Tight / JetBrains Mono (only the letters it uses),
fetched from Google Fonts, so the type looks the same everywhere. Edit the text below and run it again.
"""
import base64
import math
import pathlib
import re
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

HERE = pathlib.Path(__file__).parent
W = 1200  # every section is drawn 1200 wide and scaled to fit the README

THEMES = {
    "dark": dict(bg="#0a0a0a", line="#2a2a2a", ink="#f4f4f4", muted="#8e8e8e", glow="#2c2c2c"),
    "light": dict(bg="#fafafa", line="#dcdcdc", ink="#0a0a0a", muted="#6b6b6b", glow="#e4e4e4"),
}
FONTS = {  # class -> (Google Fonts family, weight)
    "thin": ("Inter Tight", 200),
    "light": ("Inter Tight", 300),
    "medium": ("Inter Tight", 500),
    "mono": ("JetBrains Mono", 400),
}
MONO_ADVANCE = 0.6  # JetBrains Mono: every glyph is 0.6em wide, so pills can be sized exactly

_font_cache = {}


def font_subset(cls, chars):
    """A woff2 of just these characters, base64, from the Google Fonts API."""
    family, weight = FONTS[cls]
    text = "".join(sorted(set(chars)))
    key = (cls, text)
    if key not in _font_cache:
        q = urllib.parse.urlencode({"family": f"{family}:wght@{weight}", "text": text})
        ua = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/150 Safari/537.36"}
        css = urllib.request.urlopen(urllib.request.Request(f"https://fonts.googleapis.com/css2?{q}", headers=ua)).read().decode()
        url = re.search(r"url\((https://[^)]+)\)", css).group(1)
        _font_cache[key] = base64.b64encode(urllib.request.urlopen(url).read()).decode()
    return _font_cache[key]


class Svg:
    def __init__(self, h, theme, label, w=W):
        self.w, self.h, self.c, self.label = w, h, THEMES[theme], label
        self.parts, self.used = [], {}

    def col(self, name):
        return self.c.get(name, name)

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, runs, size, fill="ink", anchor="start", ls=0, font="light"):
        """runs: a string, or [(text, font), ...] to mix weights in one line."""
        if isinstance(runs, str):
            runs = [(runs, font)]
        spans = ""
        for t, f in runs:
            self.used.setdefault(f, set()).update(t)
            spans += f'<tspan class="{f}">{escape(t)}</tspan>'
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{self.col(fill)}" text-anchor="{anchor}" letter-spacing="{ls}">{spans}</text>')

    def lines(self, x, y, lines, size, gap, **kw):
        for i, t in enumerate(lines):
            self.text(x, y + i * gap, t, size, **kw)

    def frame(self, fill="bg", r=24):
        self.add(f'<rect x="0.5" y="0.5" width="{self.w - 1}" height="{self.h - 1}" rx="{r}" fill="{self.col(fill)}" stroke="{self.col("line")}"/>')

    def arrow(self, x, y, s, direction, stroke="ink", width=2):
        """A drawn arrow (ne, e or s) in an s-by-s box at x, y."""
        c = self.col(stroke)
        if direction == "ne":
            d = f"M{x} {y + s} L{x + s} {y} M{x + s * .3} {y} H{x + s} V{y + s * .7}"
        elif direction == "e":
            d = f"M{x} {y + s / 2} H{x + s} M{x + s * .6} {y + s * .15} L{x + s} {y + s / 2} L{x + s * .6} {y + s * .85}"
        else:
            d = f"M{x + s / 2} {y} V{y + s} M{x + s * .15} {y + s * .6} L{x + s / 2} {y + s} L{x + s * .85} {y + s * .6}"
        self.add(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')

    def pill(self, x, y, label, size=15, fill="none", stroke="line", color="ink", pad=14, h=34):
        """An outlined mono label; returns its width."""
        w = len(label) * size * MONO_ADVANCE + pad * 2
        self.add(f'<rect x="{x}" y="{y}" width="{w:.1f}" height="{h}" rx="{h / 2}" fill="{self.col(fill)}" stroke="{self.col(stroke)}"/>')
        self.text(x + w / 2, y + h / 2 + size * .36, label, size, fill=color, anchor="middle", font="mono")
        return w

    def render(self, extra_css=""):
        faces = "".join(
            f"@font-face{{font-family:'pa-{cls}';src:url(data:font/woff2;base64,{font_subset(cls, chars)}) format('woff2')}}"
            f".{cls}{{font-family:'pa-{cls}','Helvetica Neue',Helvetica,Arial,sans-serif}}"
            for cls, chars in sorted(self.used.items()))
        css = faces + extra_css + "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
                f'role="img" aria-label="{escape(self.label)}"><title>{escape(self.label)}</title><style>{css}</style>'
                + "".join(self.parts) + "</svg>")


# ---------------------------------------------------------------- sections


def dotted_sphere(s, cx, cy, r, n=460):
    """A slowly turning point-cloud globe: nearer dots are bigger and brighter."""
    dots = []
    tilt_x, tilt_y = math.radians(-22), math.radians(28)
    for i in range(n):
        yy = 1 - 2 * (i + .5) / n
        rad, th = math.sqrt(1 - yy * yy), math.pi * (3 - math.sqrt(5)) * i
        x, y, z = math.cos(th) * rad, yy, math.sin(th) * rad
        y, z = y * math.cos(tilt_x) - z * math.sin(tilt_x), y * math.sin(tilt_x) + z * math.cos(tilt_x)
        x, z = x * math.cos(tilt_y) + z * math.sin(tilt_y), -x * math.sin(tilt_y) + z * math.cos(tilt_y)
        near = (z + 1) / 2
        dots.append(f'<circle cx="{cx + x * r:.1f}" cy="{cy + y * r:.1f}" r="{.9 + 1.5 * near:.2f}" opacity="{.1 + .8 * near ** 1.6:.2f}"/>')
    s.add(f'<ellipse cx="{cx}" cy="{cy}" rx="{r + 26}" ry="{(r + 26) * .28}" fill="none" stroke="{s.col("line")}" transform="rotate(-18 {cx} {cy})"/>')
    s.add(f'<g class="globe" fill="{s.col("ink")}">{"".join(dots)}</g>')
    return f".globe{{transform-box:view-box;transform-origin:{cx}px {cy}px;animation:spin 120s linear infinite}}"


def ring_badge(s, cx, cy, r, label):
    """Circular text that slowly turns around a down arrow."""
    s.add(f'<defs><path id="ring" d="M{cx - r} {cy} a{r} {r} 0 1 1 {2 * r} 0 a{r} {r} 0 1 1 {-2 * r} 0"/></defs>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{r + 16}" fill="none" stroke="{s.col("line")}"/>')
    s.used.setdefault("mono", set()).update(label)
    s.add(f'<g class="ring"><text font-size="11" fill="{s.col("muted")}"><textPath href="#ring" class="mono" textLength="{2 * math.pi * r - 4:.1f}" lengthAdjust="spacing">{escape(label)}</textPath></text></g>')
    s.arrow(cx - 9, cy - 11, 18, "s", width=1.6)
    return f".ring{{transform-box:view-box;transform-origin:{cx}px {cy}px;animation:spin 28s linear infinite}}"


def hero(theme):
    s = Svg(640, theme, "Prachiti Palande: the data scientist of your dreams. AI & Data Science, M.Sc. Computer Science at University College Dublin.")
    s.add(f'<defs><radialGradient id="glow" cx="50%" cy="0%" r="75%"><stop offset="0" stop-color="{s.col("glow")}"/>'
          f'<stop offset="1" stop-color="{s.col("bg")}"/></radialGradient></defs>')
    s.add(f'<rect x="0.5" y="0.5" width="{W - 1}" height="639" rx="24" fill="url(#glow)" stroke="{s.col("line")}"/>')
    css = dotted_sphere(s, 930, 330, 175)
    s.text(48, 64, "prachiti.", 24, font="medium")
    s.text(W / 2, 62, "AI & DATA SCIENCE", 15, fill="muted", anchor="middle", ls=2, font="mono")
    s.text(W - 48, 62, "DUBLIN, IE", 15, fill="muted", anchor="end", ls=2, font="mono")
    s.lines(48, 170, ["M.Sc. Computer Science", "University College Dublin"], 16, 24, fill="muted", font="mono")
    s.arrow(W - 84, 150, 30, "ne", width=3)
    s.text(300, 262, "THE DATA", 108, font="thin", ls=-2)
    s.text(150, 372, "SCIENTIST OF", 108, font="medium", ls=-3)
    s.text(430, 482, "YOUR DREAMS", 108, font="thin", ls=-2)
    s.lines(48, 420, ["I build GenAI prototypes,", "document-intelligence", "pipelines and automations", "that turn messy data into", "useful little tools."], 18, 26, fill="muted", font="light")
    css += ring_badge(s, W / 2, 568, 34, "SCROLL TO EXPLORE · SCROLL TO EXPLORE · ")
    return s.render(css + "@keyframes spin{to{transform:rotate(360deg)}}")


def about(theme):
    s = Svg(400, theme, "About: AI & Data Science graduate doing an M.Sc. in Computer Science at University College Dublin. 4+ internships, 1 published paper, 9.01 GPA.")
    s.frame()
    s.text(48, 118, "ABOUT", 76, font="thin", ls=-1)
    s.lines(48, 186, [
        "I'm an AI & Data Science graduate, now doing an M.Sc. in",
        "Computer Science at University College Dublin. I like",
        "building tech that feels kind: a keyboard you type with",
        "your eyes, a tool that tells you if your rent is fair.",
        "For me, AI is a way to make the world more accessible.",
    ], 20, 31, font="light")
    for i, (num, label) in enumerate([("4+", "INTERNSHIPS"), ("1", "PUBLISHED PAPER"), ("9.01", "GPA")]):
        x = 760 + i * 160
        s.text(x, 248, num, 76, anchor="middle", font="thin", ls=-2)
        s.text(x, 284, label, 12, fill="muted", anchor="middle", ls=1.5, font="mono")
    s.add(f'<line x1="700" y1="150" x2="700" y2="330" stroke="{s.col("line")}"/>')
    return s.render()


def work_head(theme):
    s = Svg(210, theme, "Selected work")
    s.frame()
    s.text(48, 112, "SELECTED WORK", 76, font="thin", ls=-1)
    s.lines(48, 158, ["A few things I've built, from ML nowcasts to accessibility tools."], 19, 28, fill="muted", font="light")
    s.text(W - 48, 112, "04", 76, anchor="end", font="thin", fill="muted")
    return s.render()


CARDS = [  # (slug, number, title, description lines, tools, link status)
    ("dublin-rent-lens", "01", "DUBLIN RENT LENS", ["Is that Dublin rent fair? Calibrated ML nowcasts", "for 600+ area and unit types, built on official", "RTB and Property Price Register data."],
     ["Python", "scikit-learn", "Quantile GBM", "Conformal"], "link"),
    ("gaze-keyboard", "02", "GAZE-BASED KEYBOARD", ["Type with your eyes: it tracks where you look", "and a blink presses the key. Built for", "accessibility."],
     ["Python", "OpenCV", "MediaPipe"], "link"),
    ("paper-archive", "03", "PAPER ARCHIVE", ["Dense academic papers retold for everyone, with", "analogies, a quiz and an in-context glossary,", "by a small model running in your browser."],
     ["JavaScript", "WebLLM", "WebGPU", "pdf.js"], "wip"),
    ("greenmix", "04", "GREENMIX", ["Closed-loop dental restoration: scan a cavity", "from a photo, model it in 3D and work out", "exactly how much composite it needs."],
     ["JavaScript", "three.js", "Python"], "link"),
]


def card(theme, slug, num, title, desc, tools, status, inverted):
    s = Svg(340, theme, f"{num} {title.title()}: {' '.join(desc)}", w=590)
    fg, sub = ("bg", "line") if inverted else ("ink", "muted")
    s.frame(fill="ink" if inverted else "bg", r=22)
    s.add(f'<circle cx="46" cy="50" r="19" fill="none" stroke="{s.col(fg)}"/>')
    s.text(46, 55, num, 13, fill=fg, anchor="middle", font="mono")
    if status == "link":
        s.add(f'<circle cx="{590 - 50}" cy="50" r="22" fill="none" stroke="{s.col(fg)}"/>')
        s.arrow(590 - 58, 42, 16, "ne", stroke=fg, width=1.8)
    else:
        w = len("IN PROGRESS") * 12 * MONO_ADVANCE + 28
        s.pill(590 - 28 - w, 33, "IN PROGRESS", size=12, stroke=sub, color=sub, h=32)
    s.text(28, 186, title, 30, fill=fg, font="medium", ls=.5)
    s.lines(28, 220, desc, 17, 25, fill=sub if not inverted else "bg", font="light")
    x = 28
    for t in tools:
        x += s.pill(x, 282, t, size=13, stroke=sub, color=fg, h=30, pad=11) + 8
    return s.render()


def more(theme):
    s = Svg(64, theme, "... and many more on my GitHub", w=360)
    s.add(f'<rect x="0.5" y="0.5" width="290" height="63" rx="31.5" fill="{s.col("ink")}"/>')
    s.text(145, 38, "... AND MANY MORE", 15, fill="bg", anchor="middle", ls=1.5, font="mono")
    s.add(f'<circle cx="327" cy="32" r="31" fill="{s.col("ink")}"/>')
    s.arrow(316, 21, 22, "ne", stroke="bg", width=2)
    return s.render()


TOOLKIT = [
    ("ML & DEEP LEARNING", ["Python", "PyTorch", "TensorFlow", "scikit-learn", "Jupyter"]),
    ("DATA", ["NumPy", "Pandas", "OpenCV", "Matplotlib", "MySQL", "SQLite"]),
    ("GENAI & WEB", ["LangChain", "TypeScript", "Vercel", "Anaconda"]),
    ("DESIGN", ["Figma", "Canva", "Framer"]),
]


def toolkit(theme):
    s = Svg(150 + len(TOOLKIT) * 58 + 30, theme, "Toolkit: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in TOOLKIT))
    s.frame()
    s.text(48, 112, "TOOLKIT", 76, font="thin", ls=-1)
    for i, (group, items) in enumerate(TOOLKIT):
        y = 162 + i * 58
        s.add(f'<line x1="48" y1="{y - 12}" x2="{W - 48}" y2="{y - 12}" stroke="{s.col("line")}"/>')
        s.text(48, y + 25, f"0{i + 1}", 13, fill="muted", font="mono")
        s.text(100, y + 25, group, 13, fill="muted", ls=1.5, font="mono")
        x = 380
        for t in items:
            x += s.pill(x, y + 3, t, size=14, h=32) + 10
    return s.render()


def contact(theme):
    s = Svg(470, theme, "Your problem called. It wants AI. Hiring for AI, ML or data roles, or want to build something together? My inbox is always open.")
    s.frame()
    s.text(250, 128, "YOUR PROBLEM", 96, font="thin", ls=-2)
    s.text(470, 224, "CALLED.", 96, font="medium", ls=-2)
    s.text(330, 320, [("IT WANTS ", "thin"), ("AI.", "medium")], 96, ls=-2)
    s.lines(W / 2, 378, ["Hiring for AI, ML or data roles, or want to build something together?", "My inbox is always open."], 18, 27, fill="muted", anchor="middle", font="light")
    s.add(f'<line x1="48" y1="430" x2="{W - 48}" y2="430" stroke="{s.col("line")}"/>')
    s.text(48, 452, "© 2026 PRACHITI PALANDE", 11, fill="muted", ls=1.5, font="mono")
    s.text(W - 48, 452, "BASED IN DUBLIN, IRELAND", 11, fill="muted", anchor="end", ls=1.5, font="mono")
    return s.render()


def button(theme, label):
    w = len(label) * 14 * MONO_ADVANCE + 44 + 50
    s = Svg(52, theme, label, w=round(w) + 2)
    s.add(f'<rect x="1" y="1" width="{w - 50:.1f}" height="50" rx="25" fill="{s.col("ink")}"/>')
    s.text((w - 50) / 2 + 1, 31, label, 14, fill="bg", anchor="middle", ls=1, font="mono")
    s.add(f'<circle cx="{w - 24:.1f}" cy="26" r="25" fill="{s.col("ink")}"/>')
    s.arrow(w - 32, 18, 16, "ne", stroke="bg", width=1.8)
    return s.render()


def main():
    for theme in THEMES:
        out = HERE / theme
        out.mkdir(exist_ok=True)
        files = {"hero": hero(theme), "about": about(theme), "work": work_head(theme), "more": more(theme),
                 "toolkit": toolkit(theme), "contact": contact(theme)}
        for i, (slug, *rest) in enumerate(CARDS):
            files[f"card-{slug}"] = card(theme, slug, *rest, inverted=i == 0)
        for label in ["PORTFOLIO", "LINKEDIN", "EMAIL", "INSTAGRAM"]:
            files[f"btn-{label.lower()}"] = button(theme, label)
        for name, svg in files.items():
            (out / f"{name}.svg").write_text(svg)
        print(theme, len(files), "files", sum(len(v) for v in files.values()) // 1024, "KB")


if __name__ == "__main__":
    main()
