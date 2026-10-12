/* Pure log helpers shared by the browser inspector and its contract checks. */
(function (root) {
  "use strict";
  function unwrap(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    const nested = value.Log_s ?? value.Log ?? value.log;
    if (typeof nested === "string") {
      try { return unwrap(JSON.parse(nested)); } catch { return null; }
    }
    if (!("event" in value || "message" in value)) return null;
    return value;
  }
  function parse(text) {
    let candidates;
    let ignored = 0;
    try {
      const parsed = JSON.parse(text);
      candidates = Array.isArray(parsed) ? parsed : [parsed];
    } catch {
      candidates = [];
      for (const line of text.split(/\r?\n/)) {
        if (!line.trim()) continue;
        try { candidates.push(JSON.parse(line)); } catch { ignored++; }
      }
    }
    const records = [];
    for (const value of candidates) {
      const event = unwrap(value);
      if (event) records.push(event); else ignored++;
    }
    const truncated = Math.max(0, records.length - 1000);
    return { records: records.slice(-1000), ignored, truncated };
  }
  function serverDuration(header) {
    const match = /(?:^|,)\s*app\s*;\s*dur=([\d.]+)/.exec(header || "");
    const value = match ? Number(match[1]) : NaN;
    return Number.isFinite(value) && value >= 0 ? value : null;
  }
  function isGuard(event) {
    return event.event === "occlusion_guard_rejection" ||
      (Number(event.status) === 422 && /occlusion|glare/i.test(event.response?.detail?.error || ""));
  }
  function summarize(records) {
    return {
      events: records.length,
      requests: records.filter(e => e.event === "http_request").length,
      errors: records.filter(e => Number(e.status) >= 400 || e.event === "client_error").length,
      guards: records.filter(isGuard).length,
    };
  }
  root.RoastLogTools = { parse, serverDuration, isGuard, summarize };
})(globalThis);
