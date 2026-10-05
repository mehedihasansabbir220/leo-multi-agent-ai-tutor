from __future__ import annotations

from pathlib import Path

from crewai import Crew, Process, Task
from .agents import make_agents
from .memory import StudentMemory
from .models import EvaluationOutput, QuizOutput, StudyPlan
from .prompts import COORDINATOR_TASK, EVALUATOR_TASK, EXPLAINER_TASK, QUIZ_TASK


def _use_project_crew_storage() -> None:
    """Keep CrewAI's kickoff database inside the project.

    CrewAI otherwise writes to ~/Library/Application Support, and SQLite
    raises "unable to open database file" when that folder is not writable.
    """
    storage = Path(__file__).resolve().parent.parent / "data" / "crewai"
    storage.mkdir(parents=True, exist_ok=True)
    target = str(storage)

    def db_storage_path() -> str:
        storage.mkdir(parents=True, exist_ok=True)
        return target

    import crewai_core.paths as paths

    paths.db_storage_path = db_storage_path
    from crewai.memory.storage import kickoff_task_outputs_storage

    kickoff_task_outputs_storage.db_storage_path = db_storage_path


class LeoTutor:
    def __init__(self):
        _use_project_crew_storage()
        self.memory = StudentMemory()
        self.coordinator, self.explainer, self.quiz_master, self.evaluator = make_agents()

    def plan_and_teach(self, request: str, on_stage=None):
        memory_context = self.memory.context()

        def watch(stage: str, nxt: str | None):
            def _callback(_output):
                if on_stage:
                    on_stage(stage, "done")
                    if nxt:
                        on_stage(nxt, "running")

            return _callback

        if on_stage:
            on_stage("coordinator", "running")

        coordinator_task = Task(
            description=COORDINATOR_TASK.format(request=request, memory=memory_context),
            expected_output="A valid StudyPlan JSON object.",
            agent=self.coordinator,
            output_pydantic=StudyPlan,
            callback=watch("coordinator", "explainer"),
        )
        explainer_task = Task(
            description=EXPLAINER_TASK.format(plan="{context}", memory=memory_context),
            expected_output="A clear lesson in Markdown with examples and recap.",
            agent=self.explainer,
            context=[coordinator_task],
            callback=watch("explainer", "quiz_master"),
        )
        quiz_task = Task(
            description=QUIZ_TASK.format(plan="{context}", lesson="{context}"),
            expected_output="A valid QuizOutput object containing 3-5 questions.",
            agent=self.quiz_master,
            context=[coordinator_task, explainer_task],
            output_pydantic=QuizOutput,
            callback=watch("quiz_master", None),
        )
        crew = Crew(
            agents=[self.coordinator, self.explainer, self.quiz_master],
            tasks=[coordinator_task, explainer_task, quiz_task],
            process=Process.sequential,
            verbose=True,
            share_crew=False,
        )
        result = crew.kickoff()
        plan = coordinator_task.output.pydantic
        quiz = quiz_task.output.pydantic
        lesson = explainer_task.output.raw
        if plan is None or quiz is None:
            raise RuntimeError("Leo could not produce the required structured plan/quiz output.")
        return plan.normalized(), lesson, quiz, result

    def evaluate(self, quiz: QuizOutput, lesson: str, answers: str, on_stage=None):
        def watch(_output):
            if on_stage:
                on_stage("evaluator", "done")

        if on_stage:
            on_stage("evaluator", "running")

        task = Task(
            description=EVALUATOR_TASK.format(
                quiz=quiz.model_dump_json(indent=2), answers=answers, lesson=lesson
            ),
            expected_output="A valid EvaluationOutput object.",
            agent=self.evaluator,
            output_pydantic=EvaluationOutput,
            callback=watch,
        )
        crew = Crew(
            agents=[self.evaluator],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            share_crew=False,
        )
        crew.kickoff()
        if task.output.pydantic is None:
            raise RuntimeError("Leo could not produce a structured evaluation.")
        return task.output.pydantic

    def remember_session(self, student_name: str, topic: str):
        self.memory.update(student_name, topic)
