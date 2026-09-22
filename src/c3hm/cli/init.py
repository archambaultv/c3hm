from pathlib import Path

import click

from c3hm.storage import Workspace, WorkspaceError


@click.command(name="init", help="Crée un dossier d'évaluation avec un evaluation.yaml modèle.")
@click.argument("directory", type=click.Path(file_okay=False, dir_okay=True, path_type=Path), default=".")
@click.option("--force", "-f", is_flag=True, help="Remplace un evaluation.yaml existant")
def init_command(directory: Path, force: bool):
    workspace = Workspace(directory)
    try:
        workspace.create_evaluation(force=force)
    except WorkspaceError as e:
        raise click.ClickException(str(e)) from e
    click.echo(f"Créé : {workspace.evaluation_path}")
