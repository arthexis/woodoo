#!/bin/bash

# Check if SITE argument is provided
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 SITE [--reload]"
    exit 1
fi

# Check if the --reload argument is provided
if [ "$2" = "--reload" ]; then
    RELOAD=1
fi

SITE=$1

# Navigate to the directory
mkdir -p ~/repos/woodoo
cd ~/repos/woodoo || exit

# Pull the latest changes
git pull

# Copy the addons
cp -r addons/* ../../"${SITE}"/addons/

# Stop if there were no changes and RELOAD is not set
if [ -z "$(git status --porcelain)" ] && [ "$RELOAD" != 1 ]; then
    echo "No changes"
    exit 0
fi

# Restart the service
sudo systemctl restart "${SITE}"

# Show the log
sudo journalctl -u "${SITE}" -n 4

# If RELOAD, wait until there are changes to the git repository
# then, start this script again. Wait 60 seconds between checks.
if [ "$RELOAD" = 1 ]; then
    echo "Waiting for changes..."
    while [ -z "$(git status --porcelain)" ]; do
        sleep 60
    done
    "$0" "$SITE" --reload
fi
