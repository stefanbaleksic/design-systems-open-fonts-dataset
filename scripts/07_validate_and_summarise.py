"""Duplicate audit, summary statistics and validation report.
Writes: data/duplicates_removed.csv, data/summary_statistics.csv, data/validation_report.md
"""
import csv, os, re
from collections import Counter

FD = os.path.join(os.path.dirname(__file__), "..")
D = os.path.join(FD, "data")

def rd(n):
    return list(csv.DictReader(open(os.path.join(D, n), encoding="utf-8")))

def norm(name):
    s = re.sub(r"\s+(variable|var|vf)$", "", name.lower().strip())
    s = re.sub(r"[^a-z0-9]", "", s)
    return re.sub(r"(variable|vf|var)$", "", s) if len(s) > 5 else s

gf = rd("google_families_raw.csv")
up = rd("upstream_font_measures.csv")
spec = rd("specimen_url_checks.csv")
cat = rd("fonts_catalogue.csv")
dsf = rd("design_system_fonts.csv")
decl = rd("design_system_font_declarations.csv")
pkgs = rd("design_system_font_packages.csv")

# 1 duplicates: every candidate row (Google Fonts families and original-repository builds) is grouped by
# normalised family name. One row is kept per group: an original-repository row first (source-first),
# a variable build before a static one. Every other row of the group is listed in duplicates_removed.csv.
def is_var(x):
    return x.get("is_variable_font") == "yes"

candidates = []
for m in up:
    candidates.append({"kind": "upstream", "name": m["family_key"], "path": m["representative_path"],
                       "source": m["repository_url"], "variable": is_var(m), "dir": "",
                       "font_id": re.sub(r"[^a-z0-9]+", "-", re.sub(r"\s+(Var|VF|Variable)$", "", m["family_key"]).lower()).strip("-")})
for g in gf:
    sel = {r["gf_directory"]: r for r in []}
    candidates.append({"kind": "google", "name": g["family"], "path": g["metadata_path"], "source": "https://github.com/google/fonts",
                       "variable": g["is_variable_metadata"] == "yes", "dir": g["gf_directory"], "font_id": ""})
groups = {}
for c in candidates:
    groups.setdefault(norm(c["name"]), []).append(c)
dups = []
for k, members in groups.items():
    if len(members) < 2:
        continue
    members.sort(key=lambda c: (c["kind"] != "upstream", not c["variable"]))  # stable: upstream first, variable first
    kept = members[0]
    for c in members[1:]:
        dups.append({"family_google_fonts": c["name"] if c["kind"] == "google" else "",
                     "google_fonts_directory": c["dir"], "kept_row_font_id": kept["font_id"] or re.sub(r"[^a-z0-9]+", "-", kept["name"].lower()).strip("-"),
                     "kept_source": kept["source"],
                     "rule": ("Google Fonts family with an original-repository row (source-first)" if c["kind"] == "google"
                              else "same family inside original repositories; variable build kept"),
                     "removed_family": "" if c["kind"] == "google" else c["name"], "removed_path": c["path"]})
with open(os.path.join(D, "duplicates_removed.csv"), "w", newline="", encoding="utf-8") as f:
    cols = ["family_google_fonts", "google_fonts_directory", "kept_row_font_id", "kept_source", "rule", "removed_family", "removed_path"]
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(dups)
n_candidates, n_unique = len(candidates), len(groups)

# 2 hard duplicate checks on the output
dup_ids = [k for k, n in Counter(r["font_id"] for r in cat).items() if n > 1]
dup_norm = [k for k, n in Counter(norm(r["family"]) for r in cat).items() if n > 1]
dup_decl = [k for k, n in Counter((r["slug"], r["npm_package"], r["family_declared"]) for r in decl).items() if n > 1]

# 3 statistics
open_rows = [r for r in cat if r["is_open_source"] == "yes"]
meas_open = [r for r in open_rows if r["is_variable_font"] in ("yes", "no")]
def share(rows, col):
    n = sum(1 for r in rows if r[col] == "yes")
    return n, round(100 * n / len(rows), 1) if rows else 0
stats = [("catalogue rows (all)", len(cat), ""), ("open-licence families", len(open_rows), ""),
         ("design-system-only families (not open or not checked)", len(cat) - len(open_rows), ""),
         ("open families from Google Fonts only", sum(1 for r in open_rows if r["primary_source_type"] == "google_fonts_repository"), ""),
         ("open families from original repositories", sum(1 for r in open_rows if r["primary_source_type"] == "original_repository"), ""),
         ("open families from npm packages (Fontsource latin subsets: Serbian letters not measured; DejaVu: full files)", sum(1 for r in open_rows if r["primary_source_type"] == "npm_package"), ""),
         ("duplicate rows removed (Google Fonts vs original, and inside original repositories)", len(dups), "see duplicates_removed.csv; candidates %d -> families %d" % (n_candidates, n_unique))]
for col, label in [("is_variable_font", "variable font (fvar table)"), ("feat_tnum", "tabular numerals (tnum)"),
                   ("feat_zero", "slashed/zero feature (zero)"), ("feat_onum", "oldstyle figures (onum)"),
                   ("feat_lnum", "lining figures (lnum)"), ("feat_liga", "standard ligatures (liga)"),
                   ("has_serbian_cyrillic", "all Serbian Cyrillic letters"), ("has_serbian_latin_diacritics", "all Serbian Latin diacritics")]:
    base = [r for r in meas_open if r.get(col) != "not_measured"]  # families where this column was measured
    n = sum(1 for r in base if r.get(col) == "yes")
    p = round(100 * n / len(base), 1) if base else 0
    stats.append((f"open families with {label}", n, f"{p}% of {len(base)} measured"))
lic = Counter(r["licence_code"] for r in open_rows)
for k, v in lic.most_common():
    stats.append((f"licence {k}", v, ""))
brand = [r for r in dsf if r["declaration_role"] == "brand_or_custom"]
stats += [("design systems scanned (npm packages, pinned version)", len(pkgs), ""),
          ("design systems with at least one brand/custom font declaration", len({r["slug"] for r in brand}), ""),
          ("design systems with no brand font in the scanned package", len({p["slug"] for p in pkgs}) - len({r["slug"] for r in brand}), "check the package list; not proof of no font"),
          ("declarations: brand or custom", len(brand), ""),
          ("declarations: operating system / browser fallback", sum(1 for r in dsf if r["declaration_role"] == "os_or_browser_fallback"), ""),
          ("declarations: not a font name (rejected noise, kept for audit)", sum(1 for r in dsf if r["declaration_role"] == "not_a_font_name"), "")]
with open(os.path.join(D, "summary_statistics.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["measure", "value", "note"]); w.writerows(stats)

errs = [p for p in pkgs if p["error"]]
md = ["# Validation report (automatic)", "",
      "Generated by `scripts/07_validate_and_summarise.py` on the collection date of this release.", "",
      "## Checks", "",
      "| check | result |", "|---|---|",
      f"| duplicate font_id in fonts_catalogue.csv | {len(dup_ids)} |",
      f"| duplicate family name after normalisation | {len(dup_norm)} |",
      f"| duplicate declaration rows (slug, package, family) | {len(dup_decl)} |",
      f"| package scan errors | {len(errs)} |",
      f"| Google Fonts families parsed | {len(gf)} |",
      f"| original-repository families measured | {len(up)} |",
      f"| measurement errors (fontTools, Google Fonts and original repositories) | {sum(1 for r in rd('google_font_measures.csv') + up if r.get('error'))} |",
      f"| Google Fonts specimen pages checked (HTTP 200 / 404 / other) | {len(spec)} ({sum(1 for r in spec if r['http_status']=='200')} / {sum(1 for r in spec if r['http_status']=='404')} / {sum(1 for r in spec if r['http_status'] not in ('200','404'))}) |", "",
      "Unit tests: `python3 -m unittest discover -s tests -v` (see the README for the list of checks).", "",
      "## Summary statistics", "", "| measure | value | note |", "|---|---|---|"]
md += [f"| {m} | {v} | {n} |" for m, v, n in stats]
md += ["", "## Removed duplicates", "", f"{n_candidates} candidate rows reduced to {n_unique} families; {len(dups)} rows were not added as separate rows: Google Fonts families whose normalised name matches an original-repository row (source-first), and variant builds inside one repository. Each is listed in `duplicates_removed.csv` with the kept row.", "",
       "## Package scan errors", "", ("none" if not errs else "\n".join(f"- {p['npm_package']}: {p['error']}" for p in errs)), ""]
open(os.path.join(D, "validation_report.md"), "w", encoding="utf-8").write("\n".join(md))
print("duplicates removed:", len(dups), "| dup ids:", len(dup_ids), "| dup norm:", len(dup_norm), "| dup decl:", len(dup_decl))
for m, v, n in stats: print(f"{m}: {v} {n}")
