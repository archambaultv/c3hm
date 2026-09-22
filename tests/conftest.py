"""Fixtures communes : un dossier d'évaluation complet, en mémoire sur disque temporaire."""

import pytest

from c3hm.model import Criterion, Evaluation, Level, Notes, Student
from c3hm.storage import Workspace
from c3hm.web import create_app


@pytest.fixture
def evaluation() -> Evaluation:
    return Evaluation(
        course="420-5D2-MA",
        session="Automne 2026",
        title="TP1",
        scale=[Level("Avancé", 100), Level("Acquis", 75), Level("Non démontré", 0)],
        criteria=[
            Criterion("Qualité du code", 30, {"Acquis": "Lisible.", "Avancé": "Et robuste."}),
            Criterion("Fonctionnalités", 50, {"Acquis": "Tout marche."}),
            Criterion("Tests", 20, {}),
        ],
    )


@pytest.fixture
def students() -> list[Student]:
    return [
        Student("1111111", "Alice", "Tremblay", team="A"),
        Student("2222222", "Bob", "Roy", team="A"),
        Student("3333333", "Chloé", "Gagnon"),
    ]


@pytest.fixture
def workspace(tmp_path, evaluation, students) -> Workspace:
    ws = Workspace(tmp_path)
    ws.save_evaluation(evaluation)
    ws.save_students(students)
    return ws


@pytest.fixture
def graded_workspace(workspace) -> Workspace:
    """Une équipe notée, un membre qui dévie, une étudiante seule notée."""
    workspace.save_team_notes(
        "A",
        Notes(
            levels={"Qualité du code": "Acquis", "Fonctionnalités": "Avancé", "Tests": "Acquis"},
            comments={"Tests": "Peu de cas d'erreur."},
            comment="Bon travail d'équipe.",
        ),
    )
    workspace.save_notes("1111111", Notes(levels={"Tests": "Non démontré"}))
    workspace.save_notes(
        "3333333",
        Notes(
            levels={"Qualité du code": "Avancé", "Fonctionnalités": "Acquis", "Tests": "Acquis"},
            comment="Excellent.",
        ),
    )
    return workspace


@pytest.fixture
def client(workspace):
    app = create_app(workspace)
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def graded_client(graded_workspace):
    app = create_app(graded_workspace)
    app.config["TESTING"] = True
    return app.test_client()
