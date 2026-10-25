"""Draws docs/img/pipeline-graph.svg: the live pipeline as a node graph (boxes with typed inputs and outputs, joined by wires)."""
from pathlib import Path

TYPE_COLOUR = {"json": "#a78bfa", "dict": "#34d399", "number": "#f472b6", "boolean": "#f59e0b", "text": "#60a5fa"}
FEATURES = [("amount", "number"), ("hour", "number"), ("outside_us", "boolean"), ("new_shop", "boolean"),
            ("new_shop_type", "boolean"), ("gap_minutes", "number"), ("count_last_hour", "number"),
            ("amount_vs_usual", "number"), ("share_same_hour", "number")]
out = []


def node(x, y, w, h, title, caption=None, rows=(), row_start=None):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="node"/>')
    out.append(f'<line x1="{x}" y1="{y + 40}" x2="{x + w}" y2="{y + 40}" class="sep"/>')
    out.append(f'<text x="{x + 16}" y="{y + 26}" class="title">{title}</text>')
    if caption:
        out.append(f'<text x="{x + w}" y="{y - 8}" class="caption" text-anchor="end">{caption}</text>')
    ry = row_start or y + 66
    for label, value in rows:
        out.append(f'<text x="{x + 16}" y="{ry}" class="row">{label}</text>')
        if value:
            out.append(f'<text x="{x + w - 16}" y="{ry}" class="val" text-anchor="end">{value}</text>')
        ry += 22


def port(x, y, kind, label=None, side="in", shape="circle"):
    c = TYPE_COLOUR[kind]
    if shape == "diamond":
        out.append(f'<rect x="{x - 5}" y="{y - 5}" width="10" height="10" fill="{c}" transform="rotate(45 {x} {y})"/>')
    else:
        out.append(f'<circle cx="{x}" cy="{y}" r="5.5" fill="{c}"/>')
    if label:
        tag = f'<tspan fill="{c}" class="tag">{kind}</tspan>'
        if side == "in":
            out.append(f'<text x="{x + 14}" y="{y + 4}" class="port">{label} {tag}</text>')
        else:
            out.append(f'<text x="{x - 14}" y="{y + 4}" class="port" text-anchor="end">{tag} {label}</text>')


def wire(x1, y1, x2, y2, kind, dashed=False):
    dx = max(abs(x2 - x1) * 0.5, 40)
    dash = ' stroke-dasharray="6 6"' if dashed else ""
    out.append(f'<path d="M{x1},{y1} C{x1 + dx},{y1} {x2 - dx},{y2} {x2},{y2}" stroke="{TYPE_COLOUR[kind]}" class="wire"{dash}/>')


# wires first, so the nodes sit on top of them
wire(280, 278, 340, 296, "json")
wire(590, 296, 660, 190, "json")
wire(590, 530, 660, 214, "dict")
out.append('<path d="M660,540 C600,540 650,554 590,554" stroke="#34d399" class="wire"/>')
for i, (_, kind) in enumerate(FEATURES):
    wire(960, 290 + 24 * i, 1060, 290 + 24 * i, kind)
wire(1350, 300, 1430, 250, "number")
wire(1350, 330, 1430, 250, "boolean")
out.append('<path d="M1555,330 L1555,410" stroke="#60a5fa" class="wire"/>')
out.append('<path d="M1430,560 C1330,560 1300,640 1205,592" stroke="#f472b6" class="wire" stroke-dasharray="6 6"/>')

# 1. producer
node(40, 150, 240, 150, "producer", "replay.py / producer.py",
     [("source", "stream.csv.gz"), ("rate", "1 per second"), ("purchases", "50,000")])
port(280, 278, "json", "purchase", "out", "diamond")

# 2. Kafka
node(340, 150, 250, 170, "Kafka", "topic: transactions",
     [("append-only log", ""), ("offsets per group", ""), ("group", "fraud-checker")])
port(340, 296, "json")
port(590, 296, "json", "message", "out", "diamond")

# 3. Redis
node(340, 470, 250, 240, "Redis · card memory", "key: card:{user}-{card}",
     [("shops", "set"), ("shop_types", "set"), ("last_time", "time"), ("recent_times", "list"),
      ("total, count", "numbers"), ("hour_counts", "dict")], row_start=596)
port(590, 530, "dict", "load_bag", "out", "diamond")
port(590, 554, "dict", "save_bag", "out")

# 4. consumer: features_from_memory()
node(660, 110, 300, 460, "features_from_memory()", "consumer.py")
port(660, 190, "json", "purchase")
port(660, 214, "dict", "bag")
out.append('<text x="676" y="258" class="hint">9 features, built BEFORE memory is updated</text>')
for i, (name, kind) in enumerate(FEATURES):
    port(960, 290 + 24 * i, kind, name, "out", "diamond")
port(660, 540, "dict", "updated bag", "in", "diamond")

# 5. FastAPI /predict
node(1060, 110, 290, 480, "FastAPI · POST /predict", "Docker: fraud-api")
for i, (name, kind) in enumerate(FEATURES):
    port(1060, 290 + 24 * i, kind, name)
port(1350, 300, "number", "fraud_score", "out", "diamond")
port(1350, 330, "boolean", "is_fraud", "out", "diamond")
out.append('<text x="1076" y="160" class="row">StandardScaler</text>')
out.append('<text x="1076" y="184" class="row">→ LogisticRegression</text>')
out.append('<text x="1076" y="208" class="row">alert when score ≥ <tspan class="accent">0.9862</tspan></text>')
out.append('<text x="1076" y="232" class="hint">about 10 ms per purchase</text>')
out.append('<text x="1076" y="565" class="hint">model.joblib · class_weight balanced</text>')

# 6. SQLite
node(1430, 170, 250, 160, "SQLite · predictions", "prediction_log.py",
     [("ts, card, amount", ""), ("score, flagged", ""), ("is_fraud, latency_ms", "")])
port(1430, 250, "number")
port(1555, 330, "text")

# 7. Streamlit
node(1430, 410, 250, 190, "Streamlit dashboard", "dashboard/app.py",
     [("live alerts", "every 3 s"), ("why flagged?", ""), ("hourly chart", ""), ("try it yourself", "→ API")])
port(1555, 410, "text")
port(1430, 560, "number")

legend = "".join(
    f'<circle cx="{190 + i * 130}" cy="770" r="5.5" fill="{c}"/><text x="{202 + i * 130}" y="775" class="legend">{k}</text>'
    for i, (k, c) in enumerate(TYPE_COLOUR.items())
)
body = "\n".join(out)
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1720 820" width="1720" height="820" role="img" aria-label="Live pipeline as a node graph: producer to Kafka to consumer features with Redis memory, to the FastAPI model, to SQLite and the Streamlit dashboard">
<defs><pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#1f2633"/></pattern></defs>
<style>
text {{ font-family: ui-monospace, "SF Mono", "JetBrains Mono", Consolas, monospace; }}
.node {{ fill: #121722; stroke: #2a3242; stroke-width: 1.2; }}
.sep {{ stroke: #2a3242; }}
.title {{ fill: #f3f4f6; font-size: 15px; font-weight: 700; }}
.caption {{ fill: #8b95a5; font-size: 11px; }}
.row {{ fill: #c9d1d9; font-size: 13px; }}
.val {{ fill: #8b95a5; font-size: 12px; }}
.port {{ fill: #c9d1d9; font-size: 12.5px; }}
.tag {{ font-size: 10px; }}
.hint {{ fill: #6b7585; font-size: 11.5px; font-style: italic; }}
.accent {{ fill: #f59e0b; font-weight: 700; }}
.wire {{ fill: none; stroke-width: 2.2; }}
.head {{ fill: #f3f4f6; font-size: 18px; font-weight: 700; }}
.badge {{ fill: #34d399; font-size: 12px; }}
.legend {{ fill: #8b95a5; font-size: 12px; }}
</style>
<rect width="1720" height="820" fill="#0b0f17"/>
<rect width="1720" height="820" fill="url(#dots)"/>
<rect width="1720" height="56" fill="#0e131c"/><line x1="0" y1="56" x2="1720" y2="56" stroke="#1f2633"/>
<text x="40" y="35" class="head">fraud-detection-realtime <tspan fill="#8b95a5" font-weight="400">/ live pipeline</tspan></text>
<rect x="1470" y="16" width="210" height="26" rx="6" fill="#0f2a22" stroke="#1f5a45"/>
<text x="1575" y="34" class="badge" text-anchor="middle">running on Docker</text>
{body}
<rect x="40" y="748" width="1640" height="44" rx="22" fill="#0e131c" stroke="#232b38"/>
<text x="68" y="775" class="legend">WIRE TYPES:</text>
{legend}
<text x="1660" y="775" class="legend" text-anchor="end">dashed = "try it yourself" sends a what-if purchase to the API</text>
</svg>
"""
Path(__file__).resolve().parent.joinpath("img", "pipeline-graph.svg").write_text(svg, encoding="utf-8")
print("saved docs/img/pipeline-graph.svg")
