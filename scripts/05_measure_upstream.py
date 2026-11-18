"""Measure font families of upstream (original foundry) repositories that are not in Google Fonts,
and detect the licence from the repository's own licence file.

Repositories are shallow clones at the commit given in UPSTREAM below (recorded in the output).
For each repository: all ttf/otf/woff2/woff files (excluding CJK packages in IBM Plex, a language
expansion of this iteration), grouped by typographic family name; one representative file per group
(variable first, then Regular, then TTF/OTF) is measured with the same function as Google Fonts.
Output: data/upstream_font_measures.csv
"""
import csv, glob, os, re, subprocess, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
from importlib.machinery import SourceFileLoader
meas = SourceFileLoader("m3", os.path.join(os.path.dirname(__file__), "03_measure_fonts.py")).load_module()

FD = os.path.join(os.path.dirname(__file__), "..")
UP = os.environ.get("UPSTREAM_ROOT", "upstream")
UPSTREAM = [  # (folder, repository url, licence note, excluded path fragments)
        ("plex", "https://github.com/IBM/plex", None, ["-sc/", "-tc/", "-jp/", "-kr/", "-sc-", "-tc-", "-jp-", "-kr-", "plex-sans-sc", "plex-sans-tc", "plex-sans-jp", "plex-sans-kr"]),
    ("mona-sans", "https://github.com/github/mona-sans", None, []),
    ("geist-font", "https://github.com/vercel/geist-font", None, []),
    ("cascadia-code", "https://github.com/microsoft/cascadia-code", None, []),
    ("Hack", "https://github.com/source-foundry/Hack", None, []),
    ("source-sans", "https://github.com/adobe-fonts/source-sans", None, []),
    ("jetbrains-mono", "https://github.com/JetBrains/JetBrainsMono", None, []),
    ("monaspace", "https://github.com/githubnext/monaspace", None, ["Frozen Fonts/", "NerdFonts/", "Web Fonts/"]),
    ("victor-mono", "https://github.com/rubjo/victor-mono", None, ["src/assets/"]),
    ("intel-one-mono", "https://github.com/intel/intel-one-mono", None, []),
    ("lilex", "https://github.com/mishamyrt/Lilex", None, []),
    ("maple-font", "https://github.com/subframe7536/maple-font", None, ["-NF-"]),
    ("departure-mono", "https://github.com/rektdeckard/departure-mono", None, []),
    ("source-serif", "https://github.com/adobe-fonts/source-serif", None, []),
    ("juliamono", "https://github.com/cormullion/juliamono", None, []),
    ("mononoki", "https://github.com/madmalik/mononoki", None, []),
    ("stixfonts", "https://github.com/stipub/stixfonts", None, []),
    ("font-doulos", "https://github.com/silnrsi/font-doulos", None, []),
    ("font-andika", "https://github.com/silnrsi/font-andika", None, []),
    ("font-awami", "https://github.com/silnrsi/font-awami", None, []),
    ("outfit-fonts", "https://github.com/Outfitio/Outfit-Fonts", None, []),
    ("junction", "https://github.com/theleagueof/junction", None, []),
    ("chunk", "https://github.com/theleagueof/chunk", None, []),
    ("RedHatFont", "https://github.com/RedHatOfficial/RedHatFont", None, []),
    ("Overpass", "https://github.com/RedHatOfficial/Overpass", None, []),
    ("public-sans", "https://github.com/uswds/public-sans", None, []),
    ("Fira", "https://github.com/mozilla/Fira", None, []),
    ("FiraCode", "https://github.com/tonsky/FiraCode", None, []),
    ("font-gentium", "https://github.com/silnrsi/font-gentium", None, []),
    ("font-charis", "https://github.com/silnrsi/font-charis", None, []),
    ("font-padauk", "https://github.com/silnrsi/font-padauk", None, []),
    ("font-abyssinica", "https://github.com/silnrsi/font-abyssinica", None, []),
    ("liberation-fonts", "https://github.com/liberationfonts/liberation-fonts", None, []),
    ("source-code-pro", "https://github.com/adobe-fonts/source-code-pro", None, []),
    ("atkinson-hyperlegible-next", "https://github.com/googlefonts/atkinson-hyperlegible-next", None, []),
    ("atkinson-hyperlegible", "https://github.com/googlefonts/atkinson-hyperlegible", None, []),
    ("lexend", "https://github.com/googlefonts/lexend", None, []),
    ("recursive", "https://github.com/arrowtype/recursive", None, ["docs/", "src/"]),
    ("instrument-sans", "https://github.com/Instrument/instrument-sans", None, []),
    ("Work-Sans", "https://github.com/weiweihuanghuang/Work-Sans", None, []),
]
# Packages on npm: (folder, npm package, version, upstream project, file pattern inside the package,
# note, Cyrillic/Serbian measured). Fontsource packages ship only the latin subset, so their Cyrillic and Serbian
# coverage cannot be measured and is recorded as not_measured.
NPM_ROOT = os.environ.get("NPM_ROOT", "npm")
NPM = [
    ("fontsource-iosevka", "@fontsource/iosevka", "5.3.0", "https://github.com/be5invis/Iosevka", "files/iosevka-latin-400-normal.woff2",
     "latin subset of the Fontsource package", False),
    ("fontsource-commit-mono", "@fontsource/commit-mono", "5.3.0", "https://github.com/commitmono/commit-mono", "files/commit-mono-latin-400-normal.woff2",
     "latin subset of the Fontsource package", False),
    ("dejavu", "dejavu-fonts-ttf", "2.37.3", "https://github.com/dejavu-fonts/dejavu-fonts", "ttf/*.ttf",
     "TrueType files of the DejaVu release, as packaged on npm", True),
]
LICENCE_PATTERNS = [
    ("Bitstream-Vera", r"Bitstream Vera"),  # first: DejaVu also contains MIT-style text for its scripts
    ("OFL-1.1", r"SIL OPEN FONT LICEN[CS]E,? Version 1\.1"),
    ("Apache-2.0", r"Apache License\s+Version 2\.0"),
    ("MIT", r"Permission is hereby granted, free of charge"),
    ("UFL-1.0", r"UBUNTU FONT LICENCE Version 1\.0"),
]

def detect_licence(folder):
    hits = []
    for name in os.listdir(folder):
        upper = name.upper()
        if (upper.startswith(("LICENSE", "LICENCE", "OFL", "COPYING")) or "OPEN FONT LICENSE" in upper) and os.path.isfile(os.path.join(folder, name)):
            text = open(os.path.join(folder, name), encoding="utf-8", errors="replace").read()[:20000]
            for code, rx in LICENCE_PATTERNS:
                if re.search(rx, text, flags=re.I):
                    hits.append(code)
                    break
    codes = sorted(set(hits))
    return ";".join(codes) if codes else "not_detected", "; ".join(sorted(os.listdir(folder))[:0])

def git_head(folder):
    return subprocess.run(["git", "-C", folder, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()

out = []
for folder, url, _, excl in UPSTREAM:
    root = os.path.join(UP, folder)
    if not os.path.isdir(root):
        print("missing", folder); continue
    files = subprocess.run(["git", "-C", root, "ls-files"], capture_output=True, text=True).stdout.splitlines()
    fonts = [f for f in files if re.search(r"\.(ttf|otf|woff2?)$", f, re.I) and not any(e in f for e in excl)
             and "/node_modules/" not in f and "/test" not in f.lower()]
    groups = defaultdict(list)
    for f in fonts:
        try:
            from fontTools.ttLib import TTFont
            t = TTFont(os.path.join(root, f), lazy=True)
            nm = t["name"]
            n16 = nm.getName(16, 3, 1, 0x409) or nm.getName(1, 3, 1, 0x409)
            key = (n16.toUnicode() if n16 else "") or "?"
            t.close()
        except Exception:
            key = "?unreadable"
        groups[key].append(f)
    lic, _ = detect_licence(root)
    commit = git_head(root)
    for key, fl in sorted(groups.items()):
        if key in ("?", "?unreadable"):
            continue
        def rank(f):
            low = os.path.basename(f).lower()
            var = 0 if "variable" in f.lower() or "[" in low or "vf" in low else 1
            reg = 0 if "regular" in low or re.search(r"-(regular|normal)\.", low) else 1
            ext = {".ttf": 0, ".otf": 1, ".woff2": 2, ".woff": 3}[os.path.splitext(low)[1]]
            ital = 1 if "italic" in low else 0
            # width or optical instances (Condensed, Expanded, Display, Mono...) are not the base family
            width = 1 if re.search(r"condensed|expanded|narrow|wide|display|semi|mono", low) else 0
            return (ital, var, width, reg, ext, f)
        rep = sorted(fl, key=rank)[0]
        exts = sorted({os.path.splitext(f)[1].lower().lstrip(".") for f in fl})
        m = meas.measure((root, rep))
        m.update({"repo_folder": folder, "repository_url": url, "repository_commit": commit, "family_key": key,
                  "representative_path": rep, "formats_in_repo": ";".join(exts), "files_in_family": len(fl),
                  "repo_licence_detected": lic})
        out.append(m)

# Inter: measured from the original GitHub release archive (rsms/inter v4.1), not from a mirror.
INTER_DIR = os.environ.get("INTER_DIR", "inter-release/x")
INTER_ZIP_SHA = "9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e"
for rel, fam_key in [("InterVariable.ttf", "Inter"), ("InterVariable-Italic.ttf", "Inter")]:
    m = meas.measure((INTER_DIR, rel))
    m.update({"repo_folder": "inter-release-4.1", "repository_url": "https://github.com/rsms/inter",
              "repository_commit": "release v4.1 (archive sha256 " + INTER_ZIP_SHA[:12] + "...)",
              "family_key": fam_key, "representative_path": rel,
              "formats_in_repo": "ttf;otf;woff2;ttc (release archive)", "files_in_family": 1,
              "repo_licence_detected": "OFL-1.1 (LICENSE.txt in archive)"})
    out.append(m) if rel == "InterVariable.ttf" else None

import hashlib
for folder, pkg, ver, upstream_url, pattern, note, measured in NPM:
    base = os.path.join(NPM_ROOT, folder)
    root = os.path.join(base, "package")
    tgz = [f for f in os.listdir(base) if f.endswith(".tgz")] if os.path.isdir(base) else []
    if "*" in pattern:
        files = sorted(os.path.relpath(f, root) for f in glob.glob(os.path.join(root, pattern)))
    else:
        files = [pattern] if os.path.exists(os.path.join(root, pattern)) else []
    if not files or not tgz:
        print("missing npm package", folder); continue
    tgz_sha = hashlib.sha256(open(os.path.join(base, tgz[0]), "rb").read()).hexdigest()
    lic, _ = detect_licence(root)
    for rel in files:
        m = meas.measure((root, rel))
        m.update({"repo_folder": "npm-" + folder, "repository_url": "https://www.npmjs.com/package/" + pkg,
                  "repository_commit": f"npm {pkg}@{ver} (tarball sha256 {tgz_sha[:12]}...); upstream project {upstream_url}",
                  "family_key": m.get("font_family_name") or folder, "representative_path": rel,
                  "formats_in_repo": f"{rel.rsplit('.', 1)[-1]} ({note})", "files_in_family": len(files),
                  "repo_licence_detected": lic})
        if not measured:
            for k in ("has_cyrillic", "has_serbian_cyrillic", "has_serbian_latin_diacritics"):
                m[k] = "not_measured"
        out.append(m)

os.makedirs(os.path.join(FD, "data"), exist_ok=True)
keys = []
for r in out:
    for k in r:
        if k not in keys: keys.append(k)
with open(os.path.join(FD, "data", "upstream_font_measures.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(out)
print("upstream families:", len(out), "errors:", sum(1 for r in out if r["error"]))
