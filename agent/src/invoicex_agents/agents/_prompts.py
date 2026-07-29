"""Prompt resource loader."""

from importlib.resources import files


def load_prompt(filename: str) -> str:
    """Load one version-controlled system prompt from the package."""

    return files("invoicex_agents.prompts").joinpath(filename).read_text(encoding="utf-8")
