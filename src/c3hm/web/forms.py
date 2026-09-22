"""
Conversion entre le formulaire HTML de l'éditeur d'évaluation et le modèle.

Les champs du formulaire sont indexés séquentiellement dans l'ordre d'affichage :
- niveau-<j>-nom, niveau-<j>-pct
- critere-<i>-nom, critere-<i>-pond, critere-<i>-desc-<j>
Les descripteurs sont indexés par position de niveau, ce qui permet de renommer
un niveau sans perdre son texte.
"""

from __future__ import annotations

from collections.abc import Mapping

from c3hm.model import Criterion, Evaluation, Level, default_scale


def parse_number(raw: str) -> int | float | str:
    """Convertit une saisie en nombre ; retourne la chaîne brute si ce n'est pas un nombre."""
    text = raw.strip().replace(",", ".")
    if text == "":
        return ""
    try:
        value = float(text)
    except ValueError:
        return raw.strip()
    return int(value) if value.is_integer() else value


def parse_evaluation_form(form: Mapping[str, str]) -> Evaluation:
    levels: list[Level] = []
    j = 0
    while f"niveau-{j}-nom" in form:
        levels.append(Level(form[f"niveau-{j}-nom"].strip(), parse_number(form.get(f"niveau-{j}-pct", ""))))
        j += 1

    criteria: list[Criterion] = []
    i = 0
    while f"critere-{i}-nom" in form:
        descriptors: dict[str, str] = {}
        for jj, lvl in enumerate(levels):
            text = form.get(f"critere-{i}-desc-{jj}", "").strip()
            if text and lvl.label:
                descriptors[lvl.label] = text
        criteria.append(
            Criterion(form[f"critere-{i}-nom"].strip(), parse_number(form.get(f"critere-{i}-pond", "")), descriptors)
        )
        i += 1

    return Evaluation(
        course=form.get("cours", "").strip(),
        session=form.get("session", "").strip(),
        title=form.get("evaluation", "").strip(),
        layout=form.get("affichage", "grille").strip(),
        scale=levels,
        criteria=criteria,
    )


def apply_action(evaluation: Evaluation, action: str) -> None:
    """Applique une action de structure (ajouter, retirer, déplacer) au modèle, en place."""
    name, _, arg = action.partition(":")
    idx = int(arg) if arg.isdigit() else None

    if name == "niveau-ajouter":
        evaluation.scale.append(Level("", ""))
    elif name == "echelle-defaut":
        evaluation.scale = default_scale()
    elif name == "critere-ajouter":
        evaluation.criteria.append(Criterion("", "", {}))
    elif idx is not None:
        items = evaluation.scale if name.startswith("niveau-") else evaluation.criteria
        if not 0 <= idx < len(items):
            return
        if name.endswith("-retirer"):
            del items[idx]
        elif name.endswith("-monter") and idx > 0:
            items[idx - 1], items[idx] = items[idx], items[idx - 1]
        elif name.endswith("-descendre") and idx < len(items) - 1:
            items[idx + 1], items[idx] = items[idx], items[idx + 1]
