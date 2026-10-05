const AGENTS = [
  ["coordinator", "Coordinator", "Plans the route"],
  ["explainer", "Explainer", "Teaches the lesson"],
  ["quiz_master", "Quiz Master", "Writes the quiz"],
  ["evaluator", "Evaluator", "Grades your answers"],
];

const EXAMPLES = [
  "Explain Python closures for an intermediate developer.",
  "Teach big-O notation to a beginner.",
  "How does a hash map work?",
];

const stageEl = document.querySelector("#stage");
const memoryEl = document.querySelector("#memory");
const pipelineEl = document.querySelector("#pipeline");
const healthEl = document.querySelector("#health-pills");

const view = {
  sessionId: null,
  poll: null,
  startedAt: null,
  clock: null,
  health: null,
  rendered: null,
};

boot();

async function boot() {
  renderPipeline(blankStages());
  const [health, memory] = await Promise.all([getJson("/api/health"), getJson("/api/memory")]);
  view.health = health;
  renderHealth(health);
  renderMemory(memory);
  renderStart();
}

function blankStages() {
  return Object.fromEntries(AGENTS.map(([id]) => [id, "waiting"]));
}

async function getJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail || "Request failed.";
    throw new Error(typeof detail === "string" ? detail : "Request failed.");
  }
  return data;
}

function renderHealth(health) {
  const ollama = health.ok
    ? `<span class="pill ok">Ollama running</span>`
    : `<span class="pill warn">Ollama offline</span>`;
  const modelClass = health.model_ready ? "ok" : "warn";
  const modelLabel = health.model_ready ? health.model : `${health.model} not pulled`;
  healthEl.innerHTML = `${ollama}<span class="pill ${modelClass}">${escapeHtml(modelLabel)}</span>`;
}

function renderMemory(memory) {
  const topics = (memory.topics || [])
    .slice(-8)
    .map((topic) => `<span class="chip">${escapeHtml(topic)}</span>`)
    .join("");
  memoryEl.innerHTML = `
    <p class="memory-name">${escapeHtml(memory.student_name || "Student")}</p>
    <p class="meta">Last topic: ${escapeHtml(memory.last_topic || "none")}<br />Sessions: ${memory.sessions || 0}</p>
    <div class="topics">${topics || `<span class="meta">No topics yet.</span>`}</div>
  `;
}

function renderPipeline(stages) {
  pipelineEl.innerHTML = AGENTS.map(([id, name, blurb]) => {
    const state = stages?.[id] || "waiting";
    return `
      <li class="agent ${state}">
        <i class="dot"></i>
        <div><strong>${name}</strong><span>${blurb}</span></div>
        <em class="state">${labelFor(state)}</em>
      </li>
    `;
  }).join("");
}

function labelFor(state) {
  if (state === "running") return "Working";
  if (state === "done") return "Done";
  if (state === "error") return "Stopped";
  return "Waiting";
}

function renderStart(message = "") {
  view.rendered = "start";
  const blocked = view.health && (!view.health.ok || !view.health.model_ready);
  stageEl.innerHTML = `
    <section class="card">
      ${message ? `<div class="banner">${escapeHtml(message)}</div>` : ""}
      <p class="eyebrow">Four agents, one lesson</p>
      <h2 class="display">What do you want to learn?</h2>
      <p class="lede">Coordinator plans the route, Explainer teaches it, Quiz Master writes the check, and Evaluator grades what you write back.</p>
      <form id="start-form">
        <label>
          <span>Student name</span>
          <input name="name" autocomplete="name" placeholder="Student" />
        </label>
        <label>
          <span>Learning request</span>
          <textarea name="request" required placeholder="Explain Python closures for an intermediate developer."></textarea>
        </label>
        <div class="examples">
          ${EXAMPLES.map((example) => `<button class="example" type="button" data-example="${escapeHtml(example)}">${escapeHtml(example)}</button>`).join("")}
        </div>
        <div class="actions">
          <button class="primary" type="submit" ${blocked ? "disabled" : ""}>Start lesson</button>
        </div>
      </form>
    </section>
  `;
  const form = document.querySelector("#start-form");
  const request = form.querySelector("[name=request]");
  form.querySelectorAll("[data-example]").forEach((button) => {
    button.addEventListener("click", () => {
      request.value = button.dataset.example;
      request.focus();
    });
  });
    form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    const body = {
      name: new FormData(form).get("name"),
      request: new FormData(form).get("request"),
    };
    try {
      const session = await getJson("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      view.sessionId = session.id;
      view.startedAt = Date.now();
      showSession(session);
      startPolling();
    } catch (error) {
      button.disabled = false;
      renderStart(error.message);
    }
  });
}

function startPolling() {
  stopPolling();
  view.poll = setInterval(async () => {
    try {
      const session = await getJson(`/api/sessions/${view.sessionId}`);
      showSession(session);
      if (["lesson_ready", "complete", "needs_detail", "error"].includes(session.status)) {
        stopPolling();
      }
    } catch (error) {
      stopPolling();
      renderStart(error.message);
    }
  }, 1200);
}

function stopPolling() {
  clearInterval(view.poll);
  clearInterval(view.clock);
  view.poll = null;
  view.clock = null;
}

function showSession(session) {
  renderPipeline(session.stages);
  if (session.memory) renderMemory(session.memory);
  if (session.status === "planning" || session.status === "evaluating") {
    renderWorking(session);
    return;
  }
  if (session.status === "needs_detail") {
    renderStart(session.plan?.coordinator_note || "Please add a clearer topic.");
    return;
  }
  if (session.status === "error") {
    renderStart(session.error || "Leo could not finish this session.");
    return;
  }
  if (session.status === "lesson_ready" && view.rendered !== `lesson:${session.id}`) {
    renderLesson(session);
  }
  if (session.status === "complete" && view.rendered !== `done:${session.id}`) {
    renderResults(session);
  }
}

function renderWorking(session) {
  const key = `${session.status}:${session.stage}`;
  const elapsed = view.startedAt ? Math.round((Date.now() - view.startedAt) / 1000) : 0;
  if (view.rendered === key) {
    const clock = document.querySelector("#elapsed");
    if (clock) clock.textContent = `${elapsed}s`;
    return;
  }
  view.rendered = key;
  const title = session.status === "evaluating" ? "Checking your answers" : "The crew is working";
  const copy = session.status === "evaluating"
    ? "Evaluator is comparing your answers with the lesson."
    : "Local models take a minute or two. The rail shows which agent is active.";
  stageEl.innerHTML = `
    <section class="card working">
      <p class="eyebrow">In progress</p>
      <h2 class="display">${title}</h2>
      <p class="lede">${copy}</p>
      <div class="pulse" aria-hidden="true"><i></i></div>
      <p class="meta">Elapsed <span id="elapsed">${elapsed}s</span></p>
    </section>
  `;
  clearInterval(view.clock);
  view.clock = setInterval(() => {
    const clock = document.querySelector("#elapsed");
    if (clock && view.startedAt) clock.textContent = `${Math.round((Date.now() - view.startedAt) / 1000)}s`;
  }, 1000);
}

function renderLesson(session) {
  view.rendered = `lesson:${session.id}`;
  const plan = session.plan || {};
  const quiz = session.quiz || { questions: [], instructions: "" };
  const chips = [
    plan.topic,
    plan.level,
    plan.objective,
  ].filter(Boolean).map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("");
  stageEl.innerHTML = `
    <section class="paper">
      ${session.error ? `<div class="banner">${escapeHtml(session.error)}</div>` : ""}
      <p class="eyebrow">Explainer</p>
      <h2>${escapeHtml(plan.topic || "Lesson")}</h2>
      <div class="plan">${chips}</div>
      <div class="lesson">${renderMarkdown(session.lesson || "")}</div>
      <form id="quiz-form">
        <h3>Quiz</h3>
        <p>${escapeHtml(quiz.instructions || "Answer each question.")}</p>
        <div class="quiz">
          ${(quiz.questions || []).map(renderQuestion).join("")}
        </div>
        <div class="actions">
          <button class="primary" type="submit">Submit answers</button>
          <button class="ghost" type="button" id="restart">New topic</button>
        </div>
      </form>
    </section>
  `;
  document.querySelector("#restart").addEventListener("click", () => {
    view.sessionId = null;
    renderPipeline(blankStages());
    renderStart();
  });
  document.querySelector("#quiz-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    const answers = (quiz.questions || []).map((question) => {
      const field = form.querySelector(`[name="q-${question.id}"]:checked`) || form.querySelector(`[name="q-${question.id}"]`);
      const value = field ? field.value.trim() : "";
      return `${question.id}: ${value || "(blank)"}`;
    }).join(" | ");
    try {
      view.startedAt = Date.now();
      const next = await getJson(`/api/sessions/${session.id}/answers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers }),
      });
      showSession(next);
      startPolling();
    } catch (error) {
      button.disabled = false;
      const banner = document.createElement("div");
      banner.className = "banner";
      banner.textContent = error.message;
      form.prepend(banner);
    }
  });
}

function renderQuestion(question) {
  const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const meta = `${question.difficulty || "question"} · ${question.answer_type === "short_answer" ? "short answer" : "multiple choice"}`;
  let body = "";
  if (question.options && question.options.length && question.answer_type !== "short_answer") {
    body = `<div class="options">${question.options.map((option, index) => `
      <label>
        <input type="radio" name="q-${question.id}" value="${letters[index] || index + 1}" required />
        <span><strong>${letters[index] || index + 1}.</strong> ${escapeHtml(option)}</span>
      </label>
    `).join("")}</div>`;
  } else {
    body = `<textarea name="q-${question.id}" required placeholder="Write your answer"></textarea>`;
  }
  return `
    <article class="question">
      <p class="q-meta">${escapeHtml(meta)}</p>
      <p>${question.id}. ${escapeHtml(question.question)}</p>
      ${body}
    </article>
  `;
}

function renderResults(session) {
  view.rendered = `done:${session.id}`;
  const evaluation = session.evaluation;
  const score = Math.round(evaluation.overall_score || 0);
  const items = (evaluation.items || []).map((item) => `
    <article class="item">
      <strong class="${item.correct ? "good" : "bad"}">${item.correct ? "Correct" : "Review"} · Question ${item.question_id}</strong>
      <p>${escapeHtml(item.feedback)}</p>
      <p class="meta">Ideal answer: ${escapeHtml(item.ideal_answer)}</p>
    </article>
  `).join("");
  const strengths = listOrEmpty(evaluation.strengths);
  const review = listOrEmpty(evaluation.areas_to_review);
  stageEl.innerHTML = `
    <section class="card results">
      <p class="eyebrow">Evaluator</p>
      <div class="score-row">
        <div class="dial" style="--score:${score}"><span>${score}%</span></div>
        <div>
          <p class="level">${escapeHtml((evaluation.performance_level || "").replaceAll("_", " "))}</p>
          <h2 class="display">Your result</h2>
          <p class="lede">${escapeHtml(evaluation.next_step || "")}</p>
        </div>
      </div>
      ${items}
      <div class="split">
        <div><h3>Strengths</h3>${strengths}</div>
        <div><h3>Review next</h3>${review}</div>
      </div>
      <div class="actions">
        <button class="primary" type="button" id="again">Study another topic</button>
      </div>
    </section>
  `;
  document.querySelector("#again").addEventListener("click", () => {
    view.sessionId = null;
    renderPipeline(blankStages());
    renderStart();
  });
}

function listOrEmpty(items) {
  if (!items || !items.length) return `<p class="meta">None noted.</p>`;
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderMarkdown(source) {
  const escaped = escapeHtml(source || "");
  const withCode = escaped.replace(/```([\s\S]*?)```/g, (_match, code) => `<pre><code>${code.trim()}</code></pre>`);
  const lines = withCode.split("\n");
  let html = "";
  let list = false;
  const flush = () => {
    if (list) {
      html += "</ul>";
      list = false;
    }
  };
  for (const line of lines) {
    if (line.startsWith("<pre>")) {
      flush();
      html += line;
      continue;
    }
    if (/^#{1,4} /.test(line)) {
      flush();
      const level = line.match(/^#+/)[0].length;
      html += `<h${Math.min(level + 1, 4)}>${inline(line.replace(/^#{1,4} /, ""))}</h${Math.min(level + 1, 4)}>`;
      continue;
    }
    if (/^\s*[-*] /.test(line)) {
      if (!list) {
        html += "<ul>";
        list = true;
      }
      html += `<li>${inline(line.replace(/^\s*[-*] /, ""))}</li>`;
      continue;
    }
    if (!line.trim()) {
      flush();
      continue;
    }
    flush();
    html += `<p>${inline(line)}</p>`;
  }
  flush();
  return html;
}

function inline(text) {
  return text
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
