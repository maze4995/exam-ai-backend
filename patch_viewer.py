import os

file_path = "viewer.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Text to Replace (String Literal method, no regex issues)
# We are replacing the old resultDiv assignment block
target_block_start = 'const resultDiv = document.getElementById(\'generator-result\');'
target_block_end = 'const randomProb = cachedProblems[Math.floor(Math.random() * cachedProblems.length)];'

# We need to capture the exact string between them to be safe, but since whitespace varies, 
# let's just find the start and end and replace everything in between.

start_index = content.find(target_block_start)
end_index = content.find(target_block_end)

if start_index != -1 and end_index != -1:
    # Check if we have the old Logic
    # We want to replace from AFTER target_block_start to BEFORE target_block_end
    # Actually, my previous script tried to replace the target_block_start line itself too.
    
    new_logic = """const resultDiv = document.getElementById('generator-result');
            
            const loadingTexts = [
                 "Selecting random problem...",
                 "Gemini 3 is thinking...",
                 "Drafting creative variation...",
                 "Drawing diagrams...",
                 "Almost done..."
            ];
            let step = 0;
            
            resultDiv.innerHTML = `
                <div class="glass p-8 rounded-3xl text-center space-y-4 animate-pulse">
                     <div class="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                     <h3 class="text-xl font-bold text-white" id="loading-msg">${loadingTexts[0]}</h3>
                     <p class="text-slate-400">Please wait... Large AI models may take 30-60s.</p>
                </div>
            `;
            
            const interval = setInterval(() => {
                step = (step + 1) % loadingTexts.length;
                const msg = document.getElementById('loading-msg');
                if(msg) msg.textContent = loadingTexts[step];
            }, 3000);

            // Pick Random
            """
            
    # Modify content
    # We replace from start_index (inclusive) up to end_index (exclusive)
    # Be careful not to lose indentation of target_block_end if it was included in "between"
    # Actually, end_index points to the start of "const randomProb..."
    # So we replace everything from start of "const resultDiv..." to start of "const randomProb..."
    
    # We need to make sure we don't break indentation of new_logic.
    # The new_logic string above has newlines but maybe not correct indentation relative to the file.
    # But HTML/JS tolerates bad indentation.
    
    content = content[:start_index] + new_logic + content[end_index:]
    print("Part 1 replaced.")
else:
    print("Part 1 target not found.")

# 2. Add clearInterval using String Replace
target_fetch_end = "const data = await res.json();"
replacement_fetch_end = "clearInterval(interval);\n                const data = await res.json();"

if target_fetch_end in content:
    content = content.replace(target_fetch_end, replacement_fetch_end)
    print("Part 2 replaced.")
else:
    print("Part 2 target not found.")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
