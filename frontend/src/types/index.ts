export interface SensorReadings {
  inside_temp: number | null;
  inside_humidity: number | null;
  inside_pressure: number | null;
  outside_temp: number | null;
  outside_humidity: number | null;
  outside_pressure: number | null;
  inside_air_temp: number | null;
  outside_air_temp: number | null;
  timestamp: string;
}

export interface Reading {
  id: number;
  timestamp: string;
  sensor: string;
  value: number;
  unit: string;
}

export interface HistoryResponse {
  sensor: string;
  value: number;
  unit: string;
  timestamp: string;
}

export interface SensorStats {
  min: number | null;
  max: number | null;
}

export interface PeriodStats {
  inside_air_temp: SensorStats | null;
  outside_air_temp: SensorStats | null;
  inside_humidity: SensorStats | null;
  inside_pressure: SensorStats | null;
}

export interface SensorStatsResponse {
  day: PeriodStats;
  week: PeriodStats;
  month: PeriodStats;
  temp_diff: number | null;
}

export interface FanState {
  state: 'on' | 'off';
  mode: 'auto' | 'manual';
  on_threshold: number;
  off_threshold: number;
}
