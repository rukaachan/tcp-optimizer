#!/bin/bash

# This script automates the uninstallation of the tcp-optimizer systemd service.

# --- Configuration ---
SERVICE_NAME="tcp-optimizer.service"
DEST_SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"

# --- Pre-flight Checks ---
if [[ "$EUID" -ne 0 ]]; then
  echo "Please run this script with sudo or as root."
  exit 1
fi

# --- Uninstallation ---
echo "Uninstalling systemd service..."

# Stop and disable the service
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    echo "Stopping service..."
    systemctl stop "${SERVICE_NAME}"
fi
if systemctl is-enabled --quiet "${SERVICE_NAME}"; then
    echo "Disabling service..."
    systemctl disable "${SERVICE_NAME}"
fi

# Remove the service file
if [ -f "${DEST_SERVICE_FILE}" ]; then
    echo "Removing service file..."
    rm "${DEST_SERVICE_FILE}"
fi

# --- Final Steps ---
echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Uninstallation complete!"
