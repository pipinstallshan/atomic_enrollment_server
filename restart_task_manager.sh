#!/bin/bash

set -e

# Path to the Python virtual environment and the script
VENV_PATH="/home/merlin/projects/atomic_enrollment_server/venv"
SCRIPT_PATH="/home/merlin/projects/atomic_enrollment_server/Task_worker.py"

# Kill existing Python processes related to Task_manager
pkill -9 -f Task_worker.py || true

# Clean up Chrome and ChromeDriver processes
pkill -f chromedriver || true
pkill -f chrome || true

# Wait for a few seconds to ensure all processes are killed
sleep 30

# Activate the virtual environment and restart two instances of the script
source "$VENV_PATH/bin/activate"
nohup python "$SCRIPT_PATH" > /home/merlin/projects/atomic_enrollment_server/nohup.out 2>&1 &

sleep 5

nohup python "$SCRIPT_PATH" > /home/merlin/projects/atomic_enrollment_server/nohup.out 2>&1 &
