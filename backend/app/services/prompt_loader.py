"""Prompt loader service.

Loads prompts from /prompts/ directory, parses YAML frontmatter,
and provides versioned access to all prompts.

Usage:
    loader = PromptLoader()
    prompt = loader.load_agent_prompt("perspective_discovery_agent")
    system_prompt = loader.load_system_prompt("base")
"""

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class PromptMetadata:
    """Parsed frontmatter metadata from a prompt file."""

    version: str
    description: str
    last_updated: str
    changelog: str


@dataclass
class Prompt:
    """A loaded prompt with metadata and content."""

    name: str
    metadata: PromptMetadata
    content: str

    @property
    def version(self) -> str:
        return self.metadata.version


class PromptLoader:
    """Loads and caches prompts from the prompts directory."""

    def __init__(self, prompts_dir: str | Path | None = None):
        if prompts_dir is None:
            # Default: look for prompts/ at project root
            # Walk up from this file to find the project root
            current = Path(__file__).resolve()
            for parent in current.parents:
                candidate = parent / "prompts"
                if candidate.is_dir():
                    prompts_dir = candidate
                    break
            if prompts_dir is None:
                raise FileNotFoundError(
                    "Could not find prompts/ directory. "
                    "Set PEA_PROMPTS_DIR environment variable or pass prompts_dir explicitly."
                )

        self._prompts_dir = Path(prompts_dir)
        self._cache: dict[str, Prompt] = {}

    def load_system_prompt(self, name: str) -> Prompt:
        """Load a system-level prompt."""
        return self._load_prompt("system", name)

    def load_agent_prompt(self, name: str) -> Prompt:
        """Load an agent prompt."""
        return self._load_prompt("agents", name)

    def load_template(self, name: str) -> Prompt:
        """Load a content template."""
        return self._load_prompt("templates", name)

    def get_agent_prompt_content(self, name: str) -> str:
        """Load agent prompt and return just the content string."""
        return self.load_agent_prompt(name).content

    def get_system_prompt_content(self, name: str = "base") -> str:
        """Load system prompt and return just the content string."""
        return self.load_system_prompt(name).content

    def get_template_content(self, name: str) -> str:
        """Load template and return just the content string."""
        return self.load_template(name).content

    def get_full_prompt(self, agent_name: str) -> str:
        """Load agent prompt with base system prompt prepended.

        Ensures all agents inherit global rules from base.md.
        """
        base = self.get_system_prompt_content("base")
        agent = self.get_agent_prompt_content(agent_name)
        return f"{base}\n\n---\n\n{agent}"

    def list_prompts(self, category: str | None = None) -> list[str]:
        """List available prompt names, optionally filtered by category."""
        results = []
        categories = [category] if category else ["system", "agents", "templates"]

        for cat in categories:
            cat_dir = self._prompts_dir / cat
            if cat_dir.is_dir():
                for f in cat_dir.glob("*.md"):
                    results.append(f"{cat}/{f.stem}")

        return sorted(results)

    def _load_prompt(self, category: str, name: str) -> Prompt:
        """Load a prompt file, parsing frontmatter."""
        cache_key = f"{category}/{name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        filepath = self._prompts_dir / category / f"{name}.md"
        if not filepath.is_file():
            raise FileNotFoundError(
                f"Prompt not found: {filepath}. "
                f"Available in '{category}': {[f.stem for f in (self._prompts_dir / category).glob('*.md')]}"
            )

        raw = filepath.read_text(encoding="utf-8")
        metadata, content = self._parse_frontmatter(raw)

        prompt = Prompt(name=name, metadata=metadata, content=content)
        self._cache[cache_key] = prompt
        return prompt

    @staticmethod
    def _parse_frontmatter(raw: str) -> tuple[PromptMetadata, str]:
        """Parse YAML frontmatter from a markdown file."""
        match = re.match(r"^---\n(.*?)\n---\n(.*)", raw, re.DOTALL)
        if not match:
            return PromptMetadata(
                version="0.0.0",
                description="",
                last_updated="",
                changelog="",
            ), raw

        frontmatter_str = match.group(1)
        content = match.group(2).strip()

        try:
            fm = yaml.safe_load(frontmatter_str)
        except yaml.YAMLError:
            fm = {}

        return PromptMetadata(
            version=fm.get("version", "0.0.0"),
            description=fm.get("description", ""),
            last_updated=fm.get("last_updated", ""),
            changelog=fm.get("changelog", ""),
        ), content
