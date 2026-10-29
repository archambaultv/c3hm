from pathlib import Path

import click

from c3hm.storage import Workspace, WorkspaceError


@click.command(
    name="create-notes",
    help="Crée les fichiers de notes vides des étudiants et des équipes d'etudiants.yaml qui n'en ont pas.",
)
@click.argument("directory", type=click.Path(file_okay=False, dir_okay=True, path_type=Path), default=".")
@click.option("--force", "-f", is_flag=True, help="Remplace aussi les fichiers existants par des fichiers vides")
def create_notes_command(directory: Path, force: bool):
    workspace = Workspace(directory)
    try:
        if not any(c.label for c in workspace.load_evaluation().criteria):
            raise click.ClickException(f"{Workspace.EVALUATION_FILE} : aucun critère.")
        students = workspace.load_students()
    except WorkspaceError as e:
        raise click.ClickException(str(e)) from e
    if not students:
        raise click.ClickException(f"Aucun étudiant dans {workspace.students_path}.")
    written = workspace.create_notes(force=force)
    click.echo(f"{len(written)} fichier(s) de notes écrit(s) dans {workspace.root / Workspace.NOTES_DIR}")
