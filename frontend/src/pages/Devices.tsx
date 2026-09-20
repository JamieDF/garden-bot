import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import { Device } from '../types';

const DRIVER_ICONS: Record<string, string> = {
  bme280: '🌡️',
  ds18b20: '🌡️',
  moisture: '💧',
  fan: '🌀',
  pump: '🚿',
  camera: '📹',
};

const DRIVERS = ['bme280', 'ds18b20', 'moisture', 'fan', 'pump', 'camera'];

const fmtParams = (d: Device) =>
  Object.entries(d.params)
    .map(([k, v]) => `${k}=${typeof v === 'number' && k === 'address' ? '0x' + v.toString(16) : v}`)
    .join(' · ');

const BLANK: Partial<Device> = {
  name: '',
  label: '',
  driver: 'ds18b20',
  params: {},
  location: '',
  enabled: true,
};

export function Devices() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [editing, setEditing] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState<Partial<Device>>(BLANK);
  const [paramsText, setParamsText] = useState('{}');
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => api.devices().then(setDevices).catch(() => {}), []);
  useEffect(() => {
    load();
  }, [load]);

  const startEdit = (d: Device) => {
    setEditing(d.name);
    setAdding(false);
    setDraft({ ...d });
    setParamsText(JSON.stringify(d.params, null, 2));
    setError(null);
  };

  const startAdd = () => {
    setAdding(true);
    setEditing(null);
    setDraft(BLANK);
    setParamsText('{}');
    setError(null);
  };

  const save = async () => {
    try {
      const params = JSON.parse(paramsText || '{}');
      const body = { ...draft, params };
      if (adding) await api.createDevice(body);
      else await api.updateDevice(editing!, body);
      setEditing(null);
      setAdding(false);
      load();
    } catch (e) {
      setError(e instanceof SyntaxError ? 'params: invalid JSON' : String(e));
    }
  };

  const remove = async (name: string) => {
    await api.deleteDevice(name).catch(() => {});
    load();
  };

  const field = (label: string, node: React.ReactNode) => (
    <label className="block">
      <span className="text-[11px] text-muted uppercase tracking-wide block mb-1">{label}</span>
      {node}
    </label>
  );

  const input =
    'w-full bg-card2 border border-line rounded-lg px-3 py-2.5 font-mono text-[13px] text-text min-h-[42px]';

  const editor = (
    <div className="bg-card border border-primary/50 rounded-2xl p-4 mt-2">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {field('name', (
          <input className={input} value={draft.name || ''} disabled={!adding}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
        ))}
        {field('label', (
          <input className={input} value={draft.label || ''}
            onChange={(e) => setDraft({ ...draft, label: e.target.value })} />
        ))}
        {field('driver', (
          <select className={input} value={draft.driver}
            onChange={(e) => setDraft({ ...draft, driver: e.target.value })}>
            {DRIVERS.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        ))}
        {field('location', (
          <input className={input} value={draft.location || ''}
            onChange={(e) => setDraft({ ...draft, location: e.target.value })} />
        ))}
        {field('enabled', (
          <select className={input} value={draft.enabled ? 'yes' : 'no'}
            onChange={(e) => setDraft({ ...draft, enabled: e.target.value === 'yes' })}>
            <option value="yes">enabled</option>
            <option value="no">disabled</option>
          </select>
        ))}
      </div>
      <div className="mt-3">
        {field('params (json)', (
          <textarea className={`${input} min-h-[90px]`} value={paramsText}
            onChange={(e) => setParamsText(e.target.value)} spellCheck={false} />
        ))}
      </div>
      {error && <p className="font-mono text-xs text-danger mt-2">{error}</p>}
      <div className="flex gap-2 mt-3">
        <button onClick={save} className="min-h-[40px] px-5 rounded-lg bg-primary text-dark font-semibold text-sm">Save</button>
        <button onClick={() => { setEditing(null); setAdding(false); }}
          className="min-h-[40px] px-4 rounded-lg bg-card2 text-muted text-sm">Cancel</button>
      </div>
    </div>
  );

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-text">Devices</h2>
        <span className="text-[11px] px-2.5 h-6 inline-flex items-center rounded-full bg-card2 text-muted font-mono">
          {devices.length} configured
        </span>
        <button onClick={startAdd}
          className="ml-auto min-h-[40px] px-4 rounded-lg bg-primary text-dark font-semibold text-sm">
          + Add device
        </button>
      </div>

      {adding && editor}

      <div className="bg-card border border-line rounded-2xl px-4">
        {devices.map((d) => (
          <div key={d.name} className="border-b border-line/60 last:border-0">
            <div className="flex items-center gap-3 py-3">
              <span className="text-xl w-7 text-center">{DRIVER_ICONS[d.driver] || '🔌'}</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-sm text-text">{d.label}</span>
                  <span className="text-[10.5px] px-2 h-5 inline-flex items-center rounded-full bg-card2 text-muted font-mono">
                    {d.location || '—'}
                  </span>
                  <span className="font-mono text-[11px] text-muted">{d.driver}</span>
                  {!d.enabled && (
                    <span className="font-mono text-[10.5px] text-warn">disabled</span>
                  )}
                </div>
                <div className="font-mono text-[11px] text-muted mt-0.5 truncate">
                  {d.name} · {fmtParams(d)}
                </div>
              </div>
              <button onClick={() => startEdit(d)}
                className="min-h-[40px] px-4 rounded-lg bg-card2 text-muted text-xs font-mono">
                Edit
              </button>
              <button onClick={() => remove(d.name)}
                className="min-h-[40px] px-3 rounded-lg bg-card2 text-danger/70 text-xs font-mono">
                ✕
              </button>
            </div>
            {editing === d.name && editor}
          </div>
        ))}
      </div>

      <p className="font-mono text-[11px] text-muted mt-4 leading-relaxed">
        drivers: bme280 (bus, address) · ds18b20 (index or device_id) · fan/pump
        (pin, active_low, watch, thresholds) · camera (width, height, fps)
      </p>
    </div>
  );
}
