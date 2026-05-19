#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH=""
SCHEME=""
CONFIGURATION="Release"
SIGNING_MODE="unsigned"
EXPORT_METHOD="development"
TEAM_ID=""
OUTPUT_DIR="build/ipa"
DERIVED_DATA="build/DerivedData"
ARCHIVE_PATH="build/archive/App.xcarchive"

usage() {
  cat <<'USAGE'
Build an iOS IPA from an Xcode project or workspace.

Usage:
  tools/build_ipa.sh [options]

Options:
  --project-path PATH       .xcodeproj or .xcworkspace path. Auto-detected when omitted.
  --scheme NAME             Xcode scheme. Auto-detected only when one shared scheme exists.
  --configuration NAME      Build configuration. Default: Release.
  --signing-mode MODE       unsigned, automatic, or manual. Default: unsigned.
  --export-method METHOD    development, ad-hoc, app-store, or enterprise. Default: development.
  --team-id TEAM_ID         Apple Developer Team ID for signed builds.
  --output-dir DIR          Directory where IPA files are written. Default: build/ipa.
  -h, --help                Show this help.

Unsigned mode creates a Payload/*.app zip IPA for testing workflows. It is not App Store/TestFlight ready.
Signed modes use xcodebuild archive/exportArchive and require valid signing configuration.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-path)
      PROJECT_PATH="$2"
      shift 2
      ;;
    --scheme)
      SCHEME="$2"
      shift 2
      ;;
    --configuration)
      CONFIGURATION="$2"
      shift 2
      ;;
    --signing-mode)
      SIGNING_MODE="$2"
      shift 2
      ;;
    --export-method)
      EXPORT_METHOD="$2"
      shift 2
      ;;
    --team-id)
      TEAM_ID="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$SIGNING_MODE" in
  unsigned|automatic|manual) ;;
  *)
    echo "Unsupported signing mode: $SIGNING_MODE" >&2
    exit 2
    ;;
esac

case "$EXPORT_METHOD" in
  development|ad-hoc|app-store|enterprise) ;;
  *)
    echo "Unsupported export method: $EXPORT_METHOD" >&2
    exit 2
    ;;
esac

find_project_path() {
  if [[ -n "$PROJECT_PATH" ]]; then
    if [[ ! -e "$PROJECT_PATH" ]]; then
      echo "Project path does not exist: $PROJECT_PATH" >&2
      exit 1
    fi
    printf '%s\n' "$PROJECT_PATH"
    return
  fi

  workspaces=()
  while IFS= read -r workspace; do
    workspaces+=("$workspace")
  done < <(find . -path './.git' -prune -o -name '*.xcworkspace' -print | sort)

  projects=()
  while IFS= read -r project; do
    projects+=("$project")
  done < <(find . -path './.git' -prune -o -name '*.xcodeproj' -print | sort)

  if [[ ${#workspaces[@]} -gt 0 ]]; then
    printf '%s\n' "${workspaces[0]}"
    return
  fi

  if [[ ${#projects[@]} -gt 0 ]]; then
    printf '%s\n' "${projects[0]}"
    return
  fi

  echo "No .xcworkspace or .xcodeproj found. Add the iOS app source or pass --project-path." >&2
  exit 1
}

xcode_container_args() {
  local path="$1"
  case "$path" in
    *.xcworkspace)
      printf '%s\n%s\n' "-workspace" "$path"
      ;;
    *.xcodeproj)
      printf '%s\n%s\n' "-project" "$path"
      ;;
    *)
      echo "Project path must end with .xcworkspace or .xcodeproj: $path" >&2
      exit 1
      ;;
  esac
}

PROJECT_PATH="$(find_project_path)"
CONTAINER_ARGS=()
while IFS= read -r arg; do
  CONTAINER_ARGS+=("$arg")
done < <(xcode_container_args "$PROJECT_PATH")

if [[ -z "$SCHEME" ]]; then
  echo "No scheme was provided. Available schemes:" >&2
  xcodebuild "${CONTAINER_ARGS[@]}" -list >&2
  echo "Pass --scheme or the workflow's scheme input." >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
rm -rf "$DERIVED_DATA" "$ARCHIVE_PATH"

if [[ "$SIGNING_MODE" == "unsigned" ]]; then
  echo "Building unsigned iphoneos app for scheme '$SCHEME'..."
  xcodebuild \
    "${CONTAINER_ARGS[@]}" \
    -scheme "$SCHEME" \
    -configuration "$CONFIGURATION" \
    -sdk iphoneos \
    -derivedDataPath "$DERIVED_DATA" \
    CODE_SIGNING_ALLOWED=NO \
    clean build

  APP_PATH="$(find "$DERIVED_DATA/Build/Products/$CONFIGURATION-iphoneos" -maxdepth 1 -name '*.app' -print -quit)"
  if [[ -z "$APP_PATH" ]]; then
    echo "Build succeeded but no .app was found in $DERIVED_DATA/Build/Products/$CONFIGURATION-iphoneos." >&2
    exit 1
  fi

  PAYLOAD_DIR="$OUTPUT_DIR/Payload"
  rm -rf "$PAYLOAD_DIR"
  mkdir -p "$PAYLOAD_DIR"
  cp -R "$APP_PATH" "$PAYLOAD_DIR/"
  IPA_PATH="$OUTPUT_DIR/${SCHEME// /-}-unsigned.ipa"
  rm -f "$IPA_PATH"
  (cd "$OUTPUT_DIR" && zip -qry "$(basename "$IPA_PATH")" Payload)
  rm -rf "$PAYLOAD_DIR"
  echo "Created unsigned IPA: $IPA_PATH"
  exit 0
fi

SIGNING_ARGS=()
if [[ "$SIGNING_MODE" == "automatic" ]]; then
  SIGNING_ARGS+=("CODE_SIGN_STYLE=Automatic" "-allowProvisioningUpdates")
else
  SIGNING_ARGS+=("CODE_SIGN_STYLE=Manual")
fi

if [[ -n "$TEAM_ID" ]]; then
  SIGNING_ARGS+=("DEVELOPMENT_TEAM=$TEAM_ID")
fi

xcodebuild \
  "${CONTAINER_ARGS[@]}" \
  -scheme "$SCHEME" \
  -configuration "$CONFIGURATION" \
  -sdk iphoneos \
  -archivePath "$ARCHIVE_PATH" \
  "${SIGNING_ARGS[@]}" \
  clean archive

EXPORT_OPTIONS="$OUTPUT_DIR/ExportOptions.plist"
cat > "$EXPORT_OPTIONS" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>method</key>
  <string>$EXPORT_METHOD</string>
  <key>signingStyle</key>
  <string>$SIGNING_MODE</string>
  <key>stripSwiftSymbols</key>
  <true/>
  <key>compileBitcode</key>
  <false/>
</dict>
</plist>
PLIST

EXPORT_ARGS=()
if [[ "$SIGNING_MODE" == "automatic" ]]; then
  EXPORT_ARGS+=("-allowProvisioningUpdates")
fi

xcodebuild \
  -exportArchive \
  -archivePath "$ARCHIVE_PATH" \
  -exportOptionsPlist "$EXPORT_OPTIONS" \
  -exportPath "$OUTPUT_DIR" \
  "${EXPORT_ARGS[@]}"

if ! compgen -G "$OUTPUT_DIR/*.ipa" > /dev/null; then
  echo "Export completed but no IPA was produced in $OUTPUT_DIR." >&2
  exit 1
fi

printf 'Created signed IPA(s):\n'
find "$OUTPUT_DIR" -maxdepth 1 -name '*.ipa' -print
