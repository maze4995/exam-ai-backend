import pdfplumber

def inspect_page(pdf_path, page_num):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num - 1]
        print(f"--- Page {page_num} Object Inspection ---")
        print(f"Page Height: {page.height}, Width: {page.width}")
        
        # 1. Words (Text)
        words = page.extract_words()
        print(f"\n[Text Segments (First 10 lines)]")
        lines = {}
        for w in words:
            top_key = int(w['top'])
            if top_key not in lines: lines[top_key] = []
            lines[top_key].append(w['text'])
            
        sorted_tops = sorted(lines.keys())
        for top in sorted_tops[:20]:
            print(f"Y={top}: {' '.join(lines[top])}")
            
        # 2. Images
        print(f"\n[Images]")
        for i, img in enumerate(page.images):
            # pdfplumber images have 'x0', 'top', 'x1', 'bottom' (sometimes 'y0', 'y1' depending on coordinate system, but top/bottom is standard for objects)
            print(f"Image {i}: Top={img.get('top')}, Bottom={img.get('bottom')}, X0={img.get('x0')}")

        graphics = []
        for obj in page.rects + page.lines + page.curves:
            graphics.append({
                "type": "graphic", 
                "top": obj['top'], 
                "bottom": obj['bottom'],
                "x0": obj['x0'],
                "x1": obj['x1']
            })
        
        # Sort by top
        graphics.sort(key=lambda x: x['top'])
        
        # Find Problem text positions
        print("\n[Problem Markers]")
        markers = {}
        for w in words:
            if str(w['text']) in ['204', '205', '206']:
                print(f"Marker '{w['text']}' at Top={w['top']:.2f}, Bottom={w['bottom']:.2f}, X0={w['x0']:.2f}, X1={w['x1']:.2f}")
                markers[w['text']] = w['top']

        if '205' in markers:
            p205_top = markers['205']
            print(f"\n[Graphics around 205 (Top={p205_top:.2f})]")
            nearby = [g for g in graphics if p205_top - 100 < g['top'] < p205_top + 100]
            max_x = 0
            for g in nearby:
                print(f"Graphic at Top={g['top']:.2f}, Bottom={g['bottom']:.2f}, X0={g.get('x0', 'N/A')}, X1={g.get('x1', 'N/A')} (Rel to 205: {g['top']-p205_top:.2f})")
                if g.get('x1', 0) > max_x: max_x = g.get('x1', 0)
            
            print(f"\n[Text in Right Column (X > 333) within Y=[{p205_top}, {p205_top+100}]]")
            overlap_text = []
            for w in words:
                if w['x0'] > 333 and p205_top < w['top'] < p205_top + 100:
                    overlap_text.append(w['text'])
            print(f"Collision Words: {overlap_text}")

if __name__ == "__main__":
    inspect_page(r"C:\Users\rlgus\.gemini\antigravity\scratch\science-problem-recommender\완자 기출픽_통합과학_본책.pdf", 53)
