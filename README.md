# AI Exam Problem Extractor (VLM 기반 시험지 문제 추출 시스템)

이 프로젝트는 멀티모달 AI(Gemini VLM)를 활용하여 필기된 과학 시험지(PDF/이미지)에서 문제를 자동으로 인식, 추출하고 개별 문제 단위로 크롭하여 데이터셋을 구축하는 도구입니다.

## 🚀 주요 기능
*   **AI 기반 문제 인식**: Gemini 1.5 Flash 모델을 사용하여 문제 번호, 지문, 보기, 수식(LaTeX) 및 문제 영역(Bounding Box)을 추출합니다.
*   **자동 이미지 크롭**: 추출된 좌표를 바탕으로 전체 시험지 이미지에서 개별 문제 이미지를 자동으로 잘라내어 저장합니다.
*   **LaTeX 수식 지원**: 문제 내 수식을 LaTeX 형식으로 변환하여 저장합니다.
*   **검증 및 수정 도구**: 추출된 영역을 시각적으로 확인하고, 필요한 경우 메타데이터 수정 후 이미지를 다시 재생성할 수 있는 툴킷을 제공합니다.
*   **배치 프로세싱**: 수십 개의 시험지 PDF를 한 번에 처리할 수 있는 자동화 스크립트를 지원합니다.

## 🛠️ 설치 및 설정

### 1. 의존성 라이브러리 설치
```powershell
pip install -r requirements.txt
```

### 2. API 키 설정
`extract_problems.py` 파일 상단의 `API_KEY` 변수에 Gemini API 키를 입력하세요.

## 📂 프로젝트 구조
*   `extract_problems.py`: 전체 PDF를 순회하며 이미지 변환, AI 추출, 크롭을 수행하는 메인 배치 스크립트입니다.
*   `visualize_bboxes.py`: 추출된 문제 영역을 원본 이미지에 그려서 시각적으로 확인(`visualized_...png`)하는 검증 도구입니다.
*   `regenerate_crops.py`: 사용자가 JSON 메타데이터의 좌표를 수정한 후, 이를 바탕으로 이미지를 다시 크롭하는 수정 도구입니다.
*   `utils.py`: AI 응답 파싱 등 공통적으로 사용되는 유틸리티 함수 모음입니다.
*   `output_extraction/`: 모든 결과물(이미지, JSON, 크롭 데이터)이 저장되는 폴더입니다.
*   `_archive/`: 기존의 YOLO 기반 및 구형 프로젝트 파일 보관소입니다.

## 📖 사용 방법

### 1. 전체 시험지 일괄 처리
`extract_problems.py` 내의 `TARGET_DIR`을 시험지 PDF들이 들어있는 폴더 경로로 설정한 후 실행합니다.
```powershell
python extract_problems.py
```

### 2. 추출 영역 검증 (Optional)
추출이 잘 되었는지 확인하려면 시각화 도구를 실행합니다.
```powershell
python visualize_bboxes.py
```

### 3. 수동 수정 (필요 시)
1. `output_extraction/[시험지명]/extracted_page_X.json` 파일을 열어 좌표(`box_2d`)를 수정합니다.
2. 아래 명령어를 실행하여 수정한 좌표대로 이미지를 다시 잘라냅니다.
```powershell
python regenerate_crops.py
```

---
## ⚠️ 주의 사항
*   Gemini API 사용 시 분당 요청 제한(RPM)을 준수하기 위해 스크립트에 대기 시간(35초)이 포함되어 있습니다.
*   `.gitignore` 설정에 따라 `output_extraction/` 폴더 내의 대용량 이미지 데이터는 Git 레파지토리에 업로드되지 않습니다.
