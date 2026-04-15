import { useEffect, useState, useCallback, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { SensorReadings, Reading, SensorStatsResponse, FanState } from './types';

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
  const [fanState, setFanState] = useState<FanState | null>(null);
  const [thresholdDraft, setThresholdDraft] = useState<{on: string, off: string}>({on: '20.0', off: '19.0'});
  const fanStateInitialized = useRef(false);
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

  const loadFanState = useCallback(async () => {
    try {
      const res = await fetch('/api/fan');
      const data = await res.json();
      setFanState(data);
      // Only init threshold draft on first load, not on every poll
      if (!fanStateInitialized.current) {
        fanStateInitialized.current = true;
        setThresholdDraft({on: String(data.on_threshold), off: String(data.off_threshold)});
      }
    } catch (err) {
      console.error('Failed to fetch fan state:', err);
    }
  }, []);

  const setFanMode = async (on: boolean) => {
    try {
      const res = await fetch('/api/fan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ on }),
      });
      const data = await res.json();
      setFanState(data);
    } catch (err) {
      console.error('Failed to set fan state:', err);
    }
  };

  const setAutoMode = async (enabled: boolean, on_threshold: number, off_threshold: number) => {
    try {
      const res = await fetch('/api/fan/auto', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled, on_threshold, off_threshold }),
      });
      const data = await res.json();
      setFanState(data);
    } catch (err) {
      console.error('Failed to set auto mode:', err);
    }
  };

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
    loadFanState();
    loadChartData();
  }, [loadReadings, loadStats, loadFanState, loadChartData]);

  useEffect(() => {
    const interval = setInterval(() => {
      loadReadings();
      loadStats();
      loadFanState();
      loadChartData();
    }, 5000);
    return () => clearInterval(interval);
  }, [loadReadings, loadStats, loadFanState, loadChartData]);

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

        {/* Fan Control */}
        {fanState && (
          <div className="bg-card rounded-xl p-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-text">💨 Fan</h2>
              {/* Mode Toggle */}
              <div className="flex gap-1">
                <button
                  onClick={() => setAutoMode(false, fanState.on_threshold, fanState.off_threshold)}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                    fanState.mode === 'manual'
                      ? 'bg-primary text-dark'
                      : 'bg-dark text-muted hover:text-text'
                  }`}
                >
                  Manual
                </button>
                <button
                  onClick={() => setAutoMode(true, fanState.on_threshold, fanState.off_threshold)}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                    fanState.mode === 'auto'
                      ? 'bg-primary text-dark'
                      : 'bg-dark text-muted hover:text-text'
                  }`}
                >
                  Auto
                </button>
              </div>
            </div>
            
            {/* Current State Indicator */}
            <div className="flex items-center justify-center mb-4 p-3 bg-dark rounded-lg">
              <div className={`w-4 h-4 rounded-full mr-3 ${fanState.state === 'on' ? 'bg-green-500' : 'bg-red-500/50'}`} />
              <span className={`text-2xl font-bold ${fanState.state === 'on' ? 'text-green-400' : 'text-muted'}`}>
                {fanState.state === 'on' ? 'FAN RUNNING' : 'FAN OFF'}
              </span>
              <span className="ml-3 text-xs text-muted">
                ({fanState.mode})
              </span>
            </div>
            
            {/* Controls */}
            {fanState.mode === 'manual' ? (
              /* Manual Toggle Button */
              <button
                onClick={() => setFanMode(fanState.state !== 'on')}
                className={`w-full py-4 rounded-lg font-bold text-lg transition-colors ${
                  fanState.state === 'on'
                    ? 'bg-red-600 hover:bg-red-700 text-white'
                    : 'bg-green-600 hover:bg-green-700 text-white'
                }`}
              >
                Turn {fanState.state === 'on' ? 'OFF' : 'ON'}
              </button>
            ) : (
              /* Auto Mode Threshold Inputs */
              <div className="space-y-3">
                <p className="text-xs text-muted text-center">
                  Auto mode: fan turns on above {fanState.on_threshold}°C, off below {fanState.off_threshold}°C
                </p>
                <div className="flex gap-4">
                  <div className="flex-1">
                    <label className="text-xs text-muted block mb-1">On above (°C)</label>
                    <input
                      type="number"
                      value={thresholdDraft.on}
                      className="w-full bg-dark rounded px-3 py-2 text-text text-center"
                      onChange={(e) => setThresholdDraft(d => ({...d, on: e.target.value}))}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          const val = parseFloat(e.currentTarget.value);
                          const offVal = parseFloat(thresholdDraft.off);
                          if (!isNaN(val) && !isNaN(offVal)) setAutoMode(true, val, offVal);
                          e.currentTarget.blur();
                        }
                      }}
                      onBlur={(e) => {
                        const val = parseFloat(e.currentTarget.value);
                        const offVal = parseFloat(thresholdDraft.off);
                        if (!isNaN(val) && !isNaN(offVal)) setAutoMode(true, val, offVal);
                      }}
                    />
                  </div>
                  <div className="flex-1">
                    <label className="text-xs text-muted block mb-1">Off below (°C)</label>
                    <input
                      type="number"
                      value={thresholdDraft.off}
                      className="w-full bg-dark rounded px-3 py-2 text-text text-center"
                      onChange={(e) => setThresholdDraft(d => ({...d, off: e.target.value}))}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          const onVal = parseFloat(thresholdDraft.on);
                          const val = parseFloat(e.currentTarget.value);
                          if (!isNaN(onVal) && !isNaN(val)) setAutoMode(true, onVal, val);
                          e.currentTarget.blur();
                        }
                      }}
                      onBlur={(e) => {
                        const onVal = parseFloat(thresholdDraft.on);
                        const val = parseFloat(e.currentTarget.value);
                        if (!isNaN(onVal) && !isNaN(val)) setAutoMode(true, onVal, val);
                      }}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

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
          Auto-refreshes every 5 seconds
        </div>
      </div>
    </div>
  );
}

export default App;
