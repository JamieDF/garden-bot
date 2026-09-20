export interface Device {
  id: number;
  name: string;
  label: string;
  driver: string;
  params: Record<string, unknown>;
  location: string;
  enabled: boolean;
}

export interface CurrentReading {
  device: string;
  label: string;
  location: string;
  metric: string;
  value: number;
  unit: string;
  timestamp: string;
}

export interface LayoutItem {
  i: string;
  type: string;
  x: number;
  y: number;
  w: number;
  h: number;
  minW?: number;
  minH?: number;
  config: Record<string, unknown>;
}

export interface JournalEntry {
  id: number;
  timestamp: string;
  kind: string;
  data: {
    user?: string;
    bot?: string;
    decision?: { mood?: string; observation?: string; action?: string; speak?: string };
    outcome?: { narration?: string };
    [key: string]: unknown;
  };
}

export interface AgentStatus {
  enabled: boolean;
  model: string;
  base_url: string;
  wake_interval: number;
  wake_count: number;
  last_wake: string | null;
}

export interface FanState {
  state: 'on' | 'off';
  mode: 'auto' | 'manual';
  on_threshold: number;
  off_threshold: number;
  name?: string;
  pin?: number;
  watch?: string;
}

export interface Reading {
  id: number;
  timestamp: string;
  sensor: string;
  value: number;
  unit: string;
}

export interface ChatResponse {
  status: string;
  reply: string;
}
