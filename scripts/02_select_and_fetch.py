"""Choose one representative font file per Google Fonts family and fetch only those blobs.

Rule (in order): variable file (name contains '[') in style normal; else weight-400 normal file;
else the first file listed. The chosen file is the one whose OpenType features are measured in
script 03. Output: data/google_selected_files.csv and a sparse checkout of the gfonts clone.
"""
import csv, os, subprocess, sys

FD = os.path.join(os.path.dirname(__file__), "..")
GF = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GF_ROOT", "gfonts")
rows = list(csv.DictReader(open(os.path.join(FD, "data", "google_families_raw.csv"), encoding="utf-8")))

def pick(row):
    files = [x for x in row["font_files"].split(";") if x]
    if not files:
        return None, "none"
    # font files are listed with style/weight in METADATA; re-read them for the rule
    text = open(os.path.join(GF, row["metadata_path"]), encoding="utf-8").read()
    import re
    blocks = re.findall(r"^fonts \{(.*?)^\}", text, flags=re.S | re.M)
    meta = []
    for b in blocks:
        fn = re.search(r'filename: "([^"]*)"', b).group(1)
        st = re.search(r'style: "([^"]*)"', b)
        wt = re.search(r"weight: (\d+)", b)
        meta.append((fn, st.group(1) if st else "", wt.group(1) if wt else ""))
    for fn, st, wt in meta:
        if "[" in fn and st == "normal":
            return fn, "variable_normal"
    for fn, st, wt in meta:
        if st == "normal" and wt == "400":
            return fn, "regular_400"
    return meta[0][0], "first_listed"

out, patterns = [], []
for r in rows:
    fn, rule = pick(r)
    if fn is None:
        continue
    path = f"{r['gf_directory']}/{fn}"
    out.append({"gf_directory": r["gf_directory"], "family": r["family"], "selected_file": fn,
                "selected_path": path, "selection_rule": rule})
    esc = "".join("\\" + c if c in "*?[]\\" else c for c in path)
    patterns.append("/" + esc)

with open(os.path.join(FD, "data", "google_selected_files.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print("selected:", len(out))

# keep the METADATA.pb files in the checkout too, so that script 01 can be rerun from the same clone
meta = ["/ofl/*/METADATA.pb", "/apache/*/METADATA.pb", "/ufl/*/METADATA.pb"]
subprocess.run(["git", "-C", GF, "sparse-checkout", "set", "--no-cone", *meta, *patterns], check=True)
subprocess.run(["git", "-C", GF, "checkout"], check=True)
print("checked out")
