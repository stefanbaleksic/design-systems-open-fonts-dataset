#!/bin/sh
# Rebuild every file in data/ and site/ from the sources, then run the checks.
# Usage: sh scripts/run_all.sh   (needs Python 3.10+, fontTools, brotli, npm, git, curl)
set -eu
cd "$(dirname "$0")/.."
sh scripts/00_fetch_sources.sh
export DS_CSV=${DS_CSV:-${DS_REPO:-ds-src}/out/design_systems_v33.csv}
export GF_ROOT=${GF_ROOT:-gfonts}
python3 scripts/01_parse_google_metadata.py "$GF_ROOT"
python3 scripts/02_select_and_fetch.py "$GF_ROOT"
python3 scripts/03_measure_fonts.py "$GF_ROOT" data/google_selected_files.csv data/google_font_measures.csv
python3 scripts/04_scan_design_system_fonts.py
python3 scripts/05_measure_upstream.py
python3 scripts/11_check_specimen_urls.py
python3 scripts/06_build_tables.py
python3 scripts/07_validate_and_summarise.py
python3 scripts/08_sources.py
python3 scripts/09_data_dictionary.py
python3 scripts/10_build_site.py
python3 -m unittest discover -s tests -v
