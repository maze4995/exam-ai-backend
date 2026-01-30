import json
try:
    from src.parser import StructureParser
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.getcwd(), 'src'))
    from src.parser import StructureParser

def test_variations():
    parser = StructureParser()
    
    print("--- Case 1: 서술형 (No Options, No Image) ---")
    text_descriptive = """1265
다음은 어떤 화학 반응의 화학 반응식이다.
$N_2 + 3H_2 -> 2NH_3$
이 반응에서 산화된 물질과 환원된 물질을 각각 쓰시오."""
    
    result1 = parser.parse("1265", 51, text_descriptive)
    print(json.dumps(result1.model_dump(), indent=2, ensure_ascii=False))

    print("\n--- Case 2: 자료 없는 일반형 (Text-only, Standard) ---")
    text_simple = """1266
다음 중 신소재에 대한 설명으로 옳은 것만을 <보기>에서 있는 대로 고른 것은?
< 보기 >
ㄱ. 초전도체는 임계 온도 이하에서 저항이 0이 된다.
ㄴ. 그래핀은 강철보다 강도가 약하다.
① ㄱ   ② ㄴ   ③ ㄱ, ㄴ
④ ㄴ, ㄷ   ⑤ ㄱ, ㄴ, ㄷ"""
    
    result2 = parser.parse("1266", 51, text_simple)
    print(json.dumps(result2.model_dump(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_variations()
