import click

from c3hm.cli.clean import clean_command
from c3hm.cli.export import export_command
from c3hm.cli.import_students import import_students_command
from c3hm.cli.init import init_command
from c3hm.cli.server import serve_command
from c3hm.cli.unpack import unpack_command


@click.group(help="c3hm — Corriger à 3 heures du matin")
def cli():
    """Point d'entrée principal pour la CLI de c3hm."""


cli.add_command(init_command)
cli.add_command(serve_command)
cli.add_command(import_students_command)
cli.add_command(export_command)
cli.add_command(unpack_command)
cli.add_command(clean_command)


def main():
    cli()
