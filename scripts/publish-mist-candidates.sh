#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Publish only the initial, explicitly requested candidates. Never force push.
set -euo pipefail
work="$(realpath "$1")"
: "${GH_TOKEN:?GH_PAT must be configured}"
owner=nobodyAtall-dev
branch=lineage-24
repos=(android_device_xiaomi_mist android_vendor_xiaomi_mist android_kernel_xiaomi_mist-prebuilt)
paths=(device/xiaomi/mist vendor/xiaomi/mist kernel/xiaomi/mist-prebuilt)
report="$work/reports/publication-status.txt"
: > "$report"
trap 'printf "Publication interrupted; inspect each destination before retrying.\n" >> "$report"' ERR
# Preflight ALL targets before writing any repository.
for i in "${!repos[@]}"; do
    repo="$owner/${repos[$i]}"
    dir="$work/android/${paths[$i]}"
    meta="$(gh api "repos/$repo")"
    jq -e '.permissions.push == true and .archived == false and .disabled == false' <<< "$meta" >/dev/null
    if (( i > 0 )); then
        jq -e '.private == true' <<< "$meta" >/dev/null || { echo "Refusing non-private binary repository $repo"; exit 1; }
    fi
    # Empty repositories normally have no refs and a 200 response with an empty branch array.
    branches="$(gh api "repos/$repo/branches?per_page=1")"
    jq -e 'length == 0' <<< "$branches" >/dev/null || { echo "Refusing existing branches in $repo"; exit 1; }
    test -d "$dir"
    test -z "$(find "$dir" -type f -size +104857599c -print -quit)"
    test ! -e "$dir/.git"
    if (( i == 0 )); then
        # Public device tree must not carry kernel or vendor binaries.
        test -z "$(find "$dir" -type f \( -name '*.ko' -o -name '*.so' -o -name '*.img' -o -name 'Image*' -o -name '*.apk' -o -name '*.jar' \) -print -quit)"
    fi
    printf "Preflight passed: %s\n" "$repo" >> "$report"
done
gh auth setup-git --hostname github.com
# Stage all three first, then publish. Each GitHub push is independent.
for i in "${!repos[@]}"; do
    dir="$work/android/${paths[$i]}"
    git -C "$dir" init -b "$branch"
    git -C "$dir" config user.name nobodyAtall-dev
    git -C "$dir" config user.email hashynaa@gmail.com
    git -C "$dir" add --all
    git -C "$dir" diff --cached --quiet && { echo "Empty candidate $dir"; exit 1; }
    git -C "$dir" commit -m "Initial Mist LineageOS 24 bring-up candidate"
    git -C "$dir" remote add origin "https://github.com/$owner/${repos[$i]}.git"
done
# Dependencies first; publish the device configuration last.
for i in 2 1 0; do
    repo="$owner/${repos[$i]}"
    dir="$work/android/${paths[$i]}"
    git -C "$dir" push -u origin "$branch"
    printf "Pushed %s %s %s\n" "$repo" "$branch" "$(git -C "$dir" rev-parse HEAD)" >> "$report"
    default="$(gh api "repos/$repo" --jq .default_branch)"
    if [[ "$default" != "$branch" ]]; then
        gh api --method PATCH "repos/$repo" -f default_branch="$branch" --silent
    fi
    test "$(gh api "repos/$repo" --jq .default_branch)" = "$branch"
    printf "Verified default branch: %s %s\n" "$repo" "$branch" >> "$report"
done
cat "$report"
