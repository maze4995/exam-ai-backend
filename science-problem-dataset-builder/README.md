# Science Problem Dataset Builder

## 1. Environment Setup (환경 설정)

1. **Install Python**: Ensure Python 3.8+ is installed.
2. **Create Virtual Environment**:
   ```bash
   python -m venv venv
   ```
3. **Activate Environment**:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
4. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 2. Project Structure (폴더 구조)
- `src/`: Core Python scripts (AI extraction, training, etc.)
- `web_tool/`: HTML viewer for results
- `input/`: Place your PDF files here
- `output/`: Generated results (images, JSON)
- `models/`: Trained YOLO models

## 3. How to Run (실행 방법)

### Run AI Extraction (문제 추출)
```bash
python src/test_ai_extraction.py
```

### View Results (결과 확인)
Open `output/gallery_test.html` in your browser.
