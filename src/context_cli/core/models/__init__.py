"""Pydantic models defining all Context Lint data contracts."""

from context_cli.core.models.audit import (
    AuditReport,
    BatchAuditReport,
    Diagnostic,
    DiscoveryResult,
    LintCheck,
    LintResult,
    PageAudit,
    Recommendation,
    SiteAuditReport,
)
from context_cli.core.models.benchmark import (
    BenchmarkConfig,
    BenchmarkReport,
    JudgeResult,
    ModelBenchmarkSummary,
    PromptBenchmarkResult,
    PromptEntry,
)
from context_cli.core.models.ci import (
    BaselineComparison,
    BaselineRegression,
    BaselineScores,
    PillarThresholds,
    ThresholdFailure,
    ThresholdResult,
)
from context_cli.core.models.compare import (
    CompareReport,
    PillarDelta,
)
from context_cli.core.models.content import ContentReport
from context_cli.core.models.generate import (
    BatchGenerateConfig,
    BatchGenerateResult,
    BatchPageResult,
    GenerateConfig,
    GenerateResult,
    OutputFormat,
    ProfileType,
    RetryConfig,
    SchemaJsonLdOutput,
)
from context_cli.core.models.llms_txt import (
    LlmsTxtContent,
    LlmsTxtLink,
    LlmsTxtReport,
    LlmsTxtSection,
)
from context_cli.core.models.plugin import PluginResult
from context_cli.core.models.radar import (
    BrandMention,
    CitationSource,
    DomainCategory,
    ModelRadarResult,
    RadarConfig,
    RadarReport,
)
from context_cli.core.models.retail import (
    ContentQualityReport,
    FeedComplianceReport,
    MarketplaceType,
    ProductData,
    ProductSchemaReport,
    RetailAuditReport,
    SocialProofReport,
    VisualAssetsReport,
)
from context_cli.core.models.robots import (
    BotAccessResult,
    RobotsReport,
)
from context_cli.core.models.schema import (
    SchemaOrgResult,
    SchemaReport,
)
from context_cli.core.models.signals import (
    ContentUsageReport,
    EeatReport,
    RslReport,
)
from context_cli.core.models.webhook import WebhookPayload

__all__ = [
    # audit
    "AuditReport",
    "BatchAuditReport",
    "Diagnostic",
    "DiscoveryResult",
    "LintCheck",
    "LintResult",
    "PageAudit",
    "Recommendation",
    "SiteAuditReport",
    # benchmark
    "BenchmarkConfig",
    "BenchmarkReport",
    "JudgeResult",
    "ModelBenchmarkSummary",
    "PromptBenchmarkResult",
    "PromptEntry",
    # ci
    "BaselineComparison",
    "BaselineRegression",
    "BaselineScores",
    "PillarThresholds",
    "ThresholdFailure",
    "ThresholdResult",
    # compare
    "CompareReport",
    "PillarDelta",
    # content
    "ContentReport",
    # generate
    "BatchGenerateConfig",
    "BatchGenerateResult",
    "BatchPageResult",
    "GenerateConfig",
    "GenerateResult",
    "OutputFormat",
    "ProfileType",
    "RetryConfig",
    "SchemaJsonLdOutput",
    # llms_txt
    "LlmsTxtContent",
    "LlmsTxtLink",
    "LlmsTxtReport",
    "LlmsTxtSection",
    # plugin
    "PluginResult",
    # radar
    "BrandMention",
    "CitationSource",
    "DomainCategory",
    "ModelRadarResult",
    "RadarConfig",
    "RadarReport",
    # retail
    "ContentQualityReport",
    "FeedComplianceReport",
    "MarketplaceType",
    "ProductData",
    "ProductSchemaReport",
    "RetailAuditReport",
    "SocialProofReport",
    "VisualAssetsReport",
    # robots
    "BotAccessResult",
    "RobotsReport",
    # schema
    "SchemaOrgResult",
    "SchemaReport",
    # signals
    "ContentUsageReport",
    "EeatReport",
    "RslReport",
    # webhook
    "WebhookPayload",
]
