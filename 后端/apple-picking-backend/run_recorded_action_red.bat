@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

if defined RECORDED_RED_DATASET_REPO_ID (
  set "DATASET_REPO_ID=%RECORDED_RED_DATASET_REPO_ID%"
) else if defined RECORDED_DATASET_REPO_ID (
  set "DATASET_REPO_ID=%RECORDED_DATASET_REPO_ID%"
) else (
  set "DATASET_REPO_ID=wyc/record_001"
)

if defined RECORDED_RED_DATASET_EPISODE (
  set "DATASET_EPISODE=%RECORDED_RED_DATASET_EPISODE%"
) else if defined RECORDED_DATASET_EPISODE (
  set "DATASET_EPISODE=%RECORDED_DATASET_EPISODE%"
) else (
  set "DATASET_EPISODE=0"
)

if not defined RECORDED_ROBOT_TYPE set "RECORDED_ROBOT_TYPE=tactile_follower"
if not defined RECORDED_ROBOT_PORT set "RECORDED_ROBOT_PORT=COM24"
if not defined RECORDED_ROBOT_ID set "RECORDED_ROBOT_ID=follower_arm"
if not defined LEROBOT_PYTHON set "LEROBOT_PYTHON=python"

if not exist "record_replay.py" (
  echo record_replay.py not found in %CD%
  echo Put record_replay.py in this backend directory, or edit this bat to point to its real path.
  exit /b 1
)

echo Replaying recorded red action: !DATASET_REPO_ID! episode !DATASET_EPISODE!
"%LEROBOT_PYTHON%" record_replay.py --dataset.repo_id=!DATASET_REPO_ID! --dataset.episode=!DATASET_EPISODE! --robot.type=!RECORDED_ROBOT_TYPE! --robot.port=!RECORDED_ROBOT_PORT! --robot.id=!RECORDED_ROBOT_ID!
