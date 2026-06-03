#!/bin/bash
echo "========================================"
echo " DGVCL Estimate Portal — Local Runner"
echo "========================================"
echo ""
pip3 install flask requests openpyxl werkzeug --quiet
echo "Starting DGVCL Portal..."
echo "Open: http://localhost:5000"
echo "Login: admin / admin123"
echo "Press CTRL+C to stop."
echo ""
python3 app.py
