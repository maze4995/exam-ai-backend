import json
import os

BASE_DIR = r"C:\Users\rlgus\.gemini\antigravity\scratch\science-problem-dataset-builder"
JSON_PATH = os.path.join(BASE_DIR, "output", "dataset_ai_test.json")
TEMPLATE_PATH = os.path.join(BASE_DIR, "web_tool", "viewer.html")
OUTPUT_HTML_PATH = os.path.join(BASE_DIR, "output", "gallery_test.html")

def generate():
    # Load JSON
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = f.read() # Read as string to embed
        
    # Load Template
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()
        
    # Replace Logic
    # 1. Replace loadData() call
    # find lines for loadData implementation
    
    # We will just inject the data at the top of script and modify loadData to do nothing or remove it.
    # Simpler: Replace the whole script tag content if I can match it, or just string replace exact lines.
    
    # Replace fetch call
    new_script = f"""
    let problems = {data};

    function loadData() {{
        renderList();
        if(problems.length > 0) loadProblem(0);
    }}
    """
    
    # We need to act carefully. Let's find "async function loadData() {" and replace the whole block until "}"
    # But regex is risky. 
    # The viewer code has:
    # async function loadData() {
    #     try {
    #         const response = await fetch('/data/dataset.json');
    #         problems = await response.json();
    #         renderList();
    #         if(problems.length > 0) loadProblem(0);
    #     } catch (e) {
    #         alert("Failed to load dataset.json: " + e);
    #     }
    # }
    
    # We can replace the whole function.
    
    template = template.replace("async function loadData() {", "function loadData() {")
    # Remove the fetch part
    # Actually, simpler to just find "let problems = [];" and replace it with "let problems = <data>;"
    # And make loadData just call renderList.
    
    template = template.replace("let problems = [];", f"let problems = {data};")
    
    # Now replace the body of loadData.
    # Or just replace the call to fetch
    template = template.replace("const response = await fetch('/data/dataset.json');", "// Fetch removed")
    template = template.replace("problems = await response.json();", "// Data inlined")
    
    # Replace Image Path
    # img.src = `/data/images/${content.visuals[0]}`;
    template = template.replace("/data/images/", "images_ai_test/")
    
    # Save
    with open(OUTPUT_HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(template)
        
    print(f"Generated {OUTPUT_HTML_PATH}")

if __name__ == "__main__":
    generate()
