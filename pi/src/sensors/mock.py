"""
Mock sensor driver - fake drifting readings for dev/testing off-Pi.
Params: {"<metric>": <base_value>, ...} e.g. {"temperature": 22, "humidity": 60}
"""

import random


class MockReader:
    """Random-walk readings pulled gently toward each base value."""

    def __init__(self, params: dict | None = None):
        p = params or {"temperature": 22.0}
        self._base = {m: float(b) for m, b in p.items()}
        self._values = dict(self._base)

    def read(self) -> dict:
        out = {}
        for metric, base in self._base.items():
            v = self._values[metric]
            # mean-reverting random walk
            v = v + (base - v) * 0.05 + random.uniform(-0.4, 0.4)
            self._values[metric] = v
            out[metric] = round(v, 2)
        return out
