# c3hm

Outil de correction avec interface web locale.

## Installation

Un fois ce dépôt cloné, installez c3hm avec la commande suivante :

```sh
uv tool install .
```

## Commandes

Il est possible de presque tout faire depuis l'interface web :

```bash
c3hm serve [DOSSIER] [-p PORT]      # interface web sur http://localhost:5000
```

Pour procéder en ligne de commande, voici les autres commandes disponibles :

Voici les commandes
```bash
c3hm init [DOSSIER]                 # crée evaluation.yaml (défaut : dossier courant)
c3hm import-students CSV [DOSSIER]  # liste Omnivox (CSV) convertie en etudiants.yaml
c3hm create-notes [DOSSIER] [-f]    # crée les fichiers de notes (prêt à être remplis)
c3hm unpack DOSSIER                 # décompresse et nettoie les remises Omnivox
c3hm clean DOSSIER                  # supprime node_modules, .venv, etc.
c3hm export [DOSSIER]               # sortie/ : notes Omnivox, rétroactions PDF, grille vierge
```

## Dossier de travail

Une évaluation correspond à un dossier contenant les fichiers suivants :

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
là où son propre fichier en donne.

## Développement

```bash
uv sync                             # installe les dépendances
uv run pytest                       # lance les tests
uv run nox -s lint format_check     # linteur et formatage
```
