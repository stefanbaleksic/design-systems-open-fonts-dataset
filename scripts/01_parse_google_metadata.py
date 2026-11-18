"""Parse Google Fonts METADATA.pb files (google/fonts repo) into one row per family.

Input : a checkout of https://github.com/google/fonts with ofl/, apache/, ufl/ METADATA.pb files
Output: data/google_families_raw.csv
Only plain protobuf-text fields used by the files are read; no protobuf library needed.
"""
import csv, glob, os, re, sys

GF_ROOT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GF_ROOT", "gfonts")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "..", "data", "google_families_raw.csv")

def q(s):
    m = re.search(r'"([^"]*)"', s)
    return m.group(1) if m else ""

def blocks(text, key):
    # top-level "key { ... }" blocks (no nesting in these files beyond one level)
    return re.findall(rf"^{key} \{{(.*?)^\}}", text, flags=re.S | re.M)

def strip_blocks(text):
    # remove nested "key { ... }" blocks so that top-level fields are read unambiguously
    return re.sub(r"^\w+ \{.*?^\}", "", text, flags=re.S | re.M)

def field(text, key):
    m = re.search(rf"^\s*{key}: (.*)$", text, flags=re.M)
    return q(m.group(1)) if m else ""

def all_fields(text, key):
    return [q(x) for x in re.findall(rf"^\s*{key}: (.*)$", text, flags=re.M)]

rows = []
for licence_dir in ("ofl", "apache", "ufl"):
    for path in sorted(glob.glob(os.path.join(GF_ROOT, licence_dir, "*", "METADATA.pb"))):
        folder = os.path.basename(os.path.dirname(path))
        text = open(path, encoding="utf-8").read()
        fonts = []
        for b in blocks(text, "fonts"):
            fonts.append({
                "filename": field(b, "filename"),
                "style": field(b, "style"),
                "weight": field(b, "weight"),
            })
        axes = [(field(b, "tag"), field(b, "min_value"), field(b, "max_value")) for b in blocks(text, "axes")]
        src = blocks(text, "source")
        src_text = src[0] if src else ""
        rows.append({
            "gf_directory": f"{licence_dir}/{folder}",
            "family": field(strip_blocks(text), "name"),
            "designer": field(strip_blocks(text), "designer"),
            "licence_code": field(strip_blocks(text), "license"),
            "category": field(strip_blocks(text), "category"),
            "date_added": field(strip_blocks(text), "date_added"),
            "subsets": ";".join(all_fields(strip_blocks(text), "subsets")),
            "n_font_files": len(fonts),
            "font_files": ";".join(f["filename"] for f in fonts),
            "styles": ";".join(sorted({f["style"] for f in fonts if f["style"]})),
            "weights": ";".join(sorted({f["weight"] for f in fonts if f["weight"]}, key=lambda x: int(x) if x.isdigit() else 0)),
            "axes": ";".join(f"{t}:{mn}-{mx}" for t, mn, mx in axes if t),
            "is_variable_metadata": "yes" if axes else "no",
            "repository_url": field(src_text, "repository_url"),
            "source_commit": field(src_text, "commit"),
            "minisite_url": field(strip_blocks(text), "minisite_url"),
            "metadata_path": f"{licence_dir}/{folder}/METADATA.pb",
        })

if not rows:
    sys.exit("no METADATA.pb files found under " + GF_ROOT + " (check the sparse checkout)")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print("families:", len(rows), "->", os.path.relpath(OUT))
