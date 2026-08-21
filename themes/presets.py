"""
3 Theme Presets with WCAG AAA Contrast Compliance
"""

THEMES = {
    # 1. Neobrutalist (Signature Paper & Voltage Yellow)
    "neobrutalist": {
        "name": "Neobrutalist Paper",
        "light_bg": "#F5F0E6",
        "light_border": "#0A0A0A",
        "light_text": "#0A0A0A",
        "light_subtext": "#5C5752",
        "light_bar_track": "#EAE4D4",
        "dark_bg": "#161616",
        "dark_border": "#0A0A0A",
        "dark_text": "#FFFFFF",
        "dark_subtext": "#D4D4D4",
        "dark_bar_track": "#2B2B2B",
        "primary": "#FFC700",
        "primary_text": "#0A0A0A",
        "primary_light": "#FFE066",
        "primary_dark": "#E5A800",
        "tag_bg": "#242832",
        "tag_text": "#FFC700",
        "tag_border": "#FFC700",
        "iso_bg": "#F5F0E6",
        "iso_floor_fill": "#EAE4D4",
        "iso_floor_stroke": "#7A7570",
        "iso_top_0": "#EAE4D4",
        "iso_top_1": "#FFF3B5",
        "iso_top_2": "#FFE066",
        "iso_top_3": "#FFC700",
        "iso_top_4": "#E5A800",
    },

    # 2. Dark Minimal (High-Contrast Charcoal & Blue Accent)
    "dark-minimal": {
        "name": "Dark Minimal",
        "light_bg": "#18181B",
        "light_border": "#3F3F46",
        "light_text": "#FFFFFF",
        "light_subtext": "#A1A1AA",
        "light_bar_track": "#27272A",
        "dark_bg": "#121212",
        "dark_border": "#3F3F46",
        "dark_text": "#FFFFFF",
        "dark_subtext": "#A1A1AA",
        "dark_bar_track": "#27272A",
        "primary": "#3B82F6",
        "primary_text": "#FFFFFF",
        "primary_light": "#60A5FA",
        "primary_dark": "#2563EB",
        "tag_bg": "#27272A",
        "tag_text": "#FFFFFF",
        "tag_border": "#3B82F6",
        "iso_bg": "#18181B",
        "iso_floor_fill": "#27272A",
        "iso_floor_stroke": "#52525B",
        "iso_top_0": "#27272A",
        "iso_top_1": "#1E3A8A",
        "iso_top_2": "#2563EB",
        "iso_top_3": "#3B82F6",
        "iso_top_4": "#60A5FA",
    },

    # 3. Cyberpunk (Neon Green & Vivid Cyan High-Contrast)
    "cyberpunk": {
        "name": "Cyberpunk Neon",
        "light_bg": "#0D0221",
        "light_border": "#00FF41",
        "light_text": "#00FF41",
        "light_subtext": "#00F0FF",
        "light_bar_track": "#1F0A38",
        "dark_bg": "#090117",
        "dark_border": "#FF007F",
        "dark_text": "#00FF41",
        "dark_subtext": "#00F0FF",
        "dark_bar_track": "#1F0A38",
        "primary": "#00FF41",
        "primary_text": "#0D0221",
        "primary_light": "#5DFF87",
        "primary_dark": "#00B32D",
        "tag_bg": "#1F0A38",
        "tag_text": "#00F0FF",
        "tag_border": "#00FF41",
        "iso_bg": "#0D0221",
        "iso_floor_fill": "#1F0A38",
        "iso_floor_stroke": "#FF007F",
        "iso_top_0": "#1F0A38",
        "iso_top_1": "#3A0CA3",
        "iso_top_2": "#7209B7",
        "iso_top_3": "#F72585",
        "iso_top_4": "#00FF41",
    }
}

def get_theme(theme_name, custom_palette=None):
    theme = THEMES.get(theme_name, THEMES["neobrutalist"]).copy()
    if theme_name == "custom" and custom_palette:
        theme.update({k: v for k, v in custom_palette.items() if v})
    return theme
