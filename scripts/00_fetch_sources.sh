#!/bin/sh
# Fetch every external source named in data/sources.csv into the working folder.
# Idempotent: an existing clone or archive is kept. Needs git, curl, sha256sum.
# Set GF_ROOT, UPSTREAM_ROOT, INTER_DIR, INTER_SRC, DS_REPO to use other locations.
set -eu
GF_ROOT=${GF_ROOT:-gfonts}
UPSTREAM_ROOT=${UPSTREAM_ROOT:-upstream}
INTER_DIR=${INTER_DIR:-inter-release/x}
INTER_SRC=${INTER_SRC:-inter-src}
DS_REPO=${DS_REPO:-ds-src}
mkdir -p "$UPSTREAM_ROOT" inter-release

# 1. Google Fonts metadata and font files (sparse, metadata first; script 02 adds the font files)
if [ ! -d "$GF_ROOT/.git" ]; then
  git clone --filter=blob:none --no-checkout --depth 1 https://github.com/google/fonts "$GF_ROOT"
  git -C "$GF_ROOT" sparse-checkout init --no-cone
  git -C "$GF_ROOT" sparse-checkout set --no-cone '/ofl/*/METADATA.pb' '/apache/*/METADATA.pb' '/ufl/*/METADATA.pb'
  git -C "$GF_ROOT" checkout
fi

# 2. Original repositories (shallow)
for repo in IBM/plex github/mona-sans vercel/geist-font microsoft/cascadia-code source-foundry/Hack adobe-fonts/source-sans JetBrains/JetBrainsMono githubnext/monaspace rubjo/victor-mono intel/intel-one-mono Lilex/lilex subframe7536/maple-font rektdeckard/departure-mono adobe-fonts/source-serif cormullion/juliamono madmalik/mononoki stipub/stixfonts silnrsi/font-doulos silnrsi/font-andika silnrsi/font-awami Outfitio/Outfit-Fonts theleagueof/junction theleagueof/chunk RedHatOfficial/RedHatFont RedHatOfficial/Overpass uswds/public-sans mozilla/Fira tonsky/FiraCode silnrsi/font-gentium silnrsi/font-charis silnrsi/font-padauk silnrsi/font-abyssinica liberationfonts/liberation-fonts adobe-fonts/source-code-pro googlefonts/atkinson-hyperlegible-next googlefonts/atkinson-hyperlegible googlefonts/lexend arrowtype/recursive Instrument/instrument-sans weiweihuanghuang/Work-Sans; do
  name=$(basename "$repo")
  [ "$name" = "JetBrainsMono" ] && name=jetbrains-mono
  [ "$name" = "plex" ] && name=plex
  [ "$name" = "Lilex" ] && name=lilex
  [ "$name" = "maple-font" ] && name=maple-font
  [ -d "$UPSTREAM_ROOT/$name" ] || git clone -q --depth 1 "https://github.com/$repo" "$UPSTREAM_ROOT/$name"
done

# 2b. Fontsource npm packages (packaged copies of Iosevka and Commit Mono, OFL-1.1; latin subset only)
NPM_ROOT=${NPM_ROOT:-npm}
for spec in fontsource-iosevka:@fontsource/iosevka@5.3.0 fontsource-commit-mono:@fontsource/commit-mono@5.3.0 dejavu:dejavu-fonts-ttf@2.37.3; do
  dir=${spec%%:*}; pkg=${spec#*:}
  if [ ! -d "$NPM_ROOT/$dir/package" ]; then
    mkdir -p "$NPM_ROOT/$dir" && (cd "$NPM_ROOT/$dir" && npm pack "$pkg" --silent >/dev/null && tar xzf ./*.tgz)
  fi
done

# 3. Inter: release archive 4.1 from the author's GitHub release, checked against its SHA-256
if [ ! -d "$INTER_DIR" ]; then
  curl -sSL -o inter-release/Inter-4.1.zip "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip"
  echo "9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e  inter-release/Inter-4.1.zip" | sha256sum -c -
  mkdir -p "$INTER_DIR" && unzip -q inter-release/Inter-4.1.zip -d "$INTER_DIR"
fi
[ -d "$INTER_SRC" ] || git clone -q --depth 1 https://github.com/rsms/inter "$INTER_SRC"

# 4. The design-systems dataset v33 (list of systems and pinned npm versions)
[ -d "$DS_REPO" ] || git clone -q --depth 1 https://github.com/stefanbaleksic/design-systems-dataset "$DS_REPO"
echo "sources ready"
