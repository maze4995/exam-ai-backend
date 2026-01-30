@echo off
cd /d "%~dp0"
echo Launching LabelImg...
"C:\Users\rlgus\.gemini\antigravity\scratch\science-problem-recommender\venv\Scripts\labelImg.exe" training_data\images training_data\classes.txt
pause
