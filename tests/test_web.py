"""Parcours principaux de l'interface web."""

import io

from c3hm.model import Notes


def test_cliquer_un_niveau_enregistre_et_recalcule(client, workspace):
    reponse = client.post("/etudiant/3333333/niveau", data={"critere": "Qualité du code", "niveau": "Acquis"})
    assert reponse.status_code == 200
    assert workspace.load_notes("3333333").level_for("Qualité du code") == "Acquis"

    # recliquer la case retenue efface le niveau
    client.post("/etudiant/3333333/niveau", data={"critere": "Qualité du code", "niveau": ""})
    assert workspace.load_notes("3333333").levels == {}


def test_un_membre_herite_devie_puis_revient(graded_client, graded_workspace):
    page = graded_client.get("/etudiant/2222222").get_data(as_text=True)
    assert "hérité de l'équipe" in page
    assert "Bon travail" in page  # commentaire hérité de l'équipe

    graded_client.post("/etudiant/2222222/niveau", data={"critere": "Tests", "niveau": "Non démontré"})
    assert graded_workspace.load_notes("2222222").level_for("Tests") == "Non démontré"

    graded_client.post("/etudiant/2222222/niveau", data={"critere": "Tests", "niveau": ""})
    assert graded_workspace.load_notes("2222222").levels == {}


def test_changer_la_grille_avertit_avant_de_casser_des_corrections(graded_client, graded_workspace):
    formulaire = {
        "cours": "420-5D2-MA",
        "session": "Automne 2026",
        "evaluation": "TP1",
        "affichage": "grille",
        "niveau-0-nom": "Avancé",
        "niveau-0-pct": "100",
        "niveau-1-nom": "Réussi",  # « Acquis » renommé : les notes existantes ne s'y retrouvent plus
        "niveau-1-pct": "75",
        "niveau-2-nom": "Non démontré",
        "niveau-2-pct": "0",
        "critere-0-nom": "Qualité du code",
        "critere-0-pond": "30",
        "critere-1-nom": "Fonctionnalités",
        "critere-1-pond": "50",
        "critere-2-nom": "Tests",
        "critere-2-pond": "20",
    }
    page = graded_client.post("/evaluation", data=formulaire).get_data(as_text=True)
    assert "invalide" in page
    assert graded_workspace.load_evaluation().scale[1].label == "Acquis"  # rien n'est écrit

    page = graded_client.post("/evaluation", data={**formulaire, "confirmer": "1"}).get_data(as_text=True)
    assert "Enregistré" in page
    assert graded_workspace.load_evaluation().scale[1].label == "Réussi"


def test_grille_invalide_refusee(client, workspace):
    page = client.post(
        "/evaluation",
        data={
            "cours": "x",
            "session": "y",
            "evaluation": "z",
            "affichage": "grille",
            "niveau-0-nom": "Acquis",
            "niveau-0-pct": "75",
            "critere-0-nom": "A",
            "critere-0-pond": "90",  # la somme ne fait pas 100
        },
    ).get_data(as_text=True)
    assert "La somme des pondérations" in page
    assert workspace.load_evaluation().title == "TP1"  # inchangée


def test_surveillance_des_fichiers(graded_client, graded_workspace):
    page = graded_client.get("/etudiant/3333333").get_data(as_text=True)
    version = page.split("notes?v=")[1].split('"')[0]

    assert graded_client.get(f"/etudiant/3333333/notes?v={version}").status_code == 204

    graded_workspace.save_notes("3333333", Notes(levels={"Tests": "Avancé"}))
    changement = graded_client.get(f"/etudiant/3333333/notes?v={version}")
    assert "ont changé sur le disque" in changement.get_data(as_text=True)


def test_import_de_la_liste_omnivox(client, workspace):
    csv = "No de dossier,Nom de l'étudiant,Prénom de l'étudiant\n9999999,Nguyen,David\n".encode("cp1252")
    reponse = client.post("/etudiants/importer", data={"csv": (io.BytesIO(csv), "liste.csv")})
    assert "1 nouveau(x)" in reponse.get_data(as_text=True)
    assert any(s.matricule == "9999999" for s in workspace.load_students())
