from pathlib import Path

import click

from c3hm.web import run_server


@click.command(
    name="serve", help="Lance l'interface web pour un dossier d'évaluation (par défaut : le dossier courant)."
)
@click.argument("directory", type=click.Path(file_okay=False, dir_okay=True, path_type=Path), default=".")
@click.option("--port", "-p", type=int, default=5000, help="Port du serveur (défaut : 5000)")
@click.option("--no-browser", is_flag=True, help="Ne pas ouvrir le navigateur automatiquement")
def serve_command(directory: Path, port: int, no_browser: bool):
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    click.echo(f"c3hm : http://localhost:{port}  ({directory})")
    run_server(root=directory, port=port, open_browser=not no_browser)
