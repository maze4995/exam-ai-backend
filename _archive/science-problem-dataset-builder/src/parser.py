import re
from typing import List, Dict, Tuple
try:
    from .schema import ScienceProblem, ProblemStructure
except ImportError:
    from schema import ScienceProblem, ProblemStructure

class StructureParser:
    def __init__(self):
        # Patterns
        self.box_start_pattern = re.compile(r'<\s*보\s*기\s*>')
        self.option_pattern = re.compile(r'([①②③④⑤❶❷❸❹❺])')
        self.directive_pattern = re.compile(r'([^\n]+(것은\?|하시오|구하시오)\s*)$', re.MULTILINE)

    def parse(self, p_id: str, page_num: int, raw_text: str) -> ScienceProblem:
        raw_text = raw_text.strip()
        lines = raw_text.split('\n')
        
        # 1. Header
        header = p_id
        
        # 2. Split Options (Bottom up)
        option_start_idx = len(lines)
        for i, line in enumerate(lines):
            if self.option_pattern.search(line):
                option_start_idx = i
                break
        
        body_lines = lines[:option_start_idx]
        options_text = "\n".join(lines[option_start_idx:]) if option_start_idx < len(lines) else ""
        
        # Parse Options
        options = []
        if options_text:
            parts = self.option_pattern.split(options_text)
            current_opt = ""
            for p in parts:
                if self.option_pattern.match(p):
                    if current_opt: options.append(current_opt.strip())
                    current_opt = p
                else:
                    current_opt += p
            if current_opt: options.append(current_opt.strip())

        # 3. Find Directive (The question sentence)
        # Look for line ending with '?' or containing specific instruction keywords
        directive_idx = -1
        for i, line in enumerate(body_lines):
            if line.strip().endswith("?") or "고른 것은" in line or "서술하시오" in line:
                directive_idx = i
                # Keep going? usually the last such line is the main directive
        
        scenario_text = ""
        directive_text = ""
        propositions_text = ""

        if directive_idx != -1:
            # Scenario is everything before Directive
            scenario_text = "\n".join(body_lines[:directive_idx]).strip()
            # Remove header from scenario if present
            if scenario_text.startswith(header):
                scenario_text = scenario_text[len(header):].strip()
                
            directive_text = body_lines[directive_idx].strip()
            
            # Propositions is everything between Directive and Options
            propositions_text = "\n".join(body_lines[directive_idx+1:]).strip()
        else:
            # Fallback: Assume all is scenario if no directive found? 
            # Or split by <보기> if exists
            scenario_text = "\n".join(body_lines)

        # Cleanup Propositions (remove <보기> tag)
        propositions_text = re.sub(r'<\s*보\s*기\s*>', '', propositions_text).strip()

        return ScienceProblem(
            id=p_id,
            page=page_num,
            full_text=raw_text,
            content=ProblemStructure(
                header=header,
                scenario=scenario_text if scenario_text else None,
                directive=directive_text,
                propositions=propositions_text if propositions_text else None,
                options=options
            )
        )

# Test with a dummy string
if __name__ == "__main__":
    dummy_text = """1264
그림 (가)는 변전소에서 전력을 송전하는 모습을 나타낸 것이다.
이에 대한 설명으로 옳은 것만을 <보기>에서 있는 대로 고른 것은?
< 보기 >
ㄱ. 교류 전류가 흐른다.
ㄴ. 저항은 A가 크다.
① ㄱ   ② ㄴ   ③ ㄱ, ㄴ
④ ㄴ, ㄷ   ⑤ ㄱ, ㄴ, ㄷ"""
    
    parser = StructureParser()
    result = parser.parse("1264", 50, dummy_text)
    import json
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
