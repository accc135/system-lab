#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_flowdroid_lab43_batch.sh [--profile min|core|extended] [--timeout SECONDS] [--skip-existing] [--with-os] [--apk-dir apks] [APP_NAME...] [-- EXTRA_FLOWDROID_ARGS...]

Examples:
  scripts/run_flowdroid_lab43_batch.sh --profile min --timeout 10800 --skip-existing
  scripts/run_flowdroid_lab43_batch.sh --profile min boss dazhongdianping qichezhijia
  JAVA_XMX=32g scripts/run_flowdroid_lab43_batch.sh --profile min --timeout 10800
  JAVA_XMX=64g scripts/run_flowdroid_lab43_batch.sh --profile min boss -- -al 8

Behavior:
  If APP_NAME is not given, run every *.apk in the APK directory.
  APP_NAME maps to apks/APP_NAME.apk.
  Results are written to results/flowdroid_lab43/APP_NAME_PROFILE.txt and .log.
  A batch summary is written to results/flowdroid_lab43/batch_PROFILE.tsv.
EOF
}

now() {
  date '+%Y-%m-%d %H:%M:%S'
}

hr() {
  printf '%*s\n' 72 '' | tr ' ' '-'
}

profile="min"
timeout_sec="10800"
skip_existing=0
with_os=0
apk_dir="apks"
apps=()
extra_args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      profile="$2"
      shift 2
      ;;
    --timeout)
      timeout_sec="$2"
      shift 2
      ;;
    --skip-existing)
      skip_existing=1
      shift
      ;;
    --with-os)
      with_os=1
      shift
      ;;
    --apk-dir)
      apk_dir="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      extra_args=("$@")
      break
      ;;
    *)
      apps+=("$1")
      shift
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
runner="$root/scripts/run_flowdroid_lab43.sh"
out_dir="$root/results/flowdroid_lab43"
summary="$out_dir/batch_${profile}.tsv"

if [[ ! -x "$runner" ]]; then
  if [[ -f "$runner" ]]; then
    chmod +x "$runner"
  else
    echo "Missing runner: $runner" >&2
    exit 1
  fi
fi

if [[ ${#apps[@]} -eq 0 ]]; then
  if [[ ! -d "$apk_dir" ]]; then
    echo "Missing APK directory: $apk_dir" >&2
    exit 1
  fi
  while IFS= read -r apk; do
    base="$(basename "$apk")"
    apps+=("${base%.apk}")
  done < <(find "$apk_dir" -maxdepth 1 -type f -name '*.apk' | sort)
fi

mkdir -p "$out_dir"
batch_start_epoch="$(date +%s)"
hr
echo "FlowDroid Lab4-3 batch run"
hr
echo "Batch start : $(now)"
echo "Profile     : $profile"
echo "Timeout     : ${timeout_sec}s"
echo "APK dir     : $apk_dir"
echo "App count   : ${#apps[@]}"
echo "With -os    : $([[ "$with_os" -eq 1 ]] && echo yes || echo no)"
if [[ ${#extra_args[@]} -gt 0 ]]; then
  printf 'Extra args  :'
  printf ' %q' "${extra_args[@]}"
  printf '\n'
fi
hr
printf "app\tprofile\tstatus\texit_code\tstart_time\tend_time\telapsed_seconds\toutput\tlog\n" > "$summary"

for app in "${apps[@]}"; do
  apk="$root/$apk_dir/${app}.apk"
  output="$out_dir/${app}_${profile}.txt"
  log="$out_dir/${app}_${profile}.log"
  app_start_time="$(now)"
  app_start_epoch="$(date +%s)"

  if [[ ! -f "$apk" ]]; then
    hr
    echo "[MISS] $app -> $apk"
    app_end_time="$(now)"
    app_end_epoch="$(date +%s)"
    printf "%s\t%s\tmissing_apk\t127\t%s\t%s\t%s\t%s\t%s\n" "$app" "$profile" "$app_start_time" "$app_end_time" "$((app_end_epoch - app_start_epoch))" "$output" "$log" >> "$summary"
    continue
  fi

  if [[ "$skip_existing" -eq 1 && -s "$output" ]]; then
    hr
    echo "[SKIP] $app already has output: $output"
    app_end_time="$(now)"
    app_end_epoch="$(date +%s)"
    printf "%s\t%s\tskipped\t0\t%s\t%s\t%s\t%s\t%s\n" "$app" "$profile" "$app_start_time" "$app_end_time" "$((app_end_epoch - app_start_epoch))" "$output" "$log" >> "$summary"
    continue
  fi

  hr
  echo "[RUN] $app ($profile) start=$(now)"
  echo "APK: $apk"
  echo "Output: $output"
  echo "Log: $log"
  set +e
  runner_args=("$app" --apk "$apk" --profile "$profile" --timeout "$timeout_sec")
  if [[ "$with_os" -eq 1 ]]; then
    runner_args+=(--with-os)
  fi

  if [[ ${#extra_args[@]} -gt 0 ]]; then
    "$runner" "${runner_args[@]}" -- "${extra_args[@]}"
  else
    "$runner" "${runner_args[@]}"
  fi
  code=$?
  set -e
  app_end_time="$(now)"
  app_end_epoch="$(date +%s)"
  elapsed="$((app_end_epoch - app_start_epoch))"

  if [[ "$code" -eq 0 ]]; then
    hr
    echo "[OK] $app end=$app_end_time elapsed=${elapsed}s"
    printf "%s\t%s\tok\t0\t%s\t%s\t%s\t%s\t%s\n" "$app" "$profile" "$app_start_time" "$app_end_time" "$elapsed" "$output" "$log" >> "$summary"
  elif [[ "$code" -eq 124 ]]; then
    hr
    echo "[TIMEOUT] $app end=$app_end_time elapsed=${elapsed}s"
    printf "%s\t%s\ttimeout\t%s\t%s\t%s\t%s\t%s\t%s\n" "$app" "$profile" "$code" "$app_start_time" "$app_end_time" "$elapsed" "$output" "$log" >> "$summary"
  else
    hr
    echo "[FAIL] $app exit=$code end=$app_end_time elapsed=${elapsed}s"
    printf "%s\t%s\tfailed\t%s\t%s\t%s\t%s\t%s\t%s\n" "$app" "$profile" "$code" "$app_start_time" "$app_end_time" "$elapsed" "$output" "$log" >> "$summary"
  fi
done

batch_end_epoch="$(date +%s)"
hr
echo "Batch end             : $(now)"
echo "Batch elapsed seconds : $((batch_end_epoch - batch_start_epoch))"
echo "Batch summary         : $summary"
hr
