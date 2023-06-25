#!/bin/bash

# Check if SITE argument is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 SITE"
    exit 1
fi

SITE=$1

# Navigate to the directory
mkdir -p ~/repos/woodoo
cd ~/repos/woodoo || exit

# Pull the latest changes
git pull

# Copy the addons
cp -r addons/* ../../"${SITE}"/addons/

# Restart the service
sudo systemctl restart "${SITE}"
