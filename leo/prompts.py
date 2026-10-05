COORDINATOR_TASK = """
Student request: {request}

Persistent student memory:
{memory}

Create a StudyPlan.
If the student named a subject, set request_clear=true, put that subject in topic, and choose teaching_focus and quiz_focus yourself.
Set request_clear=false only when topic is empty. Leave coordinator_note empty when request_clear is true.
Choose level from the request and write a one-sentence objective.
"""

EXPLAINER_TASK = """
Teach the student about the topic using the Coordinator's StudyPlan below.

Coordinator plan:
{plan}

Student memory:
{memory}

Produce a lesson suitable for the selected level. Include:
1. a simple intuition,
2. a precise explanation,
3. one or two concrete examples,
4. common mistakes or misconceptions,
5. a concise recap.
Do not create quiz questions; the Quiz Master will do that next.
"""

QUIZ_TASK = """
Create a quiz from the Explainer lesson and Coordinator plan.

Coordinator plan:
{plan}

Explainer lesson:
{lesson}

Return 3-5 questions. Mix multiple-choice and short-answer questions when appropriate.
Every question must test a concept actually covered by the lesson. Use unique integer IDs starting at 1.
For multiple choice, provide 3-4 options. For short answer, options must be an empty list.
"""

EVALUATOR_TASK = """
Evaluate the student's answers against the Quiz Master's quiz and the lesson.

Quiz:
{quiz}

Student answers:
{answers}

Lesson:
{lesson}

Grade each question independently. For multiple choice, judge the selected option exactly.
For short answers, give credit for correct meaning even if wording differs.
Return a percentage score, performance level, per-question feedback, ideal answers, strengths, areas to review, and one next step.
"""
