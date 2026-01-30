@echo off
echo ==========================================
echo GPU Training with Python 3.11 Venv
echo ==========================================

REM Path to the science dataset images
set DATASET_DIR=..\science-problem-dataset-builder\output\images

REM 1. Activate venv implicitly by using absolute path to python
set PYTHON_EXE=.venv\Scripts\python.exe

if not exist "%PYTHON_EXE%" (
    echo Error: Virtual environment not found. Please wait for setup to complete.
    pause
    exit /b
)

echo [1/3] Checking CUDA...
%PYTHON_EXE% -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}')"

echo [2/3] Training Model (GPU Enabled)...
REM Running full training (10 epochs, 200 iter) as planned initially
%PYTHON_EXE% train.py --epochs 10 --epoch_size 200 --batch_size 4 --img_size 512 --bg_dir "%DATASET_DIR%" --save_dir checkpoints_science_gpu --lr 0.0002

if %errorlevel% neq 0 (
    echo Error in training.
    pause
    exit /b
)

echo [3/3] Inference...
%PYTHON_EXE% inference.py --input "%DATASET_DIR%\p50_1.png" --output result_gpu_final.png --checkpoint checkpoints_science_gpu/last.pth

echo.
echo ==========================================
echo Completed! Check result_gpu_final.png
echo ==========================================
pause
