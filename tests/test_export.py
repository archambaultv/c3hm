"""Exports : tableur Omnivox, rétroaction PDF, grille, nettoyage du dossier."""

from c3hm.export import export_all, export_notes, omnivox_rows, ready_grades, rubric_markdown
from c3hm.model import Student


def test_seuls_les_etudiants_notes_sont_exportes(graded_workspace):
    rapport = export_notes(graded_workspace)
    assert sorted(rapport.exported) == ["Alice Tremblay", "Bob Roy", "Chloé Gagnon"]
    assert rapport.skipped == []
    assert rapport.pdf_count == 3

    graded_workspace.save_students([*graded_workspace.load_students(), Student("4444444", "David", "Nguyen")])
    rapport = export_notes(graded_workspace)
    assert rapport.skipped == ["David Nguyen"]


def test_colonnes_a_coller_dans_omnivox(graded_workspace):
    lignes = omnivox_rows(ready_grades(graded_workspace))
    par_matricule = {ligne.split("\t")[0]: ligne.split("\t") for ligne in lignes.splitlines()}
    # Alice hérite de l'équipe sauf pour les tests : 22.5 + 50 + 0 = 72.5 -> 73
    assert par_matricule["1111111"][1] == "73"
    # le commentaire tient sur une seule ligne, sinon l'import Omnivox casse
    assert all(len(colonnes) == 3 for colonnes in par_matricule.values())


def test_export_vide_le_dossier_de_sortie(graded_workspace):
    export_all(graded_workspace)
    reste = graded_workspace.root / "sortie" / "retroaction" / "Roy_Bob_2222222.pdf"
    assert reste.is_file()

    graded_workspace.save_students([s for s in graded_workspace.load_students() if s.matricule != "2222222"])
    export_all(graded_workspace)
    assert not reste.exists()  # la rétroaction d'un étudiant retiré ne traîne pas


def test_grille_en_markdown_selon_laffichage(evaluation):
    assert "| Critère |" in rubric_markdown(evaluation)  # tableau

    evaluation.layout = "liste"
    texte = rubric_markdown(evaluation)
    assert "## Qualité du code (30 %)" in texte  # sections
    assert "**Acquis (75 %)**" in texte
