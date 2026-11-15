#!/usr/bin/env bash
# Extract the 55 MILEPOST static features of C programs with the cMeta task
# extract-milepost-features-legacy - Linux and macOS (Docker or Podman running; or natively on
# Linux amd64 with glibc 2.38+ through --runtime-root).
#
#   bash _run.sh                    the two examples of this note; the reference one is checked
#   bash _run.sh my.c other.c       your programs (C89 / GNU89, at most 64 KiB)
#   bash _run.sh --runtime-root=$HOME/milepost-runtime      natively on Linux, no container
#   bash _run.sh --engine=podman my.c                       any option starting with -- goes to the task
#
# The results go to results/ beside this script (MILEPOST_RESULTS=<folder> for another one).
# The first run on a machine downloads the capsules from https://doi.org/10.5281/zenodo.24246695.
# Written for bash 3.2 too (macOS).

here=$(cd "$(dirname "$0")" && pwd)
results=${MILEPOST_RESULTS:-$here/results}
task=extract-milepost-features-legacy,4e719bc8239d4ece
reference=$here/reference/example.c

options=()
programs=()
for arg in "$@"; do
  case "$arg" in
    --*) options+=("$arg") ;;
    *) programs+=("$arg") ;;
  esac
done
if [ ${#programs[@]} -eq 0 ]; then
  programs=("$here/examples/vector-stats.c" "$reference")
fi

mkdir -p "$results" || exit 1
status=0

for program in "${programs[@]}"; do
  name=$(basename "$program" .c)
  echo
  echo "=== $program -> $results/$name.features.json"
  cx task run "$task" --source-file="$program" --output-file="$results/$name.features.json" ${options[@]+"${options[@]}"} -q || status=1
done

# The reference program must give the values extracted on 2026-10-20 with the original installation.
for program in "${programs[@]}"; do
  if [ "$program" = "$reference" ]; then
    echo
    python3 "$here/compare.py" "$results/example.features.json" "$here/reference/example.features.json" || status=1
  fi
done

exit $status
