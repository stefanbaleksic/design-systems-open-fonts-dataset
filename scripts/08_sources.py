"""Write data/sources.csv: every external source used, with the commit, tag, release or hash that was read.
Values are read from the working clones and files on the collection machine (paths below)."""
import csv, os, subprocess, hashlib
FD = os.path.join(os.path.dirname(__file__), "..")
D = os.path.join(FD, "data")
TODAY = "2026-11-18"
def git_head(path):
    return subprocess.run(["git", "-C", path, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()
up = list(csv.DictReader(open(os.path.join(D, "upstream_font_measures.csv"), encoding="utf-8")))
rows = [
 {"source_id": "google-fonts-repository", "source_type": "git repository (mirror of Google Fonts metadata and font files)",
  "url": "https://github.com/google/fonts", "version_or_ref": git_head(os.environ.get("GF_ROOT", "gfonts")), "retrieved_on": TODAY,
  "integrity": "git commit (above)", "used_for": "METADATA.pb for 2042 families; one representative font file each (sparse checkout)",
  "licence_of_source": "per-family licence in METADATA.pb (OFL-1.1, Apache-2.0, UFL-1.0)"},
 {"source_id": "inter-release-4.1", "source_type": "original release archive (author's GitHub release)",
  "url": "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip", "version_or_ref": "v4.1",
  "retrieved_on": TODAY, "integrity": "sha256 9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e",
  "used_for": "Inter: InterVariable.ttf measured (variable, opsz and wght axes); formats listed from the archive",
  "licence_of_source": "SIL Open Font License 1.1 (LICENSE.txt in the archive)"},
 {"source_id": "inter-repository", "source_type": "git repository (author's source)",
  "url": "https://github.com/rsms/inter", "version_or_ref": git_head(os.environ.get("INTER_SRC", "inter-src")), "retrieved_on": TODAY,
  "integrity": "git commit (above); version.txt in this commit reads 4.2, the archive used is 4.1",
  "used_for": "checked for licence and version; not used as a font file source in this release",
  "licence_of_source": "SIL Open Font License 1.1"},
 {"source_id": "design-systems-dataset-v33", "source_type": "dataset (same author; Zenodo DOI 10.5281/zenodo.24248035)",
  "url": "https://github.com/stefanbaleksic/design-systems-dataset", "version_or_ref": git_head(os.environ.get("DS_REPO", "ds-src")),
  "retrieved_on": TODAY, "integrity": "git commit (above); out/design_systems_v33.csv",
  "used_for": "list of 345 design systems (slug, organisation); 143 with an npm package and a pinned version (npm_latest_version)",
  "licence_of_source": "CC BY 4.0 (the design-systems dataset)"},
 {"source_id": "npm-registry", "source_type": "package registry (npm pack of pinned versions)",
  "url": "https://registry.npmjs.org/", "version_or_ref": "pinned versions listed in design_system_font_packages.csv",
  "retrieved_on": TODAY, "integrity": "sha256 of each tarball in design_system_font_packages.csv",
  "used_for": "CSS/JS/TS text scanned for font-family declarations (no code was executed)",
  "licence_of_source": "licence of each package (not redistributed in this dataset; only declarations are)"},
]
name_of = {"IBM/plex": "plex", "github/mona-sans": "mona-sans", "vercel/geist-font": "geist-font",
           "microsoft/cascadia-code": "cascadia-code", "source-foundry/Hack": "Hack", "adobe-fonts/source-sans": "source-sans",
           "JetBrains/JetBrainsMono": "jetbrains-mono"}
seen = set()
for m in up:
    url = m["repository_url"]
    if url in seen or m["repo_folder"] == "inter-release-4.1":
        continue
    seen.add(url)
    npm = m["repo_folder"].startswith("npm-")
    rows.append({"source_id": "upstream-" + m["repo_folder"].lower(), "source_type": "npm package" if npm else "original repository (font designer or foundry)",
                 "url": url, "version_or_ref": m["repository_commit"], "retrieved_on": TODAY,
                 "integrity": "git commit (above); shallow clone (depth 1)",
                 "used_for": "families measured from the repository (see upstream_font_measures.csv); licence file read",
                 "licence_of_source": m["repo_licence_detected"]})
with open(os.path.join(D, "sources.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("sources:", len(rows))
