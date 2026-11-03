const byId = (id) => document.getElementById(id);
let model = null;
let modelRevision = null;

function announce(message, isError = false) {
  const notice = byId("notice");
  notice.textContent = message;
  notice.classList.toggle("notice-error", isError);
}

async function request(url, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if ((url === "/api/model" && options.method === "PUT") || url === "/api/import") {
    if (!modelRevision) throw new Error("Reload the project before replacing or importing it.");
    headers["If-Match"] = `"${modelRevision}"`;
  }
  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : detail;
    } catch { /* Keep the status-based message. */ }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  const body = await response.json();
  const etag = response.headers.get("ETag");
  if (etag) {
    modelRevision = etag.replace(/^"|"$/g, "");
  }
  return body;
}

let actionInProgress = false;

async function runAction(action, successMessage = "Saved locally.") {
  if (actionInProgress) return;
  actionInProgress = true;
  const controls = [...document.querySelectorAll("button, input, select, textarea")];
  const disabledStates = controls.map((control) => control.disabled);
  controls.forEach((control) => { control.disabled = true; });
  document.body.setAttribute("aria-busy", "true");
  try {
    await action();
    announce(successMessage);
  } catch (error) {
    announce(error.message || "Something went wrong.", true);
  } finally {
    controls.forEach((control, index) => { control.disabled = disabledStates[index]; });
    document.body.removeAttribute("aria-busy");
    actionInProgress = false;
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

function openEditor(kind, item) {
  const definitions = {
    statement: {
      title: "Edit statement",
      fields: [
        { key: "text", label: "Statement text", multiline: true, required: true, maxLength: 2000 },
        { key: "source_label", label: "Source label", required: true, maxLength: 300 },
        { key: "source_excerpt", label: "Source excerpt (optional)", multiline: true, maxLength: 2000 },
      ],
      save: (values) => request(`/api/statements/${encodeURIComponent(item.id)}`, {
        method: "PUT",
        body: JSON.stringify({ ...item, ...values, source_excerpt: values.source_excerpt || null }),
      }),
    },
    hypothesis: {
      title: "Edit hypothesis",
      fields: [
        { key: "claim", label: "Hypothesis", multiline: true, required: true, maxLength: 2000 },
        { key: "rationale", label: "Rationale and limitations", multiline: true, maxLength: 2000 },
        { key: "uncertainty", label: "Uncertainty", options: [
          ["unknown", "Unknown"], ["tentative", "Tentative"], ["supported", "Supported (reason documented)"],
        ] },
      ],
      save: (values) => request(`/api/hypotheses/${encodeURIComponent(item.id)}`, {
        method: "PUT",
        body: JSON.stringify({
          claim: values.claim,
          rationale: values.rationale,
          uncertainty: values.uncertainty,
          evidence_statement_ids: item.evidence_statement_ids,
        }),
      }),
    },
    scenario: {
      title: "Edit scenario",
      fields: [
        { key: "name", label: "Scenario name", required: true, maxLength: 200 },
        { key: "assumptions", label: "Assumptions (one per line)", multiline: true, maxLength: 10000,
          value: item.assumptions.join("\n") },
        { key: "expected_outcome", label: "Expected outcome and trade-offs", multiline: true, maxLength: 2000 },
      ],
      save: (values) => request(`/api/scenarios/${encodeURIComponent(item.id)}`, {
        method: "PUT",
        body: JSON.stringify({
          name: values.name,
          assumptions: values.assumptions.split("\n").map((value) => value.trim()).filter(Boolean),
          expected_outcome: values.expected_outcome,
        }),
      }),
    },
  };
  const definition = definitions[kind];
  const dialog = document.createElement("dialog");
  dialog.className = "editor-dialog";
  dialog.setAttribute("aria-labelledby", "editor-dialog-title");
  const form = document.createElement("form");
  form.className = "stack editor-form";
  const heading = document.createElement("h2");
  heading.id = "editor-dialog-title";
  heading.textContent = definition.title;
  form.append(heading);
  const controls = [];
  definition.fields.forEach((field) => {
    const label = document.createElement("label");
    const control = field.options ? document.createElement("select")
      : field.multiline ? document.createElement("textarea") : document.createElement("input");
    const controlId = `editor-${field.key}`;
    label.htmlFor = controlId;
    label.textContent = field.label;
    control.id = controlId;
    control.name = field.key;
    if (field.options) {
      field.options.forEach(([value, text]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = text;
        control.append(option);
      });
    } else {
      control.maxLength = field.maxLength;
      if (field.multiline) control.rows = 4;
      if (field.required) control.required = true;
    }
    const value = field.value ?? item[field.key] ?? "";
    control.value = value ?? "";
    form.append(label, control);
    controls.push([field.key, control]);
  });
  const actions = document.createElement("div");
  actions.className = "review-controls editor-actions";
  const cancel = button("Cancel", "button button-small", () => dialog.close());
  cancel.value = "cancel";
  const save = document.createElement("button");
  save.type = "submit";
  save.className = "button button-primary";
  save.textContent = "Save changes";
  actions.append(cancel, save);
  form.append(actions);
  dialog.append(form);
  document.body.append(dialog);
  dialog.addEventListener("close", () => dialog.remove(), { once: true });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const values = Object.fromEntries(controls.map(([key, control]) => [key, control.value.trim()]));
    save.disabled = true;
    save.textContent = "Saving…";
    try {
      model = await definition.save(values);
      dialog.close();
      render();
      announce("Changes saved. Review status may have returned to proposed.");
    } catch (error) {
      announce(error.message || "Could not save changes.", true);
      save.disabled = false;
      save.textContent = "Save changes";
    }
  });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.showModal();
  controls[0]?.[1].focus();
}

function editStatement(statement) { openEditor("statement", statement); }
function editHypothesis(hypothesis) { openEditor("hypothesis", hypothesis); }
function editScenario(scenario) { openEditor("scenario", scenario); }

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

let intakeDraft = null;

function makeIntakeDraft(rawText) {
  const original = rawText.trim();
  const blocks = original.split(/\n\s*\n/).map((part) => part.trim()).filter(Boolean);
  const statements = blocks.flatMap((block) => {
    const lines = block.split(/\n(?=\s*(?:[-*•]|\d+[.)])\s+)/);
    return lines.map((line) => line.replace(/^\s*(?:[-*•]|\d+[.)])\s+/, "").trim()).filter(Boolean);
  }).slice(0, 100);
  const firstLine = original.split(/\r?\n/).find((line) => line.trim()) || original;
  const title = firstLine.replace(/^\s*(?:[-*•]|\d+[.)])\s+/, "").replace(/[.!?]$/, "").slice(0, 80);
  return {
    title: title || "New exploration",
    goal: original,
    statements: statements.length ? statements : [original],
    questions: [
      "What would you most like to understand, decide or change?",
      "Which parts of this description are directly observed, and which are assumptions?",
      "What evidence or source would help verify the important claims?",
      "What information might be missing, and who or what could provide it?",
      "What result would cause you to revise your current view?"
    ]
  };
}

function showIntakeDraft(draft) {
  const preview = byId("intake-preview");
  preview.replaceChildren();
  const heading = document.createElement("h3");
  heading.textContent = "Your starting workspace";
  const intro = document.createElement("p");
  intro.className = "section-copy";
  intro.textContent = "We have organized your own input below. Nothing here has been independently verified or generated through AI research.";
  const titleLabel = document.createElement("span");
  titleLabel.className = "draft-label";
  titleLabel.textContent = "Suggested project title";
  const title = document.createElement("p");
  title.className = "draft-title";
  title.textContent = draft.title;
  const goalLabel = document.createElement("span");
  goalLabel.className = "draft-label";
  goalLabel.textContent = "Your goal / original description";
  const goal = document.createElement("p");
  goal.className = "draft-goal";
  goal.textContent = draft.goal;
  const statementLabel = document.createElement("h4");
  statementLabel.textContent = `Input statements to preserve (${draft.statements.length})`;
  const statementList = document.createElement("ul");
  statementList.className = "draft-list";
  draft.statements.forEach((statement) => {
    const item = document.createElement("li");
    item.textContent = statement;
    statementList.append(item);
  });
  const questionsLabel = document.createElement("h4");
  questionsLabel.textContent = "Questions to guide your next thinking";
  const questions = document.createElement("ul");
  questions.className = "draft-list question-list";
  draft.questions.forEach((question) => {
    const item = document.createElement("li");
    item.textContent = question;
    questions.append(item);
  });
  const disclaimer = document.createElement("p");
  disclaimer.className = "field-help";
  disclaimer.textContent = "These are general reflection prompts, not discoveries or conclusions about your topic.";
  const actions = document.createElement("div");
  actions.className = "review-controls draft-actions";
  actions.append(
    button("Save this starting workspace", "button button-primary", () => {
      runAction(async () => {
        const statements = draft.statements.map((text) => ({
          id: crypto.randomUUID(),
          text: text.slice(0, 2000),
          source_label: "User-provided intake",
          source_excerpt: text.slice(0, 2000),
          status: "user_provided",
          created_at: new Date().toISOString(),
        }));
        const nextModel = {
          ...model,
          title: model.title === "Untitled project" ? draft.title : model.title,
          goal: model.goal ? model.goal : draft.goal,
          statements: [...model.statements, ...statements],
        };
        model = await request("/api/model", { method: "PUT", body: JSON.stringify(nextModel) });
        byId("intake-text").value = "";
        preview.hidden = true;
        preview.replaceChildren();
        intakeDraft = null;
        render();
      }, "Your starting workspace has been saved locally. Review the preserved statements below.");
    }),
    button("Discard draft", "button button-small", () => {
      preview.hidden = true;
      preview.replaceChildren();
      intakeDraft = null;
    })
  );
  preview.append(heading, intro, titleLabel, title, goalLabel, goal, statementLabel, statementList,
    questionsLabel, questions, disclaimer, actions);
  preview.hidden = false;
}

byId("intake-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const rawText = byId("intake-text").value;
  if (!rawText.trim()) {
    announce("Describe what you would like to explore first.", true);
    byId("intake-text").focus();
    return;
  }
  intakeDraft = makeIntakeDraft(rawText);
  showIntakeDraft(intakeDraft);
  announce("Draft prepared from your own words. Review it before saving.");
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
    if (!modelRevision) throw new Error("Reload the project before importing.");
    const response = await fetch("/api/import", {
      method: "PUT",
      body: form,
      headers: { "If-Match": `"${modelRevision}"` },
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `Import failed (${response.status})`);
    }
    model = await response.json();
    modelRevision = response.headers.get("ETag")?.replace(/^"|"$/g, "") || null;
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
