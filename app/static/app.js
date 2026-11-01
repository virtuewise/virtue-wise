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

async function runAction(action, successMessage = "Saved locally.") {
  try {
    await action();
    announce(successMessage);
  } catch (error) {
    announce(error.message || "Something went wrong.", true);
  }
}

function button(label, className, action) {
  const element = document.createElement("button");
  element.type = "button";
  element.className = className;
  element.textContent = label;
  element.addEventListener("click", action);
  return element;
}

function render() {
  byId("project-title").value = model.title;
  byId("project-goal").value = model.goal;
  byId("statement-count").textContent = model.statements.length;
  byId("hypothesis-count").textContent = model.hypotheses.length;
  byId("scenario-count").textContent = model.scenarios.length;

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
    const controls = document.createElement("div");
    controls.className = "review-controls";
    controls.append(button("Edit", "button button-small", () => editStatement(statement)));
    controls.append(button("Delete", "button button-small", () => {
      if (!window.confirm("Delete this statement? Evidence-linked statements must be unlinked from hypotheses first.")) return;
      runAction(async () => {
        await request(`/api/statements/${encodeURIComponent(statement.id)}`, { method: "DELETE" });
        model = await request("/api/model");
        render();
      });
    }));
    item.append(controls);
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
    const evidenceBlock = document.createElement("div");
    evidenceBlock.className = "evidence-links";
    if (hypothesis.evidence_statement_ids.length === 0) {
      const emptyEvidence = document.createElement("p");
      emptyEvidence.className = "meta";
      emptyEvidence.textContent = "No evidence statements linked.";
      evidenceBlock.append(emptyEvidence);
    }
    hypothesis.evidence_statement_ids.forEach((statementId) => {
      const statement = model.statements.find((candidate) => candidate.id === statementId);
      if (!statement) return;
      const evidenceRow = document.createElement("div");
      evidenceRow.className = "evidence-row";
      const evidenceLabel = document.createElement("span");
      evidenceLabel.textContent = `Evidence: ${statement.text}`;
      const unlink = button("Unlink", "button button-small", () => {
        runAction(async () => {
          model = await request(`/api/hypotheses/${encodeURIComponent(hypothesis.id)}`, {
            method: "PUT",
            body: JSON.stringify({
              claim: hypothesis.claim,
              rationale: hypothesis.rationale,
              evidence_statement_ids: hypothesis.evidence_statement_ids.filter((id) => id !== statementId),
              uncertainty: hypothesis.uncertainty,
            }),
          });
          render();
        }, "Evidence link removed.");
      });
      unlink.setAttribute("aria-label", `Unlink evidence statement: ${statement.text.slice(0, 60)}`);
      evidenceRow.append(evidenceLabel, unlink);
      evidenceBlock.append(evidenceRow);
    });
    item.append(evidenceBlock);
    const editControls = document.createElement("div");
    editControls.className = "review-controls";
    editControls.append(button("Edit hypothesis", "button button-small", () => editHypothesis(hypothesis)));
    item.append(editControls);
    if (hypothesis.review_status === "proposed") {
      const controls = document.createElement("div");
      controls.className = "review-controls";
      const note = document.createElement("input");
      note.maxLength = 2000;
      note.placeholder = "Review note (optional)";
      note.setAttribute("aria-label", `Review note for ${hypothesis.claim.slice(0, 50)}`);
      controls.append(note);
      [["Accept", "accepted"], ["Revise", "revised"], ["Reject", "rejected"]].forEach(([label, status]) => {
        controls.append(button(label, "button button-small", () => runAction(async () => {
          model = await request(`/api/hypotheses/${encodeURIComponent(hypothesis.id)}/review`, {
            method: "PATCH", body: JSON.stringify({ status, note: note.value }),
          });
          render();
        })));
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

  renderScenarios();
}

function renderScenarios() {
  const list = byId("scenario-list");
  list.replaceChildren();
  model.scenarios.forEach((scenario) => {
    const card = document.createElement("article");
    card.className = "scenario-card";
    const title = document.createElement("h3");
    title.textContent = scenario.name;
    const assumptionsTitle = document.createElement("h4");
    assumptionsTitle.textContent = "Assumptions";
    const assumptions = document.createElement("ul");
    scenario.assumptions.forEach((assumption) => {
      const li = document.createElement("li");
      li.textContent = assumption;
      assumptions.append(li);
    });
    if (!scenario.assumptions.length) {
      const li = document.createElement("li");
      li.textContent = "No assumptions recorded";
      assumptions.append(li);
    }
    const outcomeTitle = document.createElement("h4");
    outcomeTitle.textContent = "Expected outcome & trade-offs";
    const outcome = document.createElement("p");
    outcome.textContent = scenario.expected_outcome || "No outcome recorded yet.";
    const controls = document.createElement("div");
    controls.className = "review-controls";
    controls.append(button("Edit", "button button-small", () => editScenario(scenario)));
    controls.append(button("Delete", "button button-small", () => {
      if (!window.confirm(`Delete scenario “${scenario.name}”?`)) return;
      runAction(async () => {
        await request(`/api/scenarios/${encodeURIComponent(scenario.id)}`, { method: "DELETE" });
        model = await request("/api/model");
        render();
      });
    }));
    card.append(title, assumptionsTitle, assumptions, outcomeTitle, outcome, controls);
    list.append(card);
  });
  byId("scenario-comparison-note").textContent = model.scenarios.length >= 2
    ? "Compare assumptions and expected outcomes side by side. Differences are descriptive, not scored predictions."
    : "Add at least two scenarios to compare their assumptions and expected outcomes side by side.";
}

async function editStatement(statement) {
  const text = window.prompt("Statement text", statement.text);
  if (text === null) return;
  const sourceLabel = window.prompt("Source label", statement.source_label);
  if (sourceLabel === null) return;
  const excerpt = window.prompt("Source excerpt (optional)", statement.source_excerpt || "");
  if (excerpt === null) return;
  await runAction(async () => {
    model = await request(`/api/statements/${encodeURIComponent(statement.id)}`, {
      method: "PUT",
      body: JSON.stringify({ ...statement, text, source_label: sourceLabel, source_excerpt: excerpt || null }),
    });
    render();
  });
}

async function editHypothesis(hypothesis) {
  const claim = window.prompt("Hypothesis", hypothesis.claim);
  if (claim === null) return;
  const rationale = window.prompt("Rationale", hypothesis.rationale);
  if (rationale === null) return;
  const uncertainty = window.prompt("Uncertainty: unknown, tentative, or supported", hypothesis.uncertainty);
  if (uncertainty === null) return;
  await runAction(async () => {
    model = await request(`/api/hypotheses/${encodeURIComponent(hypothesis.id)}`, {
      method: "PUT",
      body: JSON.stringify({
        claim, rationale, evidence_statement_ids: hypothesis.evidence_statement_ids, uncertainty,
      }),
    });
    render();
  });
}

async function editScenario(scenario) {
  const name = window.prompt("Scenario name", scenario.name);
  if (name === null) return;
  const assumptions = window.prompt("Assumptions (one per line)", scenario.assumptions.join("\n"));
  if (assumptions === null) return;
  const outcome = window.prompt("Expected outcome and trade-offs", scenario.expected_outcome);
  if (outcome === null) return;
  await runAction(async () => {
    model = await request(`/api/scenarios/${encodeURIComponent(scenario.id)}`, {
      method: "PUT",
      body: JSON.stringify({
        name, assumptions: assumptions.split("\n").map((item) => item.trim()).filter(Boolean),
        expected_outcome: outcome,
      }),
    });
    render();
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

byId("scenario-form").addEventListener("submit", (event) => {
  event.preventDefault();
  runAction(async () => {
    model = await request("/api/scenarios", { method: "POST", body: JSON.stringify({
      name: byId("scenario-name").value,
      assumptions: byId("scenario-assumptions").value.split("\n").map((item) => item.trim()).filter(Boolean),
      expected_outcome: byId("scenario-outcome").value,
    }) });
    byId("scenario-form").reset();
    render();
  });
});

byId("import-file").addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  if (!window.confirm("Importing replaces the current local model. Export a backup first if needed. Continue?")) {
    event.target.value = "";
    return;
  }
  await runAction(async () => {
    const form = new FormData();
    form.append("upload", file);
    const response = await fetch("/api/import", { method: "PUT", body: form });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `Import failed (${response.status})`);
    }
    model = await response.json();
    render();
  }, "JSON model imported and validated.");
  event.target.value = "";
});

byId("delete-model").addEventListener("click", () => {
  if (!window.confirm("Delete the saved local model? This cannot be undone unless you exported a copy.")) return;
  runAction(async () => {
    await request("/api/model", { method: "DELETE" });
    model = await request("/api/model");
    render();
  }, "Local model deleted. A new empty model is ready.");
});

runAction(async () => {
  model = await request("/api/model");
  render();
}, "Ready. Your model is stored locally by this server.");
