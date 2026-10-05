from __future__ import annotations

import json
import sys

from .orchestrator import LeoTutor


def print_banner():
    print("\n" + "=" * 72)
    print("LEO — MULTI-AGENT AI TUTOR")
    print("Local CrewAI + Ollama | Coordinator → Explainer → Quiz Master → Evaluator")
    print("=" * 72)


def main():
    print_banner()
    name = input("Student name [Student]: ").strip() or "Student"
    request = input("What do you want to learn? ").strip()
    if not request:
        print("Please provide a topic or learning request.")
        return 1

    try:
        tutor = LeoTutor()
        print("\n[Coordinator] Understanding your request and planning the lesson...\n")
        plan, lesson, quiz, _ = tutor.plan_and_teach(request)
        if not plan.request_clear:
            print("\n[Coordinator] I need a little more detail before teaching:")
            print(plan.coordinator_note or "Please specify the topic and what you want to learn.")
            return 0

        tutor.remember_session(name, plan.topic or request)
        print("\n" + "-" * 72)
        print("[Explainer] LESSON")
        print("-" * 72)
        print(lesson)

        print("\n" + "-" * 72)
        print("[Quiz Master] QUIZ")
        print("-" * 72)
        print(quiz.instructions)
        for q in quiz.questions:
            print(f"\n{q.id}. {q.question} [{q.difficulty}]")
            for i, option in enumerate(q.options, 1):
                print(f"   {chr(64+i)}. {option}")

        print("\nEnter your answers. Example: 1: B | 2: explain in your own words | 3: C")
        answers = input("Your answers: ").strip()
        if not answers:
            print("No answers entered; evaluation skipped.")
            return 0

        print("\n[Evaluator] Checking your answers and preparing feedback...\n")
        evaluation = tutor.evaluate(quiz, lesson, answers)
        print("-" * 72)
        print("[Evaluator] FEEDBACK")
        print("-" * 72)
        print(f"Score: {evaluation.overall_score:.0f}%")
        print(f"Level: {evaluation.performance_level}")
        for item in evaluation.items:
            mark = "✓" if item.correct else "✗"
            print(f"\n{mark} Question {item.question_id}: {item.feedback}")
            print(f"   Ideal answer: {item.ideal_answer}")
        if evaluation.strengths:
            print("\nStrengths:")
            for item in evaluation.strengths:
                print(f"  • {item}")
        if evaluation.areas_to_review:
            print("\nReview:")
            for item in evaluation.areas_to_review:
                print(f"  • {item}")
        print(f"\nNext step: {evaluation.next_step}")
        return 0
    except KeyboardInterrupt:
        print("\nSession cancelled.")
        return 130
    except Exception as exc:
        print("\nLeo could not complete the session gracefully.")
        print(f"Reason: {exc}")
        print("Check that Ollama is running and the configured model is installed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
