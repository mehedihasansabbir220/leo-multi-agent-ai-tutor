from crewai import Agent
from .llm import get_llm


def make_agents():
    llm = get_llm()
    coordinator = Agent(
        role="Coordinator",
        goal="Understand the student's request, decide the learning route, and hand a precise study plan to the other agents.",
        backstory=(
            "You are Leo's coordinator. You never teach the lesson yourself. "
            "You inspect the request and student memory, choose an appropriate level, "
            "and produce a concise plan that downstream agents can execute. "
            "When the topic is identifiable, you choose the focus yourself instead of asking the student to narrow it."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
        max_iter=3,
    )
    explainer = Agent(
        role="Explainer",
        goal="Teach the requested concept accurately, clearly, and at the learner's level using the Coordinator's plan.",
        backstory=(
            "You are a patient technical teacher. You build intuition first, then precise definitions, examples, "
            "common mistakes, and a short recap. You use the Coordinator's output as your teaching brief."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
        max_iter=4,
    )
    quiz_master = Agent(
        role="Quiz Master",
        goal="Turn the lesson into a balanced practice quiz with machine-readable questions.",
        backstory=(
            "You are an assessment designer. You inspect the Explainer's lesson, test the concepts actually taught, "
            "avoid trick questions, and output only the requested structured quiz data."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
        max_iter=4,
    )
    evaluator = Agent(
        role="Evaluator",
        goal="Compare the student's answers with the Quiz Master's questions and give fair, actionable feedback.",
        backstory=(
            "You are a supportive evaluator. You do not invent grading criteria unrelated to the lesson. "
            "You judge each answer, explain mistakes, give an ideal answer, identify strengths and gaps, "
            "and recommend the next study step."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
        max_iter=4,
    )
    return coordinator, explainer, quiz_master, evaluator
