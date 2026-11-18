# Design System Fonts Dataset

Font families used by public design systems, and open-licence font families (Google Fonts and original
foundry repositories, Inter included), with licence, provider, source, variable-font status, OpenType
figure and ligature features, Serbian character coverage and file hashes.

**Version 1.0.0 · measured 2026-11-18 · not yet published (no DOI)**
Data: CC BY 4.0 · Scripts: MIT · Author: Stefan B. Aleksić · ORCID [0009-0009-1537-296X](https://orcid.org/0009-0009-1537-296X)

The data are metadata and facts. **No font files are included.** Each family's licence is recorded in the
data, and it belongs to that family's authors.

## Start here

| file | what it is |
|---|---|
| [`docs/index.html`](docs/index.html), live at https://stefanbaleksic.github.io/design-systems-fonts/ | single-page viewer: filter, search, detail view for every family and every design-system declaration |
| [`data/fonts_catalogue.csv`](data/fonts_catalogue.csv) | **main table**: one row per font family (2,144 open-licence families plus 116 families seen only in design systems) |
| [`data/design_system_fonts.csv`](data/design_system_fonts.csv) | design system × declared family, linked to the catalogue by `font_id` and to the design-systems dataset by `slug` |
| [`data/data_dictionary.md`](data/data_dictionary.md) | every column: meaning, allowed values, source |
| [`data/validation_report.md`](data/validation_report.md) | automatic checks, duplicate counts and summary statistics for this version |
| [`data/duplicates_removed.csv`](data/duplicates_removed.csv) | every row that was not added as a separate family, and the row kept instead |
| [`data/sources.csv`](data/sources.csv) | every external source read: commit, release or hash, licence |
| [`data/specimen_url_checks.csv`](data/specimen_url_checks.csv) | HTTP result of the Google Fonts specimen page for each of the 2,042 families |
| [`data/design_system_font_packages.csv`](data/design_system_font_packages.csv) | the 143 npm packages scanned: pinned version, tarball SHA-256, files read |
| [`data/design_system_font_declarations.csv`](data/design_system_font_declarations.csv) | raw declarations per package, with the role given to each (kept for audit) |

## Scope

| part | count | what it covers |
|---|---|---|
| Google Fonts families | 2,042 | every family in the `ofl`, `apache` and `ufl` folders of `google/fonts` at the commit in `sources.csv` |
| Original repositories | 148 families | forty repositories (IBM Plex, Mona Sans, Geist, Source Sans, Source Serif, Hack, Cascadia Code, JetBrains Mono, Monaspace, Victor Mono, Intel One Mono, Lilex, Maple Mono, Departure Mono, JuliaMono, Mononoki, STIX Two, SIL Doulos, Andika, Awami Nastaliq, Outfit, Junction, ChunkFive, Red Hat, Overpass, Public Sans, Fira, Fira Code, Gentium, Charis, Padauk, Abyssinica, Source Code Pro, Atkinson Hyperlegible, Lexend, Recursive, Instrument Sans, Work Sans) and Inter from the author's release archive (4.1) |
| npm packages | 9 families | Iosevka and Commit Mono from their Fontsource packages (OFL-1.1, latin subset only; see Limits), and DejaVu from the `dejavu-fonts-ttf` package (Bitstream Vera licence) |
| Design systems | 143 with an npm package, of 345 in the design-systems dataset v33 | the package text is scanned for font-family declarations |

Inter is required in this release and is taken from the original release (rsms/inter v4.1). Google's copy of
Inter is recorded as the same family (`also_on_google_fonts = yes`). Monaspace is taken from its repository's
static and variable builds; its Nerd Font and Frozen derivatives are not separate families.

## Results (summary)

From `data/summary_statistics.csv`. Percentages are among the open-licence families whose file was measured (the denominator is shown in `summary_statistics.csv`).

- 2,144 open-licence families: 2,088 OFL-1.1, 42 Apache-2.0, 8 Bitstream Vera, 5 UFL-1.0, 1 MIT.
- 28.1% are variable fonts (an `fvar` table is present).
- 17.3% have tabular figures (`tnum`), 13.5% a slashed-zero feature (`zero`), 12.1% oldstyle figures (`onum`),
  10.7% lining figures (`lnum`), and 47.9% standard ligatures (`liga`).
- 13.8% have every Serbian Cyrillic letter, and 70.4% have every Serbian Latin letter with diacritics. The two
  npm-packaged families are not measured for these letters, so they are left out of those percentages.
- Of the 2,042 Google Fonts specimen pages checked, 1,955 return 200 and 87 return 404 (see
  `specimen_url_checks.csv`). A 404 means fonts.google.com has no specimen page under that name.
- 95 of the 143 scanned design systems declare at least one brand or custom font; 48 do not. For 48 systems
  the package has only system or browser fallbacks, or no font declaration. This describes the package, not
  the live site.

## Method

**Fonts.** One representative file per family is measured with fontTools: variable file first, then Regular,
then TTF or OTF. Features are read from the GSUB and GPOS feature lists. A family counts as having a feature
only when the tag is present in the font. Google Fonts metadata comes from `METADATA.pb`.

**Source-first.** When an original repository and Google Fonts both publish a family, the original repository
row is kept, and the Google row is listed in `duplicates_removed.csv`. Within a repository, a variable build
is kept over a static one. Normalised names are compared (case, spaces, and variable suffixes such as `VF`).

**Design-system usage.** `npm pack` fetches each package at the version pinned in the design-systems dataset.
The CSS, SCSS, JS, TS and JSON text is read (no code is run). Each `font-family` value, `fontFamily` key, and
font custom property is split into names, generic families are dropped, and the rest are classified:
`brand_or_custom`, `os_or_browser_fallback` (Arial, Segoe UI, emoji faces...), or `not_a_font_name`
(identifiers and CSS tokens, kept so that the filter can be audited).

**Specimen pages.** Script 11 requests each Google Fonts specimen URL once and stores the status. Script 06
copies the status into `google_fonts_specimen_http_status`.

**Open numbers.** OpenType has no tag named "open numbers". The column `feat_onum` (oldstyle figures) is used
for it, as confirmed by the author.

**Commercial.** `licence_class` separates open families from vendor faces recognised by name only
(`proprietary_name_lookup`). `commercial_status` and `commercial_use_allowed` read from the licence code.

## Reproduce

```sh
pip install -r requirements.txt        # fonttools, brotli
sh scripts/run_all.sh                  # fetches the sources, rebuilds data/ and docs/, runs the tests
```

`scripts/00_fetch_sources.sh` clones or downloads every source named in `data/sources.csv`. The Inter archive is
checked against its SHA-256. Locations can be changed with `GF_ROOT`, `UPSTREAM_ROOT`, `INTER_DIR`, `INTER_SRC`,
`DS_REPO`, `NPM_CACHE` and `DS_CSV`.

The whole pipeline takes about a minute once the sources are in place. The specimen check needs network access;
set `SKIP_URL_CHECK=1` to keep the stored results instead. The GitHub workflow in `.github/workflows/reproduce.yml`
runs the same script and fails if a rebuilt file differs from the committed one.

Tests: `python3 -m unittest discover -s tests -v` checks unique identifiers, no duplicate families after
normalisation, Inter's required values, the licence closed set, the variable flag against the axes, the
arithmetic of the duplicate count, every declaration's design-system slug against the design-systems dataset,
every package hash, that every released column is documented, that each Google Fonts family has a specimen check,
that derived Nerd Font and Frozen builds are not counted as families, and that the viewer in `docs/` is present and
small enough to publish. The tests need `DS_CSV` (set by `run_all.sh`). There are 23 tests.

## Licence and citation

Data: CC BY 4.0 (`LICENSE.md`). Scripts and tests: MIT. Cite with [`CITATION.cff`](CITATION.cff); the Zenodo
metadata is in [`.zenodo.json`](.zenodo.json). The design-systems dataset that supplies the package list is
CC BY 4.0 (Zenodo 10.5281/zenodo.24248035).

## Limits (read before use)

- **Coverage.** The open-licence catalogue is the Google Fonts set plus 40 repositories (foundries, SIL, The League of
  Moveable Type, Outfit and others), Inter, and three npm packages. Where a family is on both Google Fonts and a repository, the
  repository is used (source first), so Charis SIL, Andika, Outfit, Gentium, Recursive and Lexend now come from their repositories. Recursive test and proof builds in `docs/` and `src/` are excluded.
- **Not included, and why.** Adobe Fonts (the Creative Cloud catalogue) is licensed for use inside Adobe's services and is
  not an open-licence set, so it is not in this dataset; the open Adobe repositories (Source Sans, Source Serif, Source
  Code Pro) are. Sarasa Gothic and Source Han have no font files in their repositories (they ship as release archives).
  Hasklig is Source Code Pro with added ligatures, so it is treated as a derivative and left out. The Liberation repository has no built font files, so it adds no rows.
  It is not every open font. Other open foundries are missing from this version.
- **Iosevka and Commit Mono** are measured from the latin subset that Fontsource ships (`iosevka-latin-400-normal.woff2`).
  A full Iosevka build from source was attempted but the environment refused the build step, so the full Iosevka
  family is not in this version. Their Cyrillic and Serbian letter coverage is `not_measured`, and the feature flags
  come from the Latin subset only.
- **Weights.** `variable_weight_range` gives the wght axis of a variable font (for example 100-900). `weight_class`
  gives the static weight of the one file measured for each family (OS/2 usWeightClass). Static families with
  several weights are not listed weight by weight; use the family's files for that.
- **Design systems.** Only the 143 systems that publish an npm package are scanned. The other 202 systems of the
  design-systems dataset have no font data here.
- **Declarations, not rendering.** A declared family is what the package text names. Some declarations are
  fallbacks, icon fonts, or noise that the rules did not catch. `occurrences` and `declaration_role` show this.
  Dynamic or runtime-loaded fonts are not seen.
- **Licence text.** Google Fonts licences come from `METADATA.pb`. Original-repository licences come from a text
  match on the repository's licence file. Vendor faces (`proprietary_name_lookup`) were recognised by name only.
  Nothing here is legal advice.
- **One file per family.** Features and glyph coverage come from one representative file, not from every style,
  so a family may have a feature only in some styles. `files_in_family` gives the size of each family.
- **Width and optical instances.** Some families are split into several rows (for example Mona Sans Condensed,
  Mona Sans Display). They are kept as separate families because each is a separate font file.
- **Aliases.** A small manual list maps old or shortened names (Source Sans Pro to Source Sans 3, for example).
  Each use is recorded in `alias_applied`.
- **Metadata not checked.** Designer, category and date for original-repository families are `not_checked`.
  The specimen URL is built from the family name; its HTTP status is recorded, and 87 Google families return 404.
- **Cascadia Code** is measured from the VTT source file in its repository (the release build is not in the repository).
- **Inter.** The repository's `version.txt` reads 4.2; the archive used is the 4.1 release, which is what was measured.

## Changes

- **1.0.0.** First version. Google Fonts (2,042 families), 7 original repositories, Inter from its release,
  143 design-system npm packages.
- **1.0.0, second pass.** Added Monaspace, Victor Mono and Intel One Mono (ten repositories in all).
  Added the Google Fonts specimen HTTP check (`google_fonts_specimen_http_status`), a GitHub workflow that rebuilds
  and compares outputs, quality tests, and the viewer moved to `docs/` for GitHub Pages. "Open numbers" is confirmed
  as `onum`.
- **1.0.0, fourth pass.** Added `variable_weight_range`, `weight_class` and `subfamily_name` (from the measured file).
  23 tests.
- **1.0.0, third pass.** Added Lilex, Maple Mono, Departure Mono (13 repositories) and Iosevka and Commit Mono from
  Fontsource npm packages. Percentages now exclude values that were not measured. The licence detector accepts
  "SIL Open Font License, Version 1.1" (with a comma), which had been missed.
- **1.0.0, fifth pass.** Added JuliaMono, Mononoki, STIX Two (repository), Source Serif (repository: Display,
  Caption, SmText and Subhead families) and DejaVu (npm `dejavu-fonts-ttf`, Bitstream Vera licence, 7 families).
  Left out Sarasa Gothic and Hasklig (see Coverage). The licence detector checks Bitstream Vera before MIT, because
  DejaVu's licence file also contains MIT-style text.
- **1.0.0, sixth pass.** Added SIL Doulos, Andika, Awami Nastaliq (silnrsi), Outfit (Outfitio), Junction and ChunkFive
  (The League of Moveable Type). The licence detector also reads licence files named after the licence, such as
  "Open Font License.markdown", which the earlier name rule missed.
- **1.0.0, seventh pass.** Added Red Hat, Overpass, Public Sans, Fira, Fira Code, Gentium, Charis, Padauk, Abyssinica,
  Source Code Pro, Atkinson Hyperlegible, Lexend, Recursive, Instrument Sans and Work Sans from their repositories. Recursive
  test and proof builds are excluded. The weight check accepts the OpenType range 1-1000 (Recursive Sans Linear A has 1000).
  Adobe Fonts stay out (not an open licence); Liberation adds no rows.
