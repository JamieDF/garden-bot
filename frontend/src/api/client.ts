import { SensorReadings, Reading, HistoryResponse } from '../types';

const API_BASE = '';

export async function fetchReadings(): Promise<SensorReadings> {
  const res = await fetch(`${API_BASE}/api/readings`);
  if (!res.ok) throw new Error('Failed to fetch readings');
  return res.json();
}

export async function fetchLatestReadings(): Promise<Reading[]> {
  const res = await fetch(`${API_BASE}/api/readings/latest`);
  if (!res.ok) throw new Error('Failed to fetch latest readings');
  return res.json();
}

export async function fetchHistory(
  sensor?: string,
  from?: string,
  to?: string,
  limit: number = 1000
): Promise<HistoryResponse[]> {
  const params = new URLSearchParams();
  if (sensor) params.set('sensor', sensor);
  if (from) params.set('from_time', from);
  if (to) params.set('to_time', to);
  params.set('limit', String(limit));

  const res = await fetch(`${API_BASE}/api/history?${params}`);
  if (!res.ok) throw new Error('Failed to fetch history');
  return res.json();
}
