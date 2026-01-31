# AI Exam Problem Extractor (VLM 기반 시험지 문제 추출 시스템)

이 프로젝트는 멀티모달 AI(Gemini VLM)를 활용하여 필기된 과학 시험지(PDF/이미지)에서 문제를 자동으로 인식, 추출하고 개별 문제 단위로 크롭하여 데이터셋을 구축하는 도구입니다.

## 🚀 주요 기능
*   **Gemini 3 지원**: **Gemini 3 (`gemini-3-flash-preview`)** 모델을 사용하여 문제 인식 퀄리티와 좌표 정밀도를 대폭 향상했습니다.
*   **스마트 크롭 & 시각화**: 문제, 보기, 선지, **표(Chart)**, **그림(Visual Elements)**을 개별적으로 인식하고 좌표를 추출하여 자동으로 잘라냅니다.
*   **웹 뷰어 내장**: 추출된 데이터를 시각적으로 확인할 수 있는 **웹 기반 갤러리(`viewer.html`)**를 제공합니다. Markdown 표 렌더링과 MathJax 수식 변환을 완벽하게 지원합니다.
*   **원격 공유 (Deployment)**: 터널링 도구(`localtunnel`)를 통해 로컬 서버를 외부 사용자에게 즉시 공유할 수 있는 기능을 포함합니다.
*   **검증 및 수정**: 추출된 영역을 시각적으로 확인(`visualize_bboxes.py`)하고, JSON 수정 후 이미지를 재생성(`regenerate_crops.py`)할 수 있습니다.

## 🛠️ 설치 및 설정

### 1. 의존성 라이브러리 설치
```powershell
pip install -r requirements.txt
```
웹 뷰어 및 공유 기능을 위해 Node.js 런타임(npx)이 필요할 수 있습니다.

### 2. API 키 설정 (보안 필수)
보안을 위해 API 키를 환경 변수로 관리하는 것을 권장합니다. PowerShell에서 다음 명령어를 실행하여 API 키를 설정하세요.
```powershell
$env:GEMINI_API_KEY = "발급받은_API_키"
```

## 📂 프로젝트 구조
*   `extract_problems.py`: 전체 PDF를 순회하며 이미지 변환, AI 추출, 크롭을 수행하는 메인 배치 스크립트입니다.
*   `app.py`: 웹 뷰어를 위한 FastAPI 백엔드 서버입니다.
*   `viewer.html`: 추출된 데이터를 보여주는 모던한 웹 프론트엔드입니다.
*   `share.py`: 로컬 서버를 외부로 공유하는 터널링 스크립트입니다.
*   `visualize_bboxes.py`: 추출된 문제 영역을 원본 이미지에 그려서 검증하는 도구입니다.
*   `regenerate_crops.py`: 수동 수정된 JSON을 반영하여 이미지를 다시 자르는 도구입니다.
*   `utils.py`: 공통 유틸리티 모듈입니다.
*   `output_extraction/`: 모든 결과물(이미지, JSON, 크롭 데이터)이 저장됩니다.

## 📖 사용 방법

### 1. 데이터 추출 (Extract)
```powershell
python extract_problems.py
```
`TARGET_DIR` 변수에 설정된 폴더의 모든 시험지를 분석하여 `output_extraction/`에 저장합니다.

### 2. 웹 뷰어 실행 (View)
FastAPI 서버를 실행하여 추출된 결과를 웹에서 확인합니다.
```powershell
python app.py
```
브라우저에서 `http://localhost:8000`으로 접속하세요.

### 3. 외부 공유 (Share)
웹 뷰어를 친구나 동료에게 보여주고 싶을 때 실행합니다.
```powershell
python share.py
```
생성된 `https://xxxx.loca.lt` 링크와 비밀번호를 공유하세요.

### 4. 수동 수정 (Optional)
1. `output_extraction/[시험지명]/extracted_page_X.json` 파일의 좌표를 직접 수정합니다.
2. 아래 명령어로 이미지를 재생성합니다.
```powershell
python regenerate_crops.py
```
