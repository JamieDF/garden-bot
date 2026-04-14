import { useEffect, useState, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { SensorReadings, Reading, SensorStatsResponse } from './types';

type TimeRange = '1h' | '24h' | '7d' | '30d';
type ChartType = 'temperature' | 'humidity' | 'pressure';

const TIME_RANGES: Record<TimeRange, { seconds: number; label: string }> = {
  '1h': { seconds: 3600, label: '1H' },
  '24h': { seconds: 86400, label: '24H' },
  '7d': { seconds: 604800, label: '7D' },
  '30d': { seconds: 2592000, label: '30D' },
};

const CHART_CONFIG: Record<ChartType, { sensors: { sensor: string; color: string; name: string; key: string }[]; title: string; unit: string }> = {
  temperature: {
    sensors: [
      { sensor: 'inside_air_temp', color: '#64ffda', name: 'Inside °C', key: 'inside' },
      { sensor: 'outside_air_temp', color: '#ff6b6b', name: 'Outside °C', key: 'outside' },
    ],
    title: 'Temperature History',
    unit: '°C',
  },
  humidity: {
    sensors: [
      { sensor: 'inside_humidity', color: '#64ffda', name: 'Inside %', key: 'inside_humidity' },
    ],
    title: 'Humidity History',
    unit: '%',
  },
  pressure: {
    sensors: [
      { sensor: 'inside_pressure', color: '#64ffda', name: 'hPa', key: 'inside_pressure' },
    ],
    title: 'Pressure History',
    unit: 'hPa',
  },
};

function App() {
  const [readings, setReadings] = useState<SensorReadings | null>(null);
  const [chartData, setChartData] = useState<Reading[]>([]);
  const [stats, setStats] = useState<SensorStatsResponse | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [chartType, setChartType] = useState<ChartType>('temperature');
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadReadings = useCallback(async () => {
    try {
      const res = await fetch('/api/readings');
      const data = await res.json();
      setReadings(data);
      setLastUpdated(new Date());
      setError(null);
    } catch {
      setError('Failed to connect to sensor API');
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const res = await fetch('/api/stats');
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  }, []);

  const loadChartData = useCallback(async () => {
    try {
      const fromTime = new Date(Date.now() - TIME_RANGES[timeRange].seconds * 1000).toISOString();
      const params = new URLSearchParams({ from_time: fromTime, limit: '5000' });
      
      const sensors = CHART_CONFIG[chartType].sensors;
      const results = await Promise.all(
        sensors.map(({ sensor }) => 
          fetch(`/api/history?${params}&sensor=${sensor}`).then(r => r.json())
        )
      );
      
      // Merge data by timestamp
      const merged: Record<string, any> = {};
      results.forEach((data, i) => {
        const key = sensors[i].key;
        data.forEach((r: Reading) => {
          // Cap humidity at 100%
          const value = key === 'inside_humidity' ? Math.min(r.value, 100) : r.value;
          merged[r.timestamp] = { ...merged[r.timestamp], timestamp: r.timestamp, [key]: value };
        });
      });
      
      setChartData(Object.values(merged).sort((a, b) => 
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      ));
    } catch (err) {
      console.error('Failed to fetch chart data:', err);
    }
  }, [timeRange, chartType]);

  useEffect(() => {
    loadReadings();
    loadStats();
    loadChartData();
  }, [loadReadings, loadStats, loadChartData]);

  useEffect(() => {
    const interval = setInterval(() => {
      loadReadings();
      loadStats();
      loadChartData();
    }, 30000);
    return () => clearInterval(interval);
  }, [loadReadings, loadStats, loadChartData]);

  return (
    <div className="min-h-screen bg-dark p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-text">🌱 Garden Bot</h1>
          {lastUpdated && (
            <span className="text-sm text-muted">
              {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-500/20 border border-red-500 rounded-lg p-4 flex justify-between items-center text-red-400">
            <span>⚠️ {error}</span>
            <button onClick={loadReadings} className="bg-red-500 text-white px-3 py-1 rounded text-sm">
              Retry
            </button>
          </div>
        )}

        {/* Video Stream */}
        <div className="bg-card rounded-xl p-4">
          <h2 className="text-lg font-semibold text-text mb-3">📹 Live Feed</h2>
          <div className="bg-black/50 rounded-lg flex items-center justify-center" style={{ minHeight: 300 }}>
            <img src="/stream.mjpg" alt="Live Feed" className="max-w-full max-h-[400px] object-contain" />
          </div>
        </div>

        {/* Current Readings */}
        <div className="space-y-3">
          <h2 className="text-xs font-semibold text-muted uppercase tracking-wider">Current Readings</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-card rounded-xl p-4">
              <p className="text-xs text-muted mb-1">🌡️ Inside Air</p>
              <p className="text-3xl font-bold text-primary">
                {readings?.inside_air_temp?.toFixed(1) ?? '--'}°C
              </p>
            </div>
            <div className="bg-card rounded-xl p-4">
              <p className="text-xs text-muted mb-1">💧 Humidity</p>
              <p className="text-3xl font-bold text-secondary">
                {readings?.inside_humidity?.toFixed(1) ?? '--'}%
              </p>
            </div>
            <div className="bg-card rounded-xl p-4">
              <p className="text-xs text-muted mb-1">🎯 Pressure</p>
              <p className="text-3xl font-bold text-muted">
                {readings?.inside_pressure?.toFixed(1) ?? '--'} hPa
              </p>
            </div>
            <div className="bg-card rounded-xl p-4">
              <p className="text-xs text-muted mb-1">🌡️ Outside Air</p>
              <p className="text-3xl font-bold text-accent">
                {readings?.outside_air_temp?.toFixed(1) ?? '--'}°C
              </p>
            </div>
          </div>
        </div>

        {/* Stats Section */}
        {stats && (
          <div className="space-y-3">
            <h2 className="text-xs font-semibold text-muted uppercase tracking-wider">Statistics</h2>
            
            {/* Temp Diff */}
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-card rounded-xl p-4 text-center">
                <p className="text-xs text-muted mb-1">🌡️ Temp Diff</p>
                <p className={`text-2xl font-bold ${(stats.temp_diff ?? 0) >= 0 ? 'text-primary' : 'text-accent'}`}>
                  {stats.temp_diff !== null ? `${stats.temp_diff >= 0 ? '+' : ''}${stats.temp_diff.toFixed(1)}°C` : '--'}
                </p>
              </div>
              {stats.day.inside_air_temp && (
                <div className="bg-card rounded-xl p-4 text-center">
                  <p className="text-xs text-muted mb-1">📈 24H Inside High</p>
                  <p className="text-2xl font-bold text-primary">
                    {stats.day.inside_air_temp.max?.toFixed(1) ?? '--'}°C
                  </p>
                </div>
              )}
              {stats.day.inside_air_temp && (
                <div className="bg-card rounded-xl p-4 text-center">
                  <p className="text-xs text-muted mb-1">📉 24H Inside Low</p>
                  <p className="text-2xl font-bold text-secondary">
                    {stats.day.inside_air_temp.min?.toFixed(1) ?? '--'}°C
                  </p>
                </div>
              )}
            </div>

            {/* 7 Day Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {stats.week.inside_air_temp && (
                <>
                  <div className="bg-card rounded-xl p-3 text-center">
                    <p className="text-xs text-muted">7D Inside High</p>
                    <p className="text-xl font-bold text-primary">{stats.week.inside_air_temp.max?.toFixed(1) ?? '--'}°C</p>
                  </div>
                  <div className="bg-card rounded-xl p-3 text-center">
                    <p className="text-xs text-muted">7D Inside Low</p>
                    <p className="text-xl font-bold text-secondary">{stats.week.inside_air_temp.min?.toFixed(1) ?? '--'}°C</p>
                  </div>
                </>
              )}
              {stats.week.outside_air_temp && (
                <>
                  <div className="bg-card rounded-xl p-3 text-center">
                    <p className="text-xs text-muted">7D Outside High</p>
                    <p className="text-xl font-bold text-accent">{stats.week.outside_air_temp.max?.toFixed(1) ?? '--'}°C</p>
                  </div>
                  <div className="bg-card rounded-xl p-3 text-center">
                    <p className="text-xs text-muted">7D Outside Low</p>
                    <p className="text-xl font-bold text-muted">{stats.week.outside_air_temp.min?.toFixed(1) ?? '--'}°C</p>
                  </div>
                </>
              )}
            </div>

            {/* 30 Day Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {stats.month.inside_air_temp && (
                <>
                  <div className="bg-card rounded-xl p-3 text-center">
                    <p className="text-xs text-muted">30D Inside High</p>
                    <p className="text-xl font-bold text-primary">{stats.month.inside_air_temp.max?.toFixed(1) ?? '--'}°C</p>
                  </div>
                  <div className="bg-card rounded-xl p-3 text-center">
                    <p className="text-xs text-muted">30D Inside Low</p>
                    <p className="text-xl font-bold text-secondary">{stats.month.inside_air_temp.min?.toFixed(1) ?? '--'}°C</p>
                  </div>
                </>
              )}
              {stats.month.outside_air_temp && (
                <>
                  <div className="bg-card rounded-xl p-3 text-center">
                    <p className="text-xs text-muted">30D Outside High</p>
                    <p className="text-xl font-bold text-accent">{stats.month.outside_air_temp.max?.toFixed(1) ?? '--'}°C</p>
                  </div>
                  <div className="bg-card rounded-xl p-3 text-center">
                    <p className="text-xs text-muted">30D Outside Low</p>
                    <p className="text-xl font-bold text-muted">{stats.month.outside_air_temp.min?.toFixed(1) ?? '--'}°C</p>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* Chart Section */}
        <div className="bg-card rounded-xl p-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-4">
            <div className="flex gap-1">
              {(Object.keys(CHART_CONFIG) as ChartType[]).map((type) => (
                <button
                  key={type}
                  onClick={() => setChartType(type)}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors capitalize ${
                    chartType === type
                      ? 'bg-primary text-dark'
                      : 'bg-dark text-muted hover:text-text'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
            <div className="flex gap-1">
              {(Object.keys(TIME_RANGES) as TimeRange[]).map((range) => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range)}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                    timeRange === range
                      ? 'bg-primary text-dark'
                      : 'bg-dark text-muted hover:text-text'
                  }`}
                >
                  {TIME_RANGES[range].label}
                </button>
              ))}
            </div>
          </div>
          <h2 className="text-lg font-semibold text-text mb-3">📊 {CHART_CONFIG[chartType].title}</h2>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis 
                  dataKey="timestamp" 
                  stroke="#64748b" 
                  fontSize={10}
                  tickFormatter={(v) => new Date(v).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                />
                <YAxis 
                  stroke="#64748b" 
                  fontSize={10} 
                  domain={chartType === 'humidity' ? [0, 100] : ['auto', 'auto']} 
                  tickFormatter={chartType === 'humidity' ? (v) => `${v}%` : undefined}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#16213e', border: 'none', borderRadius: 8 }}
                  labelStyle={{ color: '#ccd6f6' }}
                  labelFormatter={(v) => new Date(v).toLocaleString()}
                />
                <Legend />
                {CHART_CONFIG[chartType].sensors.map(({ sensor, key, color, name }) => (
                    <Line 
                      key={sensor}
                      type="monotone" 
                      dataKey={key} 
                      stroke={color} 
                      strokeWidth={2} 
                      dot={false} 
                      name={name} 
                    />
                  ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-muted text-xs py-4">
          Auto-refreshes every 30 seconds
        </div>
      </div>
    </div>
  );
}

export default App;
