#!/bin/bash
set -e

echo "🚀 Starting Docker Backup Guard..."

# Start Scheduler Service in background
echo "⏰ Starting Scheduler Service..."
python3 -m app.scheduler_service &
SCHEDULER_PID=$!

# Start Streamlit UI in foreground
echo "🖥️ Starting Web UI..."
exec streamlit run main.py --server.address=0.0.0.0
