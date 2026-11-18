#!/usr/bin/env python3
"""Post-process Platane/snk SVGs to soften empty 0-contribution cells into a
left-faded blueprint perfboard dot-matrix while keeping active cells & snake crisp.
"""

from __future__ import annotations

import pathlib
import re
import xml.etree.ElementTree as ET


def style_snake_svg(svg_text: str, *, is_dark: bool) -> str:
    # Start the loop ~21% in so the snake enters the active region immediately on load
    m_dur = re.search(r"animation:none\s+(\d+)ms\s+linear\s+infinite", svg_text)
    dur_ms = int(m_dur.group(1)) if m_dur else 20000
    phase_ms = -int(dur_ms * 0.21)

    dot_fill = "#2b425e" if is_dark else "#b5c6d8"
    rule_stroke = "#1d2e42" if is_dark else "#dbe5f0"
    label_fill = "#4c6480" if is_dark else "#7f93a8"
    track_bg = "#121b28" if is_dark else "#eef3f8"
    dot_group_opacity = "0.72" if is_dark else "0.78"

    # Eaten active cells turn transparent so they cleanly reveal the perfboard pinhole underneath
    svg_text = re.sub(r"--cb:[^;]+;", "--cb:transparent;", svg_text)
    svg_text = re.sub(r"--ce:[^;]+;", "--ce:transparent;", svg_text)
    svg_text = re.sub(r"--c0:[^;]+;", "--c0:transparent;", svg_text)

    extra_css = (
        f".c,.u,.s{{animation-delay:{phase_ms}ms!important}}"
        f".dot{{fill:{dot_fill}}}"
        f'.meta{{font-family:ui-monospace,SFMono-Regular,"Cascadia Mono",Consolas,monospace;'
        f"font-size:9px;fill:{label_fill};letter-spacing:1.1px}}"
    )
    svg_text = svg_text.replace("</style>", extra_css + "</style>", 1)

    defs = """<defs>
    <linearGradient id="emptyFadeGrad" x1="0" y1="0" x2="848" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.05"/>
      <stop offset="28%" stop-color="#ffffff" stop-opacity="0.14"/>
      <stop offset="54%" stop-color="#ffffff" stop-opacity="0.38"/>
      <stop offset="78%" stop-color="#ffffff" stop-opacity="0.72"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0.95"/>
    </linearGradient>
    <mask id="emptyCellMask">
      <rect x="-20" y="-40" width="900" height="220" fill="url(#emptyFadeGrad)"/>
    </mask>
  </defs>"""
    svg_text = svg_text.replace("</style>", "</style>" + defs, 1)

    # Place a centered 3.2x3.2 rounded PCB pinhole under EVERY grid slot,
    # remove 0-contribution 12x12 bricks, and gently soften distant isolated active cells on the far left.
    pinholes: list[str] = []

    def process_cell(match: re.Match[str]) -> str:
        cls = match.group(1)
        x = float(match.group(2))
        y = float(match.group(3))
        rest = match.group(4)
        dx = x + 4.4
        dy = y + 4.4
        pinholes.append(
            f'<rect class="dot" x="{dx:.1f}" y="{dy:.1f}" width="3.2" height="3.2" rx="1.6"/>'
        )
        if cls == "c":
            # Pure 0-contribution cell: replaced entirely by the masked perfboard pinhole
            return ""
        # Active contribution cell: gently attenuate isolated early-year cells so they echo softly
        if x < 500:
            soft_op = round(0.42 + 0.58 * (x / 500.0), 2)
            return f'<rect class="{cls}" x="{match.group(2)}" y="{match.group(3)}" opacity="{soft_op}"{rest}/>'
        return match.group(0)

    svg_text = re.sub(
        r'<rect class="(c(?:\s+[^"]+)?)"\s+x="([^"]+)"\s+y="([^"]+)"([^>]*)/>',
        process_cell,
        svg_text,
    )

    chrome_layer = (
        f'<g class="meta">'
        f'<text x="2" y="-10">ACTIVITY TRACE // ROLLING 52W</text>'
        f'<text x="846" y="-10" text-anchor="end">RECENT</text>'
        f"</g>"
        f'<line x1="2" y1="-3" x2="846" y2="-3" stroke="{rule_stroke}" stroke-width="0.75" stroke-dasharray="3 3"/>'
        f'<rect x="0" y="126" width="848" height="3" rx="1.5" fill="{track_bg}" mask="url(#emptyCellMask)"/>'
        f'<g mask="url(#emptyCellMask)" opacity="{dot_group_opacity}">'
        + "".join(pinholes)
        + "</g>"
    )
    svg_text = svg_text.replace("</defs>", "</defs>" + chrome_layer, 1)

    # Slim bottom telemetry progress bar (.u) onto the 3px track at y=126
    svg_text = re.sub(
        r'(<rect class="u u\d+" )height="12"([^>]*?)y="144"',
        r'\1height="3" rx="1.5"\2y="126"',
        svg_text,
    )

    svg_text = svg_text.replace(
        'viewBox="-16 -32 880 192" width="880" height="192"',
        'viewBox="-8 -24 864 162" width="864" height="162"',
    )

    # Verify output remains well-formed XML
    ET.fromstring(svg_text)
    return svg_text


def main() -> None:
    dist = pathlib.Path("dist")
    targets = [
        (dist / "github-snake.svg", False),
        (dist / "github-snake-dark.svg", True),
    ]
    for path, is_dark in targets:
        if path.exists():
            updated = style_snake_svg(path.read_text(encoding="utf-8"), is_dark=is_dark)
            path.write_text(updated, encoding="utf-8")
            print(f"Styled {path} ({len(updated)} bytes)")


if __name__ == "__main__":
    main()
