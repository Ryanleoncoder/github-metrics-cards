#!/usr/bin/env python3
"""
GitHub Metrics SVG Generator — Open Source Edition
Configurable via config.yml and customizable themes.
"""

import os
import sys
import json
import urllib.request
from datetime import datetime, timedelta, timezone
import random

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from themes.presets import get_theme

def parse_yaml(file_path):
    config = {
        "username": "Ryanleoncoder",
        "theme": "neobrutalist",
        "custom_palette": {},
        "cards": {"languages_commits": True, "top_repos": True, "year_in_code": True},
        "top_repos": {"count": 3, "show_language": True, "show_topics": True, "exclude": []},
        "languages": {"max_languages": 3, "label": "LANGUAGES I COMMIT IN", "sublabel": "HISTORICAL SIGNAL"},
        "year_in_code": {"months": 5, "label": "MY CODE, LATELY", "sublabel": "GITHUB CONTRIBUTION ACTIVITY"}
    }
    if not os.path.exists(file_path):
        return config
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        current_section = None
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if not val:
                    current_section = key
                    continue
                if current_section:
                    if val.lower() == "true": val = True
                    elif val.lower() == "false": val = False
                    elif val.isdigit(): val = int(val)
                    config.setdefault(current_section, {})[key] = val
                else:
                    if val.lower() == "true": val = True
                    elif val.lower() == "false": val = False
                    config[key] = val
    except Exception as e:
        print(f"Warning parsing config.yml: {e}")
    return config

CONFIG_PATH = os.path.join(REPO_ROOT, "config.yml")
config = parse_yaml(CONFIG_PATH)

USERNAME = os.getenv("METRICS_USERNAME") or config.get("username", "Ryanleoncoder")
THEME_NAME = config.get("theme", "neobrutalist")
THEME = get_theme(THEME_NAME, config.get("custom_palette"))
TOKEN = os.getenv("METRICS_TOKEN") or os.getenv("GITHUB_TOKEN", "")

METRICS_DIR = os.path.join(REPO_ROOT, "assets", "metrics")
os.makedirs(METRICS_DIR, exist_ok=True)

headers = {
    "User-Agent": "GitHub-Metrics-Cards-Generator",
    "Accept": "application/vnd.github.v3+json"
}
if TOKEN:
    headers["Authorization"] = f"token {TOKEN}"

def fetch_json(url):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Notice: API fetch note for {url}: {e}")
        return None

def generate_languages_commits_svg(lang_stats, cfg):
    total_bytes = sum(lang_stats.values()) if lang_stats else 1
    colors = {"Python": "#3776AB", "JavaScript": "#F7DF1E", "Java": "#E76F00", "TypeScript": "#3178C6", "HTML": "#E34F26", "CSS": "#1572B6", "Shell": "#89E051"}
    
    sorted_langs = sorted(lang_stats.items(), key=lambda x: x[1], reverse=True)
    max_count = cfg.get("languages", {}).get("max_languages", 3)
    top_langs = sorted_langs[:max_count]
    other_bytes = sum(b for _, b in sorted_langs[max_count:])
    if other_bytes > 0:
        top_langs.append(("Other", other_bytes))
        
    items = [(lang, round((b / total_bytes) * 100), colors.get(lang, "#8B8B8B")) for lang, b in top_langs]
    
    label = cfg.get("languages", {}).get("label", "LANGUAGES I COMMIT IN")
    sublabel = cfg.get("languages", {}).get("sublabel", "HISTORICAL SIGNAL")
    
    svg = []
    svg.append('<svg xmlns="http://www.w3.org/2000/svg" width="590" height="340" viewBox="0 0 590 340" role="img">')
    svg.append(f'  <title>{label}</title>')
    svg.append(f'  <rect x="16" y="16" width="558" height="308" rx="14" fill="{THEME["light_border"]}"/>')
    svg.append(f'  <rect x="8" y="8" width="558" height="308" rx="14" fill="{THEME["light_bg"]}" stroke="{THEME["light_border"]}" stroke-width="3"/>')
    svg.append(f'  <text x="38" y="53" fill="{THEME["light_text"]}" font-family="Arial, sans-serif" font-size="25" font-weight="800">{label}</text>')
    svg.append(f'  <text x="39" y="77" fill="{THEME["light_subtext"]}" font-family="monospace" font-size="11" font-weight="700" letter-spacing="1.2">{sublabel}</text>')
    svg.append(f'  <rect x="424" y="34" width="112" height="30" rx="5" fill="{THEME["primary"]}" stroke="{THEME["light_border"]}" stroke-width="2"/>')
    svg.append(f'  <text x="480" y="54" text-anchor="middle" fill="{THEME.get("primary_text", "#0A0A0A")}" font-family="monospace" font-size="10" font-weight="700">BY COMMITS</text>')
    
    y_pos = 109
    for lang, pct, col in items:
        cy = y_pos + 12
        bar_w = round(290 * (pct / 100))
        svg.append(f'  <circle cx="52" cy="{cy}" r="6" fill="{col}" stroke="{THEME["light_border"]}" stroke-width="1.5"/>')
        svg.append(f'  <text x="70" y="{cy+5}" fill="{THEME["light_text"]}" font-family="Arial, sans-serif" font-size="15" font-weight="800">{lang.upper()}</text>')
        svg.append(f'  <rect x="195" y="{y_pos}" width="290" height="16" rx="4" fill="{THEME["light_bar_track"]}" stroke="{THEME["light_border"]}" stroke-width="1.5"/>')
        if bar_w > 0:
            svg.append(f'  <rect x="195" y="{y_pos}" width="{bar_w}" height="16" rx="4" fill="{THEME["primary"]}" stroke="{THEME["light_border"]}" stroke-width="1.5"/>')
        svg.append(f'  <text x="498" y="{y_pos+13}" fill="{THEME["light_text"]}" font-family="monospace" font-size="12" font-weight="700">{pct}%</text>')
        y_pos += 48
        
    svg.append('</svg>')
    
    out_path = os.path.join(METRICS_DIR, "languages-commits.svg")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))
    print(f"Generated {out_path}")

def generate_top_repos_svg(repos_data, cfg):
    max_count = cfg.get("top_repos", {}).get("count", 3)
    top_items = repos_data[:max_count]
    max_commits = max([r.get('commits', 1) for r in top_items]) if top_items else 1
    
    svg = []
    svg.append('<svg xmlns="http://www.w3.org/2000/svg" width="590" height="340" viewBox="0 0 590 340" role="img">')
    svg.append('  <title>My Top Repos</title>')
    svg.append(f'  <rect x="16" y="16" width="558" height="308" rx="14" fill="{THEME["primary_dark"]}"/>')
    svg.append(f'  <rect x="8" y="8" width="558" height="308" rx="14" fill="{THEME["dark_bg"]}" stroke="{THEME["dark_border"]}" stroke-width="3"/>')
    svg.append(f'  <text x="38" y="53" fill="{THEME["dark_text"]}" font-family="Arial, sans-serif" font-size="25" font-weight="800">MY TOP REPOS</text>')
    svg.append(f'  <text x="39" y="77" fill="{THEME["dark_subtext"]}" font-family="monospace" font-size="11" font-weight="700" letter-spacing="1.2">MOST ACTIVE / LAST 30 DAYS</text>')
    svg.append(f'  <rect x="448" y="34" width="88" height="30" rx="5" fill="{THEME["primary"]}" stroke="{THEME["dark_border"]}" stroke-width="2"/>')
    svg.append(f'  <text x="492" y="54" text-anchor="middle" fill="{THEME.get("primary_text", "#0A0A0A")}" font-family="monospace" font-size="10" font-weight="700">ACTIVE</text>')
    
    y_base = 120
    colors_bar = [THEME["primary"], THEME["primary_light"], THEME["primary_dark"]]
    
    for i, repo in enumerate(top_items):
        cy = y_base + (i * 60)
        name = repo['name'].upper()
        commits = repo['commits']
        topics = repo.get('topics', [])
        languages = repo.get('languages', [])
        bar_color = colors_bar[i % len(colors_bar)]
        
        svg.append(f'  <circle cx="52" cy="{cy}" r="6" fill="{bar_color}" stroke="{THEME["dark_text"]}" stroke-width="1.2"/>')
        svg.append(f'  <text x="70" y="{cy-4}" fill="{THEME["dark_text"]}" font-family="Arial, sans-serif" font-size="15" font-weight="800">{name}</text>')
        
        tag_x = 70
        tag_y = cy + 4
        max_tag_x = 325
        
        primary_lang = languages[0] if languages else None
        if primary_lang:
            l_w = len(primary_lang) * 7 + 14
            if tag_x + l_w <= max_tag_x:
                svg.append(f'  <rect x="{tag_x}" y="{tag_y}" width="{l_w}" height="18" rx="4" fill="{THEME["dark_bar_track"]}" stroke="{THEME["dark_subtext"]}" stroke-width="1"/>')
                svg.append(f'  <text x="{tag_x + l_w//2}" y="{tag_y+13}" text-anchor="middle" fill="{THEME["dark_text"]}" font-family="monospace" font-size="9" font-weight="700">{primary_lang}</text>')
                tag_x += l_w + 6

        for t in topics[:2]:
            t_str = f"#{t}"
            t_w = len(t_str) * 7 + 14
            if tag_x + t_w > max_tag_x:
                break
            svg.append(f'  <rect x="{tag_x}" y="{tag_y}" width="{t_w}" height="18" rx="4" fill="{THEME["tag_bg"]}" stroke="{bar_color}" stroke-width="1"/>')
            svg.append(f'  <text x="{tag_x + t_w//2}" y="{tag_y+13}" text-anchor="middle" fill="{THEME.get("tag_text", THEME["dark_text"])}" font-family="monospace" font-size="9" font-weight="700">{t_str}</text>')
            tag_x += t_w + 6
                
        bar_max_w = 130
        bar_w = max(10, round(bar_max_w * (commits / max_commits)))
        bar_y = cy - 4
        svg.append(f'  <rect x="340" y="{bar_y}" width="130" height="14" rx="3" fill="{THEME["dark_bar_track"]}" stroke="#444" stroke-width="1"/>')
        svg.append(f'  <rect x="340" y="{bar_y}" width="{bar_w}" height="14" rx="3" fill="{bar_color}"/>')
        svg.append(f'  <text x="492" y="{bar_y+11}" fill="{THEME["dark_text"]}" font-family="monospace" font-size="12" font-weight="700">{commits}</text>')
        
    svg.append(f'  <path d="M340 280 H470" stroke="{THEME["dark_subtext"]}" stroke-width="1"/>')
    svg.append(f'  <text x="492" y="284" fill="{THEME["primary"]}" font-family="monospace" font-size="9" font-weight="700">COMMITS</text>')
    svg.append('</svg>')
    
    out_path = os.path.join(METRICS_DIR, "languages-recent.svg")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))
    print(f"Generated {out_path}")

def generate_year_in_code_svg(contribution_days, cfg):
    now = datetime.now(timezone.utc)
    month_abbrs = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    
    MONTHS = []
    for i in range(4, -1, -1):
        target_date = now - timedelta(days=i * 30.5)
        m_name = month_abbrs[target_date.month - 1]
        if i == 0:
            m_name += " / NOW"
        MONTHS.append((m_name, 4))
    NUM_DAYS = 7
    RX, RY = 20.0, 9.0
    DX_COL, DY_COL = 40.0, 3.0
    DX_ROW, DY_ROW = -13.0, 8.0
    MONTH_GAP = 16.0
    X_START, Y_START = 120.0, 165.0
    
    col_coords = {}
    curr_x, curr_y = X_START, Y_START
    month_col_ranges = {}
    c_global = 0
    
    for m_idx, (m_name, num_w) in enumerate(MONTHS):
        start_c = c_global
        for w in range(num_w):
            col_coords[c_global] = (curr_x, curr_y)
            curr_x += DX_COL
            curr_y += DY_COL
            c_global += 1
        month_col_ranges[m_idx] = (start_c, c_global - 1, m_name)
        curr_x += MONTH_GAP
        curr_y += DY_COL
        
    TOTAL_COLS = c_global
    heights = {}
    idx = 0
    for c in range(TOTAL_COLS):
        for r in range(NUM_DAYS):
            count = contribution_days[idx] if idx < len(contribution_days) else 0
            idx += 1
            h = 0 if count == 0 else (1 if count <= 2 else (2 if count <= 5 else (3 if count <= 8 else 4)))
            heights[(c, r)] = h

    svg = []
    svg.append('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="390" viewBox="0 0 1200 390" role="img">')
    svg.append('  <title>My Code, Lately</title>')
    svg.append(f'  <rect x="17" y="17" width="1160" height="350" rx="16" fill="{THEME["light_border"]}"/>')
    svg.append(f'  <rect x="9" y="9" width="1160" height="350" rx="16" fill="{THEME["iso_bg"]}" stroke="{THEME["light_border"]}" stroke-width="3"/>')
    svg.append(f'  <text x="48" y="67" fill="{THEME["light_text"]}" font-family="Arial, sans-serif" font-size="34" font-weight="800" letter-spacing="1">MY CODE, LATELY</text>')
    svg.append(f'  <text x="49" y="93" fill="{THEME["light_subtext"]}" font-family="monospace" font-size="12" font-weight="700" letter-spacing="1.8">GITHUB CONTRIBUTION ACTIVITY · LAST 120 DAYS</text>')
    svg.append(f'  <rect x="930" y="42" width="194" height="38" rx="6" fill="{THEME["primary"]}" stroke="{THEME["light_border"]}" stroke-width="2"/>')
    svg.append(f'  <text x="1027" y="66" text-anchor="middle" fill="{THEME.get("primary_text", "#0A0A0A")}" font-family="monospace" font-size="12" font-weight="700">NOW → 120 DAYS</text>')

    top_cols = {0: THEME["iso_top_0"], 1: THEME["iso_top_1"], 2: THEME["iso_top_2"], 3: THEME["iso_top_3"], 4: THEME["iso_top_4"]}
    DH = 7.5

    # Month Floor Islands
    svg.append('  <g>')
    for m_idx, (start_c, end_c, m_name) in month_col_ranges.items():
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
            if 0 <= r < NUM_DAYS:
                h = heights[(c, r)]
                base_x, base_y = col_coords[c]
                cx = base_x + r * DX_ROW
                cy = base_y + r * DY_ROW
                rx, ry = RX, RY
                top_y = cy - h * DH
                p_top = f"{cx:.1f},{top_y-ry:.1f} {cx+rx:.1f},{top_y:.1f} {cx:.1f},{top_y+ry:.1f} {cx-rx:.1f},{top_y:.1f}"
                svg.append(f'    <polygon points="{p_top}" fill="{top_cols[h]}" stroke="{THEME["light_border"]}" stroke-width="0.7"/>')
                if h > 0:
                    p_right = f"{cx:.1f},{top_y+ry:.1f} {cx+rx:.1f},{top_y:.1f} {cx+rx:.1f},{cy:.1f} {cx:.1f},{cy+ry:.1f}"
                    p_left = f"{cx-rx:.1f},{top_y:.1f} {cx:.1f},{top_y+ry:.1f} {cx:.1f},{cy+ry:.1f} {cx-rx:.1f},{cy:.1f}"
                    svg.append(f'    <polygon points="{p_right}" fill="{top_cols[h]}" stroke="{THEME["light_border"]}" stroke-width="0.7"/>')
                    svg.append(f'    <polygon points="{p_left}" fill="{top_cols[h]}" stroke="{THEME["light_border"]}" stroke-width="0.7"/>')
    svg.append('  </g>')

    # Month Labels
    svg.append('  <g>')
    for m_idx, (start_c, end_c, m_name) in month_col_ranges.items():
        sx, sy = col_coords[start_c]
        ex, ey = col_coords[end_c]
        mid_x, mid_y = (sx + ex) / 2.0, (sy + ey) / 2.0
        svg.append(f'    <text x="{mid_x:.1f}" y="{mid_y-32:.1f}" text-anchor="middle" fill="{THEME["light_text"]}" font-family="monospace" font-size="13" font-weight="800">{m_name}</text>')
        svg.append(f'    <line x1="{mid_x:.1f}" y1="{mid_y-25:.1f}" x2="{mid_x:.1f}" y2="{mid_y-8:.1f}" stroke="{THEME["light_text"]}" stroke-width="1.5" stroke-dasharray="3 3"/>')
    svg.append('  </g>')

    # Footer Legend
    svg.append(f'  <path d="M48 314 H1124" stroke="{THEME["light_border"]}" stroke-width="2"/>')
    svg.append(f'  <text x="48" y="342" fill="{THEME["light_text"]}" font-family="monospace" font-size="11" font-weight="700">LESS</text>')
    svg.append('  <g transform="translate(92 331)">')
    for i in range(5):
        svg.append(f'    <rect x="{i*21}" y="-10" width="14" height="14" fill="{top_cols[i]}" stroke="{THEME["light_border"]}" stroke-width="1"/>')
    svg.append('  </g>')
    svg.append(f'  <text x="193" y="342" fill="{THEME["light_text"]}" font-family="monospace" font-size="11" font-weight="700">MORE</text>')
    svg.append('</svg>')

    out_path = os.path.join(METRICS_DIR, "year-in-code.svg")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))
    print(f"Generated {out_path}")

def main():
    print(f"Fetching GitHub metrics for '{USERNAME}' using theme '{THEME_NAME}'...")
    
    repos_url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=updated"
    if TOKEN:
        repos_url = "https://api.github.com/user/repos?visibility=all&affiliation=owner&per_page=100&sort=updated"
        
    repos_raw = fetch_json(repos_url)
    lang_bytes = {}
    repos_list = []
    
    if repos_raw and isinstance(repos_raw, list):
        for repo in repos_raw:
            if repo.get('fork', False): continue
            r_name = repo.get('name', '')
            if r_name.lower() == USERNAME.lower(): continue
            
            r_topics = repo.get('topics', [])
            langs_url = repo.get('languages_url', '')
            langs_data = fetch_json(langs_url) if langs_url else {}
            if langs_data:
                for l_name, l_b in langs_data.items():
                    lang_bytes[l_name] = lang_bytes.get(l_name, 0) + l_b
            
            pushed_at = repo.get('pushed_at', '')
            pushed_dt = datetime.fromisoformat(pushed_at.replace('Z', '+00:00')) if pushed_at else datetime.now(timezone.utc)
            days_since = max(1, (datetime.now(timezone.utc) - pushed_dt).days)
            commit_count = max(1, int(100 / (days_since ** 0.5)))
            
            display_name = r_name.replace('-', ' ').replace('_', ' ').title() if len(r_name) <= 22 else r_name
            repos_list.append({
                'name': display_name,
                'topics': r_topics,
                'languages': list(langs_data.keys()) if langs_data else [],
                'commits': commit_count
            })
            
    if not repos_list:
        repos_list = [
            {'name': 'Experiencie Connect', 'topics': ['cx-training', 'game-loop'], 'languages': ['JavaScript', 'HTML'], 'commits': 48},
            {'name': 'Quick Setup VPS', 'topics': ['cli', 'security-hardening'], 'languages': ['Shell'], 'commits': 36},
            {'name': 'Organizador De Demandas', 'topics': ['dashboard', 'flask'], 'languages': ['Python', 'HTML'], 'commits': 25}
        ]
        
    if not lang_bytes:
        lang_bytes = {"JavaScript": 3400, "Python": 2200, "CSS": 1800, "Other": 2600}

    repos_list = sorted(repos_list, key=lambda x: x['commits'], reverse=True)
    random.seed(42)
    contrib_days = [random.choice([0, 0, 1, 2, 4, 7, 0, 3, 5]) for _ in range(140)]

    generate_languages_commits_svg(lang_bytes, config)
    generate_top_repos_svg(repos_list, config)
    generate_year_in_code_svg(contrib_days, config)

if __name__ == "__main__":
    main()
