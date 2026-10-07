"""Busca as métricas pela API, sem transformar erro em estatística de exemplo."""
import json
import os
import subprocess
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

REPOSITORIES = """
query($login:String!, $cursor:String, $privacy:RepositoryPrivacy) {
  user(login:$login) {
    repositories(first:100, after:$cursor, ownerAffiliations:[OWNER], privacy:$privacy, isFork:false) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name nameWithOwner isPrivate isFork url
        primaryLanguage { name }
        repositoryTopics(first:3) { nodes { topic { name } } }
        languages(first:100, orderBy:{field:SIZE, direction:DESC}) {
          pageInfo { hasNextPage }
          edges { size node { name } }
        }
      }
    }
  }
}
"""
CONTRIBUTIONS = """
query($login:String!, $from:DateTime!, $recentFrom:DateTime!, $to:DateTime!) {
  user(login:$login) {
    calendar:contributionsCollection(from:$from, to:$to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
    recent:contributionsCollection(from:$recentFrom, to:$to) {
      totalRepositoriesWithContributedCommits
      commitContributionsByRepository(maxRepositories:100) {
        repository { nameWithOwner isPrivate }
        contributions { totalCount }
      }
    }
  }
}
"""


class MetricsError(RuntimeError):
    pass


class GitHub:
    def __init__(self, token="", use_cli=False):
        self.token = token
        self.use_cli = use_cli

    def query(self, query, variables):
        payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        if self.use_cli:
            result = subprocess.run(["gh", "api", "graphql", "--input", "-"], input=payload,
                                    capture_output=True, timeout=60)
            if result.returncode:
                raise MetricsError("A consulta pelo GitHub CLI falhou; confira a autenticação e as permissões.")
            raw = result.stdout
        else:
            if not self.token:
                raise MetricsError("Defina GITHUB_TOKEN/METRICS_TOKEN ou use --github-cli com gh já autenticado.")
            request = urllib.request.Request("https://api.github.com/graphql", data=payload, headers={
                "Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                "Content-Type": "application/json", "User-Agent": "github-metrics-cards",
            })
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    raw = response.read()
            except urllib.error.HTTPError as error:
                raise MetricsError(f"GitHub respondeu HTTP {error.code}; os cards anteriores não serão substituídos.") from error
            except (OSError, TimeoutError) as error:
                raise MetricsError("Não foi possível consultar o GitHub; os cards anteriores serão mantidos.") from error
        try:
            data = json.loads(raw)
        except (UnicodeError, ValueError) as error:
            raise MetricsError("O GitHub devolveu uma resposta inválida.") from error
        if data.get("errors") or not data.get("data", {}).get("user"):
            raise MetricsError("A consulta GraphQL não foi concluída; confira usuário e acesso do token.")
        return data["data"]["user"]


def period(config, now):
    year = config["year_in_code"]
    end = now.date()
    if "days" in year:
        start = end - timedelta(days=year["days"] - 1)
    else:
        month_index = end.year * 12 + end.month - year["months"]
        start = end.replace(year=month_index // 12, month=month_index % 12 + 1, day=1)
    if (end - start).days >= 366:
        raise MetricsError("O calendário precisa caber em um ano de contribuições.")
    return start, end


def collect(config, github, now=None):
    now = now or datetime.now(timezone.utc)
    start, end = period(config, now)
    recent_start = end - timedelta(days=config["top_repos"]["days"] - 1)
    stamp = lambda day: day.isoformat() + "T00:00:00Z"
    contribution = github.query(CONTRIBUTIONS, {
        "login": config["username"], "from": stamp(start), "recentFrom": stamp(recent_start),
        "to": now.isoformat().replace("+00:00", "Z"),
    })
    recent = contribution["recent"]
    if recent["totalRepositoriesWithContributedCommits"] > 100:
        raise MetricsError("A API limita o ranking a 100 repositórios; reduza top_repos.days.")
    excluded = {name.casefold() for name in config["top_repos"]["exclude"]}
    excluded.add(config["username"].casefold())
    counts = {item["repository"]["nameWithOwner"]: item["contributions"]["totalCount"]
              for item in recent["commitContributionsByRepository"]
              if config["include_private"] or not item["repository"]["isPrivate"]}
    repos, sizes = [], defaultdict(int)
    cursor, seen = None, set()
    while True:
        page = github.query(REPOSITORIES, {
            "login": config["username"], "cursor": cursor,
            "privacy": None if config["include_private"] else "PUBLIC",
        })["repositories"]
        for repo in page["nodes"]:
            if repo["isFork"] or (repo["isPrivate"] and not config["include_private"]):
                continue
            if repo["name"].casefold() in excluded or repo["nameWithOwner"].casefold() in excluded:
                continue
            if repo["languages"]["pageInfo"]["hasNextPage"]:
                raise MetricsError("Um repositório tem mais de 100 linguagens; a coleta não será publicada incompleta.")
            for language in repo["languages"]["edges"]:
                sizes[language["node"]["name"]] += language["size"]
            commits = counts.get(repo["nameWithOwner"], 0)
            if commits:
                repos.append({"name": repo["name"], "url": repo["url"], "commits": commits,
                              "topics": [item["topic"]["name"] for item in repo["repositoryTopics"]["nodes"]],
                              "languages": [repo["primaryLanguage"]["name"]] if repo["primaryLanguage"] else []})
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
        if not cursor or cursor in seen:
            raise MetricsError("A paginação não avançou; a coleta foi interrompida.")
        seen.add(cursor)
    repos.sort(key=lambda item: (-item["commits"], item["name"].casefold()))
    weights = defaultdict(int)
    for repo in repos:
        weights[repo["languages"][0] if repo["languages"] else "Unknown"] += repo["commits"]
    daily = {item["date"]: item for week in contribution["calendar"]["contributionCalendar"]["weeks"]
             for item in week["contributionDays"] if start.isoformat() <= item["date"] <= end.isoformat()}
    days = [daily.get((start + timedelta(days=index)).isoformat()) for index in range((end - start).days + 1)]
    if any(day is None for day in days):
        raise MetricsError("O calendário recebido está incompleto; não será preenchido com números inventados.")
    return {"username": config["username"], "generated_at": now.isoformat().replace("+00:00", "Z"),
            "start": start.isoformat(), "end": end.isoformat(), "recent_start": recent_start.isoformat(),
            "include_private": config["include_private"], "repos": repos,
            "languages": dict(weights if config["languages"]["metric"] == "recent_commits" else sizes),
            "days": days, "source": "GitHub GraphQL API"}
