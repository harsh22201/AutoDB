/* ============================================
   AutoDB UI — Client-Side Logic
============================================ */

const API = "";

// ===== State =====
let isConnected = false;
let currentSelections = {}; // { ambiguityIndex: selectedText }

// ===== Screens =====
function showScreen(id) {
  document
    .querySelectorAll(".screen")
    .forEach((s) => s.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

// ===== Connect =====
async function connectDB() {
  const dbName = document.getElementById("db-name").value.trim();
  const dbHost = document.getElementById("db-host").value.trim();
  const dbPort = document.getElementById("db-port").value.trim();
  const dbUser = document.getElementById("db-user").value.trim();
  const dbPassword = document.getElementById("db-password").value.trim();
  const btn = document.getElementById("connect-btn");
  const errDiv = document.getElementById("connect-error");

  if (!dbName) {
    errDiv.textContent = "Please enter a database name.";
    errDiv.style.display = "block";
    return;
  }

  btn.disabled = true;
  btn.querySelector(".btn-text").textContent = "Connecting...";
  btn.querySelector(".btn-loader").style.display = "block";
  errDiv.style.display = "none";

  try {
    const res = await fetch(`${API}/api/connect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        db_name: dbName,
        host: dbHost,
        port: dbPort,
        user: dbUser,
        password: dbPassword,
      }),
    });
    const data = await res.json();

    if (data.success) {
      isConnected = true;
      document.getElementById("header-db-name").textContent = dbName;

      showScreen("main-screen");
    } else {
      errDiv.textContent = data.message || "Connection failed.";
      errDiv.style.display = "block";
    }
  } catch (e) {
    errDiv.textContent = "Could not reach server. Is the Flask server running?";
    errDiv.style.display = "block";
  } finally {
    btn.disabled = false;
    btn.querySelector(".btn-text").textContent = "Connect";
    btn.querySelector(".btn-loader").style.display = "none";
  }
}

async function disconnectDB() {
  try {
    await fetch(`${API}/api/disconnect`, { method: "POST" });
  } catch (e) {
    /* ignore */
  }
  isConnected = false;
  document.getElementById("panel-left-steps").innerHTML = "";
  document.getElementById("panel-middle-steps").innerHTML =
    '<div class="panel-placeholder" id="middle-placeholder"><span>Submit a query to see analysis, retrieval, and decomposition</span></div>';
  document.getElementById("panel-right-steps").innerHTML =
    '<div class="panel-placeholder" id="right-placeholder"><span>SQL results and final answer will appear here</span></div>';
  document.getElementById("query-input").value = "";
  showScreen("connect-screen");
}

// ===== Query Submit =====
async function submitQuery() {
  const input = document.getElementById("query-input");
  const query = input.value.trim();
  if (!query) return;

  // Clear all panels
  const leftSteps = document.getElementById("panel-left-steps");
  const middleSteps = document.getElementById("panel-middle-steps");
  const rightSteps = document.getElementById("panel-right-steps");
  leftSteps.innerHTML = "";
  middleSteps.innerHTML = "";
  rightSteps.innerHTML = "";

  document.getElementById("submit-btn").disabled = true;
  document.getElementById("execute-btn").disabled = true;
  window._sqlExtraRows = null;
  _queryClass = "";

  // Step 1 → Left panel
  leftSteps.appendChild(createStepCard(1, "Intent Ambiguity Resolution"));

  // Steps 2-4 → Middle panel
  middleSteps.appendChild(createStepCard(2, "Query Analysis"));
  middleSteps.appendChild(createStepCard(3, "Value Ambiguity Retrieval"));
  middleSteps.appendChild(createStepCard(4, "Query Decomposition"));

  // Steps 5-6 → Right panel
  rightSteps.appendChild(createStepCard(5, "SQL Result"));
  rightSteps.appendChild(createStepCard(6, "Final Answer"));

  // Run Step 1
  await runStep1(query);
}

function createStepCard(num, title) {
  const card = document.createElement("div");
  card.className = "step-card pending";
  card.id = `step-${num}`;
  card.innerHTML = `
        <div class="step-header" onclick="toggleStep(${num})">
            <div class="step-indicator">${num}</div>
            <div class="step-title">${title}</div>
            <div class="step-status">Pending</div>
        </div>
        <div class="step-content">
            <div class="step-content-inner" id="step-${num}-body"></div>
        </div>
    `;
  return card;
}

function setStepState(num, state, statusText) {
  const card = document.getElementById(`step-${num}`);
  if (!card) return;
  card.className = `step-card ${state}`;
  const statusEl = card.querySelector(".step-status");
  if (statusText) statusEl.textContent = statusText;

  if (state === "active") {
    statusEl.innerHTML = '<div class="step-spinner"></div>';
  }
}

function toggleStep(num) {
  const card = document.getElementById(`step-${num}`);
  if (!card) return;
  const content = card.querySelector(".step-content");
  if (card.classList.contains("pending")) return;

  if (content.style.display === "none") {
    content.style.display = "block";
  } else if (
    content.style.display === "block" &&
    !card.classList.contains("active")
  ) {
    content.style.display = "none";
  }
}

// ===== Step 1: Ambiguity Resolution =====
async function runStep1(query) {
  setStepState(1, "active", "Detecting...");

  try {
    const res = await fetch(`${API}/api/pipeline/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const data = await res.json();

    if (!data.success) {
      setStepState(1, "error", "Error");
      stepError(1, data.error || "Unknown error");
      enableSubmit();
      return;
    }

    await handleAmbiguityResponse(data);
  } catch (e) {
    setStepState(1, "error", "Error");
    stepError(1, e.message);
    enableSubmit();
  }
}

async function handleAmbiguityResponse(data) {
  const body = document.getElementById("step-1-body");

  if (data.has_ambiguities && data.ambiguities && data.ambiguities.length > 0) {
    currentSelections = {};
    let html = "";

    if (data.clarifications_so_far && data.clarifications_so_far.length > 0) {
      html += `<div class="section-label">Previous Clarifications</div>`;
      html += `<div class="clarification-summary" style="margin-bottom:16px">`;
      data.clarifications_so_far.forEach((c) => {
        html += `<div class="clarification-item">
                    <span class="cq">Q:</span> ${esc(c.clarification_question)}
                    <span class="ca">→ ${esc(c.user_clarification)}</span>
                </div>`;
      });
      html += `</div>`;
    }

    html += `<div class="section-label">Iteration ${data.iteration} — ${data.ambiguities.length} ambiguit${data.ambiguities.length === 1 ? "y" : "ies"} detected</div>`;

    data.ambiguities.forEach((amb, idx) => {
      const optionsData = JSON.stringify(
        amb.options.map((o) => o.text || o.display),
      );
      html += `
            <div class="ambiguity-group">
                <div class="ambiguity-label">
                    <span class="ambiguity-type-badge">${esc(amb.ambiguity_type)}</span>
                    ${amb.from_knowledge_store ? `<span class="ks-badge">Knowledge Store (ctx: ${amb.context_score}, amb: ${amb.ambiguity_score})</span>` : ""}
                </div>
                <div class="ambiguity-question">${esc(amb.clarification_question)}</div>
                <div class="ambiguity-meta">Key: ${esc(amb.context_key)} → ${esc(amb.ambiguity_key)}</div>
                <div class="option-list" id="options-${idx}">
                    ${amb.options
                      .map(
                        (opt, oi) => `
                        <button class="option-btn" data-amb="${idx}" data-opt="${oi}" 
                                data-text="${esc(opt.text)}"
                                onclick="selectOption(${idx}, ${oi}, this)">
                            <div class="option-radio"></div>
                            ${esc(opt.display)}
                        </button>
                    `,
                      )
                      .join("")}
                </div>
                <div class="manual-input-row">
                    <input class="manual-input" id="manual-${idx}" placeholder="Or type your own clarification..." 
                           oninput="manualInput(${idx}, this)">
                </div>
            </div>`;

      // Store metadata for submission
      if (!window._ambiguityMeta) window._ambiguityMeta = [];
      window._ambiguityMeta[idx] = {
        clarification_question: amb.clarification_question,
        ambiguity_key: amb.ambiguity_key,
        context_key: amb.context_key,
        from_knowledge_store: amb.from_knowledge_store,
        all_llm_options: amb.options.map((o) => o.text),
      };
    });

    html += `<button class="submit-clarifications-btn" id="submit-clarify-btn" onclick="submitClarifications()" disabled>
            Submit Clarifications
        </button>`;

    body.innerHTML = html;
    setStepState(1, "active", "Waiting for input");
    // Remove spinner for waiting state
    const statusEl = document.querySelector("#step-1 .step-status");
    statusEl.innerHTML = "Awaiting Input";
  } else {
    // No ambiguities — show summary and proceed
    let html = "";
    if (data.clarifications_so_far && data.clarifications_so_far.length > 0) {
      html += `<div class="section-label" style="display: flex; align-items: baseline;">
                         Clarifications Collected
                         <span style="font-size: 10px; opacity: 0.7; font-weight: normal; margin-left: 8px;">(in ${data.iteration - 1} iteration${data.iteration - 1 === 1 ? "" : "s"})</span>
                     </div>`;
      html += `<div class="clarification-summary" style="margin-bottom: 8px;">`;
      data.clarifications_so_far.forEach((c) => {
        html += `<div class="clarification-item">
                    <span class="cq">Q:</span> ${esc(c.clarification_question)}
                    <span class="ca">→ ${esc(c.user_clarification)}</span>
                </div>`;
      });
      html += `</div>`;
      html += `<div class="info-msg" style="margin-top: 12px; font-size: 12px; padding: 8px 12px;">Resolution complete. Proceeding with analysis.</div>`;
    } else {
      html = `<div class="info-msg">No intent ambiguities detected. Proceeding with analysis.</div>`;
    }
    body.innerHTML = html;
    setStepState(1, "done", "Done");

    // Proceed to Steps 2-6
    await runRemainingSteps();
  }
}

function selectOption(ambIdx, optIdx, el) {
  // Clear selection in this group
  document
    .querySelectorAll(`#options-${ambIdx} .option-btn`)
    .forEach((b) => b.classList.remove("selected"));
  el.classList.add("selected");
  currentSelections[ambIdx] = el.dataset.text;

  // Clear manual input
  const manual = document.getElementById(`manual-${ambIdx}`);
  if (manual) manual.value = "";

  checkClarifyReady();
}

function manualInput(ambIdx, el) {
  const val = el.value.trim();
  if (val) {
    // Clear radio selections
    document
      .querySelectorAll(`#options-${ambIdx} .option-btn`)
      .forEach((b) => b.classList.remove("selected"));
    currentSelections[ambIdx] = val;
  } else {
    delete currentSelections[ambIdx];
  }
  checkClarifyReady();
}

function checkClarifyReady() {
  const totalAmbiguities = document.querySelectorAll(".ambiguity-group").length;
  const btn = document.getElementById("submit-clarify-btn");
  if (btn) {
    btn.disabled = Object.keys(currentSelections).length < totalAmbiguities;
  }
}

async function submitClarifications() {
  const btn = document.getElementById("submit-clarify-btn");
  btn.disabled = true;
  btn.textContent = "Submitting...";

  const choices = [];
  for (const [idx, selectedText] of Object.entries(currentSelections)) {
    const meta = window._ambiguityMeta[parseInt(idx)];
    choices.push({
      clarification_question: meta.clarification_question,
      selected_option: selectedText,
      ambiguity_key: meta.ambiguity_key,
      context_key: meta.context_key,
      from_knowledge_store: meta.from_knowledge_store,
      all_llm_options: meta.all_llm_options,
    });
  }

  setStepState(1, "active", "Detecting...");

  try {
    const res = await fetch(`${API}/api/pipeline/clarify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ choices }),
    });
    const data = await res.json();

    if (!data.success) {
      setStepState(1, "error", "Error");
      stepError(1, data.error || "Unknown error");
      enableSubmit();
      return;
    }

    window._ambiguityMeta = [];
    await handleAmbiguityResponse(data);
  } catch (e) {
    setStepState(1, "error", "Error");
    stepError(1, e.message);
    enableSubmit();
  }
}

// ===== Steps 2-6 =====
// Stored query class for execution phase
let _queryClass = "";

async function runRemainingSteps() {
  try {
    // Step 2: Query Analysis
    setStepState(2, "active", "Analyzing...");
    const res2 = await fetch(`${API}/api/pipeline/step2`, { method: "POST" });
    const data2 = await res2.json();
    if (!data2.success)
      throw { step: 2, error: data2.error, traceback: data2.traceback };
    await renderStep2(data2.step2_analysis, []);

    _queryClass = String(
      data2.step2_analysis?.query_class || "",
    ).toLowerCase();

    // If undefined, skip everything
    if (_queryClass === "undefined") {
      [3, 4, 5, 6].forEach((i) => {
        setStepState(i, "done", "Skipped");
        document.getElementById(`step-${i}`).style.opacity = "0.5";
      });
      enableSubmit();
      return;
    }

    // Step 3: Value Ambiguity Retrieval
    setStepState(3, "active", "Retrieving...");
    const res3 = await fetch(`${API}/api/pipeline/step3`, { method: "POST" });
    const data3 = await res3.json();
    if (!data3.success)
      throw { step: 3, error: data3.error, traceback: data3.traceback };
    await renderStep3(data3.step3_value_ambiguities, []);

    // Step 4: Query Decomposition
    setStepState(4, "active", "Decomposing...");
    const res4 = await fetch(`${API}/api/pipeline/step4`, { method: "POST" });
    const data4 = await res4.json();
    if (!data4.success)
      throw { step: 4, error: data4.error, traceback: data4.traceback };
    await renderStep4(data4.step4_decomposition, []);

    // Enable the Execute button — Steps 5-6 wait for user
    const execBtn = document.getElementById("execute-btn");
    execBtn.disabled = false;
    enableSubmit();

  } catch (e) {
    if (e.step) {
      setStepState(e.step, "error", "Error");
      stepError(e.step, e.error, e.traceback);
    } else {
      for (let i = 2; i <= 4; i++) {
        const card = document.getElementById(`step-${i}`);
        if (card && card.classList.contains("active")) {
          setStepState(i, "error", "Error");
          stepError(i, e.message || "Unknown Error");
          break;
        }
      }
    }
    enableSubmit();
  }
}

// ===== Execute Button — Steps 5-6 =====
async function runExecutionSteps() {
  const execBtn = document.getElementById("execute-btn");
  execBtn.disabled = true;
  document.getElementById("submit-btn").disabled = true;

  try {
    // Step 5: SQL Execution
    if (_queryClass === "unstructured") {
      setStepState(5, "done", "Skipped");
      document.getElementById("step-5").style.opacity = "0.5";
    } else {
      setStepState(5, "active", "Executing...");
      const res5 = await fetch(`${API}/api/pipeline/step5`, { method: "POST" });
      const data5 = await res5.json();
      if (!data5.success)
        throw { step: 5, error: data5.error, traceback: data5.traceback };
      await renderStep5(data5.step5_sql, []);
    }

    // Step 6: Final Answer
    if (_queryClass === "structured") {
      setStepState(6, "done", "Skipped");
      document.getElementById("step-6").style.opacity = "0.5";
    } else {
      setStepState(6, "active", "Generating...");
      const res6 = await fetch(`${API}/api/pipeline/step6`, { method: "POST" });
      const data6 = await res6.json();
      if (!data6.success)
        throw { step: 6, error: data6.error, traceback: data6.traceback };
      await renderStep6(data6.step6_final_answer, []);
    }
  } catch (e) {
    if (e.step) {
      setStepState(e.step, "error", "Error");
      stepError(e.step, e.error, e.traceback);
    } else {
      for (let i = 5; i <= 6; i++) {
        const card = document.getElementById(`step-${i}`);
        if (card && card.classList.contains("active")) {
          setStepState(i, "error", "Error");
          stepError(i, e.message || "Unknown Error");
          break;
        }
      }
    }
  }

  enableSubmit();
}

async function renderStep2(analysis, errors) {
  const err = errors.find((e) => e.step === 2);
  if (err) {
    setStepState(2, "error", "Error");
    stepError(2, err.error, err.traceback);
    return;
  }

  const body = document.getElementById("step-2-body");

  let html = `
        <div class="analysis-card">
            <div class="analysis-row">
                <span class="analysis-label">Intent Summary</span>
                <span class="analysis-value">${esc(analysis.intent_summary)}</span>
            </div>

            <div class="analysis-row">
                <span class="analysis-label">Query Class</span>
                <span class="analysis-badge class-${esc((analysis.query_class || "").toLowerCase())}">${esc(analysis.query_class)}</span>
            </div>`;

  // Value ambiguities — compact view (term + columns only, no reason)
  if (analysis.value_ambiguities && analysis.value_ambiguities.length > 0) {
    html += `<div class="analysis-row" style="margin-top:4px">
                <span class="analysis-label">Value Ambiguities</span>
                <div class="va-list-compact">`;
    analysis.value_ambiguities.forEach((va) => {
      html += `<div class="va-chip">
                    <span class="va-chip-term">${esc(va.ambiguous_term)}</span>
                    <span class="va-chip-arrow">→</span>
                    ${va.candidate_columns ? va.candidate_columns.map((c) => `<span class="va-badge-col">${esc(c)}</span>`).join("") : '<span class="va-chip-none">No candidates</span>'}
                </div>`;
    });
    html += `</div></div>`;
  }

  // Hidden details body (rationale + VA reasons)
  const hasDetails = analysis.rationale || (analysis.value_ambiguities && analysis.value_ambiguities.some(va => va.reason));
  if (hasDetails) {
    let detailsHtml = ``;
    if (analysis.rationale) {
      detailsHtml += `<div class="analysis-row">
                    <span class="analysis-label">Rationale</span>
                    <span class="analysis-value">${esc(analysis.rationale)}</span>
                </div>`;
    }
    if (analysis.value_ambiguities && analysis.value_ambiguities.length > 0) {
      const reasons = analysis.value_ambiguities.filter(va => va.reason);
      if (reasons.length > 0) {
        detailsHtml += `<div class="analysis-row">
                      <span class="analysis-label">Value Ambiguity Reasons</span>
                      <div class="va-list">`;
        reasons.forEach((va) => {
          detailsHtml += `<div class="va-card">
                        <div class="va-row">
                            <span class="va-term-label">Term:</span>
                            <span class="va-term-val">${esc(va.ambiguous_term)}</span>
                        </div>
                        <div class="va-reason" style="border-top:none; margin-top:0; padding-top:0;">${esc(va.reason)}</div>
                    </div>`;
        });
        detailsHtml += `</div></div>`;
      }
    }
    html += `<div class="details-body" id="step2-details">${detailsHtml}</div>`;
  }

  html += `</div>`;

  body.innerHTML = html;
  setStepState(2, "done", "Done");

  // Add "Details" toggle in step header
  if (hasDetails) {
    addHeaderDetailsBtn(2, "step2-details");
  }
}

async function renderStep3(vaData, errors) {
  const err = errors.find((e) => e.step === 3);
  if (err) {
    setStepState(3, "error", "Error");
    stepError(3, err.error, err.traceback);
    return;
  }

  const body = document.getElementById("step-3-body");
  if (!vaData || !vaData.candidates || !vaData.candidates.length) {
    body.innerHTML = `<div class="info-msg">No candidates retrieved.</div>`;
  } else {
    let html = ``;

    vaData.candidates.forEach((cand) => {
      html += `<div class="retrieval-compact">`;
      html += `<div class="retrieval-compact-header">`;
      html += `<span class="retrieval-compact-term">${esc(cand.ambiguous_term)}</span>`;
      html += `</div>`;

      if (cand.candidate_entries && Object.keys(cand.candidate_entries).length > 0) {
        for (const [col, vals] of Object.entries(cand.candidate_entries)) {
          html += `<div class="retrieval-compact-row">`;
          html += `<span class="retrieval-compact-col">${esc(col)}</span>`;
          html += `<div class="retrieval-compact-vals">${vals.map((v) => `<span class="retrieval-val-badge">${esc(String(v))}</span>`).join("")}</div>`;
          html += `</div>`;
        }
      } else {
        html += `<div class="info-msg" style="padding: 4px 10px; font-size: 12px;">No matches found.</div>`;
      }

      html += `</div>`;
    });

    body.innerHTML = html;
  }
  setStepState(3, "done", "Done");
}

async function renderStep4(decomposition, errors) {
  const err = errors.find((e) => e.step === 4);
  if (err) {
    setStepState(4, "error", "Error");
    stepError(4, err.error, err.traceback);
    return;
  }

  const body = document.getElementById("step-4-body");

  let html = `<div class="analysis-card">`;

  if (decomposition.structured_query) {
    html += `
            <div class="analysis-row">
                <span class="analysis-label">Structured Query (SQL)</span>
                <div class="sql-block" style="margin-bottom: 0;">${esc(decomposition.structured_query)}</div>
            </div>
        `;
  }

  if (decomposition.unstructured_query) {
    html += `
            <div class="analysis-row">
                <span class="analysis-label">Unstructured Query (LLM)</span>
                <div class="unstructured-block">${esc(decomposition.unstructured_query)}</div>
            </div>
        `;
  }

  if (!decomposition.structured_query && !decomposition.unstructured_query) {
    html += `<div class="info-msg">No structured or unstructured queries were decomposed.</div>`;
  }

  // Hidden rationale body
  if (decomposition.rationale) {
    html += `<div class="details-body" id="step4-details">
                <div class="analysis-row">
                    <span class="analysis-label">Rationale</span>
                    <span class="analysis-value">${esc(decomposition.rationale)}</span>
                </div>
            </div>`;
  }

  html += `</div>`;

  body.innerHTML = html;
  setStepState(4, "done", "Done");

  // Add "Details" toggle in step header
  if (decomposition.rationale) {
    addHeaderDetailsBtn(4, "step4-details");
  }
}

async function renderStep5(sqlData, errors) {
  const err = errors.find((e) => e.step === 5);
  if (err) {
    setStepState(5, "error", "Error");
    stepError(5, err.error, err.traceback);
    return;
  }

  const body = document.getElementById("step-5-body");
  if (!sqlData || (sqlData.columns.length === 0 && sqlData.rows.length === 0)) {
    body.innerHTML = `<div class="info-msg">${esc(sqlData?.message || "No structured query to execute.")}</div>`;
  } else {
    let html = ``;
    const PREVIEW_ROWS = 3;

    if (sqlData.columns.length > 0 && sqlData.rows.length > 0) {
      const totalRows = sqlData.rows.length;
      const hasMore = totalRows > PREVIEW_ROWS;

      // Preview table (first 5 rows)
      html += `<div class="data-table-wrap"><table class="data-table" id="sql-result-table">`;
      html += `<thead><tr>${sqlData.columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>`;
      html += `<tbody>`;
      const showCount = Math.min(totalRows, PREVIEW_ROWS);
      for (let i = 0; i < showCount; i++) {
        html += `<tr>${sqlData.rows[i].map((v) => `<td>${esc(String(v ?? ""))}</td>`).join("")}</tr>`;
      }
      html += `</tbody></table></div>`;

      // Row count
      html += `<div class="row-count">${sqlData.row_count} row${sqlData.row_count !== 1 ? "s" : ""} returned${hasMore ? " (showing first " + PREVIEW_ROWS + ")" : ""}</div>`;

      // Store extra rows for expansion
      if (hasMore) {
        window._sqlExtraRows = sqlData.rows.slice(PREVIEW_ROWS);
      } else {
        window._sqlExtraRows = null;
      }
    } else {
      html += `<div class="info-msg">Query returned 0 rows.</div>`;
    }

    body.innerHTML = html;
  }
  setStepState(5, "done", "Done");

  // Add expand toggle in step header if there are extra rows
  if (window._sqlExtraRows && window._sqlExtraRows.length > 0) {
    const stepHeader = document.querySelector("#step-5 .step-header");
    if (stepHeader && !document.getElementById("expand-rows-btn")) {
      const expandBtn = document.createElement("button");
      expandBtn.id = "expand-rows-btn";
      expandBtn.className = "expand-rows-btn";
      expandBtn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg> All rows`;
      expandBtn.onclick = function(e) {
        e.stopPropagation();
        toggleAllRows(this);
      };
      stepHeader.appendChild(expandBtn);
    }
  }
}

function toggleAllRows(btn) {
  const table = document.getElementById("sql-result-table");
  if (!table) return;
  const tbody = table.querySelector("tbody");
  const isExpanded = btn.classList.contains("expanded");

  if (isExpanded) {
    // Collapse — remove extra rows
    const rows = tbody.querySelectorAll("tr");
    const PREVIEW_ROWS = 3;
    for (let i = rows.length - 1; i >= PREVIEW_ROWS; i--) {
      rows[i].remove();
    }
    btn.classList.remove("expanded");
    btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg> All rows`;
  } else {
    // Expand — add extra rows
    if (window._sqlExtraRows) {
      window._sqlExtraRows.forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = row.map((v) => `<td>${esc(String(v ?? ""))}</td>`).join("");
        tbody.appendChild(tr);
      });
    }
    btn.classList.add("expanded");
    btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg> Collapse`;
  }
}

async function renderStep6(finalAnswer, errors) {
  const err = errors.find((e) => e.step === 6);
  if (err) {
    setStepState(6, "error", "Error");
    stepError(6, err.error, err.traceback);
    return;
  }

  const body = document.getElementById("step-6-body");
  if (!finalAnswer) {
    body.innerHTML = `<div class="info-msg">No answer generated.</div>`;
  } else {
    body.innerHTML = `<div class="final-answer">${renderMarkdown(finalAnswer)}</div>`;
  }
  setStepState(6, "done", "Done");
}

// ===== Helpers =====
function stepError(num, msg, tb) {
  const body = document.getElementById(`step-${num}-body`);
  let html = `<div class="step-error">${esc(msg)}`;
  if (tb) html += `<pre>${esc(tb)}</pre>`;
  html += `</div>`;
  body.innerHTML = html;
}

function enableSubmit() {
  document.getElementById("submit-btn").disabled = false;
}

function addHeaderDetailsBtn(stepNum, detailsBodyId) {
  const stepHeader = document.querySelector(`#step-${stepNum} .step-header`);
  if (!stepHeader) return;
  const btn = document.createElement("button");
  btn.className = "expand-rows-btn";
  btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg> Details`;
  btn.onclick = function(e) {
    e.stopPropagation();
    const body = document.getElementById(detailsBodyId);
    if (!body) return;
    const isOpen = body.style.display === "block";
    body.style.display = isOpen ? "none" : "block";
    btn.classList.toggle("expanded", !isOpen);
    btn.innerHTML = !isOpen
      ? `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg> Details`
      : `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg> Details`;
  };
  stepHeader.appendChild(btn);
}

function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function esc(s) {
  if (!s) return "";
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

// Simple markdown renderer (basic — handles bold, italic, headings, lists, tables, code)
function renderMarkdown(text) {
  let html = text;

  // Code blocks
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code>${esc(code.trim())}</code></pre>`;
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Headings
  html = html.replace(/^### (.*$)/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.*$)/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.*$)/gm, "<h1>$1</h1>");

  // Bold & italic
  html = html.replace(/\*\*\*(.*?)\*\*\*/g, "<strong><em>$1</em></strong>");
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");

  // Tables
  html = html.replace(
    /^\|(.+)\|\s*\n\|[-| :]+\|\s*\n((?:\|.+\|\s*\n?)*)/gm,
    (match, header, body) => {
      const ths = header
        .split("|")
        .map((h) => h.trim())
        .filter(Boolean)
        .map((h) => `<th>${h}</th>`)
        .join("");
      const rows = body
        .trim()
        .split("\n")
        .map((row) => {
          const tds = row
            .split("|")
            .map((c) => c.trim())
            .filter(Boolean)
            .map((c) => `<td>${c}</td>`)
            .join("");
          return `<tr>${tds}</tr>`;
        })
        .join("");
      return `<table><thead><tr>${ths}</tr></thead><tbody>${rows}</tbody></table>`;
    },
  );

  // Unordered lists
  html = html.replace(/^[\-\*] (.*$)/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>\n?)+/g, "<ul>$&</ul>");

  // Ordered lists
  html = html.replace(/^\d+\. (.*$)/gm, "<li>$1</li>");

  // Line breaks → paragraphs
  html = html.replace(/\n\n/g, "</p><p>");
  html = html.replace(/\n/g, "<br>");

  // Wrap in paragraph if not already
  if (!html.startsWith("<")) html = `<p>${html}</p>`;

  return html;
}

// Enter key submit
document
  .getElementById("query-input")
  .addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitQuery();
    }
  });

// Enter key connect
document.getElementById("db-name").addEventListener("keydown", function (e) {
  if (e.key === "Enter") connectDB();
});
