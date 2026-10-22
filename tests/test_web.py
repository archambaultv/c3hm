"""Parcours principaux de l'interface web."""

import io

from c3hm.model import Notes, Student


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


def test_une_modification_sur_le_disque_change_la_version(graded_client, graded_workspace):
    avant = graded_client.get("/etat").get_json()["version"]
    assert f'let version = "{avant}";' in graded_client.get("/etudiant/3333333").get_data(as_text=True)

    graded_workspace.save_notes("3333333", Notes(comment="Modifié à la main."))
    apres = graded_client.get("/etat").get_json()["version"]
    assert apres != avant
    page = graded_client.get("/etudiant/3333333").get_data(as_text=True)
    assert "Modifié à la main." in page and f'let version = "{apres}";' in page


def test_enregistrer_sur_une_version_perimee_est_refuse(graded_client, graded_workspace):
    version = graded_client.get("/etat").get_json()["version"]
    graded_workspace.save_notes("3333333", Notes(comment="Modifié à la main."))

    reponse = graded_client.post(
        "/etudiant/3333333/commentaire", data={"texte": "Écrasé ?"}, headers={"X-C3hm-Version": version}
    )
    assert reponse.status_code == 409
    assert graded_workspace.load_notes("3333333").comment == "Modifié à la main."


def test_enregistrer_renvoie_la_nouvelle_version(graded_client, graded_workspace):
    version = graded_client.get("/etat").get_json()["version"]
    reponse = graded_client.post(
        "/etudiant/3333333/commentaire", data={"texte": "Nouveau."}, headers={"X-C3hm-Version": version}
    )
    assert reponse.status_code == 200
    assert graded_workspace.load_notes("3333333").comment == "Nouveau."
    assert reponse.headers["X-C3hm-Version"] == graded_workspace.fingerprint() != version


def test_la_grille_lue_du_disque_sert_de_reference(client):
    page = client.get("/evaluation").get_data(as_text=True)
    assert "data-brouillon data-intact" in page
    assert "data-enregistrer disabled>✓ Enregistré" in page


def test_import_de_la_liste_omnivox(client, workspace):
    csv = "No de dossier,Nom de l'étudiant,Prénom de l'étudiant\n9999999,Nguyen,David\n".encode("cp1252")
    reponse = client.post("/etudiants/importer", data={"csv": (io.BytesIO(csv), "liste.csv")})
    assert "1 nouveau(x)" in reponse.get_data(as_text=True)
    assert any(s.matricule == "9999999" for s in workspace.load_students())


def test_commentaire_par_critere(client, workspace):
    client.post("/etudiant/3333333/commentaire", data={"critere": "Tests", "texte": "Bien."})
    assert workspace.load_notes("3333333").comment_for("Tests") == "Bien."
    texte = workspace.notes_path("3333333").read_text(encoding="utf-8")
    assert "  Tests:\n    niveau: null\n    commentaire: Bien.\n" in texte


def test_affichage_liste_ne_remplace_que_la_fiche(client, workspace):
    evaluation = workspace.load_evaluation()
    evaluation.layout = "liste"
    workspace.save_evaluation(evaluation)
    page = client.get("/etudiant/3333333").get_data(as_text=True)
    fiche = page.split('id="fiche-1"')[1]
    assert "Commentaire" in fiche and "Axe de progression" not in fiche  # commentaire dans la fiche

    reponse = client.post("/etudiant/3333333/niveau", data={"critere": "Fonctionnalités", "niveau": "Acquis"})
    html = reponse.get_data(as_text=True)
    assert 'id="fiche-1"' in html and 'id="total"' in html
    assert "<textarea" not in html  # la saisie en cours n'est pas écrasée


def test_reprendre_lequipe_en_liste_ne_remplace_que_la_fiche(client, graded_workspace):
    evaluation = graded_workspace.load_evaluation()
    evaluation.layout = "liste"
    graded_workspace.save_evaluation(evaluation)
    i = [c.label for c in evaluation.criteria].index("Tests")
    page = client.get("/etudiant/1111111").get_data(as_text=True)
    bouton = page.split("↩ reprendre l'équipe")[0].rsplit("<button", 1)[1]
    assert f'hx-target="#fiche-{i}"' in bouton


def test_un_etudiant_ajoute_sur_le_disque_a_son_fichier_de_notes(client, workspace):
    client.get("/")
    assert workspace.notes_matricules() == ["1111111", "2222222", "3333333"]
    workspace.save_students([*workspace.load_students(), Student("4444444", "David", "Nguyen", team="B")])
    client.get("/etat")
    assert workspace.notes_path("4444444").is_file()
    assert workspace.team_notes_names() == ["A", "B"]


def test_masquer_les_notes_de_laccueil(graded_client):
    assert "<th>Note</th>" in graded_client.get("/").get_data(as_text=True)

    graded_client.post("/notes-masquees")
    page = graded_client.get("/").get_data(as_text=True)
    assert "<th>Note</th>" not in page
    assert "Notes masquées" in page

    graded_client.post("/notes-masquees")
    assert "<th>Note</th>" in graded_client.get("/").get_data(as_text=True)


def test_mettre_en_commun_depuis_un_coequipier(graded_client, graded_workspace):
    # sur la fiche de Bob, la pastille d'Alice (Tests : Non démontré) met son niveau en commun
    page = graded_client.get("/etudiant/2222222").get_data(as_text=True)
    assert "Alice ↑" in page

    reponse = graded_client.post("/etudiant/2222222/mettre-en-commun", data={"critere": "Tests", "source": "1111111"})
    html = reponse.get_data(as_text=True)
    assert 'id="grille"' in html and 'id="commentaire-2" hx-swap-oob="true"' in html
    assert graded_workspace.load_team_notes("A").level_for("Tests") == "Non démontré"
    assert graded_workspace.load_notes("1111111").levels == {}
    assert graded_workspace.load_notes("2222222").level_for("Tests") == "Acquis"  # Bob garde sa note


def test_le_mode_masque_cache_les_niveaux_des_coequipiers(graded_client):
    graded_client.post("/notes-masquees")
    assert "Alice ↑" not in graded_client.get("/etudiant/2222222").get_data(as_text=True)
    assert "<th>Note</th>" not in graded_client.get("/").get_data(as_text=True)


def test_mettre_en_commun_en_liste_ne_remplace_que_la_fiche(graded_client, graded_workspace):
    evaluation = graded_workspace.load_evaluation()
    evaluation.layout = "liste"
    graded_workspace.save_evaluation(evaluation)
    page = graded_client.get("/etudiant/2222222").get_data(as_text=True)
    assert "Alice : Non démontré ↑" in page

    html = graded_client.post(
        "/etudiant/1111111/mettre-en-commun", data={"critere": "Tests", "source": "1111111"}
    ).get_data(as_text=True)
    assert 'id="fiche-2"' in html and 'id="grille"' not in html
