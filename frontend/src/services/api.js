const API_URL = '/api';

export async function checkBackendStatus() {
  try {
    const res = await fetch(`${API_URL}/status`);
    return res.ok;
  } catch {
    return false;
  }
}

export async function syncSimulation(payload) {
  const res = await fetch(`${API_URL}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || 'Error al sincronizar simulación');
  }
  return res.json();
}

export async function startVideoJob(payload) {
  const res = await fetch(`${API_URL}/heatmap-video/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || 'No se pudo iniciar el video');
  }
  return res.json();
}

export async function getVideoJobStatus(jobId) {
  const res = await fetch(`${API_URL}/heatmap-video/status/${jobId}`);
  if (!res.ok) throw new Error('Error consultando progreso del video');
  return res.json();
}

export function getVideoDownloadUrl(jobId) {
  return `${API_URL}/heatmap-video/download/${jobId}`;
}

export async function fetchErrorMinimoZ(payload = {}) {
  const res = await fetch(`${API_URL}/error-minimo-z`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || 'Error al calcular E_min(z)');
  }
  return res.json();
}
