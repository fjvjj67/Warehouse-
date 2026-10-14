"""Print-ready shelf labels for the warehouse map.

Reads the rack layout straight from index.html, so labels always match the map.
Each level gets its code (R3-A-3) as big text plus a Code128 barcode of the same
code; scanning it in the map's search box opens that exact level. One rack
header label (R3-A) precedes each rack's levels.

Sheet: A4, 3 x 8 = 24 labels of 70 x 37 mm (the common A4 sticker sheet).

Usage: python3 tools/make_labels.py [ROOM ...]      (default: R3)
       python3 tools/make_labels.py all
"""
import json, re, sys, pathlib
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128

ROOT = pathlib.Path(__file__).resolve().parent.parent
html = (ROOT / "index.html").read_text(encoding="utf-8")
WAREHOUSE = json.loads(re.search(r"const WAREHOUSE = (\{.*?\});\n", html).group(1))

def room_key(z):
    return (z[0] != "R", int(z[1:]))

rooms = sys.argv[1:] or ["R3"]
if rooms == ["all"]:
    rooms = sorted(WAREHOUSE, key=room_key)

COLS, ROWS = 3, 8
LW, LH = 70 * mm, 37 * mm
PW, PH = A4
MX, MY = (PW - COLS * LW) / 2, (PH - ROWS * LH) / 2

labels = []
for room in rooms:
    for rack in sorted(WAREHOUSE[room]["aisles"]):
        levels = max(WAREHOUSE[room]["aisles"][rack])
        labels.append(("rack", room, rack, levels))
        for lv in range(1, levels + 1):
            labels.append(("level", room, rack, lv))

def draw(c, x, y, item):
    kind, room, rack, n = item
    pad = 4 * mm
    if kind == "rack":
        code = f"{room}-{rack}"
        c.setFillGray(0.12); c.rect(x + 2, y + 2, LW - 4, LH - 4, fill=1, stroke=0)
        c.setFillGray(1)
        c.setFont("Helvetica-Bold", 40); c.drawCentredString(x + LW / 2, y + LH / 2 - 2 * mm, code)
        c.setFont("Helvetica", 8); c.drawCentredString(x + LW / 2, y + 5 * mm, f"RACK {rack}  ·  ROOM {room}  ·  {n} LEVELS (1 = TOP)")
        c.setFillGray(0)
        return
    code = f"{room}-{rack}-{n}"
    c.setFont("Helvetica-Bold", 26); c.drawString(x + pad, y + LH - pad - 22, code)
    c.setFont("Helvetica", 7); c.drawRightString(x + LW - pad, y + LH - pad - 8, "AZAWI")
    c.drawRightString(x + LW - pad, y + LH - pad - 17, f"LEVEL {n}" + ("  (TOP)" if n == 1 else ""))
    bc = code128.Code128(code, barHeight=12 * mm, barWidth=0.33 * mm, quiet=False)
    bc.drawOn(c, x + (LW - bc.width) / 2, y + pad)

out = ROOT / "labels" / (("all" if len(rooms) > 3 else "-".join(rooms)) + "-labels.pdf")
c = canvas.Canvas(str(out), pagesize=A4)
c.setTitle("AZAWI shelf labels " + ", ".join(rooms))
for i, item in enumerate(labels):
    slot = i % (COLS * ROWS)
    if i and slot == 0:
        c.showPage()
    col, row = slot % COLS, slot // COLS
    draw(c, MX + col * LW, PH - MY - (row + 1) * LH, item)
c.save()
print(f"{out.relative_to(ROOT)}: {len(labels)} labels, {-(-len(labels) // (COLS * ROWS))} pages")
