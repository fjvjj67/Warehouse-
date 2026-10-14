"""Embed a Daftra product backup (xlsx) into index.html.

Same rules as the page's Excel import: rows with StockBalance <= 0 are left out,
locations like "R3-C6+C7" become a main shelf plus extra shelves, and any
location that does not exist on the map is reported (product kept, no location).

The product list is embedded in the page as plain data (no password).

Usage: python3 tools/update_catalog.py path/to/Backup_Products_....xlsx [--dry-run]
"""
import base64, json, os, re, sys, pathlib, datetime
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"

def main(src, dry):
    html = INDEX.read_text(encoding="utf-8")
    W = json.loads(re.search(r"const WAREHOUSE = (\{.*?\});\n", html).group(1))
    rows = list(openpyxl.load_workbook(src, read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True))
    head = [str(h or "").strip().lower() for h in rows[0]]
    col = lambda *names: next((head.index(n.lower()) for n in names if n.lower() in head), None)
    c_sku, c_bc, c_name, c_desc = col("ProductCode", "SKU"), col("Barcode"), col("Name"), col("Description")
    c_qty, c_loc = col("StockBalance"), col("مكان المنتج-Custom")
    if None in (c_sku, c_name, c_qty, c_loc):
        sys.exit("missing columns; expected ProductCode, Name, StockBalance, مكان المنتج-Custom")

    products, zero, no_loc = {}, 0, []
    for r in rows[1:]:
        sku = str(r[c_sku] or "").strip()
        if not sku:
            continue
        try:
            qty = float(r[c_qty] or 0)
        except (TypeError, ValueError):
            qty = 0
        if qty <= 0:
            zero += 1
            continue
        qty = int(qty) if qty == int(qty) else qty
        raw = re.sub(r"\s+", "", str(r[c_loc] or "")).upper()
        m = re.match(r"^([RM]\d+)-(.+)$", raw)
        locs = []
        if m and m.group(1) in W:
            for part in m.group(2).split("+"):
                x = re.match(r"^([A-Z])(\d+)$", part)
                nums = W[m.group(1)]["aisles"].get(x.group(1)) if x else None
                if not nums or not 1 <= int(x.group(2)) <= max(nums):
                    locs = []
                    break
                locs.append([x.group(1), int(x.group(2))])
        if not locs:
            no_loc.append(f"{sku} ({raw or 'فارغ'})")
        p = {"name": " ".join(str(r[c_name] or "").split()),
             "barcode": str(r[c_bc] or "").strip() if c_bc is not None else "",
             "model": str(r[c_desc] or "").strip() if c_desc is not None else "",
             "qty": qty, "room": m.group(1) if locs else "",
             "rack": locs[0][0] if locs else "", "level": locs[0][1] if locs else 0}
        if len(locs) > 1:
            p["extra"] = locs[1:]
        products[sku] = p

    print(f"kept {len(products)}, skipped {zero} with stock 0, {len(no_loc)} without a valid location")
    for x in no_loc:
        print("  no location:", x)
    if dry:
        return
    now = datetime.datetime.now(datetime.timezone.utc)
    body = ",\n".join(f"  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}" for k, v in products.items())
    block = (f"// Source: {pathlib.Path(src).name} (items with stock 0 left out). Update with tools/update_catalog.py.\n"
             f"const CATALOG_DATE = Date.UTC({now.year}, {now.month - 1}, {now.day}, {now.hour}, {now.minute});\n"
             f"let CATALOG_AT = CATALOG_DATE;\nconst PRODUCTS = {{\n{body}\n}};\n")
    start = html.index("// Source: ")
    end = html.index("\n};\n", html.index("const PRODUCTS = {")) + 4 if "const PRODUCTS = {\n" in html else re.search(r"const VAULT = .*?;\n", html).end()
    INDEX.write_text(html[:start] + block + html[end:], encoding="utf-8")
    print("index.html updated")

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    if len(args) != 1:
        sys.exit(__doc__)
    main(args[0], "--dry-run" in sys.argv)
