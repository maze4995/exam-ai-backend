@echo off
echo ==========================================
echo Handwriting Remover Demo
echo ==========================================

echo [1/3] Testing Data Synthesizer...
python data/synthesizer.py
if %errorlevel% neq 0 (
    echo Error in synthesizer.
    pause
    exit /b
)

echo [2/3] Training Model (Demo: 2 Epochs)...
python train.py --epochs 2 --epoch_size 50 --batch_size 2
if %errorlevel% neq 0 (
    echo Error in training.
    pause
    exit /b
)

echo [3/3] Running Inference on Debug Image...
python inference.py --input debug_synth_dirty.png --output result_demo.png
if %errorlevel% neq 0 (
    echo Error in inference.
    pause
    exit /b
)

echo.
echo ==========================================
echo Demo Completed!
echo Check 'result_demo.png' to see the result.
echo ==========================================
pause
