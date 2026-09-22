from pathlib import Path

import click

from c3hm.export import ExportError, export_all
from c3hm.storage import Workspace, WorkspaceError


@click.command(
    name="export",
    help="Écrit dans sortie/ : le tableur Omnivox, les rétroactions PDF et la grille vierge (Markdown et PDF).",
)
@click.argument("directory", type=click.Path(file_okay=False, dir_okay=True, path_type=Path), default=".")
def export_command(directory: Path):
    try:
        report = export_all(Workspace(directory))
    except (ExportError, WorkspaceError) as e:
        raise click.ClickException(str(e)) from e
    click.echo(f"{len(report.exported)} étudiant(s) exporté(s) dans {report.output_dir}")
    click.echo(f"{report.pdf_count} rétroaction(s) PDF, grille en Markdown et en PDF")
    if report.skipped:
        click.echo("Correction incomplète, ignoré(s) : " + ", ".join(report.skipped))
