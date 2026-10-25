"""Draws the README charts in docs/img/ as static SVGs that follow GitHub's light or dark theme.

Numbers come from notebooks/01_eda.ipynb, 01b_eda_ibm.ipynb and 03_modeling.ipynb.
Run from the project folder: .venv\\Scripts\\python docs/make_charts.py
"""
from pathlib import Path

OUT = Path(__file__).parent / "img"
OUT.mkdir(exist_ok=True)

STYLE = """<style>
  .bg{fill:#fcfcfb} .t1{fill:#0b0b0b} .t2{fill:#52514e} .grid{stroke:#e4e3df}
  .s1{fill:#2a78d6} .s2{fill:#eb6834} .s3{fill:#1baf7a} .muted{fill:#c9c8c2}
  .l1{stroke:#2a78d6} .ref{stroke:#8a8983}
  .box{fill:#ffffff;stroke:#d6d5d0} .done{fill:#1baf7a} .next{fill:#2a78d6} .todo{fill:#c9c8c2}
  text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Helvetica,Arial,sans-serif}
  .h{font-size:20px;font-weight:700} .sub{font-size:13px} .lab{font-size:13px} .val{font-size:13px;font-weight:600} .ax{font-size:11px}
  @media (prefers-color-scheme: dark){
    .bg{fill:#1a1a19} .t1{fill:#f0efec} .t2{fill:#c3c2b7} .grid{stroke:#34332f}
    .s1{fill:#3987e5} .s2{fill:#d95926} .s3{fill:#199e70} .muted{fill:#4a4944}
    .l1{stroke:#3987e5} .ref{stroke:#8f8e86}
    .box{fill:#232321;stroke:#3d3c38} .done{fill:#199e70} .next{fill:#3987e5} .todo{fill:#4a4944}
  }
</style>"""


def svg(w, h, title, desc, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d">'
        f'<title id="t">{title}</title><desc id="d">{desc}</desc>{STYLE}'
        f'<rect class="bg" width="{w}" height="{h}" rx="14"/>{body}</svg>'
    )


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def hbars(name, title, sub, rows, unit_fmt, note=None, w=760):
    """rows: (label, value, css_class). One series; highlighted rows use a colour class, the rest are muted."""
    top, left, right, row_h, bar_h = 78, 210, 90, 34, 18
    h = top + row_h * len(rows) + (46 if note else 24)
    vmax = max(v for _, v, _ in rows)
    plot_w = w - left - right
    body = f'<text class="h t1" x="24" y="36">{esc(title)}</text><text class="sub t2" x="24" y="58">{esc(sub)}</text>'
    for i, (lab, v, cls) in enumerate(rows):
        y = top + i * row_h
        bw = max(2, plot_w * v / vmax)
        body += f'<text class="lab t1" x="{left - 12}" y="{y + 14}" text-anchor="end">{esc(lab)}</text>'
        body += f'<path class="{cls}" d="M{left},{y} h{bw - 4} a4,4 0 0 1 4,4 v{bar_h - 8} a4,4 0 0 1 -4,4 h-{bw - 4} z"/>'
        body += f'<text class="val t1" x="{left + bw + 8}" y="{y + 14}">{unit_fmt(v)}</text>'
    if note:
        body += f'<text class="ax t2" x="24" y="{h - 18}">{esc(note)}</text>'
    (OUT / name).write_text(svg(w, h, title, sub, body), encoding="utf-8")


# 1. EDA: strongest clues, frauds per 10,000 purchases
hbars(
    "eda-clues.svg",
    "Where fraud concentrates",
    "Frauds per 10,000 purchases in each group (TabFormer, first 3 million rows)",
    [
        ("Jewellery shops", 608, "s1"),
        ("Electronics shops", 562, "s1"),
        ("Purchases abroad", 391, "s1"),
        ("First visit to a shop", 155, "s1"),
        ("Online purchases", 52, "s1"),
        ("All purchases", 11, "muted"),
    ],
    lambda v: f"{v:,}",
    note="Groups overlap, so rates are not additive. Grey bar = overall rate for reference.",
)

# 2. EDA: fraud rate by hour of day
hour_rate = [3.35, 11.38, 8.47, 12.39, 15.03, 7.89, 5.29, 8.45, 9.26, 14.34, 13.82, 18.39,
             18.63, 15.40, 18.39, 15.01, 10.59, 9.35, 9.87, 6.13, 3.41, 2.39, 2.30, 2.14]
w, h, left, top, pw, ph = 760, 330, 56, 78, 670, 190
ymax = 20
pts = [(left + pw * i / 23, top + ph * (1 - r / ymax)) for i, r in enumerate(hour_rate)]
body = '<text class="h t1" x="24" y="36">Fraud by hour of day</text>'
body += '<text class="sub t2" x="24" y="58">Frauds per 10,000 purchases. Peaks late morning to early afternoon, lowest late evening.</text>'
for g in (0, 5, 10, 15, 20):
    y = top + ph * (1 - g / ymax)
    body += f'<line class="grid" x1="{left}" x2="{left + pw}" y1="{y}" y2="{y}" stroke-width="1"/>'
    body += f'<text class="ax t2" x="{left - 8}" y="{y + 4}" text-anchor="end">{g}</text>'
y11 = top + ph * (1 - 11 / ymax)
body += f'<line class="ref" x1="{left}" x2="{left + pw}" y1="{y11}" y2="{y11}" stroke-width="1.5" stroke-dasharray="5 4"/>'
body += f'<text class="ax t2" x="{left + pw}" y="{y11 - 6}" text-anchor="end">average 11</text>'
body += '<polyline fill="none" class="l1" stroke-width="2" stroke-linejoin="round" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + '"/>'
for i in (12, 23):
    x, y = pts[i]
    body += f'<circle class="s1" cx="{x:.1f}" cy="{y:.1f}" r="4.5"/>'
body += f'<text class="val t1" x="{pts[12][0]:.1f}" y="{pts[12][1] - 12:.1f}" text-anchor="middle">noon: 18.6</text>'
body += f'<text class="val t1" x="{pts[23][0] - 4:.1f}" y="{pts[23][1] - 12:.1f}" text-anchor="end">11 pm: 2.1</text>'
for hr in range(0, 24, 3):
    x = left + pw * hr / 23
    body += f'<text class="ax t2" x="{x:.1f}" y="{top + ph + 18}" text-anchor="middle">{hr}:00</text>'
(OUT / "eda-hour.svg").write_text(svg(w, h, "Fraud by hour of day", "Fraud rate per 10,000 purchases for each hour", body), encoding="utf-8")

# 3. Drift: fraud per 10,000 by card use, three periods
groups = ["Online", "Chip", "Swipe"]
series = [("Train, before Apr 2017", "s1", [66.4, 2.6, 4.3]),
          ("Validation, after", "s2", [0.0, 12.5, 9.7]),
          ("New people, after", "s3", [1.5, 9.7, 3.4])]
w, h, left, top, pw, ph = 760, 360, 56, 104, 670, 190
ymax = 70
body = '<text class="h t1" x="24" y="36">Drift: online fraud nearly vanished after 2017</text>'
body += '<text class="sub t2" x="24" y="58">Frauds per 10,000 purchases by card use. A model trained on the old pattern flags innocent online shoppers.</text>'
lx = 24
for name, cls, _ in series:
    body += f'<rect class="{cls}" x="{lx}" y="72" width="12" height="12" rx="3"/><text class="lab t1" x="{lx + 18}" y="83">{esc(name)}</text>'
    lx += 34 + 7.4 * len(name)
for g in (0, 20, 40, 60):
    y = top + ph * (1 - g / ymax)
    body += f'<line class="grid" x1="{left}" x2="{left + pw}" y1="{y}" y2="{y}" stroke-width="1"/><text class="ax t2" x="{left - 8}" y="{y + 4}" text-anchor="end">{g}</text>'
gw, bw = pw / 3, 52
for gi, gname in enumerate(groups):
    cx = left + gw * gi + gw / 2
    for si, (_, cls, vals) in enumerate(series):
        v = vals[gi]
        x = cx + (si - 1) * (bw + 2) - bw / 2
        bh = max(1.5, ph * v / ymax)
        y = top + ph - bh
        r = 4 if bh > 8 else 0
        body += f'<path class="{cls}" d="M{x},{top + ph} v-{bh - r} a{r},{r} 0 0 1 {r},-{r} h{bw - 2 * r} a{r},{r} 0 0 1 {r},{r} v{bh - r} z"/>'
        body += f'<text class="val t1" x="{x + bw / 2}" y="{y - 6}" text-anchor="middle">{v:g}</text>'
    body += f'<text class="lab t1" x="{cx}" y="{top + ph + 22}" text-anchor="middle">{gname}</text>'
(OUT / "drift-use-chip.svg").write_text(svg(w, h, "Drift in card-use fraud", "Fraud per 10,000 by card use in three periods", body), encoding="utf-8")

# 4. Model comparison on new people
hbars(
    "model-comparison.svg",
    "Frauds caught in the top 1,000 alerts",
    "253 people the models never saw, purchases after 25 April 2017 (459 frauds in total)",
    [
        ("Logistic regression, 9 features", 177, "s1"),
        ("Logistic regression, 5 features", 142, "muted"),
        ("XGBoost, depth 3", 135, "muted"),
        ("XGBoost, depth 6", 74, "muted"),
        ("Random guessing", 1, "muted"),
    ],
    lambda v: f"{v}",
    note="Blue = chosen model. Its PR-AUC also drops least from validation (0.097) to new people (0.088).",
    w=780,
)

# 5. PaySim leakage
hbars(
    "paysim-leak.svg",
    "PaySim: the receiver balance leaked the label",
    "Share of transactions where the receiver's balance did not change although money was sent",
    [
        ("Fraud", 49.8, "s2"),
        ("All normal", 36.4, "muted"),
        ("Normal transfers and cash-outs", 0.06, "muted"),
    ],
    lambda v: f"{v:g}%",
    note="Fraud was cancelled, so balances never updated. The fair comparison (bottom bar) exposed it.",
)

# 6. Architecture with status
stages = [("Data", "TabFormer, pandas", "done"), ("Features", "per-card history", "done"),
          ("Model", "logistic regression", "done"), ("API", "FastAPI /predict", "done"),
          ("Stream", "Kafka + Redis", "done"), ("Monitor", "SQLite + Evidently", "next"),
          ("Dashboard", "Streamlit", "todo")]
w, h = 980, 230
bw, bh, gap, x0, y0 = 120, 92, 18, 24, 92
body = '<text class="h t1" x="24" y="36">How a purchase flows through the system</text>'
body += '<text class="sub t2" x="24" y="58">Each card\'s recent history lives in Redis, so features are built live, then scored by the API.</text>'
lx = 640
for cls, lab in (("done", "Done"), ("next", "Next"), ("todo", "Planned")):
    body += f'<rect class="{cls}" x="{lx}" y="27" width="12" height="12" rx="6"/><text class="lab t1" x="{lx + 18}" y="38">{lab}</text>'
    lx += 92
for i, (name, tool, st) in enumerate(stages):
    x = x0 + i * (bw + gap)
    body += f'<rect class="box" x="{x}" y="{y0}" width="{bw}" height="{bh}" rx="12" stroke-width="1"/>'
    body += f'<rect class="{st}" x="{x + 14}" y="{y0}" width="{bw - 28}" height="4" rx="2"/>'
    body += f'<text class="val t1" x="{x + bw / 2}" y="{y0 + 40}" text-anchor="middle">{name}</text>'
    body += f'<text class="ax t2" x="{x + bw / 2}" y="{y0 + 62}" text-anchor="middle">{esc(tool)}</text>'
    if i < len(stages) - 1:
        ax = x + bw + 3
        body += f'<path class="ref" d="M{ax},{y0 + bh / 2} h{gap - 8}" stroke-width="1.5" fill="none"/><path class="muted" d="M{ax + gap - 8},{y0 + bh / 2 - 4} l6,4 l-6,4 z"/>'
body += f'<text class="ax t2" x="24" y="{h - 20}">Status as of 25 October 2026.</text>'
(OUT / "architecture.svg").write_text(svg(w, h, "System architecture", "Seven stages from data to dashboard with their status", body), encoding="utf-8")

print("wrote", sorted(p.name for p in OUT.glob("*.svg")))
