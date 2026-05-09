export async function getJson(path) {
  const response = await fetch(path);

  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`);
  }

  return response.json();
}

export async function postJson(path) {
  const response = await fetch(path, { method: "POST" });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `${path} returned ${response.status}`);
  }

  return response.json();
}

export async function postJsonBody(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `${path} returned ${response.status}`);
  }

  return response.json();
}

export async function loadDashboardData() {
  const [status, tasks, journal, graphState, runStatus, config, agents, help] = await Promise.all([
    getJson("/api/status"),
    getJson("/api/tasks"),
    getJson("/api/journal"),
    getJson("/api/graph-state"),
    getJson("/api/run-status"),
    getJson("/api/config"),
    getJson("/api/agents"),
    getJson("/api/help"),
  ]);

  return { status, tasks, journal, graphState, runStatus, config, agents, help };
}

export function startOrchestrator() {
  return postJson("/api/run");
}

export function stopOrchestrator() {
  return postJson("/api/stop");
}

export function updateWorkDir(workDir) {
  return postJsonBody("/api/workdir", { work_dir: workDir });
}

export function updateOperationMode(operationMode) {
  return postJsonBody("/api/operation-mode", { operation_mode: operationMode });
}

export function resetMetrics() {
  return postJson("/api/reset-metrics");
}

export function resetActivity() {
  return postJson("/api/reset-activity");
}

export function openWorkDir() {
  return postJson("/api/open-workdir");
}

export function openWorkspacePath(filepath, reveal = false) {
  return postJsonBody("/api/open-workspace-path", { filepath, reveal });
}

export function selectWorkDir() {
  return postJson("/api/select-workdir");
}
