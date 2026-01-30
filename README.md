# AI Exam Problem Extractor (VLM 기반 시험지 문제 추출 시스템)

이 프로젝트는 멀티모달 AI(Gemini VLM)를 활용하여 필기된 과학 시험지(PDF/이미지)에서 문제를 자동으로 인식, 추출하고 개별 문제 단위로 크롭하여 데이터셋을 구축하는 도구입니다.

## 🚀 주요 기능
*   **최신 AI 모델 지원**: **Gemini 3 (`gemini-3-flash-preview`)** 모델을 사용하여 문제 인식 결과의 정확도와 좌표 정밀도를 대폭 향상했습니다.
*   **자동 이미지 크롭**: 추출된 좌표를 바탕으로 전체 시험지 이미지에서 개별 문제 이미지를 자동으로 잘라내어 저장합니다.
*   **LaTeX 수식 지원**: 문제 내 수식을 LaTeX 형식으로 변환하여 저장합니다.
*   **검증 및 수정 도구**: 추출된 영역을 시각적으로 확인(`visualize_bboxes.py`)하고, 필요한 경우 메타데이터 수정 후 이미지를 다시 재생성(`regenerate_crops.py`)할 수 있습니다.
*   **스마트 복구 및 재시도**: Quota 초과(429) 시 자동 대기 및 재시도 로직과, 기존의 실패한 추출 결과만 골라 다시 처리하는 복구 기능을 포함합니다.

## 🛠️ 설치 및 설정

### 1. 의존성 라이브러리 설치
```powershell
pip install -r requirements.txt
```

### 2. API 키 설정 (보안 필수)
보안을 위해 API 키를 환경 변수로 관리하는 것을 권장합니다. PowerShell에서 다음 명령어를 실행하여 API 키를 설정하세요.
```powershell
$env:GEMINI_API_KEY = "발급받은_API_키"
```
> [!IMPORTANT]
> 코드 내에 `API_KEY`를 직접 입력할 경우, 절대 Git 저장소에 push하지 않도록 주의하세요. 키가 유출되면 Google에 의해 자동으로 차단될 수 있습니다.

## 📂 프로젝트 구조
*   `extract_problems.py`: 전체 PDF를 순회하며 이미지 변환, AI 추출, 크롭을 수행하는 메인 배치 스크립트입니다. (현재 테스트를 위해 처음 10개 시험지로 제한 설정됨)
*   `visualize_bboxes.py`: 추출된 문제 영역을 원본 이미지에 그려서 시각적으로 확인(`visualized_...png`)하는 검증 도구입니다.
*   `regenerate_crops.py`: 사용자가 JSON 메타데이터의 좌표를 수정한 후, 이를 바탕으로 이미지를 다시 크롭하는 수정 도구입니다.
*   `utils.py`: AI 응답 파킹 및 LaTeX 보정 등 공통적으로 사용되는 유틸리티 함수 모음입니다.
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
