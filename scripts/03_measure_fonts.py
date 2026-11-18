"""Measure OpenType facts of each selected font file with fontTools (read-only).

For every file in a selection CSV it records: variable (fvar axes), format (CFF = OTF, glyf = TTF),
the GSUB/GPOS feature tags relevant to numerals and ligatures, and character coverage relevant to
Serbian (Cyrillic and Latin letters with diacritics).
Usage: python3 03_measure_fonts.py <root_dir> <selection_csv> <out_csv> [--prefix <label>]
"""
import csv, os, sys
from concurrent.futures import ProcessPoolExecutor
from fontTools.ttLib import TTFont

FEATURES = ["tnum", "pnum", "lnum", "onum", "zero", "liga", "dlig"]
# Serbian-relevant characters: Cyrillic capital/small Zhe, Serbian Cyrillic letters, Latin with diacritics
SR_CYR = [0x0416, 0x0436, 0x0402, 0x0452, 0x0409, 0x0459, 0x040A, 0x045A, 0x040B, 0x045B, 0x040F, 0x045F]
SR_LAT = [0x010C, 0x010D, 0x0106, 0x0107, 0x0160, 0x0161, 0x017D, 0x017E, 0x0110, 0x0111]

def measure(args):
    root, rel = args
    path = os.path.join(root, rel)
    rec = {"path": rel, "error": ""}
    try:
        rec["file_bytes"] = os.path.getsize(path)
        import hashlib
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        rec["file_sha256"] = h.hexdigest()
        f = TTFont(path, lazy=True)
        names = f["name"]
        def nm(i):
            n = names.getName(i, 3, 1, 0x409) or names.getName(i, 1, 0, 0)
            return n.toUnicode() if n else ""
        rec["font_family_name"] = nm(1)
        rec["typographic_family"] = nm(16)
        rec["font_version"] = nm(5)
        rec["outlines"] = "CFF" if "CFF " in f or "CFF2" in f else "glyf"
        fvar = f["fvar"] if "fvar" in f else None
        rec["is_variable_font"] = "yes" if fvar is not None else "no"
        rec["weight_class"] = str(f["OS/2"].usWeightClass) if "OS/2" in f else ""  # static weight (100-900), OS/2 table
        rec["subfamily_name"] = nm(2)
        rec["variable_axes"] = ";".join(f"{a.axisTag}:{a.minValue:g}-{a.maxValue:g}" for a in fvar.axes) if fvar else ""
        cmap = f.getBestCmap() or {}
        rec["glyph_count"] = f["maxp"].numGlyphs
        rec["has_cyrillic"] = "yes" if any(c in cmap for c in (0x0416, 0x0436)) else "no"
        rec["has_serbian_cyrillic"] = "yes" if all(c in cmap for c in SR_CYR) else "no"
        rec["has_serbian_latin_diacritics"] = "yes" if all(c in cmap for c in SR_LAT) else "no"
        tags = {}
        for tbl in ("GSUB", "GPOS"):
            tags[tbl] = set()
            if tbl in f:
                fl = f[tbl].table.FeatureList
                if fl:
                    tags[tbl] = {fr.FeatureTag for fr in fl.FeatureRecord}
        for ft in FEATURES:
            rec[f"feat_{ft}"] = "yes" if (ft in tags["GSUB"] or ft in tags["GPOS"]) else "no"
        rec["feat_slashed_zero_glyph"] = "yes" if any(n in cmap.values() for n in ("zero.slash",)) or "zero.slash" in f.getGlyphOrder() else "no"
        f.close()
    except Exception as e:  # keep going; the error is recorded and reported
        rec["error"] = f"{type(e).__name__}: {e}"[:200]
    return rec

if __name__ == "__main__":
    root, sel, out = sys.argv[1], sys.argv[2], sys.argv[3]
    rows = list(csv.DictReader(open(sel, encoding="utf-8")))
    jobs = [(root, r["selected_path"]) for r in rows]
    with ProcessPoolExecutor(max_workers=2) as ex:
        res = list(ex.map(measure, jobs, chunksize=20))
    keys = []
    for r in res:
        for k in r:
            if k not in keys: keys.append(k)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(res)
    errs = sum(1 for r in res if r["error"])
    print("measured", len(res), "errors", errs, "->", out)
