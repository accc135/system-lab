#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_flowdroid_lab43.sh APP_NAME [--apk apks/APP.apk] [--profile min|core|extended] [--timeout SECONDS] [--with-os] [--dry-run] [-- EXTRA_FLOWDROID_ARGS...]

Examples:
  scripts/run_flowdroid_lab43.sh boss --profile min --timeout 7200
  scripts/run_flowdroid_lab43.sh boss --profile min --timeout 7200 --with-os
  scripts/run_flowdroid_lab43.sh boss --profile core --timeout 7200
  scripts/run_flowdroid_lab43.sh boss --apk apks/boss.apk --profile extended --timeout 10800
  JAVA_XMX=32g scripts/run_flowdroid_lab43.sh boss --profile min -- -ns

Expected layout:
  apks/<APP_NAME>.apk
  tools/flowdroid/soot-infoflow-cmd-jar-with-dependencies.jar
  tools/android-sdk/platforms
  config/SourcesAndSinks_lab4_3_min.txt
  config/SourcesAndSinks_lab4_3_core.txt
  config/SourcesAndSinks_lab4_3_extended.txt

Output:
  results/flowdroid_lab43/<APP_NAME>_<profile>.txt
  results/flowdroid_lab43/<APP_NAME>_<profile>.log
EOF
}

now() {
  date '+%Y-%m-%d %H:%M:%S'
}

hr() {
  printf '%*s\n' 72 '' | tr ' ' '-'
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

app="$1"
shift

profile="min"
apk=""
timeout_sec="7200"
dry_run=0
with_os=0
extra_args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apk)
      apk="$2"
      shift 2
      ;;
    --profile)
      profile="$2"
      shift 2
      ;;
    --timeout)
      timeout_sec="$2"
      shift 2
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    --with-os)
      with_os=1
      shift
      ;;
    --)
      shift
      extra_args=("$@")
      break
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

case "$profile" in
  min|core|extended) ;;
  *)
    echo "Invalid profile: $profile" >&2
    exit 1
    ;;
esac

root="$(pwd)"
jar="${FLOWDROID_JAR:-$root/tools/flowdroid/soot-infoflow-cmd-jar-with-dependencies.jar}"
platforms="${ANDROID_PLATFORMS:-$root/tools/android-sdk/platforms}"
sources_sinks="$root/config/SourcesAndSinks_lab4_3_${profile}.txt"
if [[ ! -f "$sources_sinks" ]]; then
  sources_sinks="$root/SourcesAndSinks_lab4_3_${profile}.txt"
fi
apk="${apk:-$root/apks/${app}.apk}"
out_dir="$root/results/flowdroid_lab43"
out_file="$out_dir/${app}_${profile}.txt"
log_file="$out_dir/${app}_${profile}.log"
java_xmx="${JAVA_XMX:-24g}"

if [[ ! -f "$jar" ]]; then
  echo "Missing FlowDroid jar: $jar" >&2
  exit 1
fi
if [[ ! -d "$platforms" ]]; then
  echo "Missing Android platforms directory: $platforms" >&2
  exit 1
fi
if [[ ! -f "$sources_sinks" ]]; then
  echo "Missing SourcesAndSinks file: $sources_sinks" >&2
  exit 1
fi
if [[ ! -f "$apk" ]]; then
  echo "Missing APK: $apk" >&2
  exit 1
fi

mkdir -p "$out_dir"

cmd=(
  timeout "${timeout_sec}s"
  java "-Xmx${java_xmx}"
  -jar "$jar"
  -a "$apk"
  -p "$platforms"
  -s "$sources_sinks"
  -o "$out_file"
)

if [[ "$with_os" -eq 1 ]]; then
  cmd+=(-os)
fi

if [[ ${#extra_args[@]} -gt 0 ]]; then
  cmd+=("${extra_args[@]}")
fi

hr
printf 'FlowDroid Lab4-3 single run\n'
hr
printf 'App              : %s\n' "$app"
printf 'APK              : %s\n' "$apk"
printf 'Profile          : %s\n' "$profile"
printf 'SourcesAndSinks  : %s\n' "$sources_sinks"
printf 'Output           : %s\n' "$out_file"
printf 'Log              : %s\n' "$log_file"
printf 'With -os         : %s\n' "$([[ "$with_os" -eq 1 ]] && echo yes || echo no)"
printf 'Start time       : %s\n' "$(now)"
hr
printf 'Command:'
printf ' %q' "${cmd[@]}"
printf '\n'
hr

if [[ "$dry_run" -eq 1 ]]; then
  printf 'Dry run only. FlowDroid was not started.\n'
  hr
  exit 0
fi

start_epoch="$(date +%s)"
set +e
"${cmd[@]}" > "$log_file" 2>&1
code=$?
set -e
end_epoch="$(date +%s)"
elapsed="$((end_epoch - start_epoch))"

if grep -Eq "Exception during data flow analysis|There were exceptions during IFDS analysis|Worker thread execution failed" "$log_file"; then
  echo "FlowDroid analysis exception detected. See log: $log_file" >&2
  code=98
fi

hr
echo "Done."
echo "Output          : $out_file"
echo "Log             : $log_file"
echo "End time        : $(now)"
echo "Elapsed seconds : $elapsed"
hr
exit "$code"
