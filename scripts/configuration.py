"""Configuração limitada aos tipos usados pelos cards, sem dependência externa."""
import copy
import re
import shlex
from pathlib import Path

DEFAULTS = {
    "username": "Ryanleoncoder", "theme": "neobrutalist", "custom_palette": {},
    "include_private": False,
    "cards": {"languages_commits": True, "top_repos": True, "year_in_code": True},
    "top_repos": {"count": 6, "days": 30, "show_language": True, "show_topics": True, "exclude": []},
    "languages": {"max_languages": 5, "metric": "recent_commits",
                  "label": "LANGUAGES I COMMIT IN", "sublabel": ""},
    "year_in_code": {"days": 120, "label": "MY CODE, LATELY", "sublabel": "GITHUB CONTRIBUTION ACTIVITY"},
}


def _scalar(value):
    value = value.strip()
    if value[:1] in ("'", '"'):
        if value[-1:] != value[:1]:
            raise ValueError("aspas incompletas na configuração")
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        lexer = shlex.shlex(value[1:-1], posix=True)
        lexer.whitespace = ","
        lexer.whitespace_split = True
        lexer.commenters = ""
        return [item.strip() for item in lexer if item.strip()]
    if value in ("true", "false"):
        return value == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _without_comment(line):
    quote = ""
    for index, char in enumerate(line):
        if char in "\"'" and (index == 0 or line[index - 1] != "\\"):
            quote = "" if quote == char else char if not quote else quote
        elif char == "#" and not quote:
            return line[:index]
    return line


def parse_yaml(path):
    raw = {}
    if Path(path).exists():
        lines = [_without_comment(line).rstrip() for line in Path(path).read_text(encoding="utf-8").splitlines()]
        lines = [line for line in lines if line.strip()]
        stack = [(-1, raw)]
        for index, line in enumerate(lines):
            if "\t" in line:
                raise ValueError("use espaços, não tabulações, na configuração")
            indent = len(line) - len(line.lstrip())
            while stack[-1][0] >= indent:
                stack.pop()
            parent = stack[-1][1]
            text = line.strip()
            if text.startswith("- "):
                if not isinstance(parent, list):
                    raise ValueError("lista fora de uma seção")
                parent.append(_scalar(text[2:]))
                continue
            key, separator, value = text.partition(":")
            if not separator or not isinstance(parent, dict) or not re.fullmatch(r"[a-z_]+", key):
                raise ValueError(f"linha inválida na configuração: {text}")
            if key in parent:
                raise ValueError(f"chave repetida na configuração: {key}")
            if value.strip():
                parent[key] = _scalar(value)
            else:
                next_is_list = index + 1 < len(lines) and lines[index + 1].lstrip().startswith("- ")
                parent[key] = [] if next_is_list else {}
                stack.append((indent, parent[key]))
    result = copy.deepcopy(DEFAULTS)
    for key, value in raw.items():
        if key not in result:
            raise ValueError(f"opção desconhecida: {key}")
        if isinstance(result[key], dict):
            if not isinstance(value, dict):
                raise ValueError(f"{key} precisa ser uma seção")
            result[key].update(value)
        else:
            result[key] = value
    if "months" in raw.get("year_in_code", {}) and "days" not in raw["year_in_code"]:
        result["year_in_code"].pop("days")
    validate(result)
    return result


def validate(config):
    from themes.presets import THEMES

    username = config["username"]
    if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", username):
        raise ValueError("username precisa ser um nome de usuário do GitHub")
    if config["theme"] not in {*THEMES, "custom"}:
        raise ValueError("tema desconhecido")
    if not isinstance(config["include_private"], bool):
        raise ValueError("include_private precisa ser true ou false")
    for name in DEFAULTS["cards"]:
        if not isinstance(config["cards"].get(name), bool):
            raise ValueError(f"cards.{name} precisa ser true ou false")
    for section, name, low, high in [("top_repos", "count", 1, 10), ("top_repos", "days", 1, 365),
                                     ("languages", "max_languages", 1, 10)]:
        value = config[section].get(name)
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"{section}.{name} precisa estar entre {low} e {high}")
    for name in ("show_language", "show_topics"):
        if not isinstance(config["top_repos"][name], bool):
            raise ValueError(f"top_repos.{name} precisa ser true ou false")
    excluded = config["top_repos"]["exclude"]
    if not isinstance(excluded, list) or any(not isinstance(name, str) or not name for name in excluded):
        raise ValueError("top_repos.exclude precisa ser uma lista de nomes")
    if config["languages"]["metric"] not in ("recent_commits", "code_size"):
        raise ValueError("languages.metric precisa ser recent_commits ou code_size")
    for section in ("languages", "year_in_code"):
        for name in ("label", "sublabel"):
            if not isinstance(config[section].get(name), str):
                raise ValueError(f"{section}.{name} precisa ser texto")
    year = config["year_in_code"]
    if "days" in year:
        if type(year["days"]) is not int or not 1 <= year["days"] <= 365:
            raise ValueError("year_in_code.days precisa estar entre 1 e 365")
    elif type(year.get("months")) is not int or not 1 <= year["months"] <= 12:
        raise ValueError("year_in_code.months precisa estar entre 1 e 12")
    for name, value in config["custom_palette"].items():
        if name not in THEMES["neobrutalist"] or name == "name" or not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ValueError(f"cor inválida: custom_palette.{name}")
