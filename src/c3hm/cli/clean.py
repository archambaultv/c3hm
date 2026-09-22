from pathlib import Path

import click

from c3hm.clean import Cleaner
from c3hm.unpack import PATHS_TO_DELETE


@click.command(name="clean", help=("Supprime les dossiers inutiles comme __MACOSX, node_modules, etc."))
@click.argument("path", type=click.Path(file_okay=False, dir_okay=True, path_type=Path), required=True)
@click.option(
    "--git",
    "-g",
    is_flag=True,
    default=False,
    help="Supprimer les dossiers .git et .gitignore en plus des autres fichiers indésirables.",
)
@click.option("--verbose", "-v", is_flag=True, default=False, help="Affiche la progression")
def clean_command(
    path: Path,
    git: bool,
    verbose: bool,
):
    """
    Supprime les fichiers et dossiers indésirables et renomme les dossiers étudiants
    """
    to_delete = PATHS_TO_DELETE
    if git:
        to_delete.extend([".git", ".gitignore"])
    Cleaner(folder=path, paths_to_delete=to_delete, verbose=verbose).clean_folders()
