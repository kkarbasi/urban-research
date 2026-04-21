from __future__ import annotations

import logging
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .core.config import Config
from .core.models import LocationReport
from .core.registry import SourceRegistry
from .core.storage import Storage
from .geocoding import GeocodingError
from .pipeline.runner import Pipeline

import cityscope.sources  # noqa: F401 — triggers source registration

console = Console()


def _load_config(config_path: str | None) -> Config:
    if config_path:
        return Config.load(Path(config_path))
    default = Path("config/settings.yaml")
    if default.exists():
        return Config.load(default)
    return Config()


@click.group()
@click.option("--config", "-c", "config_path", default=None, help="Path to config YAML")
@click.option("--verbose", "-v", is_flag=True, help="Verbose logging")
@click.pass_context
def cli(ctx: click.Context, config_path: str | None, verbose: bool) -> None:
    """Cityscope — real estate investment research data pipeline."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    ctx.ensure_object(dict)
    ctx.obj["config"] = _load_config(config_path)


@cli.command()
@click.argument("source_id", required=False)
@click.option("--all", "fetch_all", is_flag=True, help="Fetch from all sources")
@click.option("--vintage", type=int, default=None, help="Data vintage year")
@click.option("--min-pop", type=int, default=None, help="Override minimum population filter")
@click.option("--skip-laus", is_flag=True, help="Skip LAUS unemployment (avoids BLS API limit)")
@click.pass_context
def fetch(
    ctx: click.Context,
    source_id: str | None,
    fetch_all: bool,
    vintage: int | None,
    min_pop: int | None,
    skip_laus: bool,
) -> None:
    """Fetch data from one or all sources."""
    config: Config = ctx.obj["config"]
    pipeline = Pipeline(config)

    kwargs: dict = {}
    if vintage:
        kwargs["vintage"] = vintage
    if min_pop is not None:
        kwargs["min_population"] = min_pop
    if skip_laus:
        kwargs["skip_laus"] = True

    if fetch_all:
        ids = None
    elif source_id:
        ids = [source_id]
    else:
        console.print("[red]Specify a source ID or use --all[/red]")
        available = ", ".join(SourceRegistry.list_ids())
        console.print(f"Available: {available}")
        return

    with console.status("[bold green]Fetching data..."):
        results = pipeline.run(ids, **kwargs)

    for sid, result in results.items():
        table = Table(title=result.metadata.name, show_lines=False)
        table.add_column("Stat", style="dim")
        table.add_column("Value", style="bold")
        table.add_row("Geographies", f"{len(result.geographies):,}")
        table.add_row("Data points", f"{len(result.data_points):,}")
        table.add_row("Years", f"{result.metadata.min_year}–{result.metadata.max_year}")
        table.add_row("Metrics", ", ".join(result.metadata.metrics))
        console.print(table)


@cli.command("sources")
def list_sources() -> None:
    """List registered data sources."""
    table = Table(title="Data Sources")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Description")

    for source_id in SourceRegistry.list_ids():
        cls = SourceRegistry._sources[source_id]
        table.add_row(source_id, cls.name, cls.description)

    console.print(table)


@cli.command()
@click.option("--metric", "-m", default=None, help="Filter by metric name")
@click.option("--geo-type", "-g", default=None, help="Filter by geography type")
@click.option("--year", "-y", type=int, default=None, help="Filter by year")
@click.option("--min-pop", type=int, default=None, help="Minimum population")
@click.option("--top", "-n", type=int, default=20, help="Number of rows")
@click.pass_context
def query(
    ctx: click.Context,
    metric: str | None,
    geo_type: str | None,
    year: int | None,
    min_pop: int | None,
    top: int,
) -> None:
    """Query stored data."""
    config: Config = ctx.obj["config"]
    storage = Storage(config.storage.db_path)

    rows = storage.query_data(
        metric=metric,
        geo_type=geo_type,
        year=year,
        min_population=min_pop,
        limit=top,
    )

    if not rows:
        console.print("[yellow]No data found. Run 'fetch' first.[/yellow]")
        return

    table = Table(title=f"Results ({len(rows)} rows)")
    table.add_column("Geography", style="cyan", max_width=45)
    table.add_column("Type", style="dim")
    table.add_column("Metric")
    table.add_column("Year", justify="right")
    table.add_column("Value", justify="right", style="bold")
    table.add_column("Population", justify="right", style="dim")

    for row in rows:
        value = row["value"]
        m = row["metric"]
        if "pct" in m:
            val_str = f"{value:+.2f}%"
        elif m in ("population", "population_change"):
            val_str = f"{value:,.0f}"
        else:
            val_str = f"{value:,.2f}"

        pop = row.get("population")
        pop_str = f"{pop:,}" if pop else "—"

        table.add_row(
            row["name"],
            row["geo_type"],
            m,
            str(row["year"]),
            val_str,
            pop_str,
        )

    console.print(table)


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show what data has been fetched."""
    config: Config = ctx.obj["config"]
    storage = Storage(config.storage.db_path)

    summary = storage.get_sources_summary()
    if not summary:
        console.print("[yellow]No data fetched yet.[/yellow]")
        return

    table = Table(title="Data Status")
    table.add_column("Source", style="cyan")
    table.add_column("Metric")
    table.add_column("Records", justify="right")
    table.add_column("Years")
    table.add_column("Last Fetched")

    for row in summary:
        table.add_row(
            row["source"],
            row["metric"],
            f"{row['records']:,}",
            f"{row['min_year']}–{row['max_year']}",
            row["last_fetched"][:16],
        )

    console.print(table)



METRIC_LABELS = {
    "population": "Population",
    "population_change": "Pop. Change",
    "population_change_pct": "Pop. Growth %",
    "employment": "Employment",
    "employment_change": "Job Change",
    "employment_change_pct": "Job Growth %",
    "unemployment_rate": "Unemployment Rate %",
    "avg_annual_pay": "Avg. Annual Pay",
    "avg_weekly_wage": "Avg. Weekly Wage",
}


def _fmt_metric_value(metric: str, value: float) -> str:
    if "pct" in metric or "rate" in metric:
        sign = "+" if "change" in metric else ""
        return f"{value:{sign}.2f}%"
    if metric in ("avg_annual_pay", "avg_weekly_wage"):
        return f"${value:,.0f}"
    return f"{value:,.0f}"


def _print_snapshot_panel(title: str, snapshot) -> None:
    if snapshot is None:
        console.print(f"[dim]{title}: no data[/dim]")
        return

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column(f"{snapshot.year}", justify="right", style="bold")

    if snapshot.population is not None:
        table.add_row("Population", f"{snapshot.population:,}")

    for metric in sorted(snapshot.metrics):
        if metric == "population":  # already shown as geography field
            continue
        label = METRIC_LABELS.get(metric, metric)
        table.add_row(label, _fmt_metric_value(metric, snapshot.metrics[metric]))

    console.print(table)


@cli.command()
@click.argument("address")
@click.option(
    "--auto-fetch", is_flag=True,
    help="Fetch missing data from source APIs on-the-fly (slower first time).",
)
@click.option("--year", type=int, default=None, help="Target year (default: latest available)")
@click.pass_context
def lookup(ctx: click.Context, address: str, auto_fetch: bool, year: int | None) -> None:
    """Look up stats for a US address — metro, city, and county data."""
    from . import api as api_mod

    config: Config = ctx.obj["config"]
    api_mod.configure(db_path=config.storage.db_path)

    try:
        report: LocationReport = api_mod.lookup(
            address, auto_fetch=auto_fetch, year=year,
        )
    except GeocodingError as e:
        console.print(f"[red]Geocoding failed: {e}[/red]")
        return

    console.print()
    console.print(f"[bold]Address:[/bold] {report.matched_address}")
    if report.latitude and report.longitude:
        console.print(
            f"[dim]Coordinates: {report.latitude:.4f}, {report.longitude:.4f}[/dim]"
        )
    if report.tract_geoid:
        console.print(f"[dim]Census tract: {report.tract_geoid}[/dim]")
    console.print()

    _print_snapshot_panel("Metro Area", report.metro)
    _print_snapshot_panel("City", report.city)
    _print_snapshot_panel("County", report.county)

    if report.warnings:
        console.print()
        for w in report.warnings:
            console.print(f"[yellow]⚠ {w}[/yellow]")


@cli.command("init-config")
@click.option("--path", "-p", default="config/settings.yaml", help="Output path")
def init_config(path: str) -> None:
    """Generate a default config file."""
    p = Path(path)
    if p.exists():
        console.print(f"[yellow]{p} already exists, skipping.[/yellow]")
        return
    Config().save(p)
    console.print(f"[green]Config written to {p}[/green]")
