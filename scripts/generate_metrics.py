#!/usr/bin/env python3
"""
GitHub Metrics SVG Generator — Open Source Edition
Configurable via config.yml and customizable themes.
"""

import os
import sys
import json
import argparse
import tempfile
from html import escape
from pathlib import Path
from datetime import datetime, timedelta, timezone, date

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from themes.presets import get_theme
from scripts.configuration import parse_yaml
from scripts.github_data import GitHub, MetricsError, collect

CONFIG_PATH = os.path.join(REPO_ROOT, "config.yml")
config = parse_yaml(CONFIG_PATH)

USERNAME = os.getenv("METRICS_USERNAME") or config.get("username", "Ryanleoncoder")
THEME_NAME = config.get("theme", "neobrutalist")
THEME = get_theme(THEME_NAME, config.get("custom_palette"))
TOKEN = os.getenv("METRICS_TOKEN") or os.getenv("GITHUB_TOKEN", "")

METRICS_DIR = os.path.join(REPO_ROOT, "assets", "metrics")

def _save(name, svg):
    Path(METRICS_DIR).mkdir(parents=True, exist_ok=True)
    out_path = Path(METRICS_DIR) / name
    out_path.write_text("\n".join(svg), encoding="utf-8")
    print(f"Generated {out_path}")


def _stamp(cfg):
    if cfg.get("_demo"):
        return "DEMO DATA / THEME PREVIEW"
    return ""


def _footer(svg, cfg, height, color):
    svg.append(f'<text x="536" y="{height-30}" text-anchor="end" fill="{color}" font-family="monospace" font-size="10">{escape(_stamp(cfg))}</text>')


def _height(cfg, rows, row_height):
    data = cfg.get("_data", {})
    if data:
        repo_rows = min(cfg["top_repos"]["count"], len(data["repos"]))
        languages = len(data["languages"])
        language_rows = min(languages, cfg["languages"]["max_languages"])
        language_rows += int(languages > language_rows)
        return max(260 + language_rows * 42, 180 + repo_rows * 60)
    return (260 if row_height == 42 else 180) + rows * row_height

def generate_languages_commits_svg(lang_stats, cfg):
    total_bytes = sum(lang_stats.values()) if lang_stats else 1
    colors = {
        "Python": "#3776AB", "JavaScript": "#F7DF1E", "TypeScript": "#3178C6",
        "HTML": "#E34F26", "CSS": "#1572B6", "Shell": "#89E051", "Java": "#E76F00",
        "C++": "#F34B7D", "C#": "#178600", "Go": "#00ADD8", "Rust": "#DEA584",
        "PLpgSQL": "#336791", "Dockerfile": "#384D54", "Ruby": "#CC342D",
        "PHP": "#4F5D95", "Swift": "#F05138", "Kotlin": "#A97BFF",
        "Go Template": "#00ADD8", "Makefile": "#427819", "Lua": "#000080"
    }

    # Filter out any pre-existing 'Other' key so it is never duplicated
    cleaned_stats = {k: v for k, v in lang_stats.items() if k.lower() != "other"}
    sorted_langs = sorted(cleaned_stats.items(), key=lambda x: x[1], reverse=True)

    max_count = cfg["languages"]["max_languages"]
    top_langs = sorted_langs[:max_count]
    other_bytes = sum(b for _, b in sorted_langs[max_count:])
    if other_bytes > 0:
        top_langs.append(("Other", other_bytes))

    percentages = [int(b * 100 / total_bytes) for _, b in top_langs] if total_bytes else []
    if percentages:
        order = sorted(range(len(top_langs)), key=lambda i: -(top_langs[i][1] * 100 / total_bytes - percentages[i]))
        for i in order[:100-sum(percentages)]:
            percentages[i] += 1
    items = [(lang, pct, colors.get(lang, "#8B8B8B")) for (lang, _), pct in zip(top_langs, percentages)]

    by_commits = cfg["languages"]["metric"] == "recent_commits"
    label = escape(cfg["languages"]["label"])
    sublabel = escape(cfg["languages"]["sublabel"] or (f'LAST {cfg["top_repos"]["days"]} DAYS / PRIMARY LANGUAGE' if by_commits else "CODE SIZE / OWNED REPOSITORIES"))

    # Dynamic height: header ~100px + 42px per row + 28px padding
    num_items = len(items)
    row_h = 42
    header_h = 100
    pad = 28
    svg_h = _height(cfg, num_items, row_h)
    card_h = svg_h - 32

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="590" height="{svg_h}" viewBox="0 0 590 {svg_h}" role="img">')
    svg.append(f'  <title>{label}</title>')
    svg.append(f'  <rect x="16" y="16" width="558" height="{card_h}" rx="14" fill="{THEME["light_border"]}"/>')
    svg.append(f'  <rect x="8" y="8" width="558" height="{card_h}" rx="14" fill="{THEME["light_bg"]}" stroke="{THEME["light_border"]}" stroke-width="3"/>')
    svg.append(f'  <text x="38" y="53" fill="{THEME["light_text"]}" font-family="Arial, sans-serif" font-size="25" font-weight="800">{label}</text>')
    svg.append(f'  <text x="39" y="77" fill="{THEME["light_subtext"]}" font-family="monospace" font-size="11" font-weight="700" letter-spacing="1.2">{sublabel}</text>')
    svg.append(f'  <rect x="424" y="34" width="112" height="30" rx="5" fill="{THEME["primary"]}" stroke="{THEME["light_border"]}" stroke-width="2"/>')
    primary_text = THEME.get("primary_text", "#0A0A0A")
    svg.append(f'  <text x="480" y="54" text-anchor="middle" fill="{primary_text}" font-family="monospace" font-size="10" font-weight="700">{"BY COMMITS" if by_commits else "BY BYTES"}</text>')

    row_h = max(42, (svg_h - (180 if by_commits else 130)) / max(1, num_items))
    y_pos = 109
    for lang, pct, col in items:
        cy = y_pos + 12
        bar_w = round(290 * (pct / 100))
        svg.append(f'  <circle cx="52" cy="{cy}" r="6" fill="{col}" stroke="{THEME["light_border"]}" stroke-width="1.5"/>')
        svg.append(f'  <text x="70" y="{cy+5}" fill="{THEME["light_text"]}" font-family="Arial, sans-serif" font-size="15" font-weight="800">{escape(lang.upper()[:14])}</text>')
        svg.append(f'  <rect x="195" y="{y_pos}" width="290" height="16" rx="4" fill="{THEME["light_bar_track"]}" stroke="{THEME["light_border"]}" stroke-width="1.5"/>')
        if bar_w > 0:
            svg.append(f'  <rect x="195" y="{y_pos}" width="{bar_w}" height="16" rx="4" fill="{THEME["primary"]}" stroke="{THEME["light_border"]}" stroke-width="1.5"/>')
        svg.append(f'  <text x="498" y="{y_pos+13}" fill="{THEME["light_text"]}" font-family="monospace" font-size="12" font-weight="700">{pct}%</text>')
        y_pos += row_h

    if not items:
        svg.append(f'<text x="38" y="135" fill="{THEME["light_text"]}" font-family="Arial" font-size="16">No language data in this period.</text>')
    elif by_commits:
        y = svg_h - 102
        svg.append(f'<path d="M38 {y} H536" stroke="{THEME["light_border"]}"/>')
        svg.append(f'<text x="38" y="{y+27}" fill="{THEME["light_text"]}" font-family="Arial" font-size="18" font-weight="700">{total_bytes:,} commits</text>')
        svg.append(f'<text x="38" y="{y+47}" fill="{THEME["light_subtext"]}" font-family="monospace" font-size="10">Grouped by each repository’s main language.</text>')
    _footer(svg, cfg, svg_h, THEME["light_subtext"])
    svg.append('</svg>')
    _save("languages-commits.svg", svg)

def generate_top_repos_svg(repos_data, cfg):
    max_count = cfg.get("top_repos", {}).get("count", 3)
    top_items = repos_data[:max_count]
    max_commits = max([r.get('commits', 1) for r in top_items]) if top_items else 1

    # Dynamic height for repos card
    num_repos = len(top_items)
    repo_row_h = 60
    header_h = 100
    footer_h = 40
    svg_h = _height(cfg, num_repos, repo_row_h)
    card_h = svg_h - 32

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="590" height="{svg_h}" viewBox="0 0 590 {svg_h}" role="img">')
    svg.append('  <title>My Top Repos</title>')
    svg.append(f'  <rect x="16" y="16" width="558" height="{card_h}" rx="14" fill="{THEME["primary_dark"]}"/>')
    svg.append(f'  <rect x="8" y="8" width="558" height="{card_h}" rx="14" fill="{THEME["dark_bg"]}" stroke="{THEME["dark_border"]}" stroke-width="3"/>')
    svg.append(f'  <text x="38" y="53" fill="{THEME["dark_text"]}" font-family="Arial, sans-serif" font-size="25" font-weight="800">MY TOP REPOS</text>')
    svg.append(f'  <text x="39" y="77" fill="{THEME["dark_subtext"]}" font-family="monospace" font-size="11" font-weight="700" letter-spacing="1.2">MY COMMITS / LAST {cfg["top_repos"]["days"]} DAYS</text>')
    svg.append(f'  <rect x="448" y="34" width="88" height="30" rx="5" fill="{THEME["primary"]}" stroke="{THEME["dark_border"]}" stroke-width="2"/>')
    primary_text = THEME.get("primary_text", "#0A0A0A")
    svg.append(f'  <text x="492" y="54" text-anchor="middle" fill="{primary_text}" font-family="monospace" font-size="10" font-weight="700">ACTIVE</text>')

    y_base = 120
    colors_bar = [THEME["primary"], THEME["primary_light"], THEME["primary_dark"]]

    for i, repo in enumerate(top_items):
        cy = y_base + (i * repo_row_h)
        name = escape(repo['name'].upper() if len(repo['name']) <= 28 else repo['name'][:25].upper() + "…")
        commits = repo['commits']
        topics = repo.get('topics', [])
        languages = repo.get('languages', [])
        bar_color = colors_bar[i % len(colors_bar)]

        svg.append(f'<g><title>{escape(repo["name"])}: {commits} commits</title>')
        svg.append(f'  <circle cx="52" cy="{cy}" r="6" fill="{bar_color}" stroke="{THEME["dark_text"]}" stroke-width="1.2"/>')
        svg.append(f'  <text x="70" y="{cy-4}" fill="{THEME["dark_text"]}" font-family="Arial, sans-serif" font-size="15" font-weight="800">{name}</text>')

        tag_x = 70
        tag_y = cy + 4
        max_tag_x = 325

        primary_lang = languages[0] if languages and cfg["top_repos"]["show_language"] else None
        if primary_lang:
            l_w = len(primary_lang) * 7 + 14
            if tag_x + l_w <= max_tag_x:
                svg.append(f'  <rect x="{tag_x}" y="{tag_y}" width="{l_w}" height="18" rx="4" fill="{THEME["dark_bar_track"]}" stroke="{THEME["dark_subtext"]}" stroke-width="1"/>')
                svg.append(f'  <text x="{tag_x + l_w//2}" y="{tag_y+13}" text-anchor="middle" fill="{THEME["dark_text"]}" font-family="monospace" font-size="9" font-weight="700">{escape(primary_lang)}</text>')
                tag_x += l_w + 6

        for t in (topics[:2] if cfg["top_repos"]["show_topics"] else []):
            t_str = f"#{t}"
            t_w = len(t_str) * 7 + 14
            if tag_x + t_w > max_tag_x:
                break
            tag_text = THEME.get("tag_text", THEME["dark_text"])
            svg.append(f'  <rect x="{tag_x}" y="{tag_y}" width="{t_w}" height="18" rx="4" fill="{THEME["tag_bg"]}" stroke="{bar_color}" stroke-width="1"/>')
            svg.append(f'  <text x="{tag_x + t_w//2}" y="{tag_y+13}" text-anchor="middle" fill="{tag_text}" font-family="monospace" font-size="9" font-weight="700">{escape(t_str)}</text>')
            tag_x += t_w + 6

        bar_max_w = 130
        bar_w = max(10, round(bar_max_w * (commits / max_commits)))
        bar_y = cy - 4
        svg.append(f'  <rect x="340" y="{bar_y}" width="130" height="14" rx="3" fill="{THEME["dark_bar_track"]}" stroke="#444" stroke-width="1"/>')
        svg.append(f'  <rect x="340" y="{bar_y}" width="{bar_w}" height="14" rx="3" fill="{bar_color}"/>')
        svg.append(f'  <text x="492" y="{bar_y+11}" fill="{THEME["dark_text"]}" font-family="monospace" font-size="12" font-weight="700">{commits}</text>')
        svg.append('</g>')

    footer_y = y_base + (num_repos * repo_row_h) - 20
    svg.append(f'  <path d="M340 {footer_y} H470" stroke="{THEME["dark_subtext"]}" stroke-width="1"/>')
    svg.append(f'  <text x="492" y="{footer_y+4}" fill="{THEME["primary"]}" font-family="monospace" font-size="9" font-weight="700">COMMITS</text>')
    if not top_items:
        svg.append(f'<text x="38" y="135" fill="{THEME["dark_text"]}" font-family="Arial" font-size="16">No commits in eligible repositories.</text>')
    _footer(svg, cfg, svg_h, THEME["dark_subtext"])
    svg.append('</svg>')
    _save("languages-recent.svg", svg)

def generate_year_in_code_svg(contribution_days, cfg):
    month_abbrs = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    if not contribution_days:
        raise ValueError("o calendário precisa conter dias reais")
    first_day = date.fromisoformat(contribution_days[0]["date"])
    last_day = date.fromisoformat(contribution_days[-1]["date"])
    offset = (first_day.weekday() + 1) % 7
    TOTAL_COLS = (offset + len(contribution_days) + 6) // 7
    weeks = []
    for column in range(TOTAL_COLS):
        day_index = max(0, column * 7 - offset)
        anchor = date.fromisoformat(contribution_days[day_index]["date"])
        weeks.append((anchor.year, anchor.month))
    month_count = len(set(weeks))
    NUM_DAYS = 7
    RX = min(24.0, (1030 - 16 * (month_count - 1)) / (2 * TOTAL_COLS + 4))
    RY = RX * .45
    DX_COL, DY_COL = RX * 2, min(2.0, 36 / TOTAL_COLS)
    DX_ROW, DY_ROW = -RX * .62, RX * .42
    MONTH_GAP = 16.0
    X_START, Y_START = 78 + RX + 6 * abs(DX_ROW), 183.0

    col_coords = {}
    curr_x, curr_y = X_START, Y_START
    month_col_ranges = {}
    for column, month in enumerate(weeks):
        if column and month != weeks[column - 1]:
            curr_x += MONTH_GAP
        col_coords[column] = (curr_x, curr_y)
        curr_x += DX_COL
        curr_y += DY_COL
        if month not in month_col_ranges:
            month_col_ranges[month] = (column, column, month_abbrs[month[1] - 1])
        else:
            start, _, name = month_col_ranges[month]
            month_col_ranges[month] = (start, column, name)
    heights = {}
    cells = {}
    levels = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    for index, day in enumerate(contribution_days):
        cell = divmod(index + offset, 7)
        heights[cell] = levels[day["contributionLevel"]]
        cells[cell] = day

    svg = []
    svg.append('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="390" viewBox="0 0 1200 390" role="img">')
    total = sum(day["contributionCount"] for day in contribution_days)
    svg.append(f'  <title>{escape(cfg["year_in_code"]["label"])}</title>')
    svg.append(f'<desc>{total} GitHub contributions, {first_day} to {last_day}. {_stamp(cfg)}</desc>')
    svg.append(f'  <rect x="17" y="17" width="1160" height="350" rx="16" fill="{THEME["light_border"]}"/>')
    svg.append(f'  <rect x="9" y="9" width="1160" height="350" rx="16" fill="{THEME["iso_bg"]}" stroke="{THEME["light_border"]}" stroke-width="3"/>')
    svg.append(f'  <text x="48" y="67" fill="{THEME["light_text"]}" font-family="Arial, sans-serif" font-size="34" font-weight="800" letter-spacing="1">{escape(cfg["year_in_code"]["label"])}</text>')
    svg.append(f'  <text x="49" y="93" fill="{THEME["light_subtext"]}" font-family="monospace" font-size="12" font-weight="700" letter-spacing="1.8">{escape(cfg["year_in_code"]["sublabel"])} · {len(contribution_days)} DAYS</text>')
    svg.append(f'  <rect x="930" y="42" width="194" height="38" rx="6" fill="{THEME["primary"]}" stroke="{THEME["light_border"]}" stroke-width="2"/>')
    primary_text = THEME.get("primary_text", "#0A0A0A")
    svg.append(f'  <text x="1027" y="66" text-anchor="middle" fill="{primary_text}" font-family="monospace" font-size="12" font-weight="700">{total:,} CONTRIBUTIONS</text>')

    top_cols = {0: THEME["iso_top_0"], 1: THEME["iso_top_1"], 2: THEME["iso_top_2"], 3: THEME["iso_top_3"], 4: THEME["iso_top_4"]}
    DH = 7.5

    # Month Floor Islands
    svg.append('  <g>')
    for start_c, end_c, m_name in month_col_ranges.values():
        sx, sy = col_coords[start_c]
        ex, ey = col_coords[end_c]
        pad = 7.0
        x1, y1 = sx - RX - pad, sy - RY - pad
        x2, y2 = ex + RX + pad, ey - RY - pad
        x3, y3 = ex + 6*DX_ROW + RX + pad, ey + 6*DY_ROW + RY + pad
        x4, y4 = sx + 6*DX_ROW - RX - pad, sy + 6*DY_ROW + RY + pad
        svg.append(f'    <polygon points="{x1:.1f},{y1:.1f} {x2:.1f},{y2:.1f} {x3:.1f},{y3:.1f} {x4:.1f},{y4:.1f}" fill="{THEME["iso_floor_fill"]}" stroke="{THEME["iso_floor_stroke"]}" stroke-width="1.5" opacity="0.8"/>')
    svg.append('  </g>')

    # 3D Grid Tiles
    svg.append('  <g>')
    for sort_key in range(TOTAL_COLS + NUM_DAYS):
        for c in range(TOTAL_COLS):
            r = sort_key - c
            if (c, r) in cells:
                h = heights[(c, r)]
                day = cells[(c, r)]
                svg.append(f'<g data-date="{day["date"]}" data-count="{day["contributionCount"]}"><title>{day["date"]}: {day["contributionCount"]} contributions</title>')
                base_x, base_y = col_coords[c]
                cx = base_x + r * DX_ROW
                cy = base_y + r * DY_ROW
                rx, ry = RX, RY
                top_y = cy - h * DH
                p_top = f"{cx:.1f},{top_y-ry:.1f} {cx+rx:.1f},{top_y:.1f} {cx:.1f},{top_y+ry:.1f} {cx-rx:.1f},{top_y:.1f}"
                if h > 0:
                    p_right = f"{cx:.1f},{top_y+ry:.1f} {cx+rx:.1f},{top_y:.1f} {cx+rx:.1f},{cy:.1f} {cx:.1f},{cy+ry:.1f}"
                    p_left = f"{cx-rx:.1f},{top_y:.1f} {cx:.1f},{top_y+ry:.1f} {cx:.1f},{cy+ry:.1f} {cx-rx:.1f},{cy:.1f}"
                    svg.append(f'    <polygon points="{p_right}" fill="{top_cols[h]}" stroke="{THEME["light_border"]}" stroke-width="0.7"/>')
                    svg.append(f'    <polygon points="{p_left}" fill="{top_cols[h]}" stroke="{THEME["light_border"]}" stroke-width="0.7"/>')
                svg.append(f'    <polygon points="{p_top}" fill="{top_cols[h]}" stroke="{THEME["light_border"]}" stroke-width="0.7"/>')
                svg.append('</g>')
    svg.append('  </g>')

    # Month Labels
    svg.append('  <g>')
    for start_c, end_c, m_name in month_col_ranges.values():
        sx, sy = col_coords[start_c]
        ex, ey = col_coords[end_c]
        mid_x, mid_y = (sx + ex) / 2.0, (sy + ey) / 2.0
        svg.append(f'    <text x="{mid_x:.1f}" y="{mid_y-60:.1f}" text-anchor="middle" fill="{THEME["light_text"]}" font-family="monospace" font-size="13" font-weight="800">{m_name}</text>')
    svg.append('  </g>')

    # Footer Legend
    svg.append(f'  <path d="M48 314 H1124" stroke="{THEME["light_border"]}" stroke-width="2"/>')
    svg.append(f'  <text x="48" y="342" fill="{THEME["light_text"]}" font-family="monospace" font-size="11" font-weight="700">LESS</text>')
    translate_str = "translate(92 331)"
    svg.append(f'  <g transform="{translate_str}">')
    for i in range(5):
        svg.append(f'    <rect x="{i*21}" y="-10" width="14" height="14" fill="{top_cols[i]}" stroke="{THEME["light_border"]}" stroke-width="1"/>')
    svg.append('  </g>')
    svg.append(f'  <text x="193" y="342" fill="{THEME["light_text"]}" font-family="monospace" font-size="11" font-weight="700">MORE</text>')
    svg.append(f'<text x="1124" y="358" text-anchor="end" fill="{THEME["light_subtext"]}" font-family="monospace" font-size="10">{escape(_stamp(cfg))}</text>')
    svg.append('</svg>')
    _save("year-in-code.svg", svg)

def main():
    global METRICS_DIR
    parser = argparse.ArgumentParser(description="Cards com dados reais do GitHub")
    parser.add_argument("--github-cli", action="store_true", help="usa a autenticação já configurada no gh")
    args = parser.parse_args()
    print(f"Fetching GitHub metrics for '{USERNAME}' using theme '{THEME_NAME}'...")
    cfg = dict(config, username=USERNAME)
    try:
        data = collect(cfg, GitHub(TOKEN, use_cli=args.github_cli))
        cfg["_data"] = data
        target = Path(METRICS_DIR)
        target.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="metrics-") as stage:
            METRICS_DIR = stage
            if cfg["cards"]["languages_commits"]:
                generate_languages_commits_svg(data["languages"], cfg)
            if cfg["cards"]["top_repos"]:
                generate_top_repos_svg(data["repos"], cfg)
            if cfg["cards"]["year_in_code"]:
                generate_year_in_code_svg(data["days"], cfg)
            aliases = {"year-in-code.svg": "contribution-activity.svg",
                       "languages-commits.svg": "commit-languages.svg",
                       "languages-recent.svg": "active-repositories.svg"}
            for original, alias in aliases.items():
                source = Path(stage) / original
                if source.exists():
                    (Path(stage) / alias).write_bytes(source.read_bytes())
            (Path(stage) / "metrics.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            for artifact in Path(stage).iterdir():
                (target / artifact.name).write_bytes(artifact.read_bytes())
        METRICS_DIR = str(target)
        print(f"Collected {len(data['repos'])} active repositories; source: {data['source']}.")
        return 0
    except (MetricsError, KeyError, ValueError) as error:
        print(f"Metrics not updated: {error}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
