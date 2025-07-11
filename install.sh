#!/bin/bash

# This script automates the installation of the tcp-optimizer systemd service.

# --- Configuration ---
SERVICE_NAME="tcp-optimizer.service"
SOURCE_SERVICE_FILE="$(pwd)/${SERVICE_NAME}"
DEST_SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"
PROJECT_DIR="$(pwd)"
EXEC_START_PATH="/usr/bin/python3 ${PROJECT_DIR}/daemon.py"

# --- Pre-flight Checks ---
if [[ "$EUID" -ne 0 ]]; then
  echo "Please run this script with sudo or as root."
  exit 1
fi

if [ ! -f "${SOURCE_SERVICE_FILE}" ]; then
    echo "ERROR: Source service file not found at ${SOURCE_SERVICE_FILE}"
    exit 1
fi

# --- Installation ---
echo "Installing systemd service..."

# Create a temporary service file with the correct paths
TEMP_SERVICE_FILE=$(mktemp)
cp "${SOURCE_SERVICE_FILE}" "${TEMP_SERVICE_FILE}"

# Use sed to replace placeholder paths with the actual paths
sed -i "s|WorkingDirectory=.*|WorkingDirectory=${PROJECT_DIR}|" "${TEMP_SERVICE_FILE}"
sed -i "s|ExecStart=.*|ExecStart=${EXEC_START_PATH}|" "${TEMP_SERVICE_FILE}"

echo "Generated service file with the following contents:"
echo "--------------------------------------------------"
cat "${TEMP_SERVICE_FILE}"
echo "--------------------------------------------------"

# Move the configured service file to the systemd directory
mv "${TEMP_SERVICE_FILE}" "${DEST_SERVICE_FILE}"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to move service file to ${DEST_SERVICE_FILE}."
    # Clean up temporary file
    rm -f "${TEMP_SERVICE_FILE}"
    exit 1
fi

# --- Final Steps ---
echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Installation complete!"
echo ""
echo "You can now enable and start the service with:"
echo "sudo systemctl enable --now ${SERVICE_NAME}"
echo ""
echo "To check the status of the service, use:"
echo "sudo systemctl status ${SERVICE_NAME}"
