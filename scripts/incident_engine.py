"""Stateful GitHub-Issues incident game and SVG renderer."""
from __future__ import annotations

import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "state" / "incident.json"
OUT = ROOT / "assets" / "incident.svg"

SCENARIOS = [
    {
        "id": "INC-0421", "title": "QUEUE SATURATION",
        "detail": "ingest depth +840% · consumer lag 94s · API latency climbing",
        "metric": "queue_depth", "value": "18,492", "delta": "+840%",
        "correct": "apply-backpressure",
        "why": "Backpressure protects the dependency and bounds work while consumers recover.",
    },
    {
        "id": "INC-0422", "title": "CACHE STAMPEDE",
        "detail": "hot key expired · database QPS +610% · replicas near saturation",
        "metric": "db_replica_cpu", "value": "91%", "delta": "+64%",
        "correct": "restart-service",
        "why": "In this simulation, restart-service enables request coalescing deployed in the new build.",
    },
    {
        "id": "INC-0423", "title": "WORKER EXHAUSTION",
        "detail": "job arrival rate exceeds drain rate · oldest job 11m",
        "metric": "worker_util", "value": "99%", "delta": "+31%",
        "correct": "scale-workers",
        "why": "The queue is healthy and jobs are independent; horizontal workers restore drain capacity.",
    },
    {
        "id": "INC-0424", "title": "CACHE CORRUPTION",
        "detail": "deserialization failures isolated to cache reads · origin is healthy",
        "metric": "error_rate", "value": "17.8%", "delta": "+17%",
        "correct": "bypass-cache",
        "why": "Bypassing the corrupted cache restores correctness while the cache is rebuilt.",
    },
]


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def evaluate(state: dict, command: str, operator: str) -> str:
    scenario = SCENARIOS[state["scenario"] % len(SCENARIOS)]
    good = command == scenario["correct"]
    state["resolved" if good else "degraded"] += 1
    state["last_operator"] = f"@{operator}" if operator else "anonymous"
    state["last_action"] = command
    state["last_result"] = ("RESOLVED — " if good else "DEGRADED — ") + scenario["why"]
    state["scenario"] = (state["scenario"] + 1) % len(SCENARIOS)
    return state["last_result"]


def render(state: dict) -> None:
    s = SCENARIOS[state["scenario"] % len(SCENARIOS)]
    esc = lambda value: html.escape(str(value))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="390" viewBox="0 0 1200 390" role="img"><title>Live production incident lab</title>
<defs><linearGradient id="ibg" x2="1" y2="1"><stop stop-color="#090b14"/><stop offset="1" stop-color="#10101c"/></linearGradient><filter id="ig"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter><style>text{{font-family:'JetBrains Mono','Cascadia Code',Consolas,monospace}}.dim{{fill:#777f94}}.ink{{fill:#eef2fa}}.red{{fill:#ff647c}}.amber{{fill:#ffc857}}.mint{{fill:#68f5bd}}.panel{{fill:#0c111d;stroke:#292c3d}}.wave{{stroke:#ff647c;stroke-width:2;fill:none;stroke-dasharray:10 6;animation:w 4s linear infinite}}.pulse{{animation:p 1.4s ease-in-out infinite}}@keyframes w{{to{{stroke-dashoffset:-96}}}}@keyframes p{{50%{{opacity:.3}}}}@media(prefers-reduced-motion:reduce){{.wave,.pulse{{animation:none}}}}</style></defs>
<rect width="1200" height="390" rx="20" fill="url(#ibg)" stroke="#342536"/><rect x="24" y="24" width="1152" height="342" rx="15" class="panel"/><circle cx="50" cy="50" r="5" class="red pulse" filter="url(#ig)"/><text x="65" y="55" font-size="11" class="red">SEV-1 / ACTIVE</text><text x="1050" y="55" font-size="11" class="dim">{esc(s['id'])}</text>
<text x="50" y="108" font-size="27" font-weight="700" class="ink">{esc(s['title'])}</text><text x="50" y="138" font-size="12" class="dim">{esc(s['detail'])}</text>
<path d="M50 193 C110 153 146 235 210 193 S314 153 372 193 S476 236 540 193" class="wave"/><text x="50" y="238" font-size="10" class="dim">PRIMARY SIGNAL</text><text x="50" y="275" font-size="15" class="ink">{esc(s['metric'])}</text><text x="250" y="275" font-size="28" class="red">{esc(s['value'])}</text><text x="375" y="275" font-size="11" class="red">{esc(s['delta'])}</text>
<rect x="618" y="82" width="520" height="112" rx="12" fill="#0a0f19" stroke="#292c3d"/><text x="640" y="108" font-size="10" class="dim">LAST OPERATOR / {esc(state['last_operator'])}</text><text x="640" y="140" font-size="11" class="amber">{esc(state['last_action'])}</text><text x="640" y="168" font-size="10" class="dim">{esc(state['last_result'])[:78]}</text>
<rect x="618" y="214" width="250" height="84" rx="12" fill="#0a0f19" stroke="#292c3d"/><text x="640" y="242" font-size="10" class="dim">INCIDENTS RESOLVED</text><text x="640" y="278" font-size="24" class="mint">{state['resolved']:02d}</text><rect x="888" y="214" width="250" height="84" rx="12" fill="#0a0f19" stroke="#292c3d"/><text x="910" y="242" font-size="10" class="dim">DEGRADED FURTHER</text><text x="910" y="278" font-size="24" class="red">{state['degraded']:02d}</text>
<text x="50" y="337" font-size="10" class="dim">SELECT AN OPERATIONAL RESPONSE BELOW · EACH ISSUE ADVANCES THE GLOBAL SIMULATION</text><text x="1084" y="337" font-size="10" class="mint">LIVE</text></svg>'''
    OUT.write_text(svg, encoding="utf-8")


def main() -> None:
    state = load_state()
    command = os.getenv("INCIDENT_COMMAND", "").strip().lower()
    prefix = "[incident] response: "
    if command.startswith(prefix):
        command = command.removeprefix(prefix).strip()
    operator = os.getenv("INCIDENT_OPERATOR", "")
    if command:
        evaluate(state, command, operator)
        STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    render(state)
    print(state["last_result"])


if __name__ == "__main__":
    main()
