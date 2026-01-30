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

---

## 🏗️ Science Problem Dataset Builder (과학 문제 데이터셋 도구)

이 도구는 PDF 파일에서 문제 영역을 자동으로 추출하고 라벨링하여 딥러닝 학습용 데이터를 구축하는 보조 프로그램입니다.

### 주요 기능
*   **PDF 파싱**: PDF 문서 구조 분석 (`src/parser.py`)
*   **AI 문제 추출**: YOLO 모델을 사용하여 문제/해설 영역 자동 탐지 (`src/test_ai_extraction.py`)
*   **데이터셋 생성**: 탐지된 영역을 이미지로 저장하고 학습 라벨(txt, xml) 생성

### 사용 방법
1.  `science-problem-dataset-builder` 폴더로 이동합니다.
2.  별도의 가상환경을 설정합니다 (Python 3.8+ 권장).
    ```powershell
    cd science-problem-dataset-builder
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    ```
3.  `input` 폴더에 PDF 파일을 넣습니다.
4.  추출 실행:
    ```powershell
    python src/test_ai_extraction.py
    ```
5.  결과 확인: `output/gallery_test.html`을 브라우저로 엽니다.

---

## 📂 디렉토리 구조
*   `handwriting-remover/`: 필기 제거 모델 소스 코드
    *   `data/`: 데이터셋 로더 및 합성 스크립트
    *   `models/`: 모델 아키텍처 정의 (UNet 등)
    *   `train.py`: 학습 실행 파일
    *   `inference.py`: 추론 실행 파일
*   `science-problem-dataset-builder/`: 과학 문제 데이터셋 구축 도구
    *   `src/`: 핵심 로직 (파서, 변환기)
    *   `web_tool/`: 결과 확인용 웹 뷰어
    *   `input/`, `output/`: 데이터 입출력 폴더
