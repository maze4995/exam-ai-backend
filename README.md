# Handwriting Remover (필기 제거 모델)

이 프로젝트는 시험지나 문서 이미지에서 필기(Handwriting)를 제거하고 원본 인쇄 텍스트(Printed Text)만 복원하는 딥러닝 모델입니다.

## 📌 주요 기능
*   **합성 데이터 생성**: 깨끗한 배경 이미지와 노이즈(필기)를 합성하여 학습 데이터를 무한으로 생성 (`synthesizer.py`)
*   **ResUNet 모델**: U-Net 구조에 ResNet 블록을 추가하여 텍스트 디테일 보존 능력 향상
*   **Perceptual Loss**: VGG19 기반의 손실 함수를 사용하여 자연스러운 복원 결과 생성

## 🛠️ 설치 가이드 (Installation)

이 프로젝트는 **Python 3.11** 및 **CUDA 12.1** 환경에서 최적화되어 있습니다.

### 1. 필수 프로그램 설치
*   [Git](https://git-scm.com/download/win)
*   [Python 3.11.9](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe) (설치 시 **Add Python to PATH** 체크 필수)
*   [NVIDIA GPU Driver](https://www.nvidia.com/Download/index.aspx)

### 2. 저장소 복제 (Clone)
```powershell
git clone https://github.com/maze4995/Hyun-and-Hyun.git
cd Hyun-and-Hyun/Code
```

### 3. 가상환경 설정 및 의존성 설치
PowerShell에서 다음 명령어를 실행하세요:

```powershell
# 가상환경 생성 (.venv)
py -3.11 -m venv .venv

# 가상환경 활성화
.venv\Scripts\activate

# PyTorch (GPU 버전) 설치
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 나머지 라이브러리 설치
pip install -r handwriting-remover/requirements.txt
```

## 🚀 사용법 (Usage)

### 학습 (Training)
`handwriting-remover` 폴더로 이동하여 `train_science_gpu.bat` 스크립트를 실행합니다.
이 스크립트는 `.venv` 가상환경을 자동으로 사용하여 GPU 학습을 수행합니다.

```powershell
cd handwriting-remover
.\train_science_gpu.bat
```

### 추론 (Inference)
학습된 모델(`checkpoints/last.pth`)을 사용하여 새로운 이미지의 필기를 제거합니다.

```powershell
python inference.py --input "path/to/image.png" --output "result.png"
```

## 📂 디렉토리 구조
*   `handwriting-remover/`: 필기 제거 모델 소스 코드
    *   `data/`: 데이터셋 로더 및 합성 스크립트
    *   `models/`: 모델 아키텍처 정의 (UNet 등)
    *   `train.py`: 학습 실행 파일
    *   `inference.py`: 추론 실행 파일
*   `science-problem-dataset-builder/`: 과학 문제 데이터셋 구축 도구 (별도 프로젝트)
