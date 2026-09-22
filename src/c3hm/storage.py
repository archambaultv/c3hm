"""
Accès aux fichiers d'un dossier d'évaluation (« workspace »).

Un dossier d'évaluation contient :
- evaluation.yaml : cours, session, évaluation, échelle, critères
- etudiants.yaml : liste des étudiants (matricule, prénom, nom, équipe)
- notes/<Nom>_<Prénom>_<matricule>.yaml : par critère (niveau, commentaire, axe de progression),
  commentaire général et note ajustée d'un étudiant
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


def safe_filename(student: Student) -> str:
    """Nom_Prénom_matricule, sans les caractères interdits dans un nom de fichier."""
    parts = [student.surname, student.firstname, student.matricule]
    name = "_".join(p.strip() for p in parts if p.strip())
    return "".join("-" if c in '/\\:*?"<>|' else c for c in name)


def _matricule_of(stem: str) -> str:
    """Le matricule est la dernière partie du nom de fichier (seul, dans l'ancien format)."""
    return stem.rsplit("_", 1)[-1]


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

    # --- notes/<Nom>_<Prénom>_<matricule>.yaml -------------------------------

    def _notes_filename(self, matricule: str) -> str:
        """Nom attendu d'après etudiants.yaml, comme la rétroaction ; le matricule seul si l'étudiant est inconnu."""
        try:
            student = next((s for s in self.load_students() if s.matricule == matricule), None)
        except WorkspaceError:
            student = None
        return f"{safe_filename(student) if student else matricule}.yaml"

    def _existing_notes_path(self, matricule: str) -> Path | None:
        notes_dir = self.root / self.NOTES_DIR
        if not notes_dir.is_dir():
            return None
        return next((p for p in sorted(notes_dir.glob("*.yaml")) if _matricule_of(p.stem) == matricule), None)

    def notes_path(self, matricule: str) -> Path:
        """Fichier de notes existant de l'étudiant (quel que soit son nom), sinon celui à créer."""
        return self._existing_notes_path(matricule) or self.root / self.NOTES_DIR / self._notes_filename(matricule)

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
        """Enregistre sous le nom attendu ; un fichier au nom périmé (ancien format, étudiant renommé) est remplacé."""
        path = self.root / self.NOTES_DIR / self._notes_filename(matricule)
        old = self._existing_notes_path(matricule)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump_yaml(notes.to_dict()), encoding="utf-8")
        if old is not None and old != path:
            old.unlink()

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
        return sorted(_matricule_of(p.stem) for p in notes_dir.glob("*.yaml"))
