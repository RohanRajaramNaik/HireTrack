"""Skill normalisation.

Recruiters and candidates write the same skill many ways ("JS", "javascript",
"Java Script "). Everything is reduced to one canonical, lowercase form before
it is stored or compared, so "JS" on a CV matches "JavaScript" on a job.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

# alias -> canonical. Keys and values must already be lowercase/space-collapsed.
ALIASES: dict[str, str] = {
    # Languages
    "js": "javascript",
    "java script": "javascript",
    "ecmascript": "javascript",
    "es6": "javascript",
    "ts": "typescript",
    "py": "python",
    "python3": "python",
    "python 3": "python",
    "golang": "go",
    "csharp": "c#",
    "c sharp": "c#",
    "cpp": "c++",
    "dotnet": ".net",
    "dot net": ".net",
    ".net core": ".net",
    "asp.net core": "asp.net",
    "vb": "visual basic",
    "vba": "excel vba",
    # Frameworks / runtimes
    "node": "node.js",
    "nodejs": "node.js",
    "node js": "node.js",
    "reactjs": "react",
    "react.js": "react",
    "react js": "react",
    "vuejs": "vue",
    "vue.js": "vue",
    "angularjs": "angular",
    "nextjs": "next.js",
    "next js": "next.js",
    "expressjs": "express",
    "express.js": "express",
    "springboot": "spring boot",
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    # Data
    "postgres": "postgresql",
    "psql": "postgresql",
    "postgre sql": "postgresql",
    "mssql": "sql server",
    "ms sql": "sql server",
    "microsoft sql server": "sql server",
    "t-sql": "tsql",
    "mongo": "mongodb",
    "elastic": "elasticsearch",
    "apache spark": "spark",
    "pyspark": "spark",
    "apache kafka": "kafka",
    "apache airflow": "airflow",
    "dbt core": "dbt",
    "ms excel": "excel",
    "microsoft excel": "excel",
    "powerbi": "power bi",
    "pbi": "power bi",
    "ms power bi": "power bi",
    "etl/elt": "etl",
    "data warehouse": "data warehousing",
    "dwh": "data warehousing",
    # AI / ML
    "ml": "machine learning",
    "dl": "deep learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "genai": "generative ai",
    "llm": "large language models",
    "llms": "large language models",
    # Cloud / DevOps
    "k8s": "kubernetes",
    "kube": "kubernetes",
    "amazon web services": "aws",
    "microsoft azure": "azure",
    "ms azure": "azure",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "cicd": "ci/cd",
    "ci cd": "ci/cd",
    "gh actions": "github actions",
    "iac": "infrastructure as code",
    "docker compose": "docker",
    "linux admin": "linux",
    # Practices
    "rest": "rest apis",
    "rest api": "rest apis",
    "restful": "rest apis",
    "restful apis": "rest apis",
    "oop": "object-oriented programming",
    "tdd": "test-driven development",
    "ux": "ux design",
    "ui/ux": "ux design",
    "pm": "project management",
    "ba": "business analysis",
    "bpmn 2.0": "bpmn",
    "uml diagrams": "uml",
    "pen testing": "penetration testing",
    "pentesting": "penetration testing",
    "siem tools": "siem",
    "itil v4": "itil",
    "itil4": "itil",
}

_SPACE_RE = re.compile(r"\s+")


class SkillNormaliser:
    """Turns free-text skill names into canonical lowercase names."""

    def __init__(self, aliases: dict[str, str] | None = None) -> None:
        self.aliases = dict(ALIASES if aliases is None else aliases)

    @staticmethod
    def clean(raw: str) -> str:
        """Lowercase, trim and collapse internal whitespace (no alias lookup)."""
        return _SPACE_RE.sub(" ", (raw or "").strip().lower())

    def normalise(self, raw: str) -> str:
        """Canonical form of one skill. Returns "" for blank input."""
        cleaned = self.clean(raw).strip(" ,;")
        return self.aliases.get(cleaned, cleaned)

    def is_alias(self, raw: str) -> bool:
        """True when the raw text was rewritten by the alias table (e.g. JS)."""
        cleaned = self.clean(raw)
        return cleaned in self.aliases and self.aliases[cleaned] != cleaned

    def normalise_many(self, raws: Iterable[str]) -> list[str]:
        """Normalise a list, dropping blanks and duplicates, keeping first-seen order."""
        seen: set[str] = set()
        out: list[str] = []
        for raw in raws:
            name = self.normalise(raw)
            if name and name not in seen:
                seen.add(name)
                out.append(name)
        return out

    def normalise_with_source(self, raws: Iterable[str]) -> list[tuple[str, str]]:
        """Like normalise_many but keeps what the user originally typed.

        Returns [(canonical, as_entered)]. Used to show "JS was read as
        JavaScript" in the results explanation.
        """
        seen: set[str] = set()
        out: list[tuple[str, str]] = []
        for raw in raws:
            name = self.normalise(raw)
            if name and name not in seen:
                seen.add(name)
                out.append((name, (raw or "").strip()))
        return out


normaliser = SkillNormaliser()
