"""Tests for batch generation orchestrator."""

from __future__ import annotations

import os
from unittest.mock import patch

from aeo_cli.core.models import (
    BatchGenerateConfig,
    BatchGenerateResult,
    BatchPageResult,
    GenerateConfig,
    GenerateResult,
    LlmsTxtContent,
    ProfileType,
    SchemaJsonLdOutput,
)

# ── Model tests ─────────────────────────────────────────────────────────────


class TestBatchGenerateConfig:
    def test_defaults(self):
        cfg = BatchGenerateConfig(urls=["https://example.com"])
        assert cfg.profile == ProfileType.generic
        assert cfg.model is None
        assert cfg.output_dir == "./aeo-output"
        assert cfg.concurrency == 3

    def test_all_fields(self):
        cfg = BatchGenerateConfig(
            urls=["https://a.com", "https://b.com"],
            profile=ProfileType.saas,
            model="gpt-4o",
            output_dir="/tmp/out",
            concurrency=5,
        )
        assert cfg.urls == ["https://a.com", "https://b.com"]
        assert cfg.profile == ProfileType.saas
        assert cfg.model == "gpt-4o"
        assert cfg.output_dir == "/tmp/out"
        assert cfg.concurrency == 5

    def test_empty_urls(self):
        cfg = BatchGenerateConfig(urls=[])
        assert cfg.urls == []


class TestBatchPageResult:
    def test_success(self):
        r = BatchPageResult(
            url="https://example.com",
            success=True,
            llms_txt_path="/out/llms.txt",
            schema_jsonld_path="/out/schema.jsonld",
        )
        assert r.success is True
        assert r.error is None

    def test_failure(self):
        r = BatchPageResult(
            url="https://bad.com",
            success=False,
            error="Connection refused",
        )
        assert r.success is False
        assert r.llms_txt_path is None
        assert r.schema_jsonld_path is None
        assert r.error == "Connection refused"


class TestBatchGenerateResult:
    def test_all_fields(self):
        r = BatchGenerateResult(
            total=2,
            succeeded=1,
            failed=1,
            results=[
                BatchPageResult(url="https://a.com", success=True),
                BatchPageResult(url="https://b.com", success=False, error="err"),
            ],
            model_used="gpt-4o",
            profile=ProfileType.generic,
            output_dir="/out",
        )
        assert r.total == 2
        assert r.succeeded == 1
        assert r.failed == 1
        assert len(r.results) == 2
        assert r.model_used == "gpt-4o"
        assert r.profile == ProfileType.generic
        assert r.output_dir == "/out"


# ── Sanitize URL helper tests ───────────────────────────────────────────────


class TestSanitizeUrlToDirname:
    def _sanitize(self, url: str) -> str:
        from aeo_cli.core.generate.batch import _sanitize_url_to_dirname

        return _sanitize_url_to_dirname(url)

    def test_basic_url(self):
        result = self._sanitize("https://example.com")
        assert result == "example.com"

    def test_url_with_path(self):
        result = self._sanitize("https://example.com/docs/guide")
        assert result == "example.com_docs_guide"

    def test_url_with_trailing_slash(self):
        result = self._sanitize("https://example.com/about/")
        assert result == "example.com_about"

    def test_url_with_port(self):
        result = self._sanitize("https://example.com:8080/api")
        assert result == "example.com_8080_api"

    def test_url_with_query_params(self):
        result = self._sanitize("https://example.com/search?q=hello&page=1")
        assert result == "example.com_search_q_hello_page_1"

    def test_url_with_special_chars(self):
        result = self._sanitize("https://my-site.co.uk/path/to/page")
        assert result == "my-site.co.uk_path_to_page"

    def test_http_scheme(self):
        result = self._sanitize("http://example.com/page")
        assert result == "example.com_page"

    def test_consecutive_separators_collapsed(self):
        result = self._sanitize("https://example.com///double//slash")
        # Multiple slashes should not create multiple underscores
        assert "__" not in result


# ── Batch orchestrator tests ─────────────────────────────────────────────────


def _make_generate_result(url: str, output_dir: str) -> GenerateResult:
    """Build a mock GenerateResult for testing."""
    return GenerateResult(
        url=url,
        model_used="gpt-4o-mini",
        profile=ProfileType.generic,
        llms_txt=LlmsTxtContent(title="Test", description="Test site", sections=[]),
        schema_jsonld=SchemaJsonLdOutput(
            schema_type="Organization",
            json_ld={"@context": "https://schema.org", "@type": "Organization"},
        ),
        llms_txt_path=os.path.join(output_dir, "llms.txt"),
        schema_jsonld_path=os.path.join(output_dir, "schema.jsonld"),
    )


class TestGenerateBatch:
    async def test_all_succeed(self, tmp_path):
        from aeo_cli.core.generate.batch import generate_batch

        urls = ["https://a.com", "https://b.com"]
        config = BatchGenerateConfig(
            urls=urls,
            model="gpt-4o-mini",
            output_dir=str(tmp_path),
        )

        async def mock_generate(cfg: GenerateConfig) -> GenerateResult:
            return _make_generate_result(cfg.url, cfg.output_dir)

        with patch(
            "aeo_cli.core.generate.batch.generate_assets",
            side_effect=mock_generate,
        ):
            result = await generate_batch(config)

        assert result.total == 2
        assert result.succeeded == 2
        assert result.failed == 0
        assert result.model_used == "gpt-4o-mini"
        assert result.profile == ProfileType.generic
        assert len(result.results) == 2
        assert all(r.success for r in result.results)

    async def test_some_fail(self, tmp_path):
        from aeo_cli.core.generate.batch import generate_batch

        urls = ["https://good.com", "https://bad.com", "https://also-good.com"]
        config = BatchGenerateConfig(
            urls=urls,
            model="gpt-4o-mini",
            output_dir=str(tmp_path),
        )

        async def mock_generate(cfg: GenerateConfig) -> GenerateResult:
            if "bad" in cfg.url:
                raise RuntimeError("Connection refused")
            return _make_generate_result(cfg.url, cfg.output_dir)

        with patch(
            "aeo_cli.core.generate.batch.generate_assets",
            side_effect=mock_generate,
        ):
            result = await generate_batch(config)

        assert result.total == 3
        assert result.succeeded == 2
        assert result.failed == 1
        # Check the failure
        failed = [r for r in result.results if not r.success]
        assert len(failed) == 1
        assert failed[0].url == "https://bad.com"
        assert "Connection refused" in failed[0].error

    async def test_empty_url_list(self, tmp_path):
        from aeo_cli.core.generate.batch import generate_batch

        config = BatchGenerateConfig(
            urls=[],
            model="gpt-4o-mini",
            output_dir=str(tmp_path),
        )

        result = await generate_batch(config)
        assert result.total == 0
        assert result.succeeded == 0
        assert result.failed == 0
        assert result.results == []

    async def test_single_url(self, tmp_path):
        from aeo_cli.core.generate.batch import generate_batch

        config = BatchGenerateConfig(
            urls=["https://only.com"],
            model="gpt-4o-mini",
            output_dir=str(tmp_path),
        )

        async def mock_generate(cfg: GenerateConfig) -> GenerateResult:
            return _make_generate_result(cfg.url, cfg.output_dir)

        with patch(
            "aeo_cli.core.generate.batch.generate_assets",
            side_effect=mock_generate,
        ):
            result = await generate_batch(config)

        assert result.total == 1
        assert result.succeeded == 1
        assert result.results[0].url == "https://only.com"

    async def test_model_auto_detection(self, tmp_path):
        from aeo_cli.core.generate.batch import generate_batch

        config = BatchGenerateConfig(
            urls=["https://example.com"],
            output_dir=str(tmp_path),
        )  # model=None → auto-detect

        async def mock_generate(cfg: GenerateConfig) -> GenerateResult:
            return _make_generate_result(cfg.url, cfg.output_dir)

        with (
            patch(
                "aeo_cli.core.generate.batch.generate_assets",
                side_effect=mock_generate,
            ),
            patch(
                "aeo_cli.core.generate.batch.detect_model",
                return_value="claude-sonnet-4-20250514",
            ),
        ):
            result = await generate_batch(config)

        assert result.model_used == "claude-sonnet-4-20250514"

    async def test_concurrency_limiting(self, tmp_path):
        """Verify that semaphore limits concurrent executions."""
        import asyncio

        from aeo_cli.core.generate.batch import generate_batch

        config = BatchGenerateConfig(
            urls=[f"https://site{i}.com" for i in range(6)],
            model="gpt-4o-mini",
            output_dir=str(tmp_path),
            concurrency=2,
        )

        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def mock_generate(cfg: GenerateConfig) -> GenerateResult:
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            await asyncio.sleep(0.01)  # simulate work
            async with lock:
                current_concurrent -= 1
            return _make_generate_result(cfg.url, cfg.output_dir)

        with patch(
            "aeo_cli.core.generate.batch.generate_assets",
            side_effect=mock_generate,
        ):
            result = await generate_batch(config)

        assert result.total == 6
        assert result.succeeded == 6
        assert max_concurrent <= 2

    async def test_output_dir_per_url(self, tmp_path):
        """Each URL gets its own subdirectory in output_dir."""
        from aeo_cli.core.generate.batch import generate_batch

        config = BatchGenerateConfig(
            urls=["https://a.com/page1", "https://b.com/page2"],
            model="gpt-4o-mini",
            output_dir=str(tmp_path),
        )

        received_dirs: list[str] = []

        async def mock_generate(cfg: GenerateConfig) -> GenerateResult:
            received_dirs.append(cfg.output_dir)
            return _make_generate_result(cfg.url, cfg.output_dir)

        with patch(
            "aeo_cli.core.generate.batch.generate_assets",
            side_effect=mock_generate,
        ):
            await generate_batch(config)

        # Each URL should have gotten a different output directory
        assert len(received_dirs) == 2
        assert received_dirs[0] != received_dirs[1]
        # Both should be subdirectories of the main output dir
        for d in received_dirs:
            assert d.startswith(str(tmp_path))

    async def test_all_fail(self, tmp_path):
        from aeo_cli.core.generate.batch import generate_batch

        config = BatchGenerateConfig(
            urls=["https://bad1.com", "https://bad2.com"],
            model="gpt-4o-mini",
            output_dir=str(tmp_path),
        )

        async def mock_generate(cfg: GenerateConfig) -> GenerateResult:
            raise RuntimeError(f"Failed: {cfg.url}")

        with patch(
            "aeo_cli.core.generate.batch.generate_assets",
            side_effect=mock_generate,
        ):
            result = await generate_batch(config)

        assert result.total == 2
        assert result.succeeded == 0
        assert result.failed == 2
        assert all(not r.success for r in result.results)

    async def test_profile_propagated(self, tmp_path):
        """Profile from batch config is passed to per-URL configs."""
        from aeo_cli.core.generate.batch import generate_batch

        config = BatchGenerateConfig(
            urls=["https://example.com"],
            model="gpt-4o-mini",
            output_dir=str(tmp_path),
            profile=ProfileType.ecommerce,
        )

        received_configs: list[GenerateConfig] = []

        async def mock_generate(cfg: GenerateConfig) -> GenerateResult:
            received_configs.append(cfg)
            return _make_generate_result(cfg.url, cfg.output_dir)

        with patch(
            "aeo_cli.core.generate.batch.generate_assets",
            side_effect=mock_generate,
        ):
            result = await generate_batch(config)

        assert result.profile == ProfileType.ecommerce
        assert received_configs[0].profile == ProfileType.ecommerce

    async def test_exception_type_captured(self, tmp_path):
        """Various exception types are all captured gracefully."""
        from aeo_cli.core.generate.batch import generate_batch

        config = BatchGenerateConfig(
            urls=["https://timeout.com", "https://value-error.com"],
            model="gpt-4o-mini",
            output_dir=str(tmp_path),
        )

        async def mock_generate(cfg: GenerateConfig) -> GenerateResult:
            if "timeout" in cfg.url:
                raise TimeoutError("Request timed out")
            raise ValueError("Invalid data")

        with patch(
            "aeo_cli.core.generate.batch.generate_assets",
            side_effect=mock_generate,
        ):
            result = await generate_batch(config)

        assert result.failed == 2
        errors = {r.url: r.error for r in result.results}
        assert "timed out" in errors["https://timeout.com"]
        assert "Invalid data" in errors["https://value-error.com"]
