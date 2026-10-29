"""Commandes en ligne."""

from click.testing import CliRunner

from c3hm.cli.cli import cli
from c3hm.model import Notes


def test_create_notes_nouvelles_seulement_sauf_avec_force(workspace):
    runner = CliRunner()
    resultat = runner.invoke(cli, ["create-notes", str(workspace.root)])
    assert resultat.exit_code == 0 and "4 fichier(s)" in resultat.output

    workspace.save_notes("3333333", Notes(comment="Excellent."))
    runner.invoke(cli, ["create-notes", str(workspace.root)])
    assert workspace.load_notes("3333333").comment == "Excellent."

    resultat = runner.invoke(cli, ["create-notes", str(workspace.root), "--force"])
    assert resultat.exit_code == 0 and workspace.load_notes("3333333") == Notes()


def test_create_notes_sans_evaluation(tmp_path):
    resultat = CliRunner().invoke(cli, ["create-notes", str(tmp_path)])
    assert resultat.exit_code != 0 and "evaluation.yaml" in resultat.output
