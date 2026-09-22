"""
Modèle de données d'une évaluation : échelle de niveaux et critères pondérés.

Les clés YAML sont en français, les attributs Python en anglais.
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from typing import Any

Number = int | float


def normalize_label(text: str) -> str:
    """Normalise une étiquette pour la comparaison : sans accents, sans casse, sans espaces superflus."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return stripped.casefold().strip()


def current_semester() -> str:
    today = date.today()
    if today.month <= 5:
        return f"Hiver {today.year}"
    if today.month <= 7:
        return f"Été {today.year}"
    return f"Automne {today.year}"


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


@dataclass
class Level:
    label: str
    percentage: Number | str  # str seulement lorsque la valeur saisie n'est pas un nombre

    def to_dict(self) -> dict:
        return {"niveau": self.label, "pourcentage": self.percentage}

    @classmethod
    def from_dict(cls, data: Any) -> Level:
        if not isinstance(data, dict):
            raise ValueError(f"Un niveau doit être un dictionnaire, reçu : {data!r}")
        return cls(label=str(data.get("niveau", "") or ""), percentage=data.get("pourcentage", ""))


@dataclass
class Criterion:
    label: str
    weight: Number | str
    descriptors: dict[str, str] = field(default_factory=dict)  # étiquette de niveau -> texte

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"critère": self.label, "pondération": self.weight}
        if self.descriptors:
            d["descripteurs"] = dict(self.descriptors)
        return d

    @classmethod
    def from_dict(cls, data: Any) -> Criterion:
        if not isinstance(data, dict):
            raise ValueError(f"Un critère doit être un dictionnaire, reçu : {data!r}")
        descriptors = data.get("descripteurs") or {}
        if not isinstance(descriptors, dict):
            raise ValueError(f"Les descripteurs du critère {data.get('critère')!r} doivent être un dictionnaire.")
        return cls(
            label=str(data.get("critère", "") or ""),
            weight=data.get("pondération", ""),
            descriptors={str(k): str(v) for k, v in descriptors.items()},
        )


def level_color(level: Level) -> str:
    """Couleur pastel du vert (100 %) au rouge (0 %)."""
    pct = level.percentage if _is_number(level.percentage) else 0
    hue = 120 * max(0, min(100, pct)) / 100
    return f"hsl({hue:.0f}, 70%, 88%)"


def default_scale() -> list[Level]:
    return [
        Level("Avancé", 100),
        Level("Acquis", 75),
        Level("Ça y est presque", 50),
        Level("En apprentissage", 25),
        Level("Non démontré", 0),
    ]


LAYOUTS = ("grille", "liste")


@dataclass
class Evaluation:
    course: str
    session: str
    title: str
    scale: list[Level] = field(default_factory=default_scale)
    criteria: list[Criterion] = field(default_factory=list)
    layout: str = "grille"  # « grille » : un tableau ; « liste » : une fiche par critère

    # --- calculs -------------------------------------------------------------

    def total_weight(self) -> Number:
        return sum(c.weight for c in self.criteria if _is_number(c.weight))

    def level(self, label: str) -> Level | None:
        wanted = normalize_label(label)
        for lvl in self.scale:
            if normalize_label(lvl.label) == wanted:
                return lvl
        return None

    def criterion(self, label: str) -> Criterion | None:
        wanted = normalize_label(label)
        for crit in self.criteria:
            if normalize_label(crit.label) == wanted:
                return crit
        return None

    # --- validation ----------------------------------------------------------

    def validate(self) -> list[str]:
        """Retourne la liste des erreurs (vide si l'évaluation est valide)."""
        errors: list[str] = []
        for value, name in ((self.course, "cours"), (self.session, "session"), (self.title, "évaluation")):
            if not value or not value.strip():
                errors.append(f"Le champ « {name} » ne peut pas être vide.")

        if not self.scale:
            errors.append("L'échelle doit contenir au moins un niveau.")
        seen: set[str] = set()
        for idx, lvl in enumerate(self.scale, start=1):
            if not lvl.label.strip():
                errors.append(f"Le niveau n° {idx} n'a pas de nom.")
            elif normalize_label(lvl.label) in seen:
                errors.append(f"Le niveau « {lvl.label} » apparaît plus d'une fois.")
            else:
                seen.add(normalize_label(lvl.label))
            if not _is_number(lvl.percentage) or not 0 <= lvl.percentage <= 100:
                errors.append(f"Le pourcentage du niveau « {lvl.label or idx} » doit être un nombre entre 0 et 100.")

        if self.layout not in LAYOUTS:
            errors.append(f"L'affichage doit être « grille » ou « liste », pas « {self.layout} ».")

        if not self.criteria:
            errors.append("L'évaluation doit contenir au moins un critère.")
        seen = set()
        for idx, crit in enumerate(self.criteria, start=1):
            name = crit.label.strip() or f"n° {idx}"
            if not crit.label.strip():
                errors.append(f"Le critère n° {idx} n'a pas de nom.")
            elif normalize_label(crit.label) in seen:
                errors.append(f"Le critère « {crit.label} » apparaît plus d'une fois.")
            else:
                seen.add(normalize_label(crit.label))
            if not _is_number(crit.weight) or crit.weight < 0:
                errors.append(f"La pondération du critère « {name} » doit être un nombre positif.")
            for level_label in crit.descriptors:
                if self.level(level_label) is None:
                    errors.append(f"Le critère « {name} » a un descripteur pour le niveau inconnu « {level_label} ».")
        if self.criteria and all(_is_number(c.weight) for c in self.criteria):
            total = self.total_weight()
            if abs(total - 100) > 1e-6:
                errors.append(f"La somme des pondérations doit être 100, elle est de {total:g}.")
        return errors

    def is_valid(self) -> bool:
        return not self.validate()

    # --- sérialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "cours": self.course,
            "session": self.session,
            "évaluation": self.title,
            "affichage": self.layout,
            "échelle": [lvl.to_dict() for lvl in self.scale],
            "critères": [c.to_dict() for c in self.criteria],
        }

    @classmethod
    def from_dict(cls, data: Any) -> Evaluation:
        if not isinstance(data, dict):
            raise ValueError("Le fichier d'évaluation doit contenir un dictionnaire YAML.")
        scale_data = data.get("échelle")
        if scale_data is None:
            scale = default_scale()
        elif isinstance(scale_data, list):
            scale = [Level.from_dict(d) for d in scale_data]
        else:
            raise ValueError("La clé « échelle » doit être une liste de niveaux.")
        criteria_data = data.get("critères") or []
        if not isinstance(criteria_data, list):
            raise ValueError("La clé « critères » doit être une liste de critères.")
        return cls(
            course=str(data.get("cours", "") or ""),
            session=str(data.get("session", "") or ""),
            title=str(data.get("évaluation", "") or ""),
            layout=str(data.get("affichage") or "grille"),
            scale=scale,
            criteria=[Criterion.from_dict(d) for d in criteria_data],
        )

    @classmethod
    def template(cls) -> Evaluation:
        return cls(
            course="420-XXX-MA",
            session=current_semester(),
            title="TP1",
            scale=default_scale(),
            criteria=[
                Criterion(
                    "Critère 1",
                    50,
                    {
                        "Acquis": "Ce qui est attendu pour que le critère soit acquis.",
                        "Avancé": "Ce qu'il faut en plus pour dépasser les attentes.",
                    },
                ),
                Criterion("Critère 2", 50, {"Acquis": "Ce qui est attendu pour que le critère soit acquis."}),
            ],
        )


# --- étudiants ---------------------------------------------------------------


@dataclass
class Student:
    matricule: str
    firstname: str
    surname: str
    team: str | None = None

    def fullname(self, surname_first: bool = False) -> str:
        parts = [self.surname, self.firstname] if surname_first else [self.firstname, self.surname]
        return " ".join(p.strip() for p in parts if p.strip())

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"matricule": self.matricule, "prénom": self.firstname, "nom": self.surname}
        if self.team:
            d["équipe"] = self.team
        return d

    @classmethod
    def from_dict(cls, data: Any) -> Student:
        if not isinstance(data, dict):
            raise ValueError(f"Un étudiant doit être un dictionnaire, reçu : {data!r}")
        team = data.get("équipe")
        return cls(
            matricule=str(data.get("matricule", "") or "").strip(),
            firstname=str(data.get("prénom", "") or "").strip(),
            surname=str(data.get("nom", "") or "").strip(),
            team=str(team).strip() if team not in (None, "") else None,
        )


def sort_students(students: list[Student]) -> list[Student]:
    return sorted(students, key=lambda s: (normalize_label(s.surname), normalize_label(s.firstname), s.matricule))


# --- notes -------------------------------------------------------------------


def round_half_up(value: float) -> int:
    return int(math.floor(value + 0.5))


def _get_normalized(mapping: dict[str, str], key: str) -> str | None:
    wanted = normalize_label(key)
    for k, v in mapping.items():
        if normalize_label(k) == wanted:
            return v
    return None


def _set_normalized(mapping: dict[str, str], key: str, value: str | None) -> None:
    wanted = normalize_label(key)
    for k in [k for k in mapping if normalize_label(k) == wanted]:
        del mapping[k]
    if value:
        mapping[key] = value


@dataclass
class Notes:
    """Notes d'un étudiant (ou d'une équipe) : niveau et commentaire par critère, commentaire global, note ajustée."""

    levels: dict[str, str] = field(default_factory=dict)  # critère -> niveau
    comments: dict[str, str] = field(default_factory=dict)  # critère -> commentaire
    comment: str = ""
    override: Number | str | None = None  # note ajustée

    def level_for(self, criterion_label: str) -> str | None:
        return _get_normalized(self.levels, criterion_label)

    def comment_for(self, criterion_label: str) -> str:
        return _get_normalized(self.comments, criterion_label) or ""

    def set_level(self, criterion_label: str, level_label: str | None) -> None:
        _set_normalized(self.levels, criterion_label, level_label)

    def set_comment(self, criterion_label: str, text: str | None) -> None:
        _set_normalized(self.comments, criterion_label, (text or "").strip() or None)

    def has_override(self) -> bool:
        return _is_number(self.override)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"niveaux": dict(self.levels)}
        if self.comments:
            d["commentaires"] = dict(self.comments)
        if self.comment.strip():
            d["commentaire"] = self.comment
        if self.override not in (None, ""):
            d["note ajustée"] = self.override
        return d

    @classmethod
    def from_dict(cls, data: Any) -> Notes:
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("Le fichier de notes doit contenir un dictionnaire YAML.")
        levels = data.get("niveaux") or {}
        comments = data.get("commentaires") or {}
        if not isinstance(levels, dict):
            raise ValueError("La clé « niveaux » doit être un dictionnaire critère -> niveau.")
        if not isinstance(comments, dict):
            raise ValueError("La clé « commentaires » doit être un dictionnaire critère -> commentaire.")
        override = data.get("note ajustée")
        return cls(
            levels={str(k): str(v) for k, v in levels.items() if v not in (None, "")},
            comments={str(k): str(v) for k, v in comments.items() if v not in (None, "")},
            comment=str(data.get("commentaire") or ""),
            override=None if override in (None, "") else override,
        )


@dataclass
class CriterionResult:
    criterion: Criterion
    level: Level | None
    score: float | None  # pondération × pourcentage / 100


@dataclass
class GradeResult:
    results: list[CriterionResult]
    computed: float | None  # somme des scores, None si un critère n'est pas noté
    final: int | float | None  # note ajustée si présente, sinon arrondi de computed
    complete: bool

    def result_for(self, criterion: Criterion) -> CriterionResult | None:
        return next((r for r in self.results if r.criterion is criterion), None)


def compute_grade(evaluation: Evaluation, notes: Notes) -> GradeResult:
    results: list[CriterionResult] = []
    for crit in evaluation.criteria:
        label = notes.level_for(crit.label)
        level = evaluation.level(label) if label else None
        if level is None or not _is_number(crit.weight) or not _is_number(level.percentage):
            results.append(CriterionResult(crit, level, None))
        else:
            results.append(CriterionResult(crit, level, crit.weight * level.percentage / 100))
    all_graded = bool(results) and all(r.score is not None for r in results)
    computed = sum(r.score for r in results) if all_graded else None  # type: ignore[misc]
    if notes.has_override():
        final: int | float | None = notes.override  # type: ignore[assignment]
    else:
        final = round_half_up(computed) if computed is not None else None
    return GradeResult(results, computed, final, complete=all_graded or notes.has_override())


def invalid_references(evaluation: Evaluation, notes: Notes) -> list[str]:
    """Critères ou niveaux utilisés dans les notes mais absents de l'évaluation."""
    problems: list[str] = []
    for crit_label, level_label in notes.levels.items():
        crit = evaluation.criterion(crit_label)
        if crit is None:
            problems.append(f"critère inconnu « {crit_label} »")
        elif evaluation.level(level_label) is None:
            problems.append(f"niveau inconnu « {level_label} » pour « {crit_label} »")
    for crit_label in notes.comments:
        if evaluation.criterion(crit_label) is None:
            problems.append(f"critère inconnu « {crit_label} » (commentaire)")
    return problems


def merge_notes(team: Notes, own: Notes) -> Notes:
    """Notes effectives d'un étudiant en équipe : celles de l'équipe, remplacées par les siennes là où il en a."""
    levels = dict(team.levels)
    for k, v in own.levels.items():
        _set_normalized(levels, k, v)
    comments = dict(team.comments)
    for k, v in own.comments.items():
        _set_normalized(comments, k, v)
    return Notes(
        levels=levels,
        comments=comments,
        comment=own.comment if own.comment.strip() else team.comment,
        override=own.override,
    )


def teams(students: list[Student]) -> dict[str, list[Student]]:
    """Équipes (nom -> membres triés), dans l'ordre alphabétique des noms d'équipe."""
    result: dict[str, list[Student]] = {}
    for s in sort_students(students):
        if s.team:
            result.setdefault(s.team, []).append(s)
    return dict(sorted(result.items(), key=lambda kv: normalize_label(kv[0])))
