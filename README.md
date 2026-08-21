# 🎨 GitHub Metrics Cards

Beautiful, dynamic, customizable GitHub profile metrics cards. Pick your palette, set your username, and let GitHub Actions keep your profile updated automatically.

---

## 🎨 3 Initial Themes

### 1. `neobrutalist` (Signature Paper & Voltage Yellow)
A warm, tactile neobrutalist aesthetic with paper tones, bold outlines, and voltage yellow highlights.

### 2. `dark-minimal` (Sleek Dark Mode & Blue Accent)
A clean, modern dark theme built with deep charcoal backgrounds and electric blue accents.

### 3. `cyberpunk` (Neon Hacker & Deep Purple)
A high-contrast cyberpunk theme featuring matrix green, electric cyan, and neon magenta.

---

## 🚀 Quick Start (3 Steps)

### 1. Fork this repository
Click the **Fork** button at the top right of this page to create your own copy.

### 2. Edit `config.yml`
Open `config.yml` and change `username` to your GitHub handle:

```yaml
username: "YOUR_GITHUB_USERNAME"
theme: "neobrutalist" # Options: neobrutalist | dark-minimal | cyberpunk
```

### 3. Enable GitHub Actions
Go to your forked repo's **Actions** tab, enable workflows, and click **Run workflow** on "Update GitHub Metrics Cards".

---

## 🔒 Optional: Private Repositories & Full Stats

By default, the cards render public repositories. To include private repositories:
1. Generate a Personal Access Token (PAT) with `repo` scope under **GitHub Settings ➔ Developer Settings ➔ Personal access tokens**.
2. Add it as a Repository Secret named `METRICS_TOKEN` under **Repo Settings ➔ Secrets and variables ➔ Actions**.

---

## 📄 License
MIT License. Free to use, modify, and distribute!
