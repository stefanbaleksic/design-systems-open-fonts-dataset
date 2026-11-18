"""Write data/data_dictionary.md. Every column of every CSV in data/ must have an entry here
(tests/test_dataset.py checks this), so a new column cannot be published undocumented."""
import csv, os
FD = os.path.join(os.path.dirname(__file__), "..")
D = os.path.join(FD, "data")
DESC = {
 # fonts_catalogue.csv
 "font_id": ("identifier", "Slug of the font family. In fonts_catalogue.csv it is unique; in design_system_fonts.csv it links a declaration to its catalogue row (empty when there is no match).", "derived"),
 "family": ("text", "Family name as used in this table (variable-font suffixes such as Var or VF removed).", "source name table / METADATA.pb"),
 "family_as_in_font_name": ("text", "Family name as read from the font's name table, or the METADATA name, before cleaning.", "font file name table; METADATA.pb"),
 "is_inter": ("yes / no", "yes for Inter, the family required in this release.", "rule"),
 "is_open_source": ("yes / no / not_checked", "yes when the family has an open licence (OFL-1.1, Apache-2.0, MIT or UFL-1.0) read from the source.", "licence_class"),
 "licence_class": ("open / proprietary_name_lookup / unknown_not_checked", "open = licence read from METADATA.pb or the repository licence file. proprietary_name_lookup = a vendor face recognised by name only; the licence text was not read. unknown_not_checked = no open source found and no licence read.", "see licence_evidence"),
 "licence_code": ("OFL-1.1 / Apache-2.0 / MIT / UFL-1.0 / proprietary_name_lookup / unknown_not_checked", "Licence identifier. Google Fonts codes OFL, APACHE2 and UFL are mapped to OFL-1.1, Apache-2.0 and UFL-1.0.", "METADATA.pb or repository licence file"),
 "licence_name": ("text", "Full licence name for licence_code.", "mapping"),
 "licence_evidence": ("text", "Where the licence was read: METADATA.pb, repository licence file (automatic text match), release archive, or name lookup only.", "collection log"),
 "commercial_status": ("free open licence / commercial proprietary (name lookup) / not checked", "Whether the font is free under an open licence or a commercial vendor face. The licence allows commercial use for open families; this column does not replace reading the licence.", "licence_class"),
 "commercial_use_allowed": ("yes / yes, with conditions / not_checked", "Whether the licence text grants commercial use. UFL-1.0 has conditions on modified versions and naming.", "licence text (summary)"),
 "provider": ("text", "Who publishes the family: Google Fonts, or the owner of the original repository (GitHub organisation or user).", "METADATA.pb; repository URL"),
 "designer": ("text", "Designer named in METADATA.pb (Google Fonts families). not_checked for original-repository families (not read in this release).", "METADATA.pb"),
 "primary_source_type": ("original_repository / npm_package / google_fonts_repository / none_open_source_found", "Source used for the measured file. Source-first: the original repository wins when both have the family. npm_package = the font as published on npm (Fontsource packaging, latin subset only, or a release packaged by the project); used when no repository with font files was available.", "rule"),
 "primary_source_url": ("URL", "Repository the font was measured from (original repository or github.com/google/fonts).", "source"),
 "primary_source_ref": ("text", "Commit or release of the primary source.", "source"),
 "also_on_google_fonts": ("yes / no", "yes when Google Fonts also distributes the family (its row was removed as a duplicate, see duplicates_removed.csv).", "METADATA.pb"),
 "google_fonts_directory": ("path", "Folder in google/fonts (ofl, apache or ufl) for the family, when present.", "METADATA.pb"),
 "source_file_path": ("path", "Path of the font file inside the source repository (or google/fonts) that was measured.", "selection rule"),
 "source_file_format": ("ttf / otf / woff2 / woff / ttc", "File extension of the measured file.", "file name"),
 "formats_available": ("list separated by ;", "Font formats seen in the source for this family: from METADATA file names (Google Fonts) or from the repository tree (original repositories).", "file names in source"),
 "files_in_family": ("integer", "Number of font files in the source for this family (all styles and formats).", "file names in source"),
 "is_variable_font": ("yes / no / not_measured", "yes when the measured file has an fvar table (OpenType variable font).", "fontTools (fvar)"),
 "variable_weight_range": ("min-max or empty", "Weight (wght) axis range of a variable font, for example 100-900. Empty when the font has no weight axis; not_measured for npm rows measured without this field.", "fontTools (fvar)"),
 "weight_class": ("1-1000 or empty", "OS/2 usWeightClass of the measured file: the static weight of that one file (400 = Regular, 700 = Bold). One file per family, so a family's other weights are not listed.", "fontTools (OS/2)"),
 "subfamily_name": ("text", "Name ID 2 of the measured file: the style name inside the family, for example Regular, Italic, Bold.", "fontTools (name)"),
 "variable_axes": ("tag:min-max list", "Variation axes of the measured file (for example wght:100-900).", "fontTools (fvar)"),
 "outlines": ("glyf / CFF", "Outline technology of the measured file: glyf = TrueType outlines, CFF = PostScript outlines (OTF).", "fontTools"),
 "feat_tnum": ("yes / no", "Tabular (fixed-width) figures: OpenType feature tnum present in GSUB or GPOS.", "fontTools (feature list)"),
 "feat_pnum": ("yes / no", "Proportional figures: feature pnum present.", "fontTools"),
 "feat_lnum": ("yes / no", "Lining figures (cap height): feature lnum present.", "fontTools"),
 "feat_onum": ("yes / no", "Oldstyle (text) figures: feature onum present. Read as the closest OpenType meaning of 'open numbers', which has no tag of its own.", "fontTools"),
 "feat_zero": ("yes / no", "Zero feature: feature zero present (in most fonts this switches to a slashed or dotted zero).", "fontTools"),
 "feat_slashed_zero_glyph": ("yes / no", "A glyph named zero.slash exists in the font. A direct check for a slashed zero glyph; complements feat_zero.", "fontTools (glyph order)"),
 "feat_liga": ("yes / no", "Standard ligatures: feature liga present.", "fontTools"),
 "feat_dlig": ("yes / no", "Discretionary ligatures: feature dlig present.", "fontTools"),
 "has_cyrillic": ("yes / no / not_measured", "The font maps the Cyrillic letters Ж and ж (U+0416, U+0436). not_measured when the shipped file is a Latin-only subset.", "fontTools (cmap)"),
 "has_serbian_cyrillic": ("yes / no / not_measured", "The font maps all Serbian Cyrillic letters (Ђ Ј Љ Њ Ћ Џ and lower case; U+0402 to U+045F subset used in the test). not_measured when the shipped file is a Latin-only subset.", "fontTools (cmap)"),
 "has_serbian_latin_diacritics": ("yes / no / not_measured", "The font maps the Latin letters with diacritics used in Serbian Latin (Č Ć Š Đ Ž, lower case). not_measured when the shipped file is a Latin-only subset.", "fontTools (cmap)"),
 "glyph_count": ("integer", "Number of glyphs in the measured file (maxp table).", "fontTools"),
 "category": ("text", "Google Fonts category (SANS_SERIF, SERIF, DISPLAY, HANDWRITING, MONOSPACE). not_checked for original-repository families.", "METADATA.pb"),
 "date_added": ("date", "Date the family was added to Google Fonts.", "METADATA.pb"),
 "subsets": ("list separated by ;", "Unicode subsets declared for the family in METADATA.pb.", "METADATA.pb"),
 "google_fonts_specimen_url": ("URL", "Specimen page on fonts.google.com for Google Fonts families (constructed from the family name by a fixed rule).", "rule"),
 "google_fonts_specimen_http_status": ("HTTP status", "Result of an HTTP request to the specimen URL (script 11, date in specimen_url_checks.csv). 200 = page exists; 404 = family has no specimen page on fonts.google.com; not_checked = upstream or design-system-only row.", "HTTP GET"),
 "source_file_bytes": ("integer", "Size of the measured file in bytes.", "file system"),
 "source_file_sha256": ("hex", "SHA-256 of the measured file: the identity check for reproduction.", "sha256"),
 "design_systems_declaring": ("integer", "Number of design systems (of the 143 scanned npm packages) that declare this family, by normalised name.", "design_system_font_declarations.csv"),
 "design_system_slugs": ("list separated by ;", "Slugs of the design systems that declare this family (join with design_systems_v33.csv on slug).", "design_system_font_declarations.csv"),
 "measured_on": ("date", "Date the file was measured.", "collection date"),
 # design_system_fonts.csv
 "slug": ("identifier", "Design system slug in design-systems dataset v33 (join key).", "design_systems_v33.csv"),
 "design_system": ("text", "Design system name from design-systems dataset v33.", "design_systems_v33.csv"),
 "organisation": ("text", "Organisation from design-systems dataset v33.", "design_systems_v33.csv"),
 "npm_package": ("text", "npm package scanned (pinned version in npm_version).", "design_systems_v33.csv npm_package"),
 "npm_version": ("text", "Version pinned from npm_latest_version of design-systems dataset v33.", "design_systems_v33.csv"),
 "family_declared": ("text", "Family name as written in the package (most frequent spelling). Empty for rows with no brand font.", "npm package text"),
 "occurrences": ("integer", "Number of declarations of this family name found in the package text.", "regex count"),
 "declaration_role": ("brand_or_custom / os_or_browser_fallback / not_a_font_name / none_in_scanned_package", "brand_or_custom = a family that is not a common system face. os_or_browser_fallback = system or emoji face (Arial, Segoe UI, Menlo...). not_a_font_name = identifier or code token, kept for audit only.", "rule (scripts/04)"),
 "match_status": ("matched_catalogue / os_or_browser_fallback / not_in_catalogue / no_brand_font_in_package", "How the row relates to the catalogue.", "rule"),
 "alias_applied": ("text", "Manual alias rule used for the name (for example Source Sans Pro to Source Sans 3). Empty when no alias.", "manual alias list in scripts/06"),
 "licence_code": ("text", "Licence code of the matched catalogue family. In fonts_catalogue.csv see the row above.", "fonts_catalogue.csv"),
 "is_variable_font": ("yes / no / not_measured", "Variable font flag of the matched catalogue family.", "fonts_catalogue.csv"),
 "variable_weight_range": ("min-max or empty", "Weight axis range of the matched catalogue family.", "fonts_catalogue.csv"),
 "weight_class": ("1-1000 or empty", "Static weight of the measured file of the matched catalogue family.", "fonts_catalogue.csv"),
 "has_serbian_cyrillic": ("yes / no / not_measured", "Serbian Cyrillic coverage of the matched catalogue family.", "fonts_catalogue.csv"),
 "feat_tnum": ("yes / no", "Tabular figures of the matched catalogue family.", "fonts_catalogue.csv"),
 "feat_zero": ("yes / no", "Zero feature of the matched catalogue family.", "fonts_catalogue.csv"),
 # declarations
 # packages
 "tarball_sha256": ("hex", "SHA-256 of the npm tarball that was scanned.", "sha256 of npm pack output"),
 "files_read": ("integer", "Number of text files (CSS, JS, TS, JSON, HTML, Markdown...) below 2 MB that were read.", "tarfile"),
 "families_found": ("integer", "Number of distinct family names found in the package (before role classification).", "regex"),
 "source_id": ("identifier", "Short name of the source; used in the README.", "rule"),
 "source_type": ("text", "Kind of source (git repository, release archive, dataset, package registry).", "rule"),
 "url": ("URL", "Address the source was read from.", "source"),
 "version_or_ref": ("text", "Git commit, release tag, or pinned version of the source.", "git / metadata"),
 "retrieved_on": ("date", "Date the source was read.", "collection log"),
 "integrity": ("text", "How the source can be checked again: commit hash or SHA-256.", "git / sha256"),
 "used_for": ("text", "What the source contributed to the dataset.", "rule"),
 "licence_of_source": ("text", "Licence of the source as read; the source licence does not extend to this dataset.", "licence file or METADATA.pb"),
 "error": ("text", "Error message when the package could not be packed or read; empty when it was read.", "npm pack / tarfile"),
}
DICT = {"fonts_catalogue.csv": "Font families (one row per family). Main table.",
        "design_system_fonts.csv": "Design system x declared family (one row per declaration, plus one row per scanned package with no brand font).",
        "design_system_font_declarations.csv": "Raw declarations per design system (all roles, including rejected noise).",
        "design_system_font_packages.csv": "One row per scanned npm package: pinned version, tarball hash, files read, errors.",
        "sources.csv": "External sources read: commit, release or hash, licence."}
def cols(name):
    return list(csv.DictReader(open(os.path.join(D, name), encoding="utf-8")).fieldnames)
lines = ["# Data dictionary", "", "Every column of every CSV in `data/` is listed here (tests check this).", ""]
seen = set()
for f, purpose in DICT.items():
    lines += [f"## `{f}`", "", purpose, "", "| column | type / allowed values | meaning | source |", "|---|---|---|---|"]
    for c in cols(f):
        if c not in DESC:
            raise SystemExit(f"undocumented column: {f}:{c}")
        t, meaning, src = DESC[c]
        lines.append(f"| `{c}` | {t} | {meaning} | {src} |")
        seen.add(c)
    lines.append("")
open(os.path.join(D, "data_dictionary.md"), "w", encoding="utf-8").write("\n".join(lines))
print("documented columns:", len(seen))
