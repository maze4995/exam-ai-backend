import json
import re

def strict_json_parse(text):
    # Try to extract from markdown code blocks first
    match = re.search(r'```json\s*(.*?)```', text, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON Error: {e}. Attempting repair...")
            repaired = re.sub(r'\\(?![\\"/bfnrtu])', r'\\\\', json_str)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass
            pass
            
    # Fallback: Try to find start/end of list
    match = re.search(r'^\s*\[', text, re.MULTILINE)
    if match:
        start_idx = match.start()
        end_idx = text.rfind(']')
        if end_idx != -1:
            json_str = text[start_idx : end_idx+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
    return None
