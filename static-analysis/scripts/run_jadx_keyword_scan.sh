#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_jadx_keyword_scan.sh APP_NAME [--clean] [--scope sources|all|resources]

Examples:
  scripts/run_jadx_keyword_scan.sh boss --clean
  scripts/run_jadx_keyword_scan.sh dazhongdianping --clean
  scripts/run_jadx_keyword_scan.sh renminribao --clean --scope all

Expected project layout:
  JADX_keyword_categories/grep_patterns/*.txt
  decompiled/<APP_NAME>/sources
  decompiled/<APP_NAME>/resources
  results/jadx_hits/<APP_NAME>

Output:
  sources scope:
    results/jadx_hits/<APP_NAME>/<category>.txt
    results/jadx_hits/<APP_NAME>/summary.tsv
  all/resources scope:
    results/jadx_hits/<APP_NAME>_<scope>/<category>.txt
    results/jadx_hits/<APP_NAME>_<scope>/summary.tsv
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

app="$1"
shift || true

clean=0
scope="sources"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --clean)
      clean=1
      shift
      ;;
    --scope)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --scope" >&2
        usage
        exit 1
      fi
      scope="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

root="$(pwd)"
patterns_dir="$root/JADX_keyword_categories/grep_patterns"
src_dir="$root/decompiled/$app/sources"

case "$scope" in
  sources)
    scan_dir="$src_dir"
    out_dir="$root/results/jadx_hits/$app"
    ;;
  all)
    scan_dir="$root/decompiled/$app"
    out_dir="$root/results/jadx_hits/${app}_all"
    ;;
  resources)
    scan_dir="$root/decompiled/$app/resources"
    out_dir="$root/results/jadx_hits/${app}_resources"
    ;;
  *)
    echo "Invalid --scope value: $scope" >&2
    usage
    exit 1
    ;;
esac

summary="$out_dir/summary.tsv"

if [[ ! -d "$patterns_dir" ]]; then
  echo "Missing pattern directory: $patterns_dir" >&2
  exit 1
fi

if [[ ! -d "$scan_dir" ]]; then
  echo "Missing JADX scan directory: $scan_dir" >&2
  exit 1
fi

mkdir -p "$out_dir"

if [[ "$clean" -eq 1 ]]; then
  find "$out_dir" -maxdepth 1 -type f \( -name '*.txt' -o -name 'summary.tsv' \) -delete
fi

if command -v rg >/dev/null 2>&1; then
  search_tool="rg"
else
  search_tool="grep"
fi

printf "category\tlines\toutput\n" > "$summary"

for pattern_file in "$patterns_dir"/*.txt; do
  category="$(basename "$pattern_file" .txt)"
  out_file="$out_dir/${category}.txt"

  if [[ "$search_tool" == "rg" ]]; then
    rg -n -F \
      -f "$pattern_file" \
      "$scan_dir" \
      -g '!**/R.java' \
      -g '!**/BuildConfig.java' \
      -g '!**/META-INF/**' \
      -g '!**/res/values*/public.xml' \
      -g '!**/res/values*/attrs.xml' \
      -g '!**/res/values-*/*.xml' \
      -g '!**/*.css' \
      -g '!**/*.less' \
      -g '!**/androidx/**' \
      -g '!**/kotlinx/**' \
      -g '!**/org/apache/commons/**' \
      -g '!**/org/webrtc/**' \
      -g '!**/org/alita/webrtc/**' \
      > "$out_file" || true
  else
    grep -RInF -f "$pattern_file" "$scan_dir" \
      | grep -vE '/R\.java:|/BuildConfig\.java:|/META-INF/|/res/values[^/]*/public\.xml:|/res/values[^/]*/attrs\.xml:|/res/values-[^/]*/[^/]+\.xml:|\.css:|\.less:|/androidx/|/kotlinx/|/org/apache/commons/|/org/webrtc/|/org/alita/webrtc/' \
      > "$out_file" || true
  fi

  lines="$(wc -l < "$out_file" | tr -d ' ')"
  printf "%s\t%s\t%s\n" "$category" "$lines" "$out_file" | tee -a "$summary"
done

echo "Done. Summary: $summary"
