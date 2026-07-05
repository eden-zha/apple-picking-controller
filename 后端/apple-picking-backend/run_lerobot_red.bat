@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "DATASET_BASE_DIR=%USERPROFILE%\.cache\huggingface\lerobot\Keyon"
set /a DATASET_INDEX=1
:find_dataset_repo
set "DATASET_NAME=eval_so101_!DATASET_INDEX!"
if exist "%DATASET_BASE_DIR%\!DATASET_NAME!" (
  set /a DATASET_INDEX+=1
  goto find_dataset_repo
)
set "DATASET_REPO_ID=Keyon/!DATASET_NAME!"
echo Using dataset repo id: !DATASET_REPO_ID!
python -m lerobot.record --robot.type=so101_follower --robot.port=COM24 --robot.id=my_awesome_follower_arm --robot.calibration_dir=C:/Users/HUAWEI/.cache/huggingface/lerobot/calibration/robots/so101_follower --robot.cameras="{ handeye: {type: opencv,index_or_path: 2, width: 640, height: 480, fps: 30}, front: {type: opencv,index_or_path: 0, width: 640, height: 480, fps: 30}}" --display_data=true --dataset.repo_id=!DATASET_REPO_ID! --dataset.single_task="Grab the screwdriver" --policy.path=outputs/train/red_policy/checkpoints/100000/pretrained_model --dataset.push_to_hub=false
