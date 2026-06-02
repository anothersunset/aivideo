let documents = [];
let shots = [];
let agents = [];
let budget = [];
let risks = [];
let tasks = [];
let pipeline = {};

const fallback = {
  documents: [
    ["Overview", "README_开发包目录说明.md", "Development package guide."],
    ["Tech", "影狩罗刹帖_Agent化制作系统设计_v0.1.md", "Agent production architecture."],
  ],
  shots: [
    ["007", "Rinzo crashes through roof", "S", "Key shot", "First visual impact"],
    ["008", "Triple kill", "S", "Key shot", "Speed and lethal intent"],
    ["019", "Lantern in water reveals membrane", "S", "Key shot", "Main visual memory point"],
  ],
  agents: [
    ["WriterAgent", "Expands script, compresses dialogue, repairs arcs.", "MVP"],
    ["ProducerAgent", "Tracks budget, schedule, scope changes, and reports.", "MVP"],
    ["RiskAgent", "Checks similarity, rating risk, and promo language risk.", "MVP"],
  ],
  budget: [["Action design and key animation", 30000]],
  risks: [["Originality boundary", "Generated visuals require similarity checks."]],
  tasks: [],
  pipeline: {
    stage: "offline_fallback",
    master: {},
    segments: [],
    providers: { providers: [], provider_count: 0, request_packets: 0, jobs_processed: 0 },
    adapter_runs: { rendered_count: 0, outputs_ready: 0, provider: "" },
    external_video_runs: { provider_count: 0, ready_provider_count: 0, total_submission_count: 0, providers: [] },
    submit_gate: { allowed_provider_count: 0, blocked_provider_count: 0, total_estimated_cost_usd: 0 },
    provider_submit: { submitted_count: 0, blocked_provider_count: 0, failed_count: 0 },
    provider_poll: { submitted_item_count: 0, ready_for_download_count: 0, pending_count: 0, downloaded_count: 0 },
    external_results: { expected_result_count: 0, accepted_count: 0, rejected_count: 0, unknown_count: 0 },
    external_reviews: { reviewed_count: 0, approved_count: 0, returned_count: 0 },
    replacements: { candidate_count: 0, applied_replacement_count: 0 },
    acceptance: { decision: "not_run", passed_count: 0, failed_count: 0, final_release_ready: false },
    director_review: { decision: "not_run", reviewed_keyframe_count: 0, nonblank_keyframe_count: 0 },
    director_review_v02: { decision: "not_run", reviewed_keyframe_count: 0, nonblank_keyframe_count: 0 },
    producer_demo_package: { decision: "not_run", artifact_count: 0, zip: {} },
    producer_demo_package_v02: { decision: "not_run", artifact_count: 0, zip: {} },
    current_demo: { decision: "not_run", current_version: "", current_zip: {}, current_video: {} },
    polish_queue: { decision: "not_run", queue_count: 0, provider_packet_count: 0 },
    provider_launch: { decision: "not_run", selected_shot_count: 0, selected_provider_count: 0 },
    provider_returns: { decision: "not_run", generated_count: 0, accepted_count: 0, rejected_count: 0 },
    review_closure: { decision: "not_run", approved_count: 0, kept_open_count: 0 },
    local_polish: { decision: "not_run", rendered_count: 0, accepted_count: 0, rejected_count: 0 },
    local_polish_promotion: { decision: "not_run", promoted_count: 0 },
    artifacts: [],
  },
};

const titles = {
  dashboard: "Overview",
  documents: "Development Files",
  shots: "Shot Board",
  agents: "Agent Tasks",
  pipeline: "Pipeline",
  risks: "Risks and Budget",
};

function switchView(viewId) {
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active-view"));
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  document.getElementById(viewId).classList.add("active-view");
  document.querySelector(`[data-view="${viewId}"]`).classList.add("active");
  document.getElementById("viewTitle").textContent = titles[viewId];
}

function normalizeDocuments(serverDocuments) {
  return serverDocuments.map((item) => [item.category, item.name, item.summary]);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`API ${path} returned ${response.status}`);
  }
  return response.json();
}

async function loadServerData() {
  try {
    const data = await api("/api/data");
    documents = normalizeDocuments(data.documents ?? []);
    shots = data.shots ?? [];
    agents = data.agents ?? [];
    budget = data.budget ?? [];
    risks = data.risks ?? [];
    tasks = data.tasks ?? [];
    pipeline = data.pipeline ?? fallback.pipeline;
  } catch (error) {
    documents = fallback.documents;
    shots = fallback.shots;
    agents = fallback.agents;
    budget = fallback.budget;
    risks = fallback.risks;
    tasks = fallback.tasks;
    pipeline = fallback.pipeline;
  }
  document.getElementById("docCount").textContent = String(documents.length);
}

function renderDocuments(filter = "all") {
  const list = document.getElementById("documentList");
  const filtered = documents.filter(([category]) => filter === "all" || category === filter);
  list.innerHTML = filtered
    .map(
      ([category, name, summary]) => `
        <article class="document-card">
          <span class="tag">${category}</span>
          <strong>${name}</strong>
          <p>${summary}</p>
        </article>
      `,
    )
    .join("");
}

function renderShots() {
  const statuses = ["Key shot", "Storyboard", "Design", "To storyboard"];
  const board = document.getElementById("shotBoard");
  board.innerHTML = statuses
    .map((status) => {
      const cards = shots
        .filter((shot) => shot[3] === status)
        .map(
          ([id, title, difficulty, , note]) => `
            <article class="shot-card">
              <strong>SH${id} · ${title}</strong>
              <p>${note}</p>
              <div class="shot-meta">
                <span class="badge ${difficulty.toLowerCase()}">${difficulty}</span>
                <span class="badge">KAGE_SQ01_SH${id}</span>
              </div>
            </article>
          `,
        )
        .join("");
      return `
        <section class="column">
          <h3>${status}<span>${shots.filter((shot) => shot[3] === status).length}</span></h3>
          ${cards}
        </section>
      `;
    })
    .join("");
}

function renderAgents() {
  const agentOptions = agents.map(([name]) => `<option value="${name}">${name}</option>`).join("");
  document.getElementById("agentGrid").innerHTML = `
    <section class="panel task-form-panel">
      <div class="panel-header">
        <h3>Create Agent Task</h3>
        <span class="tag">MVP</span>
      </div>
      <form id="taskForm" class="task-form">
        <label>Agent<select name="agent">${agentOptions}</select></label>
        <label>Priority<select name="priority"><option>High</option><option selected>Medium</option><option>Low</option></select></label>
        <label class="wide">Title<input name="title" required placeholder="Expand Act II upper scenes" /></label>
        <label class="wide">Prompt<textarea name="prompt" rows="4" required placeholder="Describe the task for this agent"></textarea></label>
        <button type="submit">Create Task</button>
      </form>
    </section>
    <section class="panel task-list-panel">
      <div class="panel-header">
        <h3>Task Queue</h3>
        <span class="tag">${tasks.length} tasks</span>
      </div>
      <div class="task-list">${renderTaskCards()}</div>
    </section>
  `;
  document.getElementById("taskForm").addEventListener("submit", createTask);
  document.querySelectorAll("[data-run-task]").forEach((button) => {
    button.addEventListener("click", () => runTask(button.dataset.runTask));
  });
  document.querySelectorAll("[data-approve-task]").forEach((button) => {
    button.addEventListener("click", () => reviewTask(button.dataset.approveTask, "Approved"));
  });
  document.querySelectorAll("[data-return-task]").forEach((button) => {
    button.addEventListener("click", () => reviewTask(button.dataset.returnTask, "Returned"));
  });
}

function renderTaskCards() {
  if (!tasks.length) {
    return `<p class="empty">No tasks yet. Create the first WriterAgent, ProducerAgent, or RiskAgent task.</p>`;
  }
  return tasks
    .map(
      (task) => `
        <article class="task-card">
          <div class="task-head">
            <strong>${task.id} · ${task.title}</strong>
            <span class="tag">${task.agent}</span>
          </div>
          <p>${task.prompt}</p>
          ${task.output ? `<pre>${task.output}</pre>` : ""}
          <div class="shot-meta">
            <span class="badge">${task.priority}</span>
            <span class="badge">${task.status}</span>
            <span class="badge">${task.review}</span>
          </div>
          <div class="task-actions">
            <button data-run-task="${task.id}">Run</button>
            <button data-approve-task="${task.id}">Approve</button>
            <button data-return-task="${task.id}">Return</button>
          </div>
        </article>
      `,
    )
    .join("");
}

async function refreshTasks() {
  try {
    tasks = await api("/api/tasks");
  } catch (error) {
    tasks = [];
  }
  renderAgents();
}

async function createTask(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  await api("/api/tasks", {
    method: "POST",
    body: JSON.stringify({
      agent: formData.get("agent"),
      priority: formData.get("priority"),
      title: formData.get("title"),
      prompt: formData.get("prompt"),
    }),
  });
  await refreshTasks();
}

async function runTask(taskId) {
  await api(`/api/tasks/${taskId}/run`, { method: "POST", body: "{}" });
  await refreshTasks();
}

async function reviewTask(taskId, decision) {
  await api(`/api/tasks/${taskId}/review`, {
    method: "POST",
    body: JSON.stringify({ decision, note: `${decision} from Hub MVP` }),
  });
  await refreshTasks();
}

function renderBudget() {
  const max = Math.max(...budget.map(([, amount]) => amount), 1);
  document.getElementById("budgetBars").innerHTML = budget
    .map(
      ([label, amount]) => `
        <div class="budget-row">
          <div class="budget-label"><span>${label}</span><strong>$${amount.toLocaleString()}</strong></div>
          <div class="bar"><div class="bar-fill" style="width:${(amount / max) * 100}%"></div></div>
        </div>
      `,
    )
    .join("");
}

function renderRisks() {
  document.getElementById("riskList").innerHTML = risks
    .map(
      ([title, summary]) => `
        <article class="risk-item">
          <strong>${title}</strong>
          <p>${summary}</p>
        </article>
      `,
    )
    .join("");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatSeconds(seconds) {
  const value = Number(seconds || 0);
  if (!value) return "0s";
  const minutes = Math.floor(value / 60);
  const remaining = Math.round(value % 60);
  return minutes ? `${minutes}m ${String(remaining).padStart(2, "0")}s` : `${remaining}s`;
}

function formatBytes(bytes) {
  const value = Number(bytes || 0);
  if (!value) return "0 B";
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function renderFileLine(label, file) {
  const path = escapeHtml(file?.path || "");
  const state = file?.exists ? "ready" : "missing";
  return `
    <div class="file-line">
      <span>${label}</span>
      <code>${path || "not generated"}</code>
      <strong class="${state}">${state}${file?.exists ? ` / ${formatBytes(file.bytes)}` : ""}</strong>
    </div>
  `;
}

function renderPipeline() {
  const master = pipeline.master ?? {};
  const providerData = pipeline.providers ?? {};
  const adapterRuns = pipeline.adapter_runs ?? {};
  const externalVideoRuns = pipeline.external_video_runs ?? {};
  const submitGate = pipeline.submit_gate ?? {};
  const providerSubmit = pipeline.provider_submit ?? {};
  const providerPoll = pipeline.provider_poll ?? {};
  const external = pipeline.external_results ?? {};
  const externalReviews = pipeline.external_reviews ?? {};
  const replacement = pipeline.replacements ?? {};
  const acceptance = pipeline.acceptance ?? {};
  const directorReview = pipeline.director_review ?? {};
  const directorReviewV02 = pipeline.director_review_v02 ?? {};
  const producerPackage = pipeline.producer_demo_package ?? {};
  const producerPackageV02 = pipeline.producer_demo_package_v02 ?? {};
  const currentDemo = pipeline.current_demo ?? {};
  const polishQueue = pipeline.polish_queue ?? {};
  const providerLaunch = pipeline.provider_launch ?? {};
  const providerReturns = pipeline.provider_returns ?? {};
  const reviewClosure = pipeline.review_closure ?? {};
  const localPolish = pipeline.local_polish ?? {};
  const localPolishPromotion = pipeline.local_polish_promotion ?? {};
  const segments = pipeline.segments ?? [];
  const providerRows = (providerData.providers ?? [])
    .map(
      (provider) => `
        <article class="provider-row">
          <strong>${escapeHtml(provider.name)}</strong>
          <span>${escapeHtml(provider.status)}</span>
          <code>${escapeHtml(provider.adapter)}</code>
        </article>
      `,
    )
    .join("");
  const externalVideoRows = (externalVideoRuns.providers ?? [])
    .map(
      (provider) => `
        <article class="provider-row compact">
          <strong>${escapeHtml(provider.provider)}</strong>
          <span>${provider.ready_for_api_submit ? "ready" : "config needed"}</span>
          <code>${provider.submission_count || 0} chunks / ${provider.packet_count || 0} packets</code>
        </article>
      `,
    )
    .join("");

  document.getElementById("pipelineGrid").innerHTML = `
    <article class="metric">
      <span>Master preview</span>
      <strong>${formatSeconds(master.duration_seconds)}</strong>
      <p>${master.shot_count || 0} shots / ${master.width || 0}x${master.height || 0} / ${master.fps || 0}fps</p>
    </article>
    <article class="metric">
      <span>Providers</span>
      <strong>${providerData.provider_count || 0}</strong>
      <p>${providerData.request_packets || 0} request packets, ${providerData.jobs_processed || 0} routed jobs</p>
    </article>
    <article class="metric">
      <span>External inbox</span>
      <strong>${external.expected_result_count || 0}</strong>
      <p>${external.accepted_count || 0} accepted / ${external.rejected_count || 0} rejected / ${external.unknown_count || 0} unknown</p>
    </article>
    <article class="metric">
      <span>Replacement tests</span>
      <strong>${replacement.applied_replacement_count || 0}</strong>
      <p>${replacement.candidate_count || 0} candidates, ${replacement.applied_segment_count || 0} segment manifests ready</p>
    </article>
    <article class="metric">
      <span>Acceptance</span>
      <strong>${acceptance.passed_count || 0}/${(acceptance.passed_count || 0) + (acceptance.failed_count || 0)}</strong>
      <p>${escapeHtml(acceptance.decision || "not_run")}</p>
    </article>
    <article class="metric">
      <span>Director review</span>
      <strong>${directorReview.nonblank_keyframe_count || 0}/${directorReview.reviewed_keyframe_count || 0}</strong>
      <p>${escapeHtml(directorReview.decision || "not_run")}</p>
    </article>
    <article class="metric">
      <span>Director v02</span>
      <strong>${directorReviewV02.nonblank_keyframe_count || 0}/${directorReviewV02.reviewed_keyframe_count || 0}</strong>
      <p>${escapeHtml(directorReviewV02.decision || "not_run")}</p>
    </article>
    <article class="metric">
      <span>Producer package</span>
      <strong>${producerPackage.artifact_count || 0}</strong>
      <p>${escapeHtml(producerPackage.decision || "not_run")}</p>
    </article>
    <article class="metric">
      <span>Demo v02</span>
      <strong>${producerPackageV02.artifact_count || 0}</strong>
      <p>${escapeHtml(producerPackageV02.decision || "not_run")}</p>
    </article>
    <article class="metric">
      <span>Current demo</span>
      <strong>${escapeHtml(currentDemo.current_version || "none")}</strong>
      <p>${escapeHtml(currentDemo.decision || "not_run")}</p>
    </article>
    <article class="metric">
      <span>Polish queue</span>
      <strong>${polishQueue.queue_count || 0}</strong>
      <p>${polishQueue.provider_packet_count || 0} provider packets / $${Number(polishQueue.estimated_external_cost_usd || 0).toFixed(2)}</p>
    </article>
    <article class="metric">
      <span>HQ launch</span>
      <strong>${providerLaunch.selected_shot_count || 0}</strong>
      <p>${providerLaunch.selected_provider_count || 0} providers / $${Number(providerLaunch.estimated_first_pass_cost_usd || 0).toFixed(2)}</p>
    </article>
    <article class="metric">
      <span>HQ returns</span>
      <strong>${providerReturns.accepted_count || 0}/${providerReturns.generated_count || 0}</strong>
      <p>${escapeHtml(providerReturns.mode || providerReturns.decision || "not_run")}</p>
    </article>
    <article class="metric">
      <span>Review closure</span>
      <strong>${reviewClosure.kept_open_count || 0}</strong>
      <p>${reviewClosure.approved_count || 0} approved this pass</p>
    </article>
    <article class="metric">
      <span>Local polish</span>
      <strong>${localPolish.accepted_count || 0}/${localPolish.rendered_count || 0}</strong>
      <p>${escapeHtml(localPolish.decision || "not_run")}</p>
    </article>
    <article class="metric">
      <span>Polish promoted</span>
      <strong>${localPolishPromotion.promoted_count || 0}</strong>
      <p>${escapeHtml(localPolishPromotion.decision || "not_run")}</p>
    </article>
  `;

  document.getElementById("pipelineMaster").innerHTML = `
    <section class="panel">
      <div class="panel-header">
        <h3>Master Edit</h3>
        <span class="tag">${escapeHtml(master.replacement_status || master.review_status || "Needs review")}</span>
      </div>
      ${renderFileLine("Local master", master.video)}
      ${renderFileLine("Replacement master", master.replacement_video)}
      ${renderFileLine("Local-polish master", master.local_polish_video)}
      <p class="pipeline-note">Stage: ${escapeHtml(pipeline.stage || "")}</p>
    </section>
  `;

  document.getElementById("pipelineSegments").innerHTML = segments
    .map(
      (segment) => `
        <article class="panel">
          <div class="panel-header">
            <h3>${escapeHtml(segment.name)}</h3>
            <span class="tag">${segment.existing_shot_count || 0}/${segment.shot_count || 0} shots</span>
          </div>
          <div class="segment-stats">
            <span>${formatSeconds(segment.duration_seconds)}</span>
            <span>${segment.width || 0}x${segment.height || 0}</span>
            <span>${segment.fps || 0}fps</span>
            <span>${segment.replacement_count || 0} replacements</span>
          </div>
          ${renderFileLine("Segment video", segment.video)}
          ${renderFileLine("Temp audio", segment.audio)}
          ${renderFileLine("Replacement video", segment.replacement_video)}
          ${renderFileLine("Local-polish video", segment.local_polish_video)}
        </article>
      `,
    )
    .join("");

  document.getElementById("providerMatrix").innerHTML = `
    <section class="panel">
      <div class="panel-header">
        <h3>Provider Adapters</h3>
        <span class="tag">${providerData.external_provider_count || 0} external routes</span>
      </div>
      <div class="provider-list">${providerRows}</div>
      <p class="pipeline-note">${escapeHtml(providerData.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>Adapter Runs</h3>
        <span class="tag">${escapeHtml(adapterRuns.provider || "none")}</span>
      </div>
      <div class="segment-stats">
        <span>${adapterRuns.rendered_count || 0} rendered</span>
        <span>${adapterRuns.outputs_ready || 0} files ready</span>
        <span>${escapeHtml(adapterRuns.mode || "not run")}</span>
      </div>
      <p class="pipeline-note">${escapeHtml(adapterRuns.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>External Video Queues</h3>
        <span class="tag">${externalVideoRuns.ready_provider_count || 0}/${externalVideoRuns.provider_count || 0} ready</span>
      </div>
      <div class="segment-stats">
        <span>${externalVideoRuns.total_submission_count || 0} chunks</span>
        <span>${externalVideoRuns.blocked_provider_count || 0} need config</span>
        <span>${externalVideoRuns.assembly?.assembled_count || 0} assembled</span>
        <span>${externalVideoRuns.assembly?.waiting_count || 0} waiting</span>
        <span>${escapeHtml(externalVideoRuns.mode || "not prepared")}</span>
      </div>
      <div class="provider-list">${externalVideoRows}</div>
      <p class="pipeline-note">${escapeHtml(externalVideoRuns.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>Submit Gate</h3>
        <span class="tag">${submitGate.allowed_provider_count || 0}/${submitGate.provider_count || 0} allowed</span>
      </div>
      <div class="segment-stats">
        <span>${submitGate.blocked_provider_count || 0} blocked</span>
        <span>$${Number(submitGate.total_estimated_cost_usd || 0).toFixed(2)} estimate</span>
        <span>${escapeHtml(submitGate.mode || "not evaluated")}</span>
      </div>
      <div class="file-line">
        <span>Approval</span>
        <code>${escapeHtml(submitGate.approval_request || "not generated")}</code>
        <strong class="${submitGate.approval_request ? "ready" : "missing"}">${submitGate.approval_request ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(submitGate.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>Provider Submit</h3>
        <span class="tag">${providerSubmit.submitted_count || 0} submitted</span>
      </div>
      <div class="segment-stats">
        <span>${providerSubmit.blocked_provider_count || 0} providers blocked</span>
        <span>${providerSubmit.failed_count || 0} failed</span>
        <span>${escapeHtml(providerSubmit.mode || "not run")}</span>
      </div>
      <div class="file-line">
        <span>Run</span>
        <code>${escapeHtml(providerSubmit.manifest || "not generated")}</code>
        <strong class="${providerSubmit.manifest ? "ready" : "missing"}">${providerSubmit.manifest ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(providerSubmit.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>Provider Poll</h3>
        <span class="tag">${providerPoll.ready_for_download_count || 0} ready</span>
      </div>
      <div class="segment-stats">
        <span>${providerPoll.submitted_item_count || 0} submitted items</span>
        <span>${providerPoll.pending_count || 0} pending</span>
        <span>${providerPoll.downloaded_count || 0} downloaded</span>
        <span>${escapeHtml(providerPoll.mode || "not run")}</span>
      </div>
      <div class="file-line">
        <span>Poll</span>
        <code>${escapeHtml(providerPoll.manifest || "not generated")}</code>
        <strong class="${providerPoll.manifest ? "ready" : "missing"}">${providerPoll.manifest ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(providerPoll.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>External Result Inbox</h3>
        <span class="tag">${escapeHtml(external.inbox || "not ready")}</span>
      </div>
      <div class="segment-stats">
        <span>${external.expected_result_count || 0} expected</span>
        <span>${external.accepted_count || 0} accepted</span>
        <span>${external.rejected_count || 0} rejected</span>
        <span>${external.unknown_count || 0} unknown</span>
      </div>
      <p class="pipeline-note">${escapeHtml(external.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>External Review</h3>
        <span class="tag">${externalReviews.approved_count || 0} approved</span>
      </div>
      <div class="segment-stats">
        <span>${externalReviews.reviewed_count || 0} reviewed</span>
        <span>${externalReviews.returned_count || 0} returned</span>
        <span>${escapeHtml(externalReviews.stage || "not run")}</span>
      </div>
      <div class="file-line">
        <span>Report</span>
        <code>${escapeHtml(externalReviews.report || "not generated")}</code>
        <strong class="${externalReviews.report ? "ready" : "missing"}">${externalReviews.report ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(externalReviews.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>Master Acceptance</h3>
        <span class="tag">${escapeHtml(acceptance.decision || "not run")}</span>
      </div>
      <div class="segment-stats">
        <span>${acceptance.passed_count || 0} checks passed</span>
        <span>${acceptance.failed_count || 0} failed</span>
        <span>${acceptance.final_release_ready ? "release ready" : "internal review"}</span>
        <span>${escapeHtml(acceptance.risk_status || "risk pending")}</span>
      </div>
      <div class="file-line">
        <span>Report</span>
        <code>${escapeHtml(acceptance.report || "not generated")}</code>
        <strong class="${acceptance.report ? "ready" : "missing"}">${acceptance.report ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(acceptance.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>Director/Risk Review</h3>
        <span class="tag">${escapeHtml(directorReview.decision || "not run")}</span>
      </div>
      <div class="segment-stats">
        <span>${directorReview.nonblank_keyframe_count || 0}/${directorReview.reviewed_keyframe_count || 0} nonblank</span>
        <span>${directorReview.replacement_keyframe_count || 0} replacement frames</span>
        <span>${directorReview.risk_keyframe_count || 0} risk frames</span>
        <span>${directorReview.final_release_ready ? "release ready" : "producer demo"}</span>
      </div>
      <div class="file-line">
        <span>Contact</span>
        <code>${escapeHtml(directorReview.contact_sheet || "not generated")}</code>
        <strong class="${directorReview.contact_sheet ? "ready" : "missing"}">${directorReview.contact_sheet ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Report</span>
        <code>${escapeHtml(directorReview.report || "not generated")}</code>
        <strong class="${directorReview.report ? "ready" : "missing"}">${directorReview.report ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(directorReview.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>Director/Risk Review v02</h3>
        <span class="tag">${escapeHtml(directorReviewV02.decision || "not run")}</span>
      </div>
      <div class="segment-stats">
        <span>${directorReviewV02.nonblank_keyframe_count || 0}/${directorReviewV02.reviewed_keyframe_count || 0} nonblank</span>
        <span>${directorReviewV02.replacement_keyframe_count || 0} local-polish frames</span>
        <span>${directorReviewV02.risk_keyframe_count || 0} risk frames</span>
        <span>${directorReviewV02.final_release_ready ? "release ready" : "producer demo"}</span>
      </div>
      <div class="file-line">
        <span>Contact</span>
        <code>${escapeHtml(directorReviewV02.contact_sheet || "not generated")}</code>
        <strong class="${directorReviewV02.contact_sheet ? "ready" : "missing"}">${directorReviewV02.contact_sheet ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Report</span>
        <code>${escapeHtml(directorReviewV02.report || "not generated")}</code>
        <strong class="${directorReviewV02.report ? "ready" : "missing"}">${directorReviewV02.report ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(directorReviewV02.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>Producer Demo Package</h3>
        <span class="tag">${escapeHtml(producerPackage.decision || "not run")}</span>
      </div>
      <div class="segment-stats">
        <span>${producerPackage.artifact_count || 0} artifacts</span>
        <span>${producerPackage.final_release_ready ? "release ready" : "internal demo"}</span>
        <span>${escapeHtml(producerPackage.acceptance_decision || "acceptance pending")}</span>
        <span>${escapeHtml(producerPackage.director_review_decision || "review pending")}</span>
      </div>
      ${renderFileLine("Zip", producerPackage.zip)}
      <div class="file-line">
        <span>Readme</span>
        <code>${escapeHtml(producerPackage.readme || "not generated")}</code>
        <strong class="${producerPackage.readme ? "ready" : "missing"}">${producerPackage.readme ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Manifest</span>
        <code>${escapeHtml(producerPackage.manifest || "not generated")}</code>
        <strong class="${producerPackage.manifest ? "ready" : "missing"}">${producerPackage.manifest ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(producerPackage.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>Producer Demo v02</h3>
        <span class="tag">${escapeHtml(producerPackageV02.decision || "not run")}</span>
      </div>
      <div class="segment-stats">
        <span>${producerPackageV02.artifact_count || 0} artifacts</span>
        <span>${producerPackageV02.promoted_count || 0} promoted</span>
        <span>${producerPackageV02.final_release_ready ? "release ready" : "internal demo"}</span>
      </div>
      ${renderFileLine("Zip", producerPackageV02.zip)}
      <div class="file-line">
        <span>Readme</span>
        <code>${escapeHtml(producerPackageV02.readme || "not generated")}</code>
        <strong class="${producerPackageV02.readme ? "ready" : "missing"}">${producerPackageV02.readme ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Manifest</span>
        <code>${escapeHtml(producerPackageV02.manifest || "not generated")}</code>
        <strong class="${producerPackageV02.manifest ? "ready" : "missing"}">${producerPackageV02.manifest ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(producerPackageV02.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>Current Demo</h3>
        <span class="tag">${escapeHtml(currentDemo.decision || "not run")}</span>
      </div>
      <div class="segment-stats">
        <span>${escapeHtml(currentDemo.current_version || "none")}</span>
        <span>${currentDemo.zip_entry_count || 0} zip entries</span>
        <span>${currentDemo.promoted_count || 0} promoted</span>
        <span>${currentDemo.final_release_ready ? "release ready" : "internal demo"}</span>
      </div>
      ${renderFileLine("Zip", currentDemo.current_zip)}
      ${renderFileLine("Video", currentDemo.current_video)}
      <div class="file-line">
        <span>Readme</span>
        <code>${escapeHtml(currentDemo.readme || "not generated")}</code>
        <strong class="${currentDemo.readme ? "ready" : "missing"}">${currentDemo.readme ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Manifest</span>
        <code>${escapeHtml(currentDemo.manifest || "not generated")}</code>
        <strong class="${currentDemo.manifest ? "ready" : "missing"}">${currentDemo.manifest ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Registry</span>
        <code>${escapeHtml(currentDemo.registry || "not generated")}</code>
        <strong class="${currentDemo.registry ? "ready" : "missing"}">${currentDemo.registry ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(currentDemo.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>Polish Queue</h3>
        <span class="tag">${escapeHtml(polishQueue.decision || "not run")}</span>
      </div>
      <div class="segment-stats">
        <span>${polishQueue.queue_count || 0} shots</span>
        <span>${polishQueue.provider_packet_count || 0} packets</span>
        <span>$${Number(polishQueue.estimated_external_cost_usd || 0).toFixed(2)} estimate</span>
        <span>${polishQueue.submit_allowed_provider_count || 0}/${(polishQueue.submit_allowed_provider_count || 0) + (polishQueue.submit_blocked_provider_count || 0)} submit allowed</span>
      </div>
      ${renderFileLine("Packets", polishQueue.provider_packets)}
      <div class="file-line">
        <span>Work order</span>
        <code>${escapeHtml(polishQueue.report || "not generated")}</code>
        <strong class="${polishQueue.report ? "ready" : "missing"}">${polishQueue.report ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Manifest</span>
        <code>${escapeHtml(polishQueue.manifest || "not generated")}</code>
        <strong class="${polishQueue.manifest ? "ready" : "missing"}">${polishQueue.manifest ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(polishQueue.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>HQ Provider Launch</h3>
        <span class="tag">${escapeHtml(providerLaunch.decision || "not run")}</span>
      </div>
      <div class="segment-stats">
        <span>${providerLaunch.selected_shot_count || 0} shots</span>
        <span>${providerLaunch.selected_provider_count || 0} providers</span>
        <span>$${Number(providerLaunch.estimated_first_pass_cost_usd || 0).toFixed(2)} first pass</span>
        <span>${providerLaunch.handoff_artifact_count || 0} handoff artifacts</span>
      </div>
      <div class="file-line">
        <span>Config</span>
        <code>${escapeHtml(providerLaunch.config_template || "not generated")}</code>
        <strong class="${providerLaunch.config_template ? "ready" : "missing"}">${providerLaunch.config_template ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Env</span>
        <code>${escapeHtml(providerLaunch.env_example || "not generated")}</code>
        <strong class="${providerLaunch.env_example ? "ready" : "missing"}">${providerLaunch.env_example ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Rows</span>
        <code>${escapeHtml(providerLaunch.selected_rows_jsonl || "not generated")}</code>
        <strong class="${providerLaunch.selected_rows_jsonl ? "ready" : "missing"}">${providerLaunch.selected_rows_jsonl ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Report</span>
        <code>${escapeHtml(providerLaunch.report || "not generated")}</code>
        <strong class="${providerLaunch.report ? "ready" : "missing"}">${providerLaunch.report ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Manifest</span>
        <code>${escapeHtml(providerLaunch.manifest || "not generated")}</code>
        <strong class="${providerLaunch.manifest ? "ready" : "missing"}">${providerLaunch.manifest ? "ready" : "missing"}</strong>
      </div>
      ${renderFileLine("Handoff zip", providerLaunch.handoff_zip)}
      <div class="file-line">
        <span>Handoff manifest</span>
        <code>${escapeHtml(providerLaunch.handoff_manifest || "not generated")}</code>
        <strong class="${providerLaunch.handoff_manifest ? "ready" : "missing"}">${providerLaunch.handoff_manifest ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(providerLaunch.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>HQ Provider Returns</h3>
        <span class="tag">${escapeHtml(providerReturns.decision || "not run")}</span>
      </div>
      <div class="segment-stats">
        <span>${providerReturns.generated_count || 0} generated</span>
        <span>${providerReturns.accepted_count || 0} accepted</span>
        <span>${providerReturns.rejected_count || 0} rejected</span>
        <span>${escapeHtml(providerReturns.mode || "not run")}</span>
      </div>
      <div class="file-line">
        <span>Report</span>
        <code>${escapeHtml(providerReturns.report || "not generated")}</code>
        <strong class="${providerReturns.report ? "ready" : "missing"}">${providerReturns.report ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Manifest</span>
        <code>${escapeHtml(providerReturns.manifest || "not generated")}</code>
        <strong class="${providerReturns.manifest ? "ready" : "missing"}">${providerReturns.manifest ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Contact sheet</span>
        <code>${escapeHtml(providerReturns.contact_sheet || "not generated")}</code>
        <strong class="${providerReturns.contact_sheet ? "ready" : "missing"}">${providerReturns.contact_sheet ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(providerReturns.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>Review Closure</h3>
        <span class="tag">${escapeHtml(reviewClosure.decision || "not run")}</span>
      </div>
      <div class="segment-stats">
        <span>${reviewClosure.approved_count || 0} approved</span>
        <span>${reviewClosure.kept_open_count || 0} open</span>
        <span>${reviewClosure.remaining_needs_review_count || 0} needs review</span>
        <span>${reviewClosure.remaining_returned_count || 0} returned</span>
        <span>${reviewClosure.remaining_pending_count || 0} pending</span>
      </div>
      <div class="file-line">
        <span>Report</span>
        <code>${escapeHtml(reviewClosure.report || "not generated")}</code>
        <strong class="${reviewClosure.report ? "ready" : "missing"}">${reviewClosure.report ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Manifest</span>
        <code>${escapeHtml(reviewClosure.manifest || "not generated")}</code>
        <strong class="${reviewClosure.manifest ? "ready" : "missing"}">${reviewClosure.manifest ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(reviewClosure.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>Local Polish</h3>
        <span class="tag">${escapeHtml(localPolish.decision || "not run")}</span>
      </div>
      <div class="segment-stats">
        <span>${localPolish.rendered_count || 0} rendered</span>
        <span>${localPolish.accepted_count || 0} accepted</span>
        <span>${localPolish.rejected_count || 0} rejected</span>
        <span>${escapeHtml(localPolish.mode || "local")}</span>
      </div>
      <div class="file-line">
        <span>Contact</span>
        <code>${escapeHtml(localPolish.contact_sheet || "not generated")}</code>
        <strong class="${localPolish.contact_sheet ? "ready" : "missing"}">${localPolish.contact_sheet ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Report</span>
        <code>${escapeHtml(localPolish.report || "not generated")}</code>
        <strong class="${localPolish.report ? "ready" : "missing"}">${localPolish.report ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Manifest</span>
        <code>${escapeHtml(localPolish.manifest || "not generated")}</code>
        <strong class="${localPolish.manifest ? "ready" : "missing"}">${localPolish.manifest ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(localPolish.next_step || "")}</p>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h3>Local Polish Promotion</h3>
        <span class="tag">${escapeHtml(localPolishPromotion.decision || "not run")}</span>
      </div>
      <div class="segment-stats">
        <span>${localPolishPromotion.promoted_count || 0} promoted</span>
        <span>${escapeHtml(localPolishPromotion.stage || "not run")}</span>
        <span>${escapeHtml(localPolishPromotion.mode || "versioned")}</span>
      </div>
      ${renderFileLine("Master", localPolishPromotion.master_video)}
      <div class="file-line">
        <span>Report</span>
        <code>${escapeHtml(localPolishPromotion.report || "not generated")}</code>
        <strong class="${localPolishPromotion.report ? "ready" : "missing"}">${localPolishPromotion.report ? "ready" : "missing"}</strong>
      </div>
      <div class="file-line">
        <span>Manifest</span>
        <code>${escapeHtml(localPolishPromotion.manifest || "not generated")}</code>
        <strong class="${localPolishPromotion.manifest ? "ready" : "missing"}">${localPolishPromotion.manifest ? "ready" : "missing"}</strong>
      </div>
      <p class="pipeline-note">${escapeHtml(localPolishPromotion.next_step || "")}</p>
    </section>
  `;

  document.getElementById("pipelineArtifacts").innerHTML = (pipeline.artifacts ?? [])
    .map((artifact) => `<code>${escapeHtml(artifact)}</code>`)
    .join("");
}

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.view));
});

document.getElementById("docFilter").addEventListener("change", (event) => {
  renderDocuments(event.target.value);
});

async function init() {
  await loadServerData();
  renderDocuments();
  renderShots();
  renderAgents();
  renderBudget();
  renderRisks();
  renderPipeline();
}

init();
