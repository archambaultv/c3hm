# c3hm

Outil de correction avec interface web locale.

## Installation

Un fois ce dépôt cloné, installez les dépendances et l'outil lui-même dans un
environnement virtuel Python :

```sh
uv tool install .
```

## Commandes

```bash
c3hm init [DOSSIER]                 # crée evaluation.yaml (défaut : dossier courant)
c3hm import-students CSV [DOSSIER]  # liste Omnivox (CSV) vers etudiants.yaml
c3hm export [DOSSIER]               # sortie/ : notes Omnivox, rétroactions PDF, grille vierge
c3hm unpack DOSSIER                 # décompresse et nettoie les remises Omnivox
c3hm clean DOSSIER                  # supprime node_modules, .venv, etc.
c3hm serve [DOSSIER] [-p PORT]      # interface web sur http://localhost:5000
```

Un dossier correspond à une évaluation.

```
tp1/
├── evaluation.yaml          cours, session, affichage, échelle, critères pondérés
├── etudiants.yaml           matricule, prénom, nom, équipe
├── notes/
│   ├── equipes/
│   │   └── A.yaml           notes et commentaires de l'équipe A
│   ├── Tremblay_Alice_1234567.yaml   notes et commentaires d'un étudiant
│   └── Roy_Bob_2345678.yaml
└── sortie/                  écrit par c3hm export
    ├── notes_omnivox.xlsx
    ├── grille.md
    ├── grille.pdf
    ├── Travaux.zip
    └── retroaction/
        └── Tremblay_Alice_1234567.pdf
```

Un étudiant en équipe hérite des notes et des commentaires de son équipe, sauf
là où son propre fichier en donne. Tous ces fichiers peuvent être modifiés dans
l'interface web ou directement dans un éditeur. Le dossier `sortie/` est généré
par `c3hm export`.

## Développement

```bash
uv sync                             # installe les dépendances
uv run pytest                       # lance les tests
uv run nox -s lint format_check     # linteur et formatage
```
