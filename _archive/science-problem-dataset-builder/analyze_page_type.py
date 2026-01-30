import pdfplumber

PDF_PATH = r"C:\Users\rlgus\.gemini\antigravity\scratch\science-problem-recommender\완자 기출픽_통합과학_본책.pdf"

def analyze_pages(pages):
    with pdfplumber.open(PDF_PATH) as pdf:
        for p_num in pages:
            page = pdf.pages[p_num - 1]
            text = page.extract_text()
            print(f"--- Page {p_num} ---")
            print(text[:500])  # Print first 500 chars
            print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    analyze_pages([56, 57, 58])
