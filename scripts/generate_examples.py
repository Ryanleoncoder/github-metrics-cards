#!/usr/bin/env python3
"""
Generate SVG preview examples for all 3 themes in examples/
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import scripts.generate_metrics as gm
from themes.presets import THEMES, get_theme

def main():
    examples_dir = os.path.join(REPO_ROOT, "examples")
    os.makedirs(examples_dir, exist_ok=True)
    
    sample_langs = {"JavaScript": 4500, "Python": 3200, "HTML": 1800, "CSS": 1500, "Shell": 1000}
    sample_repos = [
        {'name': 'Experiencie Connect', 'topics': ['cx-training', 'game-loop'], 'languages': ['JavaScript', 'HTML'], 'commits': 48},
        {'name': 'Quick Setup VPS', 'topics': ['cli', 'security-hardening'], 'languages': ['Shell'], 'commits': 36},
        {'name': 'Organizador De Demandas', 'topics': ['dashboard', 'flask'], 'languages': ['Python', 'HTML'], 'commits': 25}
    ]
    import random
    random.seed(42)
    sample_contribs = [random.choice([0, 0, 1, 2, 4, 7, 0, 3, 5]) for _ in range(140)]

    for theme_name in THEMES.keys():
        print(f"Generating example SVGs for theme '{theme_name}'...")
        theme_dir = os.path.join(examples_dir, theme_name)
        os.makedirs(theme_dir, exist_ok=True)
        
        gm.THEME_NAME = theme_name
        gm.THEME = get_theme(theme_name)
        gm.METRICS_DIR = theme_dir
        
        gm.generate_languages_commits_svg(sample_langs, gm.config)
        gm.generate_top_repos_svg(sample_repos, gm.config)
        gm.generate_year_in_code_svg(sample_contribs, gm.config)
        
    print("All theme examples generated successfully in examples/")

if __name__ == "__main__":
    main()
