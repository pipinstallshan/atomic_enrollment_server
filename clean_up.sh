#!/bin/bash

# Set the folder path
TARGET_DIR="/home/merlin/projects/atomic_enrollment_server/output"

# Delete files older than 5 days
find "$TARGET_DIR" -type f -mtime +5 -exec rm -f {} \;
