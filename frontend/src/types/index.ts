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
