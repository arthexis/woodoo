#!/bin/bash

# Check if SITE argument is provided
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 SITE [BRANCH]"
    exit 1
fi

SITE=$1
BRANCH=$2

# Navigate to the directory
mkdir -p ~/repos/woodoo
cd ~/repos/woodoo || exit

# Print the name of the current branch
current_branch=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $current_branch"

# If BRANCH argument is provided, checkout to that branch
if [ -n "$BRANCH" ]; then
    git checkout "$BRANCH"
fi

# Pull the latest changes
git pull

# Show the last commit 
echo "Last commit: "
git log -1 --pretty=%B

# Copy the addons
cp -r addons/* ../../"${SITE}"/addons/

# Restart the service
sudo systemctl restart "${SITE}"

# Show the log
sudo journalctl -u "${SITE}" -n 4
