const API_BASE_URL = (import.meta.env.VITE_ROBOT_BACKEND_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const WS_BASE_URL = API_BASE_URL.replace(/^http/, "ws");

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

export function setTargetMaturity(targetMaturity) {
  return request("/set_target_apple", {
    method: "POST",
    body: JSON.stringify({ target_maturity: targetMaturity }),
  });
}

export function startTask() {
  return request("/start_task", {
    method: "POST",
  });
}

export function stopTask() {
  return request("/stop", {
    method: "POST",
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

export function subscribeVision({ onMessage, onError }) {
  const socket = new WebSocket(`${WS_BASE_URL}/ws/vision`);

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

export { API_BASE_URL };
