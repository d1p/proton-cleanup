#!/usr/bin/env bash
set -euo pipefail

APP_ID="io.github.protoncleanup.ProtonCleanup"
RUNTIME_VERSION="24.08"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$ROOT_DIR/flatpak/io.github.protoncleanup.ProtonCleanup.yaml"
BUILD_DIR="$ROOT_DIR/.flatpak-builder"
REPO_DIR="$ROOT_DIR/dist/flatpak-repo"
BUNDLE_PATH="$ROOT_DIR/dist/proton-cleanup.flatpak"

if ! command -v flatpak-builder >/dev/null 2>&1; then
  echo "error: flatpak-builder is not installed." >&2
  echo "Install it first, for example:" >&2
  echo "  sudo apt install flatpak-builder" >&2
  exit 1
fi

if ! command -v flatpak >/dev/null 2>&1; then
  echo "error: flatpak is not installed." >&2
  exit 1
fi

mkdir -p "$ROOT_DIR/dist"

# Ensure required runtime/toolchain is available for the current user.
flatpak --user install -y flathub "org.freedesktop.Platform//$RUNTIME_VERSION"
flatpak --user install -y flathub "org.freedesktop.Sdk//$RUNTIME_VERSION"

flatpak-builder --user --force-clean --repo="$REPO_DIR" "$BUILD_DIR" "$MANIFEST"
flatpak build-bundle "$REPO_DIR" "$BUNDLE_PATH" "$APP_ID"

echo "Built Flatpak bundle: $BUNDLE_PATH"
echo "Install locally with: flatpak --user install --bundle -y $BUNDLE_PATH"
echo "Run with: flatpak run $APP_ID"
