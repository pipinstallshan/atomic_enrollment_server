import os

# Create the folders if they don't exist
folders = ["data", "logs", "output", "temp", "instance"]
for folder in folders:
    if not os.path.exists(folder):
        os.makedirs(folder)
