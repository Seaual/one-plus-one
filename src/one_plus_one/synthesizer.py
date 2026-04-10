"""Project synthesizer: combines two projects into an innovation proposal."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


@dataclass
class SynthesisReport:
    """Result of synthesizing two projects."""

    combination_name: str
    one_liner: str
    core_innovations: list[str]
    tech_architecture: str
    risks: list[str]
    mvp_suggestion: str
    project_a: str
    project_b: str

    def to_markdown(self) -> str:
        parts = [
            f"# {self.combination_name}",
            f"## 1+1>2 组合方案",
            f"> {self.one_liner}",
            "",
            f"**参考项目**: [{self.project_a}](https://github.com/{self.project_a}) + [{self.project_b}](https://github.com/{self.project_b})",
            "",
            "## 核心创新点",
        ]
        for i, inn in enumerate(self.core_innovations, 1):
            parts.append(f"{i}. {inn}")
        parts.extend([
            "",
            "## 技术架构",
            self.tech_architecture,
            "",
            "## 潜在风险",
        ])
        for risk in self.risks:
            parts.append(f"- {risk}")
        parts.extend([
            "",
            "## MVP 建议",
            self.mvp_suggestion,
        ])
        return "\n".join(parts)


class Synthesizer:
    """Analyzes two projects and generates a combination proposal.

    Uses Claude Code (via subprocess) for LLM-powered analysis.
    Falls back to a rule-based heuristic if Claude Code is unavailable.
    """

    @classmethod
    def synthesize(cls, project_a: dict, project_b: dict) -> SynthesisReport:
        """Synthesize two projects into a combination proposal.

        Args:
            project_a: Dict with full_name, description, stars, language, topics, readme
            project_b: Same structure as project_a
        """
        # Use rule-based synthesis by default to avoid hanging on CLI
        # To enable LLM, set ONEPLUSONE_LLM=1 and ensure 'claude' is in PATH
        import os
        if os.environ.get("ONEPLUSONE_LLM"):
            try:
                return cls._synthesize_with_llm(project_a, project_b)
            except Exception:
                pass
        return cls._synthesize_rule_based(project_a, project_b)

    @classmethod
    def _synthesize_with_llm(cls, project_a: dict, project_b: dict) -> SynthesisReport:
        """Use Claude Code subprocess for LLM analysis."""
        prompt = cls._build_llm_prompt(project_a, project_b)

        result = subprocess.run(
            ["claude", "--print", "--max-turns", "3", prompt],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Claude subprocess failed: {result.stderr}")

        return cls._parse_llm_response(result.stdout, project_a, project_b)

    @classmethod
    def _build_llm_prompt(cls, a: dict, b: dict) -> str:
        return f"""You are a project innovation synthesizer. Given two GitHub projects, analyze their complementarity and generate a combination proposal.

## Project A: {a.get('full_name', 'unknown')}
- Description: {a.get('description', 'N/A')}
- Stars: {a.get('stars', 0)}
- Language: {a.get('language', 'N/A')}
- Topics: {', '.join(a.get('topics', []))}
- README: {a.get('readme', '')[:1000]}

## Project B: {b.get('full_name', 'unknown')}
- Description: {b.get('description', 'N/A')}
- Stars: {b.get('stars', 0)}
- Language: {b.get('language', 'N/A')}
- Topics: {', '.join(b.get('topics', []))}
- README: {b.get('readme', '')[:1000]}

Respond with ONLY a valid JSON object (no markdown code blocks, no extra text) in this exact format:

{{
  "combination_name": "Creative name combining both project names",
  "one_liner": "One sentence describing the combined vision",
  "core_innovations": ["Innovation 1", "Innovation 2", "Innovation 3"],
  "tech_architecture": "Brief architecture description in markdown (2-3 paragraphs)",
  "risks": ["Risk 1", "Risk 2", "Risk 3"],
  "mvp_suggestion": "Concrete MVP suggestion (2-3 sentences)"
}}"""

    @classmethod
    def _parse_llm_response(cls, text: str, project_a: dict, project_b: dict) -> SynthesisReport:
        """Parse JSON response from LLM."""
        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found in response")

        data = json.loads(text[start:end])
        return SynthesisReport(
            combination_name=data["combination_name"],
            one_liner=data["one_liner"],
            core_innovations=data["core_innovations"],
            tech_architecture=data["tech_architecture"],
            risks=data["risks"],
            mvp_suggestion=data["mvp_suggestion"],
            project_a=project_a.get("full_name", ""),
            project_b=project_b.get("full_name", ""),
        )

    @classmethod
    def _synthesize_rule_based(cls, project_a: dict, project_b: dict) -> SynthesisReport:
        """Fallback: rule-based synthesis without LLM."""
        name_a = project_a.get("full_name", "Project A").split("/")[-1]
        name_b = project_b.get("full_name", "Project B").split("/")[-1]
        desc_a = project_a.get("description", "")
        desc_b = project_b.get("description", "")
        lang_a = project_a.get("language", "")
        lang_b = project_b.get("language", "")
        topics_a = set(project_a.get("topics", []))
        topics_b = set(project_b.get("topics", []))
        overlap = topics_a & topics_b

        combination_name = f"{name_a.title()}-{name_b.title()}"
        one_liner = f"Combine {desc_a or name_a} with {desc_b or name_b}"
        if overlap:
            one_liner += f" (shared: {', '.join(overlap)})"

        innovations = [
            f"Merge {desc_a or name_a}'s core functionality with {desc_b or name_b}",
            f"Cross-pollinate {lang_a or 'A'} and {lang_b or 'B'} ecosystems",
            f"Leverage shared topics ({', '.join(overlap) if overlap else 'complementary strengths'}) for unified UX",
        ]

        tech_arch = f"## Proposed Architecture\n\n- **Frontend**: {lang_b} ({name_b})\n- **Backend**: {lang_a} ({name_a})\n- **Integration**: REST API + shared data models"
        risks = [
            "Different tech stacks may complicate integration",
            "Conflicting design philosophies",
            "User acquisition for a combined product is unproven",
        ]
        mvp = f"Build a minimal integration: expose {name_a}'s core API through {name_b}'s UI. Validate with a simple use case before expanding."

        return SynthesisReport(
            combination_name=combination_name,
            one_liner=one_liner,
            core_innovations=innovations,
            tech_architecture=tech_arch,
            risks=risks,
            mvp_suggestion=mvp,
            project_a=project_a.get("full_name", ""),
            project_b=project_b.get("full_name", ""),
        )
