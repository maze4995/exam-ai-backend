@echo off
echo ==========================================
echo Training on Science Problem Dataset
echo ==========================================

REM Path to the science dataset images
set DATASET_DIR=..\science-problem-dataset-builder\output\images

echo [1/3] Checking Dataset...
if not exist "%DATASET_DIR%" (
    echo Error: Dataset directory not found at %DATASET_DIR%
    pause
    exit /b
)

echo [2/3] Training Model (GPU if available)...
REM Using larger epoch size and more epochs for better results
REM Adjusted batch size for potential GPU memory limits (or CPU speed)
python train.py --epochs 10 --epoch_size 200 --batch_size 4 --img_size 512 --bg_dir "%DATASET_DIR%" --save_dir checkpoints_science --lr 0.0002

if %errorlevel% neq 0 (
    echo Error in training.
    pause
    exit /b
)

echo [3/3] Testing Inference...
REM Use one of the real images for testing (it will be resized and cleaned)
python inference.py --input "%DATASET_DIR%\p50_1.png" --output result_science_p50_1.png --checkpoint checkpoints_science/last.pth

echo.
echo ==========================================
echo Training and Test Completed!
echo Check 'result_science_p50_1.png'
echo ==========================================
pause
