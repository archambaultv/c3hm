from pathlib import Path

import click

from c3hm.unpack import PATHS_TO_DELETE, UnpackOmnivox


@click.command(
    name="unpack",
    help=(
        "Prépare un dossier de travaux téléchargés depuis Omnivox pour la correction. "
        "Fonctionne bien avec l'option Omnivox 'Lister tous les dépôts dans le même répertoire'\n"
        "Cette commande: \n"
        "- dézippe le dossier s'il est encore sous format zip;\n"
        "- dézippe tous les fichiers .zip trouvés dans le dossier;\n"
        "- supprime les dossiers inutiles comme __MACOSX, node_modules, etc.;\n"
        "- raccourcit les noms de fichiers/dossier trop longs générés par Omnivox;\n"
        "- aplatit la structure des dossiers si nécessaire."
    ),
)
@click.argument("path", type=click.Path(file_okay=True, dir_okay=True, path_type=Path), required=True)
@click.option(
    "--git",
    "-g",
    is_flag=True,
    default=False,
    help="Supprimer les dossiers .git et .gitignore en plus des autres fichiers indésirables.",
)
@click.option("--verbose", "-v", is_flag=True, default=False, help="Affiche la progression")
def unpack_command(
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
    UnpackOmnivox(folder=path, paths_to_delete=to_delete, verbose=verbose).unpack()
