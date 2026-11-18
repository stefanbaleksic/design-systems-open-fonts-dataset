"""Build the two release tables.

fonts_catalogue.csv          one row per font family (open-licence families from Google Fonts and
                             original repositories, plus families seen in design systems)
design_system_fonts.csv      one row per design system x declared family (+ one row per scanned package
                             with no brand family)
Duplicate rule: a family is one row. Where the original repository and Google Fonts both have it, the
original repository is the primary source (source-first) and also_on_google_fonts = yes.
"""
import csv, os, re
from collections import defaultdict

FD = os.path.join(os.path.dirname(__file__), "..")
D = os.path.join(FD, "data")
TODAY = "2026-11-18"
LICENCE_NAME = {"OFL-1.1": "SIL Open Font License 1.1", "APACHE2": "Apache License 2.0", "Apache-2.0": "Apache License 2.0",
                "UFL": "Ubuntu Font Licence 1.0", "UFL-1.0": "Ubuntu Font Licence 1.0", "MIT": "MIT License", "Bitstream-Vera": "Bitstream Vera Fonts licence",
                "OFL": "SIL Open Font License 1.1"}
LICENCE_CODE = {"OFL": "OFL-1.1", "APACHE2": "Apache-2.0", "UFL": "UFL-1.0", "Bitstream-Vera": "Bitstream-Vera"}
COMMERCIAL_USE = {"OFL-1.1": "yes", "Apache-2.0": "yes", "MIT": "yes", "UFL-1.0": "yes, with conditions (see licence text)",
                  "Bitstream-Vera": "yes (free licence; see licence text for the conditions on renaming)"}
# Known proprietary faces named in design-system CSS (name lookup, not checked against EULAs)
PROPRIETARY = {"segoeui", "segoeuimono", "segoeuisymbol", "segoeuiemoji", "helvetica", "helveticaneue", "arial", "avenir", "avenirnext",
               "proximanova", "akkurat", "akkuratmono", "consolas", "menlo", "monaco", "sfmono", "sfmonoregular", "lucidaconsole",
               "comicsansms", "couriernew", "andalemono", "gdstransport", "yugothic", "pingfangsc", "microsoftyahei", "hiraginosans",
               "applegothic", "malgungothic", "geneva", "simsun", "mingliu", "heititclight", "heitisclight", "hiraginokakugothicpronw"}

# Manual alias rules: names used in CSS that are a previous or shortened name of a catalogue family.
# Reported in the alias_rule column; a row matched by alias keeps the family_declared name as written.
ALIASES = {"source sans pro": "Source Sans 3", "source sans pro web": "Source Sans 3", "inter-bold": "Inter",
           "intervariable": "Inter", "roboto-regular": "Roboto", "roboto-bold": "Roboto", "roboto-black": "Roboto",
           "roboto-light": "Roboto", "roboto-medium": "Roboto", "roboto-thin": "Roboto", "roboto mono web": "Roboto Mono",
           "roboto-condensed-light": "Roboto Condensed", "source serif pro": "Source Serif 4", "roboto rouble": "Roboto",
           "noto sans cjk jp": "Noto Sans JP", "noto mono": "Noto Sans Mono", "ubuntu monospace": "Ubuntu Mono",
           "merriweather web": "Merriweather", "noto sans backtick fix": "Noto Sans"}

def norm(name):
    s = name.lower().strip()
    if s in ALIASES:
        s = ALIASES[s].lower()
    s = re.sub(r"\s+(variable|var|vf)$", "", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    # variable builds whose name has no space before the suffix (e.g. SourceSans3VF)
    if len(s) > 5:
        s = re.sub(r"(variable|vf|var)$", "", s)
    return s

def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

def rd(name):
    return list(csv.DictReader(open(os.path.join(D, name), encoding="utf-8")))

gf_raw = {r["gf_directory"]: r for r in rd("google_families_raw.csv")}
gf_sel = {r["gf_directory"]: r for r in rd("google_selected_files.csv")}
gf_meas = {r["path"]: r for r in rd("google_font_measures.csv")}
up = rd("upstream_font_measures.csv")
def wght_range(axes):
    """'wght:100-900' from the variable axes text, or '' when the font has no weight axis."""
    for part in (axes or "").split(";"):
        if part.startswith("wght:"):
            return part[5:]
    return ""

SPECIMEN = {r["url"]: r["http_status"] for r in rd("specimen_url_checks.csv")} if os.path.exists(os.path.join(D, "specimen_url_checks.csv")) else {}
decl = rd("design_system_font_declarations.csv")
pkgs = rd("design_system_font_packages.csv")
ds_all = {r["slug"]: r for r in csv.DictReader(open(os.environ.get("DS_CSV", "design_systems_v33.csv"), encoding="utf-8"))}

MEAS_KEYS = ["is_variable_font", "variable_axes", "weight_class", "subfamily_name", "outlines", "glyph_count", "has_cyrillic", "has_serbian_cyrillic",
             "has_serbian_latin_diacritics", "feat_tnum", "feat_pnum", "feat_lnum", "feat_onum", "feat_zero",
             "feat_slashed_zero_glyph", "feat_liga", "feat_dlig"]

families = {}  # norm -> row

def add(key, row):
    if key in families and row.get("_source") == "upstream" and families[key].get("_source") == "upstream":
        # same family inside original repositories (e.g. a variable and a static build): keep the variable one
        if row.get("is_variable_font") == "yes" and families[key].get("is_variable_font") != "yes":
            old = families[key]
            row["family"], row["font_id"] = old["family"], old.get("font_id", "")
            families[key] = row
        return
    if key in families:
        # keep the first (original repository) row, record the other source
        families[key]["also_on_google_fonts"] = families[key].get("also_on_google_fonts", "no")
        if row.get("_source") == "google":
            families[key]["also_on_google_fonts"] = "yes"
            families[key]["google_fonts_directory"] = row["google_fonts_directory"]
            families[key]["google_fonts_specimen_url"] = row["google_fonts_specimen_url"]
            families[key]["google_fonts_specimen_http_status"] = row["google_fonts_specimen_http_status"]
        return
    families[key] = row

# 1) original repositories (source-first)
for m in up:
    owner = re.sub(r"https://github.com/([^/]+)/.*", r"\1", m["repository_url"])
    is_npm = m["repo_folder"].startswith("npm-")
    if is_npm:
        owner = "npm package " + m["repository_url"].split("/package/")[1]
    lic = m["repo_licence_detected"].split(" ")[0].split(";")[0]
    fam = m["family_key"]
    display = re.sub(r"\s+(Var|VF|Variable)$", "", fam)
    row = {"family": display, "family_as_in_font_name": fam, "primary_source_type": "npm_package" if is_npm else "original_repository", "primary_source_url": m["repository_url"],
           "primary_source_ref": m["repository_commit"], "source_file_path": m["representative_path"],
           "provider": owner, "designer": "not_checked", "licence_code": lic, "licence_name": LICENCE_NAME.get(lic, lic),
           "licence_evidence": "licence file in repository (automatic text match)" if m["repo_folder"] != "inter-release-4.1" else "licence file in release archive (LICENSE.txt)",
           "formats_available": m["formats_in_repo"], "files_in_family": m["files_in_family"], "_source": "upstream",
           "_path": m["representative_path"], "_repo_folder": m["repo_folder"]}
    for k in MEAS_KEYS: row[k] = m[k]
    row["variable_weight_range"] = wght_range(m.get("variable_axes", ""))
    row["glyph_count"] = m["glyph_count"]
    row["source_file_bytes"] = m.get("file_bytes", ""); row["source_file_sha256"] = m.get("file_sha256", "")
    row["google_fonts_specimen_url"] = ""
    row["category"] = "not_checked"; row["date_added"] = "not_checked"; row["subsets"] = "not_checked"
    row["google_fonts_directory"] = ""
    row["also_on_google_fonts"] = "no"
    row["google_fonts_specimen_url"] = ""
    row["_measured_path"] = m["path"]
    add(norm(fam), row)

# 2) Google Fonts (all families; used only where no original-repository row exists)
for gfd, r in gf_raw.items():
    sel = gf_sel[gfd]
    meas = gf_meas[sel["selected_path"]]
    lic = LICENCE_CODE.get(r["licence_code"], r["licence_code"])
    exts = sorted({os.path.splitext(x)[1].lower().lstrip(".") for x in r["font_files"].split(";") if x})
    row = {"family": r["family"], "family_as_in_font_name": r["family"], "primary_source_type": "google_fonts_repository",
           "primary_source_url": f"https://github.com/google/fonts/tree/main/{gfd}",
           "primary_source_ref": "google/fonts sparse checkout (commit at collection date)",
           "source_file_path": sel["selected_path"], "provider": "Google Fonts", "designer": r["designer"],
           "licence_code": lic, "licence_name": LICENCE_NAME.get(lic, lic),
           "licence_evidence": "METADATA.pb licence field (google/fonts)",
           "formats_available": ";".join(exts), "files_in_family": r["n_font_files"], "_source": "google",
           "category": r["category"], "date_added": r["date_added"], "subsets": r["subsets"].replace(";", ";"),
           "google_fonts_directory": gfd, "also_on_google_fonts": "yes", "_measured_path": sel["selected_path"],
           "_path": sel["selected_path"]}
    for k in MEAS_KEYS: row[k] = meas.get(k, "")
    row["variable_weight_range"] = wght_range(meas.get("variable_axes", ""))
    row["glyph_count"] = meas.get("glyph_count", "")
    row["source_file_bytes"] = meas.get("file_bytes", ""); row["source_file_sha256"] = meas.get("file_sha256", "")
    row["google_fonts_specimen_url"] = "https://fonts.google.com/specimen/" + r["family"].replace(" ", "+")
    row["google_fonts_specimen_http_status"] = SPECIMEN.get(row["google_fonts_specimen_url"], "not_checked")
    row["_repo_folder"] = "google"
    add(norm(r["family"]), row)

# 3) families declared by design systems that have no row yet (proprietary or not checked)
from collections import Counter
declared = defaultdict(Counter)
for d in decl:
    if d["declaration_role"] != "brand_or_custom":
        continue
    declared[norm(d["family_declared"])][d["family_declared"]] += int(d["occurrences"])
# after the alias step the family key of an alias is the catalogue family
for key, names in declared.items():
    if not key or key in families:
        continue
    name = names.most_common(1)[0][0]  # most frequent spelling in the packages
    prop = key in PROPRIETARY
    row = {"family": name, "family_as_in_font_name": name, "primary_source_type": "none_open_source_found", "primary_source_url": "",
           "primary_source_ref": "", "source_file_path": "", "provider": "not_checked", "designer": "not_checked",
           "licence_code": "proprietary_name_lookup" if prop else "unknown_not_checked",
           "licence_name": "not checked (vendor licence; name lookup only)" if prop else "not checked",
           "licence_evidence": "name lookup in this session; licence text not read" if prop else "not checked",
           "formats_available": "", "files_in_family": "", "_source": "design_system_only", "also_on_google_fonts": "no",
           "_path": "", "_repo_folder": ""}
    for k in MEAS_KEYS: row[k] = "not_measured"
    row["variable_weight_range"] = "not_measured"
    row["glyph_count"] = "not_measured"
    row["category"] = "not_checked"; row["date_added"] = "not_checked"; row["subsets"] = "not_checked"
    row["google_fonts_directory"] = ""; row["_measured_path"] = ""; row["google_fonts_specimen_url"] = ""
    row["source_file_bytes"] = ""; row["source_file_sha256"] = ""
    families[key] = row

# font_id + usage counts
usage = defaultdict(set)
for d in decl:
    if d["declaration_role"] == "brand_or_custom":
        usage[norm(d["family_declared"])].add(d["slug"])

rows = []
for key, r in families.items():
    r["font_id"] = slug(r["family"])
    r["design_systems_declaring"] = str(len(usage.get(key, set())))
    r["design_system_slugs"] = ";".join(sorted(usage.get(key, set())))
    r["alias_rule"] = ""
    r["licence_class"] = ("open" if r["licence_code"] in COMMERCIAL_USE or r["licence_code"] in LICENCE_CODE.values() else
                          "proprietary_name_lookup" if r["licence_code"] == "proprietary_name_lookup" else "unknown_not_checked")
    r["commercial_status"] = ("free open licence" if r["licence_class"] == "open" else
                              "commercial proprietary (name lookup)" if r["licence_class"] == "proprietary_name_lookup" else "not checked")
    r["commercial_use_allowed"] = COMMERCIAL_USE.get(r["licence_code"], "not_checked")
    r["is_variable_font"] = r.get("is_variable_font", "not_measured") or "not_measured"
    r["is_open_source"] = "yes" if r["licence_class"] == "open" else "no" if r["licence_class"] == "proprietary_name_lookup" else "not_checked"
    r["is_inter"] = "yes" if key == "inter" else "no"
    r["measured_on"] = TODAY
    r["source_file_format"] = os.path.splitext(r.get("source_file_path", ""))[1].lower().lstrip(".") or ""
    r["catalogue_source_path"] = r.get("_measured_path") or r.get("source_file_path", "")
    rows.append(r)

# stable order: Inter first, then open families A-Z, then design-system-only families
def order(r):
    return (0 if r["is_inter"] == "yes" else 1 if r["licence_class"] == "open" else 2, r["family"].lower())
rows.sort(key=order)

CAT_COLS = ["font_id", "family", "family_as_in_font_name", "is_inter", "is_open_source", "licence_class", "licence_code", "licence_name",
            "licence_evidence", "commercial_status", "commercial_use_allowed", "provider", "designer",
            "primary_source_type", "primary_source_url", "primary_source_ref", "also_on_google_fonts",
            "google_fonts_directory", "source_file_path", "source_file_format", "formats_available", "files_in_family",
            "is_variable_font", "variable_axes", "variable_weight_range", "weight_class", "subfamily_name", "outlines", "feat_tnum", "feat_pnum", "feat_lnum", "feat_onum",
            "feat_zero", "feat_slashed_zero_glyph", "feat_liga", "feat_dlig", "has_cyrillic", "has_serbian_cyrillic",
            "has_serbian_latin_diacritics", "glyph_count", "category", "date_added", "subsets", "google_fonts_specimen_url", "google_fonts_specimen_http_status",
            "source_file_bytes", "source_file_sha256",
            "design_systems_declaring", "design_system_slugs", "measured_on"]
with open(os.path.join(D, "fonts_catalogue.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=CAT_COLS, extrasaction="ignore", restval="not_checked"); w.writeheader()
    for r in rows: w.writerow(r)

# design system x family table
catalogue_by_norm = {norm(r["family"]): r for r in rows}
DS_COLS = ["slug", "design_system", "organisation", "npm_package", "npm_version", "family_declared",
           "occurrences", "declaration_role", "font_id", "match_status", "alias_applied", "licence_class", "licence_code",
           "is_variable_font", "has_serbian_cyrillic", "feat_tnum", "feat_zero"]
ds_rows = []
pkg_by_slug = {p["slug"]: p for p in pkgs}
seen_slugs_with_brand = set()
for d in decl:
    key = norm(d["family_declared"])
    c = catalogue_by_norm.get(key) if d["declaration_role"] == "brand_or_custom" else None
    if d["declaration_role"] == "brand_or_custom":
        seen_slugs_with_brand.add(d["slug"])
    base = ds_all.get(d["slug"], {})
    ds_rows.append({"slug": d["slug"], "design_system": base.get("design_system", ""), "organisation": base.get("organisation", ""),
                    "npm_package": d["npm_package"], "npm_version": d["npm_version"], "family_declared": d["family_declared"],
                    "occurrences": d["occurrences"], "declaration_role": d["declaration_role"],
                    "font_id": c["font_id"] if c else "", "match_status": ("matched_catalogue" if c else
                                                                          "os_or_browser_fallback" if d["declaration_role"] != "brand_or_custom" else "not_in_catalogue"),
                    "licence_class": c["licence_class"] if c else "",
                    "licence_code": c["licence_code"] if c else "",
                    "alias_applied": ALIASES.get(d["family_declared"].lower(), ""),
                    "is_variable_font": c["is_variable_font"] if c else "",
                    "has_serbian_cyrillic": c["has_serbian_cyrillic"] if c else "",
                    "feat_tnum": c["feat_tnum"] if c else "", "feat_zero": c["feat_zero"] if c else ""})
for p in pkgs:
    if p["slug"] not in seen_slugs_with_brand and p["files_read"] != "0":
        base = ds_all.get(p["slug"], {})
        ds_rows.append({"slug": p["slug"], "design_system": base.get("design_system", ""), "organisation": base.get("organisation", ""),
                        "npm_package": p["npm_package"], "npm_version": p["npm_version"], "family_declared": "",
                        "occurrences": "0", "declaration_role": "none_in_scanned_package", "font_id": "",
                        "match_status": "no_brand_font_in_package", "alias_applied": "", "licence_class": "", "licence_code": "",
                        "is_variable_font": "", "has_serbian_cyrillic": "", "feat_tnum": "", "feat_zero": ""})
with open(os.path.join(D, "design_system_fonts.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=DS_COLS); w.writeheader(); w.writerows(ds_rows)

print("catalogue rows:", len(rows), "| open:", sum(1 for r in rows if r["licence_class"] == "open"),
      "| design-system-only:", sum(1 for r in rows if r["primary_source_type"] == "none_open_source_found"))
print("design-system rows:", len(ds_rows), "| systems with brand font:", len(seen_slugs_with_brand))
