"""Generate a dependency-free, self-owned SVG pulse for a GitHub profile."""
from __future__ import annotations

import html
import json
import os
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


OWNER = os.getenv("GITHUB_REPOSITORY_OWNER", "your-github-username")
TOKEN = os.getenv("GITHUB_TOKEN", "")
OUT = Path(__file__).resolve().parents[1] / "assets" / "pulse.svg"


def get(path: str):
    request = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-pulse", **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def main() -> None:
    user = get(f"/users/{OWNER}")
    repos = get(f"/users/{OWNER}/repos?per_page=100&sort=updated")
    owned = [r for r in repos if not r["fork"]]
    languages = Counter(r["language"] for r in owned if r["language"])
    stars = sum(r["stargazers_count"] for r in owned)
    recent = next((r for r in owned if r["name"].lower() != OWNER.lower()), owned[0] if owned else None)
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d UTC")
    lang_text = " · ".join(name for name, _ in languages.most_common(4)) or "building the first signal"
    repo_text = recent["name"] if recent else "next-project"
    description = (recent or {}).get("description") or "engineering in progress"
    values = [
        ("PUBLIC REPOS", str(user.get("public_repos", 0))),
        ("OWNED PROJECTS", str(len(owned))),
        ("STARS EARNED", str(stars)),
        ("FOLLOWERS", str(user.get("followers", 0))),
    ]
    cards = "".join(
        f'<g transform="translate({28 + i * 209} 62)"><rect width="190" height="82" rx="10" class="card"/><text x="16" y="28" class="label">{label}</text><text x="16" y="62" class="value">{value}</text></g>'
        for i, (label, value) in enumerate(values)
    )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="250" viewBox="0 0 900 250" role="img">
<title>Live GitHub pulse for {html.escape(OWNER)}</title><style>text{{font-family:'JetBrains Mono','Cascadia Code',Consolas,monospace}}.card{{fill:#0d1724;stroke:#263a52}}.label{{font-size:10px;fill:#7890aa;letter-spacing:1px}}.value{{font-size:25px;fill:#62e6a7;font-weight:700}}.small{{font-size:11px;fill:#7890aa}}.text{{font-size:12px;fill:#e6edf6}}</style>
<rect width="900" height="250" rx="18" fill="#080e17" stroke="#203047"/><text x="28" y="35" class="small">GITHUB TELEMETRY / GENERATED {updated}</text>{cards}
<text x="28" y="181" class="small">LATEST ACTIVE REPOSITORY</text><text x="210" y="181" class="text">{html.escape(repo_text)}</text>
<text x="28" y="207" class="small">SIGNAL</text><text x="210" y="207" class="text">{html.escape(description[:72])}</text>
<text x="28" y="231" class="small">LANGUAGES</text><text x="210" y="231" class="text">{html.escape(lang_text)}</text></svg>'''
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
