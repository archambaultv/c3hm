"""Lecture et écriture des fichiers YAML, import de la liste Omnivox."""

import pytest

from c3hm.model import Notes, Student
from c3hm.omnivox import merge_students, parse_students_csv
from c3hm.storage import Workspace, WorkspaceError


def test_aller_retour_des_fichiers(workspace, evaluation):
    assert workspace.load_evaluation() == evaluation

    notes = Notes(levels={"Tests": "Acquis"}, comment="ligne 1\nligne 2\n")
    workspace.save_notes("1111111", notes)
    assert workspace.load_notes("1111111") == notes
    # un commentaire multiligne reste lisible et modifiable à la main
    assert "commentaire: |" in workspace.notes_path("1111111").read_text(encoding="utf-8")


def test_fichier_illisible_donne_un_message_clair(workspace):
    workspace.evaluation_path.write_text("cours: [oops", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="YAML invalide"):
        workspace.load_evaluation()


def test_grille_modifiee_a_la_main_se_charge_sans_etre_valide(workspace):
    workspace.evaluation_path.write_text("cours: X\ncritères:\n- critère: A\n  pondération: abc\n", encoding="utf-8")
    evaluation = workspace.load_evaluation()
    assert evaluation.criteria[0].weight == "abc"
    assert evaluation.validate()  # lisible, mais signalée comme incomplète


def test_lecture_du_csv_omnivox():
    csv = "No de dossier;Nom de l'étudiant;Prénom de l'étudiant;Courriel\n=\"1234567\";Tremblay;Alice;a@x\n"
    assert parse_students_csv(csv) == [Student("1234567", "Alice", "Tremblay")]


def test_reimporter_met_a_jour_les_noms_et_garde_les_equipes():
    existants = [Student("1", "Alice", "Tremblay", team="A")]
    fusion, nouveaux = merge_students(existants, [Student("1", "Alice-Marie", "Tremblay"), Student("2", "Bob", "Roy")])
    assert nouveaux == 1
    assert (fusion[0].firstname, fusion[0].team) == ("Alice-Marie", "A")


def test_dossier_sans_fichiers(tmp_path):
    vide = Workspace(tmp_path)
    assert not vide.has_evaluation()
    assert vide.load_students() == []
    assert vide.load_notes("1234567") == Notes()
