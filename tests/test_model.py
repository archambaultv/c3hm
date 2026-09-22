"""Calcul des notes, héritage d'équipe, validation de la grille."""

import pytest

from c3hm.model import Notes, compute_grade, invalid_references, merge_notes


def test_note_calculee_et_arrondie(evaluation):
    notes = Notes(levels={"Qualité du code": "Acquis", "Fonctionnalités": "Avancé", "Tests": "Acquis"})
    grade = compute_grade(evaluation, notes)
    assert grade.computed == pytest.approx(22.5 + 50 + 15)  # 87.5
    assert grade.final == 88
    assert grade.complete


def test_note_incomplete_tant_quun_critere_manque(evaluation):
    grade = compute_grade(evaluation, Notes(levels={"Tests": "Acquis"}))
    assert grade.final is None
    assert not grade.complete


def test_niveaux_ecrits_a_la_main_sans_accents(evaluation):
    notes = Notes(levels={"qualite du code": "acquis", "Fonctionnalités": "AVANCE", "Tests": "Acquis"})
    assert compute_grade(evaluation, notes).final == 88


def test_note_ajustee_remplace_le_calcul(evaluation):
    grade = compute_grade(evaluation, Notes(levels={"Qualité du code": "Acquis"}, override=61.5))
    assert grade.final == 61.5
    assert grade.complete  # une note ajustée suffit : la correction est faite


def test_heritage_dequipe():
    equipe = Notes(levels={"A": "Acquis", "B": "Avancé"}, comments={"A": "équipe"}, comment="général équipe")
    perso = Notes(levels={"B": "Non démontré"}, comments={"B": "perso"}, override=50)
    fusion = merge_notes(equipe, perso)
    assert fusion.level_for("A") == "Acquis"  # hérité
    assert fusion.level_for("B") == "Non démontré"  # remplacé
    assert (fusion.comment_for("A"), fusion.comment_for("B")) == ("équipe", "perso")
    assert fusion.comment == "général équipe"  # pas de commentaire personnel
    assert fusion.override == 50  # jamais hérité


def test_grille_invalide_est_signalee(evaluation):
    evaluation.criteria[0].weight = 40  # la somme fait 110
    evaluation.criteria[1].descriptors["Expert"] = "niveau qui n'existe pas"
    erreurs = evaluation.validate()
    assert any("100" in e for e in erreurs)
    assert any("Expert" in e for e in erreurs)


def test_renommer_un_critere_ou_un_niveau_invalide_les_notes(evaluation):
    notes = Notes(levels={"Qualité du code": "Acquis"})
    assert invalid_references(evaluation, notes) == []
    evaluation.scale[1].label = "Réussi"
    assert invalid_references(evaluation, notes)
