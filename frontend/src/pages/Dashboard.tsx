import { useCallback, useEffect, useRef, useState } from 'react';
import { Layout, Responsive, WidthProvider } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import { api } from '../api/client';
import { AgentStatus, CurrentReading, Device, JournalEntry, LayoutItem } from '../types';
import { BotCard } from '../components/BotCard';
import { MetricCard } from '../components/MetricCard';
import { ChartWidget } from '../components/ChartWidget';
import { CameraWidget } from '../components/CameraWidget';
import { JournalFeed } from '../components/JournalFeed';
import { FanWidget } from '../components/FanWidget';

const Grid = WidthProvider(Responsive);

const WIDGET_DEFAULTS: Record<string, { w: number; h: number }> = {
  bot: { w: 8, h: 2 },
  metric: { w: 3, h: 1 },
  chart: { w: 8, h: 4 },
  camera: { w: 4, h: 2 },
  journal: { w: 12, h: 3 },
  fan: { w: 4, h: 4 },
};

const PALETTE = ['metric', 'chart', 'camera', 'journal', 'fan', 'bot'];

export function Dashboard() {
  const [layout, setLayout] = useState<LayoutItem[]>([]);
  const [current, setCurrent] = useState<CurrentReading[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [journal, setJournal] = useState<JournalEntry[]>([]);
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [editing, setEditing] = useState(false);
  const counter = useRef(0);

  const load = useCallback(async () => {
    const [l, c, d, jn, st] = await Promise.all([
      api.layout().catch(() => []),
      api.current().catch(() => []),
      api.devices().catch(() => []),
      api.agentJournal(30).catch(() => []),
      api.agentStatus().catch(() => null),
    ]);
    setLayout(l);
    setCurrent(c);
    setDevices(d);
    setJournal(jn);
    setStatus(st);
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, [load]);

  const saveLayout = useCallback((items: LayoutItem[]) => {
    setLayout(items);
    api.saveLayout(items).catch(() => {});
  }, []);

  const onLayoutChange = (rgl: Layout[]) => {
    setLayout((prev) =>
      prev.map((w) => {
        const l = rgl.find((r) => r.i === w.i);
        return l ? { ...w, x: l.x, y: l.y, w: l.w, h: l.h } : w;
      })
    );
  };

  const commitLayout = () => api.saveLayout(layout).catch(() => {});

  const addWidget = (type: string) => {
    const d = WIDGET_DEFAULTS[type] || { w: 4, h: 2 };
    const item: LayoutItem = {
      i: `${type}-${Date.now()}-${counter.current++}`,
      type,
      x: 0,
      y: 9999,
      ...d,
      config: {},
    };
    saveLayout([...layout, item]);
  };

  const removeWidget = (i: string) =>
    saveLayout(layout.filter((w) => w.i !== i));

  const setWidgetConfig = (i: string, config: Record<string, unknown>) =>
    saveLayout(layout.map((w) => (w.i === i ? { ...w, config } : w)));

  const readingFor = (sensor?: string) =>
    current.find((r) => `${r.device}.${r.metric}` === sensor || r.device === sensor);
  const deviceByName = (name?: string) => devices.find((d) => d.name === name);
  const sensorKeys = current.map((r) => `${r.device}.${r.metric}`);
  const cameras = devices.filter((d) => d.driver === 'camera');
  const actuators = devices.filter((d) => d.driver === 'fan' || d.driver === 'pump');

  const renderWidget = (w: LayoutItem) => {
    switch (w.type) {
      case 'bot':
        return <BotCard status={status} musings={journal} />;
      case 'metric':
        return (
          <MetricCard
            reading={readingFor(w.config.sensor as string)}
            sensorKey={w.config.sensor as string}
          />
        );
      case 'chart':
        return <ChartWidget current={current} />;
      case 'camera':
        return <CameraWidget device={deviceByName(w.config.device as string) || cameras[0]} />;
      case 'journal':
        return <JournalFeed entries={journal} />;
      case 'fan':
        return <FanWidget device={deviceByName(w.config.device as string) || actuators[0]} />;
      default:
        return (
          <div className="bg-card border border-line rounded-2xl h-full flex items-center justify-center font-mono text-xs text-muted">
            {w.type}
          </div>
        );
    }
  };

  const widgetConfig = (w: LayoutItem) => {
    if (!editing) return null;
    if (w.type === 'metric')
      return (
        <select
          className="absolute top-1 left-6 z-10 bg-card2 text-muted text-[10px] font-mono rounded px-1 max-w-[60%]"
          value={(w.config.sensor as string) || ''}
          onChange={(e) => setWidgetConfig(w.i, { ...w.config, sensor: e.target.value })}
        >
          <option value="">pick sensor…</option>
          {sensorKeys.map((k) => (
            <option key={k} value={k}>{k}</option>
          ))}
        </select>
      );
    if (w.type === 'camera' || w.type === 'fan')
      return (
        <select
          className="absolute top-1 left-6 z-10 bg-card2 text-muted text-[10px] font-mono rounded px-1 max-w-[60%]"
          value={(w.config.device as string) || ''}
          onChange={(e) => setWidgetConfig(w.i, { ...w.config, device: e.target.value })}
        >
          <option value="">auto</option>
          {(w.type === 'camera' ? cameras : actuators).map((d) => (
            <option key={d.name} value={d.name}>{d.label}</option>
          ))}
        </select>
      );
    return null;
  };

  return (
    <div>
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        {editing && (
          <>
            <span className="px-3 h-8 inline-flex items-center rounded-full bg-primary/15 text-primary text-xs font-mono">
              ✏️ editing layout
            </span>
            <span className="font-mono text-[11px] text-muted">drag to move · ◢ to resize · + adds</span>
            {PALETTE.map((p) => (
              <button
                key={p}
                onClick={() => addWidget(p)}
                className="px-2.5 h-8 rounded-full bg-card2 text-muted text-xs font-mono"
              >
                + {p}
              </button>
            ))}
          </>
        )}
        <button
          onClick={() => (editing ? commitLayout() : null, setEditing(!editing))}
          className={`ml-auto min-h-[36px] px-4 rounded-lg text-xs font-semibold ${
            editing ? 'bg-primary text-dark' : 'bg-card2 text-muted'
          }`}
        >
          {editing ? 'Done' : '✏️ edit layout'}
        </button>
      </div>
      <Grid
        className="layout"
        layouts={{ lg: layout, xxs: layout }}
        breakpoints={{ lg: 920, xxs: 0 }}
        cols={{ lg: 12, xxs: 4 }}
        rowHeight={52}
        margin={[14, 14]}
        isDraggable={editing}
        isResizable={editing}
        onLayoutChange={onLayoutChange}
        onDragStop={commitLayout}
        onResizeStop={commitLayout}
      >
        {layout.map((w) => (
          <div
            key={w.i}
            className={`relative ${editing ? 'outline outline-1 outline-dashed outline-line rounded-2xl' : ''}`}
          >
            {editing && (
              <button
                onClick={() => removeWidget(w.i)}
                className="absolute top-1 right-1 z-10 w-6 h-6 rounded bg-card2 text-muted text-xs font-mono"
              >
                ✕
              </button>
            )}
            {widgetConfig(w)}
            {renderWidget(w)}
          </div>
        ))}
      </Grid>
    </div>
  );
}
