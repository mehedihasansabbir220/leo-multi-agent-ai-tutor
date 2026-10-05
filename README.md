# Leo — Multi-Agent AI Tutor

Leo is a fully local multi-agent study assistant built with **CrewAI + Ollama**. It uses four distinct agents that collaborate through real task handoffs:

1. **Coordinator** — understands the student's request, uses persistent student memory, chooses the learning route, and produces a structured study plan.
2. **Explainer** — receives the Coordinator's plan and teaches the concept at the selected level.
3. **Quiz Master** — receives the Coordinator plan and Explainer lesson, then creates a structured 3–5 question quiz.
4. **Evaluator** — receives the Quiz Master's questions, the lesson, and the student's answers, then grades and gives feedback.

No cloud LLM API and no API key are required. The LLM runs locally through Ollama.

## Demo

A full browser session is recorded in [demo/demovideo.mov](demo/demovideo.mov): the student request, the four-agent handoff, the lesson, the quiz, and the evaluation.

## Architecture

```text
                     Student
                        |
                        v
              +-------------------+
              |   COORDINATOR     |
              | Request + Memory  |
              +---------+---------+
                        |
                  StudyPlan
                        |
                        v
              +-------------------+
              |     EXPLAINER     |
              | Concept + Examples|
              +---------+---------+
                        |
                    Lesson
                        |
                        v
              +-------------------+
              |    QUIZ MASTER    |
              | Structured Quiz   |
              +---------+---------+
                        |
                      Quiz
                        |
                   Student answers
                        |
                        v
              +-------------------+
              |     EVALUATOR     |
              | Score + Feedback  |
              +-------------------+
                        |
                        v
                  Student Result

       +---------------------------------------+
       | SQLite persistent student memory      |
       | name / previous topic / topic history |
       +---------------------------------------+
```

## Orchestration pattern

Leo uses **CrewAI sequential orchestration**.

The handoffs are explicit through CrewAI task context:

- Coordinator task → Explainer task
- Coordinator + Explainer → Quiz Master task
- Quiz + lesson + student answers → Evaluator task

This is not four isolated prompts. The output of one role becomes context for the next role.

The human answer step intentionally occurs between Quiz Master and Evaluator so the Evaluator can grade the student's actual answers.

## Memory

Leo has a small local SQLite memory store at `data/leo_memory.db`.

It remembers:

- student name
- latest topic
- topics studied
- completed session count

Nothing is sent to a third-party memory service.

## Prompt templates

Each agent has a distinct role, goal, backstory, and task prompt in `leo/prompts.py` and `leo/agents.py`.

The prompt design keeps responsibilities separate:

- Coordinator: routing and planning
- Explainer: teaching
- Quiz Master: assessment creation
- Evaluator: assessment and feedback

## Requirements

- Python 3.10, 3.11, 3.12, or 3.13. CrewAI 1.x does not install on Python 3.14.
- Ollama
- A local Ollama model, such as `llama3.2:3b`

## Installation

### 1. Install Ollama

Install Ollama for your operating system, then verify it:

```bash
ollama --version
```

### 2. Download a local model

```bash
ollama pull llama3.2:3b
```

If your machine has more RAM, you can use another Ollama model by changing `OLLAMA_MODEL` in `.env`.

### 3. Start Ollama

On systems where Ollama is not already running as a background service:

```bash
ollama serve
```

Keep that terminal running.

### 4. Create Python environment

Mac/Linux:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

Use `python3.13` when `python3` points at Python 3.14. Check with `python --version` after activating the environment.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure local environment

Mac/Linux:

```bash
cp .env.example .env
```

Windows:

```powershell
copy .env.example .env
```

The default configuration is already local:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
LEO_DB_PATH=./data/leo_memory.db
```

No API key should be added.

## Run in the browser

From the project root, with the virtual environment active and Ollama running:

```bash
python web.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

The page shows student memory, the four-agent pipeline, the lesson, a quiz form, and the evaluation. Local models usually take a minute or two; the agent rail shows which role is working. CrewAI's verbose log still prints in the terminal that started the server.

## Run in the terminal

```bash
python main.py
```

You will see the agents work in sequence. CrewAI's verbose output shows the active agent/task, followed by Leo's clean lesson, quiz, and evaluation sections.

## Example flow

```text
Student: What do you want to learn? Explain Python closures for an intermediate developer.

[Coordinator] Understanding your request...

[Explainer] LESSON
...

[Quiz Master] QUIZ
1. ...
2. ...
3. ...

Your answers: 1: B | 2: ... | 3: C

[Evaluator] Checking your answers...

Score: 83%
Level: good
...
```

## Graceful handling

The Coordinator can mark a request as unclear instead of inventing a topic. The CLI also catches runtime failures and gives a useful local setup message instead of crashing with an unhandled traceback.

## Project structure

```text
leo_multi_agent_tutor/
├── leo/
│   ├── __init__.py
│   ├── agents.py          # four distinct CrewAI agents
│   ├── cli.py             # local CLI interface
│   ├── llm.py             # local Ollama configuration
│   ├── memory.py          # persistent SQLite student memory
│   ├── models.py          # structured Pydantic outputs
│   ├── orchestrator.py    # CrewAI sequential orchestration + handoffs
│   ├── prompts.py         # role-specific task prompt templates
│   └── web.py             # local browser API
├── web/
│   ├── index.html         # study desk page
│   ├── styles.css
│   └── app.js
├── demo/
│   └── demovideo.mov      # browser session recording
├── .env.example
├── .gitignore
├── main.py                # terminal entry point
├── web.py                 # browser entry point
├── README.md
└── requirements.txt
```

## No API keys committed

`.env` is ignored by Git. Only `.env.example` is included in the repository.

## GitHub checklist

```bash
git init
git add .
git commit -m "Build Leo multi-agent AI tutor"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

Before pushing, confirm that `.env` and `data/leo_memory.db` are not tracked.

## Assignment mapping

| Requirement | Implementation |
|---|---|
| CrewAI / AutoGen | CrewAI |
| 4 distinct roles | Coordinator, Explainer, Quiz Master, Evaluator |
| Real handoffs | CrewAI task `context` chains |
| Clear orchestration | Sequential process |
| Memory | Local SQLite student memory |
| Prompt template per role | `leo/prompts.py` + role-specific agent prompts |
| Structured quiz | Pydantic `QuizOutput` |
| Structured evaluation | Pydantic `EvaluationOutput` |
| Graceful unclear/stalled request | Coordinator clarity flag + CLI exception handling |
| Interface | Browser study desk (`python web.py`) and CLI (`python main.py`) |
| No third-party AI API | Ollama runs locally |
| API keys committed | None |
