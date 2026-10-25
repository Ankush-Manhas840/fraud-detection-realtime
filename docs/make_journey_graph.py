"""Draws docs/img/transaction-journey.svg: one real purchase followed through every step of the live pipeline.

The purchase is an example; card 254-0's memory (from Redis) and the score (from the FastAPI model) are real.
"""
from pathlib import Path
from xml.sax.saxutils import escape

STEPS = [
    ("#a78bfa", "A purchase happens", "producer.py",
     ["Card 254-0 pays $412.00 at 3 AM", "at a shop it has never used."],
     ['{"user": 254, "card": 0,', ' "amount": 412.0,', ' "timestamp": "...T03:12",', ' "merchant_name": ...}']),
    ("#a78bfa", "Kafka holds it in line", "topic: transactions",
     ["The purchase is added to the end", "of the topic and gets an offset."],
     ["offset = its place in line", "e.g. offset 211042", "waiting for fraud-checker"]),
    ("#a78bfa", "The consumer picks it up", "consumer.py",
     ["consumer.poll(1) returns the", "message; json.loads turns it", "back into a dictionary."],
     ["message = consumer.poll(1)", "purchase = json.loads(...)"]),
    ("#34d399", "Load this card's memory", "Redis · load_bag",
     ["Everything the system remembers", "about card 254-0 so far."],
     ["2,826 past purchases", "usual amount  $45.39", "favourite hours 17, 7, 15", "never bought at 3 AM"]),
    ("#f472b6", "Build the 9 features", "features_from_memory()",
     ["Compare this purchase with the", "card's habits, BEFORE updating", "the memory."],
     ["amount_vs_usual   9.08", "new_shop          1", "new_shop_type     1", "count_last_hour   3", "share_same_hour   0.00"]),
    ("#f59e0b", "The model scores it", "FastAPI · POST /predict",
     ["Scaler + logistic regression", "give a score between 0 and 1.", "About 10 ms."],
     ["fraud_score  0.9988", "threshold    0.9862", "is_fraud     true"]),
    ("#34d399", "Update the memory", "update_memory + save_bag",
     ["Add this purchase to the card's", "history so the next purchase is", "compared with it too."],
     ["shops   + new shop", "count   2,826 → 2,827", "hour 3  0 → 1"]),
    ("#60a5fa", "Write it down", "SQLite · predictions",
     ["Every decision is saved with its", "features and how long it took."],
     ["INSERT INTO predictions", "score 0.9988, flagged 1"]),
    ("#e8a13a", "Show it", "Streamlit dashboard",
     ["The alert appears in the live feed", "with the reasons it was flagged,", "within 3 seconds."],
     ["FRAUD ALERT", "new shop · 9× usual amount", "3 purchases in the last hour"]),
]

W, H = 1720, 900
CARD_W, CARD_H = 292, 300
COLS = 5
X0, Y0, GAP_X, GAP_Y = 40, 150, 45, 90

out = []


def card_xy(i):
    row, col = divmod(i, COLS)
    if row == 1:   # second row runs right to left, like a snake, so the path never jumps back
        col = COLS - 1 - col
    return X0 + col * (CARD_W + GAP_X), Y0 + row * (CARD_H + GAP_Y)


# path between the cards, drawn first so the cards sit on top of it
for i in range(len(STEPS) - 1):
    x1, y1 = card_xy(i)
    x2, y2 = card_xy(i + 1)
    colour = STEPS[i][0]
    if y1 == y2:
        if x2 > x1:
            ax, bx = x1 + CARD_W, x2
        else:
            ax, bx = x1, x2 + CARD_W
        y = y1 + 44
        out.append(f'<path d="M{ax},{y} L{bx},{y}" stroke="{colour}" class="flow"/>')
        tip = bx - 8 if x2 > x1 else bx + 8
        out.append(f'<path d="M{tip},{y - 6} L{bx},{y} L{tip},{y + 6}" stroke="{colour}" class="flow"/>' if x2 > x1 else
                   f'<path d="M{tip},{y - 6} L{bx},{y} L{tip},{y + 6}" stroke="{colour}" class="flow"/>')
    else:   # turn down from the end of row 1 into row 2
        x = x1 + CARD_W / 2
        out.append(f'<path d="M{x},{y1 + CARD_H} L{x},{y2}" stroke="{colour}" class="flow"/>')
        out.append(f'<path d="M{x - 6},{y2 - 8} L{x},{y2} L{x + 6},{y2 - 8}" stroke="{colour}" class="flow"/>')

for i, (colour, title, where, what, example) in enumerate(STEPS):
    x, y = card_xy(i)
    out.append(f'<rect x="{x}" y="{y}" width="{CARD_W}" height="{CARD_H}" rx="12" class="card"/>')
    out.append(f'<rect x="{x}" y="{y}" width="{CARD_W}" height="4" rx="2" fill="{colour}"/>')
    out.append(f'<circle cx="{x + 30}" cy="{y + 44}" r="17" fill="{colour}"/>')
    out.append(f'<text x="{x + 30}" y="{y + 50}" class="num" text-anchor="middle">{i + 1}</text>')
    out.append(f'<text x="{x + 58}" y="{y + 40}" class="title">{escape(title)}</text>')
    out.append(f'<text x="{x + 58}" y="{y + 60}" class="where" fill="{colour}">{escape(where)}</text>')
    ty = y + 100
    for line in what:
        out.append(f'<text x="{x + 20}" y="{ty}" class="what">{escape(line)}</text>')
        ty += 21
    box_y = y + CARD_H - 30 - 22 * len(example)
    out.append(f'<rect x="{x + 14}" y="{box_y}" width="{CARD_W - 28}" height="{22 * len(example) + 16}" rx="8" class="code"/>')
    ey = box_y + 23
    for line in example:
        cls = "alert" if line == "FRAUD ALERT" or line.startswith("is_fraud") else "mono"
        out.append(f'<text x="{x + 28}" y="{ey}" class="{cls}">{escape(line)}</text>')
        ey += 22

body = "\n".join(out)
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="The journey of one purchase through the pipeline, in nine numbered steps, from the purchase to the dashboard alert">
<defs><pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#1f2633"/></pattern></defs>
<style>
text {{ font-family: -apple-system, "Segoe UI", Inter, Helvetica, Arial, sans-serif; }}
.card {{ fill: #121722; stroke: #2a3242; stroke-width: 1.2; }}
.code {{ fill: #0b0f17; stroke: #232b38; }}
.num {{ fill: #0b0f17; font-size: 17px; font-weight: 800; }}
.title {{ fill: #f3f4f6; font-size: 17px; font-weight: 700; }}
.where {{ font-family: ui-monospace, Consolas, monospace; font-size: 12px; }}
.what {{ fill: #c9d1d9; font-size: 14px; }}
.mono {{ fill: #9aa4b2; font-family: ui-monospace, Consolas, monospace; font-size: 12.5px; }}
.alert {{ fill: #f59e0b; font-family: ui-monospace, Consolas, monospace; font-size: 12.5px; font-weight: 700; }}
.flow {{ fill: none; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; }}
.head {{ fill: #f3f4f6; font-size: 26px; font-weight: 700; letter-spacing: -0.4px; }}
.sub {{ fill: #8b95a5; font-size: 15px; }}
</style>
<rect width="{W}" height="{H}" fill="#0b0f17"/>
<rect width="{W}" height="{H}" fill="url(#dots)"/>
<text x="40" y="62" class="head">The journey of one purchase</text>
<text x="40" y="92" class="sub">Card 254-0 usually spends $45 in the afternoon. Suppose at 3 AM it spends $412 at a new shop. Real card memory, real model score. Follow 1 → 9.</text>
{body}
</svg>
"""
Path(__file__).resolve().parent.joinpath("img", "transaction-journey.svg").write_text(svg, encoding="utf-8")
print("saved docs/img/transaction-journey.svg")
