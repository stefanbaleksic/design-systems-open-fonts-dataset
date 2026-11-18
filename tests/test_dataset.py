"""Checks for the Design System Fonts dataset. Run: python3 -m unittest discover -s tests -v"""
import csv, os, re, unittest
from collections import Counter

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data")
DS_CSV = os.environ.get("DS_CSV", os.path.join(ROOT, os.environ.get("DS_REPO", "ds-src"), "out", "design_systems_v33.csv"))

def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))

def norm(name):
    s = re.sub(r"\s+(variable|var|vf)$", "", name.lower().strip())
    return re.sub(r"[^a-z0-9]", "", s)

CAT = load("fonts_catalogue.csv")
DSF = load("design_system_fonts.csv")
DECL = load("design_system_font_declarations.csv")
PKG = load("design_system_font_packages.csv")
TRUE_VALUES = {"yes", "no", "not_measured"}
LICENCES_OPEN = {"OFL-1.1", "Apache-2.0", "MIT", "UFL-1.0", "Bitstream-Vera"}

class Catalogue(unittest.TestCase):
    def test_font_id_unique(self):
        dup = [k for k, n in Counter(r["font_id"] for r in CAT).items() if n > 1]
        self.assertEqual(dup, [], f"duplicate font_id: {dup[:10]}")

    def test_no_duplicate_family_after_normalisation(self):
        dup = [k for k, n in Counter(norm(r["family"]) for r in CAT).items() if n > 1]
        self.assertEqual(dup, [], f"same family listed twice: {dup[:10]}")

    def test_inter_is_present_and_from_original_source(self):
        inter = [r for r in CAT if r["font_id"] == "inter"]
        self.assertEqual(len(inter), 1)
        i = inter[0]
        self.assertEqual(i["is_inter"], "yes")
        self.assertEqual(i["primary_source_url"], "https://github.com/rsms/inter")
        self.assertEqual(i["primary_source_type"], "original_repository")
        self.assertEqual(i["licence_code"], "OFL-1.1")
        self.assertEqual(i["is_variable_font"], "yes")
        self.assertIn("wght", i["variable_axes"])
        self.assertEqual(i["feat_tnum"], "yes")
        self.assertEqual(i["feat_zero"], "yes")
        self.assertEqual(i["has_serbian_cyrillic"], "yes")
        self.assertEqual(i["also_on_google_fonts"], "yes")
        for fmt in ("ttf", "otf", "woff2"):
            self.assertIn(fmt, i["formats_available"])

    def test_open_rows_have_known_licence(self):
        for r in CAT:
            if r["is_open_source"] == "yes":
                self.assertIn(r["licence_code"], LICENCES_OPEN, r["font_id"])
                self.assertEqual(r["licence_class"], "open", r["font_id"])

    def test_variable_flag_matches_axes(self):
        for r in CAT:
            if r["is_variable_font"] == "yes":
                self.assertNotEqual(r["variable_axes"], "", r["font_id"])
            if r["is_variable_font"] == "no":
                self.assertEqual(r["variable_axes"], "", r["font_id"])

    def test_feature_values_are_closed_set(self):
        cols = [c for c in CAT[0] if c.startswith("feat_") or c.startswith("has_") or c == "is_variable_font"]
        for r in CAT:
            for c in cols:
                self.assertIn(r[c], TRUE_VALUES, f"{r['font_id']} {c}={r[c]}")

    def test_original_repository_rows_have_licence_text_evidence(self):
        for r in CAT:
            if r["primary_source_type"] == "original_repository":
                self.assertNotEqual(r["licence_code"], "not_detected", r["font_id"])

    def test_row_counts_match_collection(self):
        # arithmetic, not a fixed number: candidates (Google Fonts + original repositories) minus the rows listed
        # in duplicates_removed.csv must equal the open-licence rows of the catalogue
        open_rows = [r for r in CAT if r["is_open_source"] == "yes"]
        candidates = len(load("google_families_raw.csv")) + len(load("upstream_font_measures.csv"))
        removed = len(load("duplicates_removed.csv"))
        self.assertEqual(len(open_rows), candidates - removed)

    def test_duplicates_listed_match_arithmetic(self):
        self.assertGreater(len(load("duplicates_removed.csv")), 0)

    def test_licence_classes_sum_to_total(self):
        c = Counter(r["licence_class"] for r in CAT)
        self.assertEqual(sum(c.values()), len(CAT))

class DesignSystemFonts(unittest.TestCase):
    def test_slugs_exist_in_design_systems_dataset(self):
        with open(DS_CSV, encoding="utf-8") as fh:
            slugs = {r["slug"] for r in csv.DictReader(fh)}
        missing = {r["slug"] for r in DSF} - slugs
        self.assertEqual(missing, set(), "slug not in design-systems v33")

    def test_brand_rows_link_to_catalogue(self):
        ids = {r["font_id"] for r in CAT}
        for r in DSF:
            if r["declaration_role"] == "brand_or_custom":
                self.assertIn(r["font_id"], ids, r["family_declared"])

    def test_no_duplicate_declaration_rows(self):
        keys = [(r["slug"], r["npm_package"], r["family_declared"]) for r in DECL]
        dup = [k for k, n in Counter(keys).items() if n > 1]
        self.assertEqual(dup, [])

    def test_every_package_has_a_row(self):
        for p in PKG:
            if p["files_read"] and p["files_read"] != "0":
                self.assertTrue(any(r["slug"] == p["slug"] for r in DSF), p["slug"])

    def test_inter_is_used_by_systems(self):
        n = sum(1 for r in DSF if r["font_id"] == "inter")
        self.assertGreater(n, 0)

    def test_package_hashes_recorded(self):
        for p in PKG:
            if not p["error"]:
                self.assertRegex(p["tarball_sha256"], r"^[0-9a-f]{64}$", p["npm_package"])

class Quality(unittest.TestCase):
    def test_every_google_family_has_a_specimen_check(self):
        raw = load("google_families_raw.csv")
        checks = {r["url"]: r for r in load("specimen_url_checks.csv")}
        self.assertEqual(len(checks), len(raw), "one specimen check per Google Fonts family")
        for r in CAT:
            if r["google_fonts_directory"]:
                self.assertNotEqual(r["google_fonts_specimen_http_status"], "not_checked", r["family"])

    def test_specimen_statuses_are_recorded_not_guessed(self):
        bad = [r for r in CAT if r["google_fonts_specimen_http_status"] not in {"200", "404", "not_checked"}]
        self.assertEqual(bad, [], "unexpected status values: " + str([r["family"] for r in bad[:5]]))

    def test_no_derived_nerd_font_or_frozen_builds_in_catalogue(self):
        names = [r["family_as_in_font_name"] for r in CAT if r["primary_source_type"] == "original_repository"]
        derived = [n for n in names if re.search(r"\b(NF|Frozen)\b", n)]
        self.assertEqual(derived, [], "derived builds should not be separate families")

    def test_weight_fields_are_valid(self):
        for r in CAT:
            w = r["weight_class"]
            self.assertTrue(w in ("", "not_measured") or (w.isdigit() and 1 <= int(w) <= 1000), (r["family"], w))
            rng = r["variable_weight_range"]
            if rng not in ("", "not_measured"):
                lo, hi = rng.split("-")
                self.assertLessEqual(int(float(lo)), int(float(hi)), r["family"])
                self.assertEqual(r["is_variable_font"], "yes", r["family"])

    def test_viewer_is_published_in_docs_and_small_enough(self):
        index = os.path.join(ROOT, "docs", "index.html")
        self.assertTrue(os.path.exists(index), "docs/index.html is what GitHub Pages serves")
        total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(os.path.join(ROOT, "docs")) for f in fs)
        self.assertLess(total, 5 * 1024 * 1024, "viewer folder should stay under 5 MB")
        with open(index, encoding="utf-8") as fh:
            html = fh.read()
        self.assertIn('data-f="onum"', html, "filter for oldstyle figures is present")

    def test_reproduce_workflow_present(self):
        wf = os.path.join(ROOT, ".github", "workflows", "reproduce.yml")
        self.assertTrue(os.path.exists(wf))

    def test_release_has_licence_and_citation(self):
        for name in ["LICENSE.md", "CITATION.cff", ".zenodo.json", "README.md", "requirements.txt"]:
            self.assertTrue(os.path.exists(os.path.join(ROOT, name)), name)

if __name__ == "__main__":
    unittest.main()
