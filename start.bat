@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo Apple Picking Robot Launcher
echo.
echo 1. Robot PC: only start FastAPI backend on port 8000
echo 2. PC1: only start frontend and connect to robot PC backend
echo 3. Single machine: start backend and frontend on this robot PC
echo.
set /p ROLE_CHOICE=Choose 1/2/3:

if "%ROLE_CHOICE%"=="1" (
  python launcher.py --role backend
  pause
  exit /b
)

if "%ROLE_CHOICE%"=="2" (
  echo.
  set /p ROBOT_BACKEND_URL=Robot PC backend URL, for example http://192.168.1.20:8000:
  python launcher.py --role frontend --robot-backend-url "%ROBOT_BACKEND_URL%"
  pause
  exit /b
)

if "%ROLE_CHOICE%"=="3" (
  python launcher.py --role all
  pause
  exit /b
)

echo Invalid choice.
pause
