"""
Lecture de la liste d'étudiants exportée d'Omnivox (CSV).

Colonnes attendues : « No de dossier », « Prénom de l'étudiant », « Nom de l'étudiant ».
Les en-têtes sont reconnus sans tenir compte des accents ni de la casse. Seules
ces colonnes sont importées ; les équipes se définissent ensuite dans les YAML.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from c3hm.model import Student, normalize_label

COL_ID = "no de dossier"
COL_FIRSTNAME = "prenom de l'etudiant"
COL_SURNAME = "nom de l'etudiant"
DISPLAY_NAMES = {
    COL_ID: "No de dossier",
    COL_FIRSTNAME: "Prénom de l'étudiant",
    COL_SURNAME: "Nom de l'étudiant",
}


class OmnivoxError(Exception):
    pass


def decode_csv(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise OmnivoxError("Impossible de décoder le fichier CSV (encodage inconnu).")


def _clean(field: str | None) -> str:
    field = (field or "").strip()
    if field.startswith('="') and field.endswith('"'):
        field = field[2:-1]
    return field.strip()


def parse_students_csv(text: str) -> list[Student]:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        raise OmnivoxError("Le fichier CSV est vide.")

    header = {normalize_label(_clean(name)): idx for idx, name in enumerate(rows[0])}
    missing = [col for col in (COL_ID, COL_FIRSTNAME, COL_SURNAME) if col not in header]
    if missing:
        raise OmnivoxError(
            "Colonnes manquantes dans le CSV : "
            + ", ".join(f"« {DISPLAY_NAMES[m]} »" for m in missing)
            + ". Colonnes trouvées : "
            + ", ".join(f"« {_clean(h)} »" for h in rows[0])
        )

    def cell(row: list[str], col: str) -> str:
        idx = header.get(col)
        return _clean(row[idx]) if idx is not None and idx < len(row) else ""

    students: list[Student] = []
    for row in rows[1:]:
        matricule = cell(row, COL_ID)
        if not matricule:
            continue
        students.append(
            Student(
                matricule=matricule,
                firstname=cell(row, COL_FIRSTNAME),
                surname=cell(row, COL_SURNAME),
            )
        )
    return students


def read_students_csv(path: Path) -> list[Student]:
    return parse_students_csv(decode_csv(path.read_bytes()))


def merge_students(existing: list[Student], imported: list[Student]) -> tuple[list[Student], int]:
    """
    Fusionne une importation dans la liste existante, par matricule.

    Les noms viennent du CSV ; tout le reste (équipe, etc.) est conservé tel quel.
    Les étudiants absents du CSV sont conservés.
    Retourne (liste fusionnée, nombre de nouveaux étudiants).
    """
    by_id = {s.matricule: s for s in existing}
    new_count = 0
    for student in imported:
        current = by_id.get(student.matricule)
        if current is None:
            by_id[student.matricule] = student
            new_count += 1
            continue
        current.firstname = student.firstname
        current.surname = student.surname
    return list(by_id.values()), new_count
