#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

DATASET_REPO_ID="${RECORDED_RED_DATASET_REPO_ID:-${RECORDED_DATASET_REPO_ID:-wyc/record_001}}"
DATASET_EPISODE="${RECORDED_RED_DATASET_EPISODE:-${RECORDED_DATASET_EPISODE:-0}}"
ROBOT_TYPE="${RECORDED_ROBOT_TYPE:-tactile_follower}"
ROBOT_PORT="${RECORDED_ROBOT_PORT:-COM24}"
ROBOT_ID="${RECORDED_ROBOT_ID:-follower_arm}"
LEROBOT_PYTHON="${LEROBOT_PYTHON:-python3}"

if [ ! -f "record_replay.py" ]; then
  echo "record_replay.py not found in $(pwd)"
  echo "Put record_replay.py in this backend directory, or edit this script to point to its real path."
  exit 1
fi

echo "Replaying recorded red action: ${DATASET_REPO_ID} episode ${DATASET_EPISODE}"
"$LEROBOT_PYTHON" record_replay.py \
  --dataset.repo_id="$DATASET_REPO_ID" \
  --dataset.episode="$DATASET_EPISODE" \
  --robot.type="$ROBOT_TYPE" \
  --robot.port="$ROBOT_PORT" \
  --robot.id="$ROBOT_ID"
