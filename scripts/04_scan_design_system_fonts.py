"""Find font families declared by design-system npm packages.

Input : design_systems_v33.csv of the design-systems dataset (rows with an npm package)
Process: `npm pack <package>@<pinned version>` into a download cache; the tarball is unpacked with
         Python's tarfile (no scripts are run) and every text file below 2 MB is read.
         Declarations found: `font-family:` (CSS/SCSS/LESS/HTML/inline style), `fontFamily:` (JS/TS
         objects), and `--*font*` custom properties whose value is a family list.
Output: data/design_system_font_declarations.csv  (one row per package x family)
        data/design_system_font_packages.csv      (one row per package, with the sha256 of the tarball)
Limits: static text only; a family found here is a declaration in the package, not proof of what the
        rendered site shows. Generic families and CSS keywords are removed.
"""
import csv, hashlib, os, re, subprocess, sys, tarfile, io, json
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

FD = os.path.join(os.path.dirname(__file__), "..")
SRC = os.environ.get("DS_CSV", "design_systems_v33.csv")  # the design-systems dataset v33 (see sources.csv)
CACHE = os.environ.get("NPM_CACHE", "npm_tarballs")  # cache of pinned npm packs; set NPM_CACHE outside the repo
TEXT_EXT = (".css", ".scss", ".sass", ".less", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".json", ".html", ".md", ".mdx", ".vue", ".svelte", ".styl")
GENERIC = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-sans-serif", "ui-serif",
           "ui-monospace", "ui-rounded", "emoji", "math", "fangsong", "inherit", "initial", "unset", "revert",
           "-apple-system", "blinkmacsystemfont", "none", "normal", "auto", "var", "font", "fonts"}
FF_CSS = re.compile(r"font-family\s*:\s*([^;}{]+)", re.I)
FF_JS = re.compile(r"fontFamily\s*:\s*([\"'`][^\"'`]+[\"'`]|[^,}\n]+)", re.I)
FF_VAR = re.compile(r"--[\w-]*font[\w-]*\s*:\s*([^;}{]+)", re.I)

# operating-system, browser and emoji faces: found in CSS but not a brand typeface of the system
OS_FALLBACK = {"arial", "helvetica", "helvetica neue", "times new roman", "times", "courier", "courier new",
               "liberation mono", "liberation sans", "consolas", "menlo", "monaco", "sfmono-regular", "sf mono",
               "segoe ui", "segoe ui emoji", "segoe ui symbol", "apple color emoji", "noto color emoji",
               "georgia", "verdana", "tahoma", "trebuchet ms",
               "san francisco", "sf pro text", "sf pro display", "-apple-system", "system-ui", "dejavu sans",
               "symbola", "helvetica-neue", "sans serif", "segoe", "lucida grande", "ms gothic"}
# Note: open faces that are also common defaults (Roboto, Noto Sans, Ubuntu, DejaVu, Cantarell) are NOT here:
# they are brand or custom declarations and are matched to the open-licence catalogue.
UNIT = re.compile(r"^[-+]?[\d.]+\s*(px|rem|em|%|pt|vh|vw|vmin|vmax|ms|s|ch|ex)?$", re.I)

def split_families(value):
    out = []
    for part in value.split(","):
        p = part.strip().strip("\"'`").strip()
        p = re.sub(r"\s*!(important|default).*$", "", p, flags=re.I).strip().strip("\"'`").strip()
        p = re.sub(r"[;)\]}]+$", "", p).strip().strip("\"'`").strip()
        if not p or p.startswith(("var(", "$", "@", "{", "(", "[", "#", ".", "'", "\"")) or "${" in p or "{" in p:
            continue
        if UNIT.match(p) or re.search(r"[;:=<>\\/]|\bfunction\b|\breturn\b", p):
            continue
        p = re.sub(r"\s+", " ", p)
        if p.lower() in GENERIC or len(p) > 60 or not re.search(r"[A-Za-z]", p):
            continue
        # identifiers and keywords, not family names: dotted identifiers, one lowercase word, or <= 2 letters
        if "." in p or (" " not in p and p.islower()) or len(p) <= 2:
            continue
        out.append(p)
    return out

NOT_A_FONT = re.compile(r"[()\"'\[\]{},$+*=_]|(?i:\bvar\b|\bcalc\b|\bround\b|\btypeof\b|\btokens?\b|\bresolver\b)|[a-z][A-Z]|\s-\s|\s\d+\s")
NOT_A_FONT_NAMES = {"accordion", "checkbox", "dropdown", "step", "rating", "icons", "navigo", "videojs", "tokenobj",
                    "x-localespecific", "font a", "font b", "defaultfontfamily", "fontfamily", "themedfontfamily",
                    "canvasfontfamilies", "lining-nums tabular-nums slashed-zero", "kern", "sans-serif )", "fonts"}

def role(family):
    low = family.lower()
    if NOT_A_FONT.search(family) or low in NOT_A_FONT_NAMES or family.isupper() and len(family) > 20:
        return "not_a_font_name"
    return "os_or_browser_fallback" if low in OS_FALLBACK else "brand_or_custom"

def pack(row):
    pkg, ver = row["npm_package"], row["npm_latest_version"]
    safe = pkg.replace("/", "__").replace("@", "") + f"@{ver}"
    target = os.path.join(CACHE, safe + ".tgz")
    if not os.path.exists(target):
        cmd = ["npm", "pack", f"{pkg}@{ver}", "--pack-destination", CACHE, "--silent"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        produced = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        if not produced:
            return {"pkg": pkg, "ver": ver, "error": "npm pack failed: " + r.stderr.strip()[:160]}
        name = os.path.join(CACHE, produced)
        if name != target:
            os.replace(name, target)
    sha = hashlib.sha256(open(target, "rb").read()).hexdigest()
    counts = Counter()
    files_read = 0
    try:
        with tarfile.open(target, "r:gz") as tf:
            for m in tf.getmembers():
                if not m.isfile() or not m.name.lower().endswith(TEXT_EXT) or m.size > 2_000_000:
                    continue
                if "node_modules" in m.name:
                    continue
                files_read += 1
                text = tf.extractfile(m).read().decode("utf-8", "replace")
                for rx in (FF_CSS, FF_JS, FF_VAR):
                    for mm in rx.finditer(text):
                        for fam in split_families(mm.group(1)):
                            counts[fam] += 1
    except tarfile.TarError as e:
        return {"pkg": pkg, "ver": ver, "sha256": sha, "error": f"tar: {e}"}
    return {"pkg": pkg, "ver": ver, "sha256": sha, "files_read": files_read, "counts": counts, "error": ""}

if __name__ == "__main__":
    rows = [r for r in csv.DictReader(open(SRC, encoding="utf-8")) if r["npm_package"] and r["npm_package"] != "not_checked" and r["npm_latest_version"]]
    os.makedirs(CACHE, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(pack, rows))
    decl, pk = [], []
    by = {r["npm_package"]: r for r in rows}
    for res in results:
        slug = by[res["pkg"]]["slug"]
        pk.append({"slug": slug, "npm_package": res["pkg"], "npm_version": res["ver"], "tarball_sha256": res.get("sha256", ""),
                   "files_read": res.get("files_read", 0), "families_found": len(res.get("counts", {})), "error": res["error"]})
        for fam, n in sorted(res.get("counts", {}).items(), key=lambda x: -x[1]):
            decl.append({"slug": slug, "npm_package": res["pkg"], "npm_version": res["ver"], "family_declared": fam, "occurrences": n, "declaration_role": role(fam)})
    with open(os.path.join(FD, "data", "design_system_font_declarations.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(decl[0].keys())); w.writeheader(); w.writerows(decl)
    with open(os.path.join(FD, "data", "design_system_font_packages.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pk[0].keys())); w.writeheader(); w.writerows(pk)
    print("packages", len(pk), "errors", sum(1 for p in pk if p["error"]), "declarations", len(decl))
