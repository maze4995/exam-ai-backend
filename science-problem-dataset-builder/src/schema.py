from typing import List, Optional
from pydantic import BaseModel, Field

class ProblemStructure(BaseModel):
    header: Optional[str] = Field(None, description="Problem Number e.g., '1264'")
    scenario: Optional[str] = Field(None, description="Context/Scenario text")
    visuals: List[str] = Field(default=[], description="Paths to cropped visual images")
    directive: Optional[str] = Field(None, description="The specific question, e.g., 'Correct one?'")
    propositions: Optional[str] = Field(None, description="Content of the <Box>, e.g., 'ㄱ..., ㄴ...'")
    options: List[str] = Field(default=[], description="Multiple choice options ①~⑤")

class ScienceProblem(BaseModel):
    id: str
    page: int
    unit: Optional[str] = None
    difficulty: Optional[str] = None
    question_type: Optional[str] = None
    content: ProblemStructure
    full_text: str

# Example usage
if __name__ == "__main__":
    print(ScienceProblem.schema_json(indent=2))
