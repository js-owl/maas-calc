#!/usr/bin/env bash
set +e

cleanup_app_images() {
  local repo="$1"
  local current_tag="${2:-}"
  [ -z "$repo" ] && return 0
  local keep=""
  while IFS= read -r line; do keep="$keep $line"; done < <(
    docker images "$repo" --format '{{.Tag}} {{.CreatedAt}}' 2>/dev/null \
      | grep -E '^(v|dev-v)[0-9]' | sort -k2 -r | head -2 | awk '{print $1}'
  )
  for meta in latest dev-latest; do
    docker images "$repo" --format '{{.Tag}}' 2>/dev/null | grep -qx "$meta" && keep="$keep $meta"
  done
  [ -n "$current_tag" ] && keep="$keep $current_tag"
  while IFS= read -r tag; do
    [ -z "$tag" ] && continue
    echo " $keep " | grep -q " ${tag} " && continue
    docker rmi "${repo}:${tag}" 2>/dev/null || true
  done < <(docker images "$repo" --format '{{.Tag}}' 2>/dev/null)
  docker image prune -f >/dev/null 2>&1 || true
}
