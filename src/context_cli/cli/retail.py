"""Retail command -- audit product URLs for AI-readiness."""
from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from context_cli.core.retail.auditor import retail_audit

console = Console()


def register(app: typer.Typer) -> None:
    """Register the retail command onto the Typer app."""

    @app.command()
    def retail(
        url: str = typer.Argument(help="Product URL to audit"),
        verbose: bool = typer.Option(
            False, "--verbose", "-v", help="Show detailed breakdown"
        ),
        json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    ) -> None:
        """Audit a product URL for retail AI-readiness."""
        try:
            report = asyncio.run(retail_audit(url))
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)

        if json_output:
            console.print(report.model_dump_json(indent=2))
            return

        # Rich output
        console.print(f"\n[bold]Retail Audit: {report.url}[/bold]")
        console.print(f"  Marketplace: {report.marketplace.value}")
        console.print(f"  Score: {report.score}/100")

        console.print()
        console.print(f"  Product Schema:    {report.product_schema.score}/25")
        console.print(f"  Content Quality:   {report.content_quality.score}/30")
        console.print(f"  Visual Assets:     {report.visual_assets.score}/15")
        console.print(f"  Social Proof:      {report.social_proof.score}/20")
        console.print(f"  Feed Compliance:   {report.feed_compliance.score}/10")

        if verbose:
            _print_verbose(report)


def _print_verbose(report: object) -> None:
    """Print detailed per-pillar breakdown."""
    from context_cli.core.models import RetailAuditReport

    assert isinstance(report, RetailAuditReport)

    # Product Schema details
    ps = report.product_schema
    console.print("\n[bold]Product Schema Details:[/bold]")
    console.print(f"  Has Product schema: {ps.has_product_schema}")
    console.print(f"  Has Offer: {ps.has_offer}")
    console.print(f"  Has AggregateRating: {ps.has_aggregate_rating}")
    if ps.missing_fields:
        console.print(f"  Missing fields: {', '.join(ps.missing_fields)}")

    # Content Quality details
    cq = report.content_quality
    console.print("\n[bold]Content Quality Details:[/bold]")
    console.print(f"  Bullet points: {cq.bullet_count}")
    console.print(f"  Description length: {cq.description_length} chars")
    console.print(f"  Has A+ content: {cq.has_aplus}")
    console.print(f"  Has spec chart: {cq.has_spec_chart}")

    # Visual Assets details
    va = report.visual_assets
    console.print("\n[bold]Visual Assets Details:[/bold]")
    console.print(f"  Images: {va.image_count}")
    console.print(f"  Images with alt text: {va.images_with_alt}")
    console.print(f"  Has video: {va.has_video}")

    # Social Proof details
    sp = report.social_proof
    console.print("\n[bold]Social Proof Details:[/bold]")
    console.print(f"  Reviews: {sp.review_count}")
    console.print(f"  Rating: {sp.rating}")
    console.print(f"  Has Q&A: {sp.has_qa}")

    # Feed Compliance details
    fc = report.feed_compliance
    console.print("\n[bold]Feed Compliance Details:[/bold]")
    pct = int(fc.compliance_rate * 100)
    console.print(f"  Compliance rate: {pct}%")
    if fc.present_fields:
        console.print(f"  Present fields: {', '.join(fc.present_fields)}")
    if fc.missing_fields:
        console.print(f"  Missing fields: {', '.join(fc.missing_fields)}")
