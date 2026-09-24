"""
Rendu Markdown des descripteurs et des commentaires.

Les descripteurs sont écrits par l'enseignant : listes, gras, liens. Le HTML
produit est affiché dans l'interface et dans les PDF. Il est assaini : un
commentaire contenant du HTML brut (attributs d'événement, <script>, liens
javascript:) ne doit pas s'exécuter dans le navigateur.
"""

from __future__ import annotations

import nh3
from markdown import Markdown
from markupsafe import Markup

# Pas de « nl2br » : les descripteurs longs sont écrits avec des lignes repliées,
# qui doivent se rejoindre en un paragraphe comme le veut Markdown.
_renderer = Markdown()


def render_markdown(text: str | None) -> Markup:
    if not text or not text.strip():
        return Markup("")
    _renderer.reset()
    return Markup(nh3.clean(_renderer.convert(text)))
