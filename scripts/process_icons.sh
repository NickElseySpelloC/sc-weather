#!/usr/bin/env bash
: '=======================================================
Process icons by cropping their viewboxes to remove excess whitespace.

Also generates new icons with all black/dark-grey colors replaced by white, which is necessary for the dark theme.

Requires Python and UV to be installed
=========================================================='

# set -euo pipefail

# Setup the parameters
CROP_LEVEL=0.9
BASE_DIR="../src/weather_client/weather_icons"

# Find uv reliably (systemd often has a minimal PATH)
if command -v uv >/dev/null 2>&1; then
  UVCmd="$(command -v uv)"
elif [ -x "$HOME/.local/bin/uv" ]; then
  UVCmd="$HOME/.local/bin/uv"
else
  echo "[launcher] Error: 'uv' not found in PATH or at \$HOME/.local/bin/uv" >&2
  exit 1
fi

HomeDir="$(pwd)"
# make sure HomeDir is an absolute path
HomeDir="$(cd "$HomeDir" && pwd)"

# Change to the home directory so uv commands work correctly
cd "$HomeDir" || {
  echo "[launcher] Error: Cannot change to directory $HomeDir" >&2
  exit 1
}

echo "Generating white monochrome vesion of $BASE_DIR/meteocons/uncropped/monochrome-black "
read -p "Press Enter to continue or Ctrl+C to cancel..."
$UVCmd run convert_svg_to_white.py "$BASE_DIR/meteocons/uncropped/monochrome-black" "$BASE_DIR/meteocons/uncropped/monochrome-white" --include-static

echo "Generating white monochrome vesion of $BASE_DIR/weather-icons/uncropped/monochrome-black "
read -p "Press Enter to continue or Ctrl+C to cancel..."  
$UVCmd run convert_svg_to_white.py "$BASE_DIR/weather-icons/uncropped/monochrome-black" "$BASE_DIR/weather-icons/uncropped/monochrome-white" --include-static

echo "Generating cropped SVG viewboxes in $BASE_DIR/meteocons"
read -p "Press Enter to continue or Ctrl+C to cancel..."
$UVCmd run crop_svg_viewbox.py "$BASE_DIR/meteocons/uncropped" "$BASE_DIR/meteocons/cropped" --include-static --target-fill "$CROP_LEVEL"

echo "Generating cropped SVG viewboxes in $BASE_DIR/weather-icons"
read -p "Press Enter to continue or Ctrl+C to cancel..."
$UVCmd run crop_svg_viewbox.py "$BASE_DIR/weather-icons/uncropped" "$BASE_DIR/weather-icons/cropped" --include-static --target-fill "$CROP_LEVEL"
