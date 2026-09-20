import {
  AgentStatus,
  ChatResponse,
  CurrentReading,
  Device,
  FanState,
  JournalEntry,
  LayoutItem,
  Reading,
} from '../types';

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

const get = <T>(path: string) => fetch(path).then(j<T>);
const send = <T>(path: string, method: string, body?: unknown) =>
  fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then(j<T>);

export const api = {
  devices: () => get<Device[]>('/api/devices'),
  createDevice: (d: Partial<Device>) => send<Device>('/api/devices', 'POST', d),
  updateDevice: (name: string, d: Partial<Device>) =>
    send<Device>(`/api/devices/${name}`, 'PUT', d),
  deleteDevice: (name: string) =>
    send<{ deleted: string }>(`/api/devices/${name}`, 'DELETE'),
  deviceAction: (name: string, body: object) =>
    send<FanState>(`/api/devices/${name}/action`, 'POST', body),

  current: () => get<CurrentReading[]>('/api/readings/current'),
  history: (sensor: string, from: string, limit = 3000) =>
    get<Reading[]>(
      `/api/history?sensor=${encodeURIComponent(sensor)}&from_time=${encodeURIComponent(from)}&limit=${limit}`
    ),

  layout: () => get<LayoutItem[]>('/api/dashboard/layout'),
  saveLayout: (l: LayoutItem[]) => send<LayoutItem[]>('/api/dashboard/layout', 'PUT', l),

  agentStatus: () => get<AgentStatus>('/api/agent/status'),
  agentJournal: (limit = 30, kind?: string) =>
    get<JournalEntry[]>(
      `/api/agent/journal?limit=${limit}${kind ? `&kind=${kind}` : ''}`
    ),
  agentWake: () => send<Record<string, unknown>>('/api/agent/wake', 'POST'),
  agentChat: (message: string) =>
    send<ChatResponse>('/api/agent/chat', 'POST', { message }),

  fan: () => get<FanState>('/api/fan'),
  fanSet: (on: boolean) => send<FanState>('/api/fan', 'POST', { on }),
  fanAuto: (enabled: boolean, on_threshold: number, off_threshold: number) =>
    send<FanState>('/api/fan/auto', 'PUT', { enabled, on_threshold, off_threshold }),
};
