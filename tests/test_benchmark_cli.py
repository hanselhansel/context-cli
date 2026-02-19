"""Tests for benchmark CLI command and MCP tool — cli/benchmark.py + server.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from aeo_cli.core.models import (
    BenchmarkReport,
    ModelBenchmarkSummary,
    PromptBenchmarkResult,
    PromptEntry,
)
from aeo_cli.main import app

runner = CliRunner()


def _make_report(brand: str = "TestBrand") -> BenchmarkReport:
    """Create a mock benchmark report for testing."""
    return BenchmarkReport(
        brand=brand,
        competitors=["CompA", "CompB"],
        overall_mention_rate=0.75,
        overall_recommendation_rate=0.50,
        per_prompt=[
            PromptBenchmarkResult(
                prompt="best brand?",
                mention_rate=0.8,
                recommendation_rate=0.6,
                total_runs=5,
            ),
        ],
        per_model=[
            ModelBenchmarkSummary(
                model="gpt-4o-mini",
                mention_rate=0.75,
                recommendation_rate=0.50,
                total_runs=5,
            ),
        ],
        estimated_cost=0.05,
        total_runs=5,
    )


def _make_prompts() -> list[PromptEntry]:
    return [
        PromptEntry(text="best brand?", category="general"),
        PromptEntry(text="top recommendations?", category="general"),
    ]


class TestBenchmarkCLIRegistration:
    """Verify the benchmark command is registered on the Typer app."""

    def test_benchmark_command_exists(self) -> None:
        """The 'benchmark' command should be available."""
        result = runner.invoke(app, ["benchmark", "--help"])
        assert result.exit_code == 0
        assert "benchmark" in result.output.lower() or "brand" in result.output.lower()


class TestBenchmarkCLIPromptFileValidation:
    """Tests for prompts file validation."""

    def test_missing_prompts_file(self, tmp_path: Path) -> None:
        """Should fail with exit code 1 if prompts file doesn't exist."""
        result = runner.invoke(
            app,
            ["benchmark", str(tmp_path / "nonexistent.txt"), "-b", "Brand"],
        )
        assert result.exit_code != 0

    @patch("aeo_cli.core.benchmark.loader.load_prompts", return_value=[])
    def test_empty_prompts_file(self, mock_load: MagicMock, tmp_path: Path) -> None:
        """Should fail if prompts file contains no prompts after loading."""
        f = tmp_path / "empty.txt"
        f.write_text("")
        result = runner.invoke(app, ["benchmark", str(f), "-b", "Brand", "-y"])
        assert result.exit_code != 0
        assert "no prompts" in result.output.lower()


class TestBenchmarkCLIFlow:
    """Tests for the full benchmark CLI flow (with mocked core functions)."""

    @patch("aeo_cli.cli.benchmark._run_benchmark")
    @patch("aeo_cli.core.benchmark.loader.load_prompts")
    def test_basic_run_rich_output(
        self, mock_load: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Should display Rich output on success."""
        f = tmp_path / "prompts.txt"
        f.write_text("best brand?\ntop recommendations?")
        mock_load.return_value = _make_prompts()
        mock_run.return_value = _make_report()

        result = runner.invoke(
            app,
            ["benchmark", str(f), "-b", "TestBrand", "-y"],
        )
        assert result.exit_code == 0
        assert "TestBrand" in result.output
        assert "75" in result.output or "0.75" in result.output

    @patch("aeo_cli.cli.benchmark._run_benchmark")
    @patch("aeo_cli.core.benchmark.loader.load_prompts")
    def test_json_output(
        self, mock_load: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Should output valid JSON when --json is passed."""
        f = tmp_path / "prompts.txt"
        f.write_text("best brand?")
        mock_load.return_value = _make_prompts()
        mock_run.return_value = _make_report()

        result = runner.invoke(
            app,
            ["benchmark", str(f), "-b", "TestBrand", "-y", "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["brand"] == "TestBrand"
        assert "overall_mention_rate" in data

    @patch("aeo_cli.cli.benchmark._run_benchmark")
    @patch("aeo_cli.core.benchmark.loader.load_prompts")
    def test_competitor_flags(
        self, mock_load: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Should pass competitors through to the benchmark."""
        f = tmp_path / "prompts.txt"
        f.write_text("best brand?")
        mock_load.return_value = _make_prompts()
        mock_run.return_value = _make_report()

        result = runner.invoke(
            app,
            [
                "benchmark",
                str(f),
                "-b",
                "TestBrand",
                "-c",
                "CompA",
                "-c",
                "CompB",
                "-y",
                "--json",
            ],
        )
        assert result.exit_code == 0

    @patch("aeo_cli.cli.benchmark._run_benchmark")
    @patch("aeo_cli.core.benchmark.loader.load_prompts")
    def test_model_flags(
        self, mock_load: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Should pass model list through to the benchmark."""
        f = tmp_path / "prompts.txt"
        f.write_text("best brand?")
        mock_load.return_value = _make_prompts()
        mock_run.return_value = _make_report()

        result = runner.invoke(
            app,
            [
                "benchmark",
                str(f),
                "-b",
                "TestBrand",
                "-m",
                "gpt-4o",
                "-m",
                "gpt-4o-mini",
                "-y",
            ],
        )
        assert result.exit_code == 0

    @patch("aeo_cli.cli.benchmark._run_benchmark")
    @patch("aeo_cli.core.benchmark.loader.load_prompts")
    def test_runs_flag(
        self, mock_load: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Should pass runs_per_model through."""
        f = tmp_path / "prompts.txt"
        f.write_text("best brand?")
        mock_load.return_value = _make_prompts()
        mock_run.return_value = _make_report()

        result = runner.invoke(
            app,
            ["benchmark", str(f), "-b", "TestBrand", "-r", "5", "-y"],
        )
        assert result.exit_code == 0

    @patch("aeo_cli.cli.benchmark._run_benchmark")
    @patch("aeo_cli.core.benchmark.loader.load_prompts")
    def test_cost_display(
        self, mock_load: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Should show estimated cost in Rich output."""
        f = tmp_path / "prompts.txt"
        f.write_text("best brand?")
        mock_load.return_value = _make_prompts()
        mock_run.return_value = _make_report()

        result = runner.invoke(
            app,
            ["benchmark", str(f), "-b", "TestBrand", "-y"],
        )
        assert result.exit_code == 0
        assert "$" in result.output

    @patch("aeo_cli.cli.benchmark._run_benchmark")
    @patch("aeo_cli.core.benchmark.loader.load_prompts")
    def test_exception_handling(
        self, mock_load: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Should handle exceptions gracefully."""
        f = tmp_path / "prompts.txt"
        f.write_text("best brand?")
        mock_load.return_value = _make_prompts()
        mock_run.side_effect = RuntimeError("API error")

        result = runner.invoke(
            app,
            ["benchmark", str(f), "-b", "TestBrand", "-y"],
        )
        assert result.exit_code != 0

    @patch("aeo_cli.cli.benchmark._run_benchmark")
    @patch("aeo_cli.core.benchmark.loader.load_prompts")
    def test_rich_output_per_model(
        self, mock_load: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Rich output should include per-model summaries."""
        f = tmp_path / "prompts.txt"
        f.write_text("best brand?")
        mock_load.return_value = _make_prompts()
        report = _make_report()
        report.per_model.append(
            ModelBenchmarkSummary(
                model="gpt-4o",
                mention_rate=0.9,
                recommendation_rate=0.7,
                total_runs=5,
            )
        )
        mock_run.return_value = report

        result = runner.invoke(
            app,
            ["benchmark", str(f), "-b", "TestBrand", "-y"],
        )
        assert result.exit_code == 0
        assert "gpt-4o-mini" in result.output

    @patch("aeo_cli.cli.benchmark._run_benchmark")
    @patch("aeo_cli.core.benchmark.loader.load_prompts")
    def test_rich_output_per_prompt(
        self, mock_load: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Rich output should include per-prompt results."""
        f = tmp_path / "prompts.txt"
        f.write_text("best brand?")
        mock_load.return_value = _make_prompts()
        mock_run.return_value = _make_report()

        result = runner.invoke(
            app,
            ["benchmark", str(f), "-b", "TestBrand", "-y"],
        )
        assert result.exit_code == 0
        assert "best brand?" in result.output


class TestBenchmarkCLICostConfirmation:
    """Tests for the cost confirmation prompt."""

    @patch("aeo_cli.cli.benchmark._run_benchmark")
    @patch("aeo_cli.core.benchmark.loader.load_prompts")
    def test_cost_confirmation_abort(
        self, mock_load: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Should abort if user declines the cost confirmation."""
        f = tmp_path / "prompts.txt"
        f.write_text("best brand?")
        mock_load.return_value = _make_prompts()
        mock_run.return_value = _make_report()

        runner.invoke(
            app,
            ["benchmark", str(f), "-b", "TestBrand"],
            input="n\n",
        )
        # Should abort (exit code != 0 or not run)
        mock_run.assert_not_called()

    @patch("aeo_cli.cli.benchmark._run_benchmark")
    @patch("aeo_cli.core.benchmark.loader.load_prompts")
    def test_cost_confirmation_proceed(
        self, mock_load: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Should proceed if user confirms the cost."""
        f = tmp_path / "prompts.txt"
        f.write_text("best brand?")
        mock_load.return_value = _make_prompts()
        mock_run.return_value = _make_report()

        result = runner.invoke(
            app,
            ["benchmark", str(f), "-b", "TestBrand"],
            input="y\n",
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()


class TestBenchmarkCLILitellmImportError:
    """Tests for litellm import error handling."""

    @patch(
        "aeo_cli.core.benchmark.loader.load_prompts",
        side_effect=ImportError("No module named 'litellm'"),
    )
    def test_litellm_import_error_on_call(
        self, mock_load: MagicMock, tmp_path: Path
    ) -> None:
        """Should show install instructions when load_prompts raises ImportError."""
        f = tmp_path / "prompts.txt"
        f.write_text("best brand?")

        result = runner.invoke(
            app,
            ["benchmark", str(f), "-b", "TestBrand", "-y"],
        )
        assert result.exit_code != 0
        assert "litellm" in result.output.lower() or "install" in result.output.lower()

    def test_litellm_import_error_on_module(self, tmp_path: Path) -> None:
        """Should show install instructions when loader module can't be imported."""
        import builtins

        f = tmp_path / "prompts.txt"
        f.write_text("best brand?")

        original_import = builtins.__import__

        def mock_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "aeo_cli.core.benchmark.loader":
                raise ImportError("No module named 'litellm'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = runner.invoke(
                app,
                ["benchmark", str(f), "-b", "TestBrand", "-y"],
            )
        assert result.exit_code != 0


class TestRunBenchmarkFunction:
    """Tests for _run_benchmark() to cover the function body directly."""

    @patch("aeo_cli.core.benchmark.metrics.compute_report")
    @patch("aeo_cli.core.benchmark.judge.judge_all", new_callable=AsyncMock)
    @patch("aeo_cli.core.benchmark.dispatcher.dispatch_queries", new_callable=AsyncMock)
    def test_run_benchmark_calls_pipeline(
        self,
        mock_dispatch: AsyncMock,
        mock_judge: AsyncMock,
        mock_compute: MagicMock,
    ) -> None:
        """_run_benchmark should call dispatch, judge, and compute in sequence."""
        from aeo_cli.cli.benchmark import _run_benchmark
        from aeo_cli.core.models import BenchmarkConfig

        config = BenchmarkConfig(
            prompts=["p1"], brand="B", models=["gpt-4o-mini"], runs_per_model=1
        )
        mock_dispatch.return_value = ["result1"]
        mock_judge.return_value = ["judged1"]
        mock_compute.return_value = _make_report()

        report = _run_benchmark(config)

        mock_dispatch.assert_called_once_with(config)
        mock_judge.assert_called_once_with(["result1"], "B", [])
        mock_compute.assert_called_once_with(config, ["judged1"])
        assert report.brand == "TestBrand"


class TestBenchmarkMCPTool:
    """Tests for the benchmark MCP tool in server.py."""

    @pytest.mark.asyncio
    async def test_mcp_benchmark_tool(self) -> None:
        """MCP benchmark tool should accept prompts list and return dict."""
        from aeo_cli.server import benchmark_tool

        # FastMCP 2.x wraps @mcp.tool functions in FunctionTool; access via .fn
        _bench_fn = benchmark_tool.fn if hasattr(benchmark_tool, "fn") else benchmark_tool

        with (
            patch(
                "aeo_cli.core.benchmark.dispatcher.dispatch_queries",
                new_callable=AsyncMock,
                return_value=["response1"],
            ),
            patch(
                "aeo_cli.core.benchmark.judge.judge_all",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "aeo_cli.core.benchmark.metrics.compute_report",
                return_value=_make_report(),
            ),
        ):
            result = await _bench_fn(
                prompts=["best brand?"],
                brand="TestBrand",
                competitors=["CompA"],
                models=["gpt-4o-mini"],
                runs_per_model=1,
            )
        assert isinstance(result, dict)
        assert result["brand"] == "TestBrand"

    @pytest.mark.asyncio
    async def test_mcp_benchmark_defaults(self) -> None:
        """MCP tool should work with default parameters."""
        from aeo_cli.server import benchmark_tool

        _bench_fn = benchmark_tool.fn if hasattr(benchmark_tool, "fn") else benchmark_tool

        with (
            patch(
                "aeo_cli.core.benchmark.dispatcher.dispatch_queries",
                new_callable=AsyncMock,
                return_value=["response1"],
            ),
            patch(
                "aeo_cli.core.benchmark.judge.judge_all",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "aeo_cli.core.benchmark.metrics.compute_report",
                return_value=_make_report(),
            ),
        ):
            result = await _bench_fn(
                prompts=["q1"],
                brand="TestBrand",
            )
        assert isinstance(result, dict)
