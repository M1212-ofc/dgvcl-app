@echo off
echo ========================================
echo  DGVCL Estimate Portal — Local Runner
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Download from https://python.org
    pause
    exit /b
)

:: Install dependencies if needed
echo Installing dependencies...
pip install flask requests openpyxl werkzeug --quiet

:: Run
echo.
echo Starting DGVCL Portal...
echo Open your browser at: http://localhost:5000
echo Login: admin / admin123
echo Press CTRL+C to stop.
echo.
python app.py
pause
