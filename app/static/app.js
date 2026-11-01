const byId = (id) => document.getElementById(id);
let model = null;

function announce(message, isError = false) {
  const notice = byId("notice");
  notice.textContent = message;
  notice.classList.toggle("notice-error", isError);
}

async function request(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : detail;
    } catch { /* Keep the status-based message. */ }
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

async function runAction(action) {
  try {
    await action();
    announce("Saved locally.");
  } catch (error) {
    announce(error.message || "Something went wrong.", true);
  }
}

function render() {
  byId("project-title").value = model.title;
  byId("project-goal").value = model.goal;
  byId("statement-count").textContent = model.statements.length;
  byId("hypothesis-count").textContent = model.hypotheses.length;
  const statementList = byId("statement-list");
  statementList.replaceChildren();
  const evidenceSelect = byId("hypothesis-evidence");
  evidenceSelect.replaceChildren();
  model.statements.forEach((statement, index) => {
    const item = document.createElement("li");
    item.className = "item-card";
    const text = document.createElement("p");
    text.textContent = statement.text;
    const source = document.createElement("span");
    source.className = "meta";
    source.textContent = `Source: ${statement.source_label}`;
    item.append(text, source);
    if (statement.source_excerpt) {
      const excerpt = document.createElement("p");
      excerpt.className = "excerpt";
      excerpt.textContent = statement.source_excerpt;
      item.append(excerpt);
    }
    statementList.append(item);
    const option = document.createElement("option");
    option.value = statement.id;
    option.textContent = `${index + 1}. ${statement.text.slice(0, 90)}`;
    evidenceSelect.append(option);
  });
  const hypothesisList = byId("hypothesis-list");
  hypothesisList.replaceChildren();
  model.hypotheses.forEach((hypothesis) => {
    const item = document.createElement("li");
    item.className = "item-card hypothesis-card";
    const claim = document.createElement("p");
    claim.className = "claim";
    claim.textContent = hypothesis.claim;
    const meta = document.createElement("span");
    meta.className = "meta";
    meta.textContent = `${hypothesis.review_status} · uncertainty: ${hypothesis.uncertainty} · evidence links: ${hypothesis.evidence_statement_ids.length}`;
    item.append(claim, meta);
    if (hypothesis.rationale) {
      const rationale = document.createElement("p");
      rationale.textContent = hypothesis.rationale;
      item.append(rationale);
    }
    if (hypothesis.review_status === "proposed") {
      const controls = document.createElement("div");
      controls.className = "review-controls";
      const note = document.createElement("input");
      note.maxLength = 2000;
      note.placeholder = "Review note (optional)";
      note.setAttribute("aria-label", "Review note");
      controls.append(note);
      [["Accept", "accepted"], ["Revise", "revised"], ["Reject", "rejected"]].forEach(([label, status]) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "button button-small";
        button.textContent = label;
        button.addEventListener("click", () => runAction(async () => {
          model = await request(`/api/hypotheses/${encodeURIComponent(hypothesis.id)}/review`, {
            method: "PATCH", body: JSON.stringify({ status, note: note.value }),
          });
          render();
        }));
        controls.append(button);
      });
      item.append(controls);
    } else if (hypothesis.review_note) {
      const note = document.createElement("p");
      note.className = "excerpt";
      note.textContent = `Review note: ${hypothesis.review_note}`;
      item.append(note);
    }
    hypothesisList.append(item);
  });
}

byId("project-form").addEventListener("submit", (event) => {
  event.preventDefault();
  runAction(async () => {
    model.title = byId("project-title").value.trim();
    model.goal = byId("project-goal").value.trim();
    model = await request("/api/model", { method: "PUT", body: JSON.stringify(model) });
    render();
  });
});

byId("statement-form").addEventListener("submit", (event) => {
  event.preventDefault();
  runAction(async () => {
    model = await request("/api/statements", { method: "POST", body: JSON.stringify({
      text: byId("statement-text").value,
      source_label: byId("source-label").value,
      source_excerpt: byId("source-excerpt").value || null,
    }) });
    byId("statement-form").reset();
    byId("source-label").value = "User provided";
    render();
  });
});

byId("hypothesis-form").addEventListener("submit", (event) => {
  event.preventDefault();
  runAction(async () => {
    const evidence = [...byId("hypothesis-evidence").selectedOptions].map((option) => option.value);
    model = await request("/api/hypotheses", { method: "POST", body: JSON.stringify({
      claim: byId("hypothesis-claim").value,
      rationale: byId("hypothesis-rationale").value,
      evidence_statement_ids: evidence,
      uncertainty: byId("hypothesis-uncertainty").value,
    }) });
    byId("hypothesis-form").reset();
    render();
  });
});

byId("delete-model").addEventListener("click", () => {
  if (!window.confirm("Delete the saved local model? This cannot be undone unless you exported a copy.")) return;
  runAction(async () => {
    await request("/api/model", { method: "DELETE" });
    model = await request("/api/model");
    render();
    announce("Local model deleted. A new empty model is ready.");
  });
});

runAction(async () => {
  model = await request("/api/model");
  render();
  announce("Ready. Your model is stored locally by this server.");
});
