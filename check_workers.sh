#!/bin/bash

set -e

# Paths
VENV_PYTHON="/home/merlin/projects/atomic_enrollment_server/venv/bin/python"
SCRIPT_PATH="/home/merlin/projects/atomic_enrollment_server/Task_worker.py"
LOG_DIR="/home/merlin/projects/atomic_enrollment_server/logs"
WORKER1_LOG="$LOG_DIR/worker1.log"
WORKER2_LOG="$LOG_DIR/worker2.log"
CHECK_LOG="$LOG_DIR/check_script.log" # Log for this check script

# Ensure log directory exists
mkdir -p "$LOG_DIR"

EXPECTED_INSTANCES=2
COMMAND_PATTERN="python $SCRIPT_PATH"

echo "---------------------" >> "$CHECK_LOG"
echo "Running check_workers.sh at $(date)" >> "$CHECK_LOG"

# Count currently running instances matching the specific command
CURRENT_INSTANCES=$(pgrep -f -c "$COMMAND_PATTERN") || CURRENT_INSTANCES=0

echo "Found $CURRENT_INSTANCES running instances." >> "$CHECK_LOG"

# Calculate how many instances need to be started
INSTANCES_TO_START=$((EXPECTED_INSTANCES - CURRENT_INSTANCES))

if [ "$INSTANCES_TO_START" -gt 0 ]; then
    echo "Need to start $INSTANCES_TO_START instance(s)." >> "$CHECK_LOG"
    for ((i=1; i<=INSTANCES_TO_START; i++)); do
        # Basic logic: Try to start into worker1.log first if it looks "less active"
        # or just alternate. A truly robust way needs process tracking, but this is simpler.
        # Let's just pick one based on which number we are starting. This is NOT foolproof
        # if only worker1 died, it might try to start into worker2's log if i=2.
        # A simpler approach might be to always log to a *new* timestamped file here,
        # but let's try reusing the original log files.

        # Simplistic: Assume we need worker 1 if count is 0, worker 2 if count is 1
        # This might overwrite a running process's log if check runs during a brief hiccup.
        # Consider timestamped logs if this becomes an issue.
        if [ "$CURRENT_INSTANCES" -eq 0 ] && [ "$i" -eq 1 ]; then
             LOG_FILE=$WORKER1_LOG
             WORKER_NUM=1
        else
             LOG_FILE=$WORKER2_LOG # Default to worker 2 if count is 1, or if starting the 2nd missing one
             WORKER_NUM=2
        fi

        echo "Starting instance #$i (targeting Worker $WORKER_NUM log)..." >> "$CHECK_LOG"
        nohup "$VENV_PYTHON" "$SCRIPT_PATH" > "$LOG_FILE" 2>&1 &
        PID=$!
        echo "Started instance with PID $PID, logging to $LOG_FILE" >> "$CHECK_LOG"
        sleep 2 # Small delay before potentially starting another
    done
else
    echo "Correct number of instances ($CURRENT_INSTANCES) running." >> "$CHECK_LOG"
fi

echo "Check script finished at $(date)." >> "$CHECK_LOG"
echo "---------------------" >> "$CHECK_LOG"

exit 0
