(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const tools = window.RoastLogTools;
  const sources = { session: [], recorded: [], imported: [] };
  const notes = {
    session: "Browser observations of actual responses in this tab. Server logs can be correlated by request ID. Latest 1,000 events are retained.",
    recorded: "Representative structured events from reports/evidence/ci-container.log. This is a historical sample, not a complete log or a live stream.",
    imported: "Open a log file to inspect it locally. Nothing is uploaded to the API.",
  };
  let selected = null;
  let runtimeConfig = null;
  function element(tag, text, className) {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
  }
  function ms(value) { return value !== null && value !== undefined && Number.isFinite(Number(value)) ? `${Number(value).toFixed(2)} ms` : "Not recorded"; }
  function field(label, value) {
    $("event-fields").append(element("dt", label), element("dd", value ?? "Not recorded"));
  }
  function inspect(event) {
    selected = event;
    $("inspector-empty").hidden = true;
    $("event-inspector").hidden = false;
    $("event-source").textContent = $("log-source").selectedOptions[0].textContent;
    const guard = tools.isGuard(event);
    const body = event.response;
    const detail = body?.detail && typeof body.detail === "object" ? body.detail : {};
    const outcome = $("event-outcome");
    const error = Number(event.status) >= 400 || guard || event.event === "client_error";
    outcome.className = `event-outcome${error ? " error" : ""}`;
    outcome.textContent = guard ? "Optical guard rejected the frame before model inference. No class probabilities were produced." :
      event.event === "client_error" ? "The browser did not receive a usable response. Server completion is unknown." :
      event.version_consistent === false ? "Model version mismatch between the response header and body." :
      body?.predicted_class ? `Prediction completed: ${body.predicted_class}. The optical guard accepted the frame.` :
      Number(event.status) >= 400 ? `HTTP ${event.status}: ${typeof body?.detail === "string" ? body.detail : detail.message || "Inspect the raw event for recorded details."}` :
      event.event === "http_request" ? "HTTP request completed. Individual scoring stages are not recorded in this log event." :
      "Service event. Inspect the fields and original JSON below.";
    const stages = $("request-stages");
    stages.replaceChildren();
    if (guard || body?.predicted_class) {
      for (const [name, state] of [["Image decoded", ""], [guard ? "Guard rejected" : "Guard passed", guard ? "blocked" : ""], [guard ? "Inference skipped" : "Model scored", guard ? "skipped" : ""], [guard ? "No prediction" : "Probabilities returned", guard ? "skipped" : ""]]) {
        stages.append(element("li", name, state));
      }
    }
    $("event-fields").replaceChildren();
    field("Event", event.event || "Service message");
    field("Timestamp", event.ts || event.TimeGenerated);
    field("Request ID", event.request_id || (guard ? "Absent in this guard log; do not assume a request association" : null));
    field("Route / status", `${event.path || "—"} / ${event.status ?? "—"}`);
    field("Model version", event.model_version || body?.model_version);
    field("Server request", ms(event.latency_ms));
    field("Browser round trip", ms(event.browser_ms));
    field("Scoring", ms(event.scoring_ms ?? body?.latency_ms));
    const spread = event.pixel_std ?? body?.pixel_std ?? detail.pixel_std;
    const entropy = event.entropy ?? body?.shannon_entropy ?? detail.shannon_entropy;
    field("Pixel spread", spread === undefined ? null : Number(spread).toFixed(4));
    field("Entropy", entropy === undefined ? null : `${Number(entropy).toFixed(4)} bits`);
    if (guard || body?.predicted_class) {
      const config = event.runtime_config;
      field("Guard criteria", config ? `Spread ≥ ${config.pixel_std_threshold}; entropy ≥ ${config.entropy_threshold} bits` : event.threshold !== undefined || detail.threshold !== undefined ? `Recorded spread threshold: ${event.threshold ?? detail.threshold}; entropy threshold not recorded` : "Thresholds not recorded in this event");
    }
    if (event.file_name) field("Input", `${event.file_name} · ${Number(event.file_bytes || 0).toLocaleString()} bytes`);
    if (event.version_consistent !== undefined) field("Version check", event.version_consistent === null ? "Not enough fields to compare" : event.version_consistent ? "Header and body match" : "Mismatch");
    if (event.message) field("Message", event.message);
    $("raw-event").textContent = JSON.stringify(event, null, 2);
  }
  function render() {
    const source = $("log-source").value;
    const records = sources[source];
    $("source-note").textContent = `${notes[source]} Counts cover the full source before filtering.`;
    const stats = tools.summarize(records);
    $("log-stats").replaceChildren();
    for (const [name, value] of [["Events", stats.events], ["HTTP requests", stats.requests], ["Errors", stats.errors], ["Guard events", stats.guards]]) {
      const cell = element("div", undefined, "stat-cell");
      cell.append(element("strong", value), element("span", name));
      $("log-stats").append(cell);
    }
    const search = $("log-search").value.toLowerCase();
    const filter = $("log-filter").value;
    const filtered = records.filter(event => {
      if (filter === "errors" && !(Number(event.status) >= 400 || event.event === "client_error")) return false;
      if (filter === "guard" && !tools.isGuard(event)) return false;
      if (filter === "requests" && event.event !== "http_request") return false;
      return !search || JSON.stringify(event).toLowerCase().includes(search);
    }).slice().reverse();
    const rows = $("log-rows");
    rows.replaceChildren();
    if (selected && !filtered.includes(selected)) selected = null;
    if (!selected && filtered.length) inspect(filtered[0]);
    if (!filtered.length) {
      $("event-inspector").hidden = true;
      $("inspector-empty").hidden = false;
      $("event-source").textContent = "NO EVENT";
      const row = element("tr");
      const cell = element("td", records.length ? "No events match the filters." : "No events yet. Run a prediction or open a log file.");
      cell.colSpan = 4;
      row.append(cell);
      rows.append(row);
    }
    for (const event of filtered) {
      const row = element("tr", undefined, event === selected ? "selected" : "");
      const first = element("td");
      const button = element("button", undefined, "event-select");
      button.type = "button";
      button.setAttribute("aria-pressed", String(event === selected));
      button.append(element("strong", event.event || "service_message"), element("span", event.ts || "Timestamp not recorded"));
      button.addEventListener("click", () => { inspect(event); render(); });
      first.append(button);
      const status = element("td");
      status.append(element("span", event.status ?? "—", `status-badge${Number(event.status) >= 400 ? " error" : ""}`));
      row.append(first, element("td", event.path || "—"), status, element("td", ms(event.latency_ms)));
      rows.append(row);
    }
  }
  async function refreshRuntime() {
    $("refresh-runtime").disabled = true;
    try {
      const [readyResponse, configResponse] = await Promise.all([fetch("/ready", { cache: "no-store" }), fetch("/demo-config", { cache: "no-store" })]);
      if (!configResponse.ok) throw new Error("Runtime configuration unavailable");
      runtimeConfig = await configResponse.json();
      const ready = await readyResponse.json();
      $("runtime-strip").replaceChildren();
      for (const text of [readyResponse.ok ? `Engine: ${ready.engine}` : `Model: ${ready.status || "unavailable"}`, `Input: ${runtimeConfig.input_size} × ${runtimeConfig.input_size} RGB`, `Worker concurrency: ${runtimeConfig.max_concurrency}`, `Guard: spread ≥ ${runtimeConfig.pixel_std_threshold} · entropy ≥ ${runtimeConfig.entropy_threshold} bits`]) $("runtime-strip").append(element("span", text));
      if (selected) inspect(selected);
    } catch {
      $("runtime-strip").textContent = "Runtime configuration unavailable. Recorded logs and file import remain available.";
    } finally { $("refresh-runtime").disabled = false; }
  }
  async function loadEvidence() {
    try {
      const response = await fetch("/demo/evidence.json");
      if (!response.ok) throw new Error("Missing evidence snapshot");
      const evidence = await response.json();
      sources.recorded = evidence.recorded_logs;
      const summary = evidence.cloud_log_summary;
      const guardCount = summary.filter(e => e.Event === "occlusion_guard_rejection").reduce((n,e) => n + Number(e.Count), 0);
      const errors = summary.filter(e => e.Event === "http_request" && Number(e.Status) >= 400).reduce((n,e) => n + Number(e.Count), 0);
      const cards = [
        ["Warm HTTP p95 / p99", `${evidence.warm.p95_ms.toFixed(2)} / ${evidence.warm.p99_ms.toFixed(2)} ms`, `${evidence.warm.successful_requests} / ${evidence.warm.requests} requests succeeded · concurrency ${evidence.warm.concurrency} · ${evidence.warm.client_origin}`, "reports/evidence/initial-warm.json"],
        ["Cold-start p95 / p99", `${(evidence.cold.p95_ms / 1000).toFixed(2)} / ${(evidence.cold.p99_ms / 1000).toFixed(2)} s`, `${evidence.cold.trials} trials · zero replicas verified before every request.`, "reports/evidence/initial-cold.json"],
        ["Frozen warm release limits", `${evidence.slo.warm_p95_ms} / ${evidence.slo.warm_p99_ms} ms`, `p95 / p99 limits. An individual browser request does not establish a percentile or release result.`, "monitoring/slo.json"],
        ["Recorded Azure log summary", `${guardCount} guard events · ${errors} HTTP errors`, "Historical query counts. Guard events and HTTP 422 entries may describe the same rejected frame; do not add them as unique requests.", "reports/evidence/deployed-log-summary.json"],
      ];
      for (const [title, value, note, source] of cards) {
        const card = element("div", undefined, "evidence-card");
        card.append(element("h4", title), element("strong", value), element("p", note), element("p", source));
        $("evidence-grid").append(card);
      }
      $("evidence-note").textContent = `Snapshot for ${evidence.slo.model_version}; targets frozen ${evidence.slo.frozen_at_utc}. Warm and cold evidence use different measurement boundaries. Cloud query counts are separate from the representative CI log sample above. Refresh runtime does not refresh this historical snapshot.`;
      render();
    } catch { $("evidence-note").textContent = "Recorded snapshot unavailable. Live responses and file import still work."; }
  }
  window.RoastObservability = {
    record(event) {
      if (runtimeConfig) event.runtime_config = { ...runtimeConfig };
      sources.session.push(event);
      if (sources.session.length > 1000) sources.session.shift();
      $("log-source").value = "session";
      $("log-filter").value = "all";
      $("log-search").value = "";
      inspect(event);
      render();
    },
  };
  for (const id of ["log-source", "log-filter"]) $(id).addEventListener("change", () => { selected = null; render(); });
  $("log-search").addEventListener("input", render);
  $("refresh-runtime").addEventListener("click", refreshRuntime);
  $("clear-session").addEventListener("click", () => { sources.session = []; if ($("log-source").value === "session") { selected = null; render(); } });
  $("export-session").addEventListener("click", () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(sources.session, null, 2)], { type: "application/json" }));
    const link = element("a"); link.href = url; link.download = "roast-session.json"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  $("log-upload").addEventListener("change", async event => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    $("log-source").value = "imported";
    sources.imported = [];
    selected = null;
    try {
      if (file.size > 5 * 1024 * 1024) throw new Error("File exceeds the 5 MiB import limit.");
      const result = tools.parse(await file.text());
      sources.imported = result.records;
      notes.imported = `${file.name}: ${result.records.length} structured events. ${result.ignored} non-event lines / records ignored; ${result.truncated} older events omitted. Imported locally in this browser.`;
    } catch (error) { notes.imported = error.message; }
    render();
  });
  render();
  refreshRuntime();
  loadEvidence();
})();
