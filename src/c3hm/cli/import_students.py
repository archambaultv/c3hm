from pathlib import Path

import click

from c3hm.omnivox import OmnivoxError, decode_csv, merge_students, parse_students_csv
from c3hm.storage import Workspace, WorkspaceError


@click.command(name="import-students", help="Importe la liste d'étudiants Omnivox (CSV) dans etudiants.yaml.")
@click.argument("csv_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("directory", type=click.Path(file_okay=False, dir_okay=True, path_type=Path), default=".")
def import_students_command(csv_file: Path, directory: Path):
    workspace = Workspace(directory)
    try:
        text = decode_csv(csv_file.read_bytes())
        imported = parse_students_csv(text)
        merged, new_count = merge_students(workspace.load_students(), imported)
        workspace.save_students(merged)
    except (OmnivoxError, WorkspaceError) as e:
        raise click.ClickException(str(e)) from e
    click.echo(f"{len(imported)} étudiant(s) lus, {new_count} nouveau(x). Enregistré : {workspace.students_path}")
