"""Recommendation engine: matches project signals to available plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.skill_scout.github_search import PluginInfo
    from htmlgraph.skill_scout.project_analyzer import ProjectAnalysis


@dataclass
class Recommendation:
    """A scored plugin recommendation with reasons."""

    plugin_name: str
    repo: str
    description: str
    category: str
    score: int = 0
    reasons: list[str] = field(default_factory=list)


# Rule table: (signal_key, signal_value, plugin_name, repo_hint, reason, points)
# signal_value of "*" means "any non-empty list"
PLUGIN_RULES: list[tuple[str, str | bool, str, str, str, int]] = [
    # Language-based recommendations
    (
        "languages",
        "python",
        "pyright-lsp",
        "anthropics/claude-plugins-official",
        "Python project — type checking LSP",
        10,
    ),
    (
        "languages",
        "javascript",
        "typescript-lsp",
        "anthropics/claude-plugins-official",
        "JS/TS project — language server",
        10,
    ),
    (
        "languages",
        "rust",
        "rust-lsp",
        "anthropics/claude-plugins-official",
        "Rust project — rust-analyzer LSP",
        10,
    ),
    (
        "languages",
        "go",
        "gopls-lsp",
        "anthropics/claude-plugins-official",
        "Go project — gopls LSP",
        10,
    ),
    # Framework-based
    (
        "frameworks",
        "FastAPI",
        "sentry",
        "getsentry/sentry-claude",
        "FastAPI project — error monitoring",
        6,
    ),
    (
        "frameworks",
        "Django",
        "sentry",
        "getsentry/sentry-claude",
        "Django project — error monitoring",
        6,
    ),
    (
        "frameworks",
        "React",
        "figma",
        "anthropics/claude-plugins-official",
        "React project — design-to-code",
        5,
    ),
    (
        "frameworks",
        "Next.js",
        "vercel",
        "anthropics/claude-plugins-official",
        "Next.js project — Vercel deploy",
        8,
    ),
    (
        "frameworks",
        "Phoenix",
        "htmlgraph",
        "shakestzd/htmlgraph",
        "Elixir/Phoenix — HtmlGraph observability",
        9,
    ),
    # Structural signals
    (
        "has_ci",
        True,
        "commit-commands",
        "anthropics/claude-code",
        "CI configured — git workflow commands",
        7,
    ),
    (
        "has_ci",
        True,
        "pr-review-toolkit",
        "anthropics/claude-code",
        "CI configured — PR review agents",
        6,
    ),
    (
        "has_tests",
        True,
        "code-review",
        "anthropics/claude-code",
        "Tests present — code review agent",
        5,
    ),
    (
        "has_docker",
        True,
        "feature-dev",
        "anthropics/claude-code",
        "Docker present — feature development workflow",
        4,
    ),
    # Universal (low score, always recommended for active projects)
    (
        "has_tests",
        True,
        "hookify",
        "anthropics/claude-code",
        "Any project — create hooks from conversation",
        2,
    ),
]


def recommend(
    signals: ProjectAnalysis,
    available_plugins: list[PluginInfo] | None = None,
    existing_plugins: list[str] | None = None,
    limit: int = 5,
) -> list[Recommendation]:
    """Score plugins against project signals, return top-N sorted by score.

    Args:
        signals: ProjectAnalysis from project_analyzer
        available_plugins: Optional list of PluginInfo from plugin_index
            (enriches descriptions)
        existing_plugins: Plugin names already installed (excluded from results)
        limit: Maximum recommendations to return
    """
    already_installed = set(existing_plugins or [])
    scores: dict[str, Recommendation] = {}

    for signal_key, signal_value, plugin_name, repo, reason, points in PLUGIN_RULES:
        if plugin_name in already_installed:
            continue

        if _check_signal(signals, signal_key, signal_value):
            if plugin_name not in scores:
                scores[plugin_name] = Recommendation(
                    plugin_name=plugin_name,
                    repo=repo,
                    description="",
                    category="",
                )
            scores[plugin_name].score += points
            scores[plugin_name].reasons.append(reason)

    if available_plugins:
        plugin_map = {p.name: p for p in available_plugins}
        for rec in scores.values():
            if rec.plugin_name in plugin_map:
                p = plugin_map[rec.plugin_name]
                rec.description = p.description
                rec.category = p.category

    ranked = sorted(scores.values(), key=lambda r: r.score, reverse=True)
    return ranked[:limit]


def _check_signal(signals: ProjectAnalysis, key: str, value: str | bool) -> bool:
    """Check if a project signal matches a rule condition."""
    sig_val = getattr(signals, key, None)
    if sig_val is None:
        return False
    if isinstance(sig_val, bool):
        return sig_val == value
    if isinstance(sig_val, list):
        if value == "*":
            return len(sig_val) > 0
        return value in sig_val
    return False
