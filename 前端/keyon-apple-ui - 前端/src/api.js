const API_BASE_URL = "http://127.0.0.1:8000";
export const STATS_WS_URL = "ws://127.0.0.1:8000/ws/stats";

async function request(path, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return response.json();
    }

    return null;
  } catch (error) {
    throw new Error(
      "接口请求失败，请检查后端是否运行在 8000 端口",
      { cause: error }
    );
  }
}

export function setTargetMode(targetMode) {
  return request("/set_target_apple", {
    method: "POST",
    body: JSON.stringify({ target_mode: targetMode }),
  });
}

export function startTask(mode) {
  return request("/start_task", {
    method: "POST",
    body: JSON.stringify({ mode }),
  });
}

export function stopTask(mode) {
  return request("/stop", {
    method: "POST",
    body: JSON.stringify({ mode }),
  });
}

export function resetTask() {
  return request("/reset", { method: "POST" });
}

export function getStatus() {
  return request("/status");
}

export function getLogs() {
  return request("/logs");
}

export function startMonitor() {
  return request("/monitor/start", { method: "POST" });
}

export function stopMonitor() {
  return request("/monitor/stop", { method: "POST" });
}

export function resetStats() {
  return request("/stats/reset", { method: "POST" });
}

export function createSnapshot() {
  return request("/snapshot", { method: "POST" });
}

export function getExportCsvUrl() {
  return `${API_BASE_URL}/export/csv`;
}
