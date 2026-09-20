import { useEffect, useState } from 'react';
import { Device, FanState } from '../types';
import { api } from '../api/client';

export function FanWidget({ device }: { device?: Device }) {
  const [fan, setFan] = useState<FanState | null>(null);

  const load = () => {
    if (!device) return;
    fetch(`/api/devices/${device.name}/state`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setFan)
      .catch(() => {});
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [device?.name]);

  if (!device) return null;
  const on = fan?.state === 'on';
  const act = (body: object) =>
    api.deviceAction(device.name, body).then(setFan).catch(() => {});

  return (
    <div className="bg-card border border-line rounded-2xl p-4 h-full overflow-hidden flex flex-col gap-2.5">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-sm text-text">
          {device.driver === 'pump' ? '🚿' : '🌀'} {device.label}
        </span>
        <span className={`w-2.5 h-2.5 rounded-full ${on ? 'bg-moss' : 'bg-danger/50'}`} />
      </div>
      <div className="font-mono text-[12px] text-muted">
        {fan ? `${fan.state.toUpperCase()} · ${fan.mode}` : '—'}
        {fan?.mode === 'auto' && (
          <span className="block mt-1">
            on ≥ {fan.on_threshold}° · off ≤ {fan.off_threshold}°
            {fan.watch ? ` · ${fan.watch}` : ''}
          </span>
        )}
      </div>
      <div className="mt-auto flex gap-2">
        <button
          onClick={() => act({ action: on ? 'off' : 'on' })}
          className={`flex-1 min-h-[40px] rounded-lg font-semibold text-sm ${
            on ? 'bg-red-600 text-white' : 'bg-green-700 text-white'
          }`}
        >
          {on ? 'Turn off' : 'Turn on'}
        </button>
        <button
          onClick={() =>
            act({
              action: fan?.mode === 'auto' ? 'manual' : 'auto',
              on_threshold: fan?.on_threshold,
              off_threshold: fan?.off_threshold,
            })
          }
          className="min-h-[40px] px-3 rounded-lg bg-card2 text-muted text-xs font-mono"
        >
          {fan?.mode === 'auto' ? 'manual' : 'auto'}
        </button>
      </div>
    </div>
  );
}
