#!/bin/bash
# Quick start script for Speakly

echo "🎙️ Starting Speakly..."
echo ""
echo "Backend will be available at: http://localhost:8000"
echo "Frontend will be available at: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop"
echo ""

podman compose up backend frontend
