#!/usr/bin/env bash
# Cross-platform (Linux/macOS) helper to update repo: pull, run optional tests, commit, tag, push
# Usage:
#   ./scripts/update_repo.sh "Commit message" [tag]
#   ./scripts/update_repo.sh "Commit message" v2.0.0 --run-tests

MSG="$1"
TAG="$2"
RUN_TESTS=false
DRY_RUN=false
for arg in "$@"; do
  if [[ "$arg" == "--run-tests" ]]; then RUN_TESTS=true; fi
  if [[ "$arg" == "--dry-run" ]]; then DRY_RUN=true; fi
done

if [ -z "$MSG" ]; then
  echo "Usage: $0 \"Commit message\" [tag] [--run-tests] [--dry-run]"
  exit 1
fi

function exec_cmd() {
  echo "> $1"
  if [ "$DRY_RUN" = false ]; then
    eval $1
    if [ $? -ne 0 ]; then
      echo "Command failed: $1"; exit 1
    fi
  fi
}

if [ ! -d .git ]; then echo "Not a git repository"; exit 1; fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
exec_cmd "git fetch origin"
exec_cmd "git pull origin $BRANCH"

if [ "$RUN_TESTS" = true ]; then
  echo "Running tests: python scripts/run_test.py --video tests/test_videos/fall_sample_01.mp4 --output test_outputs"
  if [ "$DRY_RUN" = false ]; then
    python scripts/run_test.py --video tests/test_videos/fall_sample_01.mp4 --output test_outputs
  fi
fi

CHANGES=$(git status --porcelain)
if [ -z "$CHANGES" ]; then
  echo "No changes to commit"
else
  exec_cmd "git add -A"
  exec_cmd "git commit -m \"$MSG\""
fi

if [ -n "$TAG" ]; then
  exec_cmd "git tag -a $TAG -m \"$MSG\""
fi

exec_cmd "git push origin $BRANCH"
if [ -n "$TAG" ]; then exec_cmd "git push origin $TAG"; fi

echo "Done"
