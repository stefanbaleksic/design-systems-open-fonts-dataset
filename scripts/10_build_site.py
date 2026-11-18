"""Build docs/index.html (GitHub Pages serves it): a single-file page with a filterable, searchable table of the font catalogue and of
design-system font usage. Data are embedded from data/*.csv, nothing is fetched at run time."""
import csv, json, os
FD = os.path.join(os.path.dirname(__file__), "..")
D = os.path.join(FD, "data")
OUT = os.path.join(FD, "docs", "index.html")

def rd(n):
    return list(csv.DictReader(open(os.path.join(D, n), encoding="utf-8")))

cat = rd("fonts_catalogue.csv")
dsf = rd("design_system_fonts.csv")
stats = rd("summary_statistics.csv")

C = []
for r in cat:
    C.append({"id": r["font_id"], "fam": r["family"], "fin": r["family_as_in_font_name"], "lic": r["licence_code"],
              "cls": r["licence_class"], "comm": r["commercial_status"], "use": r["commercial_use_allowed"],
              "prov": r["provider"], "des": r["designer"], "src": r["primary_source_type"], "url": r["primary_source_url"],
              "ref": r["primary_source_ref"], "gf": r["also_on_google_fonts"], "gfd": r["google_fonts_directory"],
              "path": r["source_file_path"], "ext": r["source_file_format"], "fmt": r["formats_available"],
              "var": r["is_variable_font"], "axes": r["variable_axes"], "outl": r["outlines"], "tnum": r["feat_tnum"],
              "pnum": r["feat_pnum"], "lnum": r["feat_lnum"], "onum": r["feat_onum"], "zero": r["feat_zero"],
              "zglyph": r["feat_slashed_zero_glyph"], "liga": r["feat_liga"], "dlig": r["feat_dlig"],
              "cyr": r["has_cyrillic"], "srcyr": r["has_serbian_cyrillic"], "srlat": r["has_serbian_latin_diacritics"],
              "glyphs": r["glyph_count"], "cat": r["category"], "added": r["date_added"], "subsets": r["subsets"],
              "spec": r["google_fonts_specimen_url"], "bytes": r["source_file_bytes"], "sha": r["source_file_sha256"],
              "dsn": int(r["design_systems_declaring"] or 0), "dss": r["design_system_slugs"], "inter": r["is_inter"],
              "open": r["is_open_source"]})

U = []
for r in dsf:
    U.append({"slug": r["slug"], "ds": r["design_system"], "org": r["organisation"], "pkg": r["npm_package"],
              "ver": r["npm_version"], "fam": r["family_declared"], "occ": int(r["occurrences"] or 0),
              "role": r["declaration_role"], "fid": r["font_id"], "match": r["match_status"], "alias": r["alias_applied"],
              "cls": r["licence_class"], "lic": r["licence_code"], "var": r["is_variable_font"],
              "srcyr": r["has_serbian_cyrillic"], "tnum": r["feat_tnum"], "zero": r["feat_zero"]})

S = [{"m": r["measure"], "v": r["value"], "n": r["note"]} for r in stats]

def dump_lines(records, path):
    """One JSON array with one record per line: readable, diffable, and fetched by the page."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("[\n" + ",\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in records) + "\n]\n")

os.makedirs(os.path.join(FD, "docs", "data"), exist_ok=True)
dump_lines(C, os.path.join(FD, "docs", "data", "catalogue.json"))
dump_lines(U, os.path.join(FD, "docs", "data", "usage.json"))
dump_lines(S, os.path.join(FD, "docs", "data", "stats.json"))
html = open(os.path.join(os.path.dirname(__file__), "site_template.html"), encoding="utf-8").read()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(html)
print("site:", os.path.relpath(OUT, FD), "+ data/*.json;", len(C), "catalogue rows;", len(U), "usage rows")
