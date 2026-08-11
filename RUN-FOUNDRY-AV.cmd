@echo off
setlocal
cd /d "C:\Users\learn\Downloads\supercollider-foundry-av"
title SuperCollider Foundry AV Relay
if not exist node_modules (
  echo Installing local AV dependencies...
  call npm install
  if errorlevel 1 pause & exit /b 1
)
start "" "http://127.0.0.1:8899"
echo Keep this window open. SuperCollider sends OSC to UDP 57220.
echo Visuals: http://127.0.0.1:8899
echo.
node server.js
pause
