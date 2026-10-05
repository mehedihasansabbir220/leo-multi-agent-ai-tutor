from typing import List, Literal
from pydantic import BaseModel, Field


_PLACEHOLDER_TOPICS = {
    "",
    "none",
    "n/a",
    "na",
    "unknown",
    "unclear",
    "not identified",
    "no subject",
    "no topic",
}


class StudyPlan(BaseModel):
    request_clear: bool = True
    topic: str = ""
    level: str = "beginner"
    objective: str = ""
    teaching_focus: List[str] = Field(default_factory=list)
    quiz_focus: List[str] = Field(default_factory=list)
    coordinator_note: str = ""

    def has_topic(self) -> bool:
        return self.topic.strip().lower().strip(".") not in _PLACEHOLDER_TOPICS

    def normalized(self) -> "StudyPlan":
        """A named topic is teachable even if a small model sets request_clear false."""
        if self.has_topic():
            self.request_clear = True
        return self


class QuizQuestion(BaseModel):
    id: int
    question: str
    options: List[str] = Field(default_factory=list)
    answer_type: Literal["multiple_choice", "short_answer"]
    difficulty: Literal["easy", "medium", "hard"]
    concept: str


class QuizOutput(BaseModel):
    topic: str
    instructions: str
    questions: List[QuizQuestion] = Field(min_length=3, max_length=5)


class EvaluationItem(BaseModel):
    question_id: int
    correct: bool
    score: float = Field(ge=0, le=1)
    feedback: str
    ideal_answer: str


class EvaluationOutput(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    performance_level: Literal["needs_review", "developing", "good", "excellent"]
    items: List[EvaluationItem]
    strengths: List[str] = Field(default_factory=list)
    areas_to_review: List[str] = Field(default_factory=list)
    next_step: str
