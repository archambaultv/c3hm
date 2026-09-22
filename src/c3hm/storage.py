"""
Accès aux fichiers d'un dossier d'évaluation (« workspace »).

Un dossier d'évaluation contient :
- evaluation.yaml : cours, session, évaluation, échelle, critères
- etudiants.yaml : liste des étudiants (matricule, prénom, nom, équipe)
- notes/<matricule>.yaml : niveaux, commentaires et note ajustée d'un étudiant
- notes/equipes/<équipe>.yaml : niveaux et commentaires d'une équipe, hérités par ses membres
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from c3hm.model import Evaluation, Notes, Student, sort_students


class WorkspaceError(Exception):
    """Erreur de lecture d'un fichier du dossier d'évaluation, avec un message destiné à l'utilisateur."""


class _Dumper(yaml.SafeDumper):
    pass


def _represent_str(dumper: yaml.SafeDumper, value: str):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_Dumper.add_representer(str, _represent_str)


def dump_yaml(data: Any) -> str:
    return yaml.dump(data, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=120)


def load_yaml(text: str) -> Any:
    return yaml.safe_load(text)


class Workspace:
    EVALUATION_FILE = "evaluation.yaml"
    STUDENTS_FILE = "etudiants.yaml"
    NOTES_DIR = "notes"
    TEAMS_DIR = "equipes"

    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()

    # --- evaluation.yaml -----------------------------------------------------

    @property
    def evaluation_path(self) -> Path:
        return self.root / self.EVALUATION_FILE

    def has_evaluation(self) -> bool:
        return self.evaluation_path.is_file()

    def read_evaluation_text(self) -> str:
        return self.evaluation_path.read_text(encoding="utf-8")

    def load_evaluation(self) -> Evaluation:
        """Charge evaluation.yaml sans le valider (utiliser Evaluation.validate())."""
        if not self.has_evaluation():
            raise WorkspaceError(f"Le fichier {self.EVALUATION_FILE} n'existe pas dans {self.root}.")
        try:
            data = load_yaml(self.read_evaluation_text())
        except yaml.YAMLError as e:
            raise WorkspaceError(f"{self.EVALUATION_FILE} : YAML invalide. {e}") from e
        try:
            return Evaluation.from_dict(data)
        except ValueError as e:
            raise WorkspaceError(f"{self.EVALUATION_FILE} : {e}") from e

    def save_evaluation(self, evaluation: Evaluation) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.evaluation_path.write_text(dump_yaml(evaluation.to_dict()), encoding="utf-8")

    def create_evaluation(self, force: bool = False) -> Evaluation:
        if self.has_evaluation() and not force:
            raise WorkspaceError(f"Le fichier {self.EVALUATION_FILE} existe déjà dans {self.root}.")
        evaluation = Evaluation.template()
        self.save_evaluation(evaluation)
        return evaluation

    # --- etudiants.yaml ------------------------------------------------------

    @property
    def students_path(self) -> Path:
        return self.root / self.STUDENTS_FILE

    def has_students(self) -> bool:
        return self.students_path.is_file()

    def load_students(self) -> list[Student]:
        """Charge etudiants.yaml ; liste vide si le fichier n'existe pas."""
        if not self.has_students():
            return []
        try:
            data = load_yaml(self.students_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise WorkspaceError(f"{self.STUDENTS_FILE} : YAML invalide. {e}") from e
        if data is None:
            return []
        if not isinstance(data, list):
            raise WorkspaceError(f"{self.STUDENTS_FILE} : le fichier doit contenir une liste d'étudiants.")
        try:
            return sort_students([Student.from_dict(d) for d in data])
        except ValueError as e:
            raise WorkspaceError(f"{self.STUDENTS_FILE} : {e}") from e

    def save_students(self, students: list[Student]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        data = [s.to_dict() for s in sort_students(students)]
        self.students_path.write_text(dump_yaml(data), encoding="utf-8")

    # --- notes/<matricule>.yaml ----------------------------------------------

    def notes_path(self, matricule: str) -> Path:
        return self.root / self.NOTES_DIR / f"{matricule}.yaml"

    def load_notes(self, matricule: str) -> Notes:
        """Charge les notes d'un étudiant ; notes vides si le fichier n'existe pas."""
        path = self.notes_path(matricule)
        if not path.is_file():
            return Notes()
        try:
            data = load_yaml(path.read_text(encoding="utf-8"))
            return Notes.from_dict(data)
        except yaml.YAMLError as e:
            raise WorkspaceError(f"{path.name} : YAML invalide. {e}") from e
        except ValueError as e:
            raise WorkspaceError(f"{path.name} : {e}") from e

    def save_notes(self, matricule: str, notes: Notes) -> None:
        path = self.notes_path(matricule)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump_yaml(notes.to_dict()), encoding="utf-8")

    # --- notes/equipes/<équipe>.yaml -----------------------------------------

    def team_notes_path(self, team: str) -> Path:
        if not team.strip() or any(c in team for c in "/\\") or team.startswith("."):
            raise WorkspaceError(f"Nom d'équipe invalide : « {team} ».")
        return self.root / self.NOTES_DIR / self.TEAMS_DIR / f"{team.strip()}.yaml"

    def load_team_notes(self, team: str) -> Notes:
        path = self.team_notes_path(team)
        if not path.is_file():
            return Notes()
        try:
            return Notes.from_dict(load_yaml(path.read_text(encoding="utf-8")))
        except yaml.YAMLError as e:
            raise WorkspaceError(f"equipes/{path.name} : YAML invalide. {e}") from e
        except ValueError as e:
            raise WorkspaceError(f"equipes/{path.name} : {e}") from e

    def save_team_notes(self, team: str, notes: Notes) -> None:
        path = self.team_notes_path(team)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump_yaml(notes.to_dict()), encoding="utf-8")

    def team_notes_names(self) -> list[str]:
        """Équipes ayant un fichier de notes."""
        teams_dir = self.root / self.NOTES_DIR / self.TEAMS_DIR
        if not teams_dir.is_dir():
            return []
        return sorted(p.stem for p in teams_dir.glob("*.yaml"))

    def notes_matricules(self) -> list[str]:
        """Matricules ayant un fichier de notes."""
        notes_dir = self.root / self.NOTES_DIR
        if not notes_dir.is_dir():
            return []
        return sorted(p.stem for p in notes_dir.glob("*.yaml"))

    def notes_version(self, matricule: str | None = None, team: str | None = None) -> str:
        """Jeton qui change dès que evaluation.yaml, les notes de l'étudiant ou celles de son équipe changent."""
        own = _mtime(self.notes_path(matricule)) if matricule else 0
        team_mtime = _mtime(self.team_notes_path(team)) if team else 0
        return f"{_mtime(self.evaluation_path)}-{own}-{team_mtime}"


def _mtime(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except FileNotFoundError:
        return 0
