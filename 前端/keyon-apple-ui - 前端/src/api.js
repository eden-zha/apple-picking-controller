const API_BASE_URL = "http://127.0.0.1:8000";
const WS_BASE_URL = "ws://127.0.0.1:8000";

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

export function subscribeStatus({ onMessage, onError }) {
  const socket = new WebSocket(`${WS_BASE_URL}/ws/status`);

  socket.addEventListener("message", (event) => {
    try {
      onMessage(JSON.parse(event.data));
    } catch (error) {
      onError?.(error);
    }
  });

  socket.addEventListener("error", (error) => {
    onError?.(error);
  });

  return () => socket.close();
}
