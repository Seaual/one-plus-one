"""Tests for the project synthesizer."""

import json

from one_plus_one.synthesizer import Synthesizer, SynthesisReport


class TestSynthesizer:
    def test_synthesize_returns_report(self):
        proj_a = {
            "full_name": "a/ml-lib",
            "description": "Machine learning framework for Python",
            "stars": 15000,
            "language": "Python",
            "topics": ["ml", "ai", "python"],
            "readme": "# ML-Lib\n\nA fast ML framework with scikit-learn compatible API.\nFeatures: pipelines, cross-validation, model selection.",
        }
        proj_b = {
            "full_name": "b/viz-tool",
            "description": "Interactive data visualization toolkit",
            "stars": 8000,
            "language": "JavaScript",
            "topics": ["visualization", "charts", "dashboard"],
            "readme": "# Viz-Tool\n\nCreate interactive charts with ease.\nSupports: bar charts, line charts, scatter plots, heatmaps.",
        }

        report = Synthesizer.synthesize(proj_a, proj_b)

        assert isinstance(report, SynthesisReport)
        assert report.combination_name
        assert report.one_liner
        assert len(report.core_innovations) == 3
        assert report.risks
        assert report.mvp_suggestion
        assert report.tech_architecture  # markdown string

    def test_synthesize_empty_description(self):
        """Handles projects with minimal metadata."""
        proj_a = {"full_name": "a/repo", "description": "", "stars": 0, "language": "", "topics": [], "readme": ""}
        proj_b = {"full_name": "b/repo", "description": "", "stars": 0, "language": "", "topics": [], "readme": ""}

        report = Synthesizer.synthesize(proj_a, proj_b)
        assert isinstance(report, SynthesisReport)
        # Even with empty metadata, should produce a valid report
        assert report.combination_name
        assert report.one_liner

    def test_report_to_markdown(self):
        report = SynthesisReport(
            combination_name="ML-Viz Hub",
            one_liner="ML meets visualization",
            core_innovations=["Innovation A", "Innovation B", "Innovation C"],
            tech_architecture="## Architecture\n\nComponents: A, B, C",
            risks=["Risk 1", "Risk 2"],
            mvp_suggestion="Build a simple dashboard first",
            project_a="a/ml-lib",
            project_b="b/viz-tool",
        )
        md = report.to_markdown()
        assert "ML-Viz Hub" in md
        assert "ML meets visualization" in md
        assert "Innovation A" in md
        assert "Risk 1" in md
