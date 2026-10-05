"""Local browser interface for Leo. The CLI in leo.cli remains available."""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .models import QuizOutput
from .orchestrator import LeoTutor

load_dotenv()

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
STAGES = ("coordinator", "explainer", "quiz_master", "evaluator")

app = FastAPI(title="Leo", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

_lock = threading.Lock()
_sessions: dict[str, dict] = {}


class StartBody(BaseModel):
    name: str = "Student"
    request: str = Field(min_length=1, max_length=4000)


class AnswersBody(BaseModel):
    answers: str = Field(min_length=1, max_length=8000)


def _fresh_stages() -> dict[str, str]:
    return {stage: "waiting" for stage in STAGES}


def _public(session: dict) -> dict:
    return {
        "id": session["id"],
        "status": session["status"],
        "stage": session["stage"],
        "stages": session["stages"],
        "name": session["name"],
        "request": session["request"],
        "plan": session["plan"],
        "lesson": session["lesson"],
        "quiz": session["quiz"],
        "evaluation": session["evaluation"],
        "error": session["error"],
        "memory": session["memory"],
    }


def _update(session_id: str, **changes) -> None:
    with _lock:
        _sessions[session_id].update(changes)


def _ollama_status() -> dict:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    try:
        with urllib.request.urlopen(f"{base}/api/tags", timeout=2) as response:
            payload = json.load(response)
        names = [item.get("name", "") for item in payload.get("models", [])]
        ready = model in names or f"{model}:latest" in names
        return {
            "ok": True,
            "model": model,
            "model_ready": ready,
            "models": names,
            "base_url": base,
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {
            "ok": False,
            "model": model,
            "model_ready": False,
            "models": [],
            "base_url": base,
            "error": str(exc),
        }


def _require_ollama() -> dict:
    status = _ollama_status()
    if not status["ok"]:
        raise HTTPException(
            status_code=503,
            detail="Ollama is not running. Start it, then try again.",
        )
    if not status["model_ready"]:
        raise HTTPException(
            status_code=503,
            detail=f"Model '{status['model']}' is not installed. Run: ollama pull {status['model']}",
        )
    return status


def _run_lesson(session_id: str, name: str, request: str) -> None:
    tutor = LeoTutor()

    def on_stage(stage: str, state: str) -> None:
        with _lock:
            session = _sessions[session_id]
            session["stages"][stage] = state
            if state == "running":
                session["stage"] = stage

    try:
        plan, lesson, quiz, _result = tutor.plan_and_teach(request, on_stage=on_stage)
        if not plan.request_clear:
            _update(
                session_id,
                status="needs_detail",
                stage="coordinator",
                plan=plan.model_dump(),
                error=None,
                memory=tutor.memory.get(),
            )
            return
        tutor.remember_session(name, plan.topic or request)
        _update(
            session_id,
            status="lesson_ready",
            stage="quiz_master",
            plan=plan.model_dump(),
            lesson=lesson,
            quiz=quiz.model_dump(),
            error=None,
            memory=tutor.memory.get(),
            _quiz=quiz,
            _lesson=lesson,
            _tutor=tutor,
        )
    except Exception as exc:
        _update(session_id, status="error", error=str(exc))


def _run_evaluation(session_id: str, answers: str) -> None:
    with _lock:
        session = _sessions[session_id]
        tutor: LeoTutor = session["_tutor"]
        quiz: QuizOutput = session["_quiz"]
        lesson: str = session["_lesson"]

    def on_stage(stage: str, state: str) -> None:
        with _lock:
            current = _sessions[session_id]
            current["stages"][stage] = state
            if state == "running":
                current["stage"] = stage

    try:
        evaluation = tutor.evaluate(quiz, lesson, answers, on_stage=on_stage)
        _update(
            session_id,
            status="complete",
            stage="evaluator",
            evaluation=evaluation.model_dump(),
            error=None,
            memory=tutor.memory.get(),
        )
    except Exception as exc:
        with _lock:
            session = _sessions[session_id]
            session["status"] = "lesson_ready"
            session["error"] = str(exc)
            session["stages"]["evaluator"] = "waiting"


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health():
    return _ollama_status()


@app.get("/api/memory")
def memory():
    return LeoTutor().memory.get()


@app.post("/api/sessions")
def start_session(body: StartBody):
    _require_ollama()
    session_id = uuid.uuid4().hex
    name = body.name.strip() or "Student"
    request = body.request.strip()
    session = {
        "id": session_id,
        "status": "planning",
        "stage": "coordinator",
        "stages": _fresh_stages(),
        "name": name,
        "request": request,
        "plan": None,
        "lesson": None,
        "quiz": None,
        "evaluation": None,
        "error": None,
        "memory": LeoTutor().memory.get(),
        "_quiz": None,
        "_lesson": None,
        "_tutor": None,
    }
    session["stages"]["coordinator"] = "running"
    with _lock:
        _sessions[session_id] = session
    threading.Thread(
        target=_run_lesson,
        args=(session_id, name, request),
        daemon=True,
    ).start()
    return _public(session)


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    with _lock:
        session = _sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        return _public(session)


@app.post("/api/sessions/{session_id}/answers")
def submit_answers(session_id: str, body: AnswersBody):
    _require_ollama()
    with _lock:
        session = _sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        if session["status"] != "lesson_ready":
            raise HTTPException(status_code=409, detail="The quiz is not ready for answers.")
        session["status"] = "evaluating"
        session["stage"] = "evaluator"
        session["stages"]["evaluator"] = "running"
        session["error"] = None
        snapshot = _public(session)
    threading.Thread(
        target=_run_evaluation,
        args=(session_id, body.answers.strip()),
        daemon=True,
    ).start()
    return snapshot


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
