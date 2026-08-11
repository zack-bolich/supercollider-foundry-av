@echo off
cd /d "C:\Users\learn\Downloads\supercollider-foundry-av"
title Launch Foundry Full AV
python launch_full_av.py
if errorlevel 1 pause
