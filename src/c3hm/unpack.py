import os
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path

PATHS_TO_DELETE = [
    "__pycache__",
    ".DS_Store",
    ".idea",
    ".pytest_cache",
    ".venv",
    "venv",
    ".vscode",
    "node_modules",
    "__MACOSX",
]


@dataclass
class UnpackOmnivox:
    folder: Path
    paths_to_delete: list[str]
    verbose: bool = False

    def unpack(self):
        """
        Décompresse les archives dans le dossier spécifié et supprime les
        fichiers et dossiers indésirables.
        """
        if not self.folder.exists():
            raise FileNotFoundError(f"Le dossier {self.folder} n'existe pas.")

        self._vprint(f"Début de l'extraction de {self.folder}")

        # Si le dossier est lui-même une archive, on le décompresse d'abord
        self._extract_self()

        # Parcourt le dossier pour trouver les archives des étudiants
        self._extract_student_archives()

        # Nettoyage des fichiers et dossiers indésirables
        self._clean_student_archives()

    def _clean_student_archives(self):
        """
        Supprime les fichiers et dossiers indésirables dans le dossier spécifié.
        """
        for archive in self.folder.glob("*"):
            if archive.is_dir():
                self._clean_student_archive(archive)
            elif archive.is_file():
                new_name = archive.parent / self._shorten_omnivox_file_name(archive)
                i = 2
                while new_name.exists():
                    new_stem = Path(self._shorten_omnivox_file_name(archive)).stem + f"_{i}"
                    new_name = archive.parent / f"{new_stem}{new_name.suffix}"
                    i += 1
                archive.rename(new_name)

    def _clean_student_archive(self, path: Path):
        """
        Supprime les fichiers et dossiers indésirables dans le dossier spécifié.
        """
        self._vprint(f"Nettoyage de l'archive : {path}")

        # Décompresse les archives additionnelles dans le dossier de l'étudiant
        for item in list(path.glob("*.zip")) + list(path.glob("*.rar")) + list(path.glob("*.7z")):
            if item.is_file():
                output = item.parent / self._shorten_omnivox_archive_name(item.stem)
                self._extract_archive(item, output)
            item.unlink()

        # Supprime les fichiers et dossiers indésirables
        for item in path.rglob("*"):
            if any(item.match(pat) for pat in self.paths_to_delete):
                if item.is_dir():
                    self._vprint(f"Suppression du dossier: {item}")
                    shutil.rmtree(item, ignore_errors=True)
                elif item.is_file():
                    self._vprint(f"Suppression du fichier: {item}")
                    item.unlink()

        # Aplatit les dossiers uniques
        self._flatten_single_folders(path)

    def _extract_student_archives(self):
        for archive in self.folder.glob("*"):
            if archive.is_file() and archive.suffix in [".zip", ".rar", ".7z"]:
                stem = self._shorten_omnivox_archive_name(archive.stem)
                output_path = archive.parent / stem
                self._extract_archive(archive, output_path)

    def _extract_self(self):
        """
        Décompresse l'archive dans le dossier spécifié et supprime les
        fichiers et dossiers indésirables.
        """
        if self.folder.is_file() and self.folder.suffix in [".zip"]:
            output_path = self.folder.parent / self.folder.stem
            self._extract_archive(self.folder, output_path)
            self.folder = output_path

    def _vprint(self, *args):
        if self.verbose:
            print(*args)

    def _extract_archive(self, archive: Path, output: Path):
        try:
            if archive.suffix == ".zip":
                with zipfile.ZipFile(archive) as z:
                    z.extractall(output)
                self._vprint(f"Dézipper : {archive}")
                archive.unlink()
            elif archive.suffix in [".rar", ".7z"]:
                self._extract_archive_7z(archive, output)
                self._vprint(f"Décompresser {archive.suffix} : {archive}")
                archive.unlink()
        except Exception as e:
            self._vprint(f"Erreur avec {archive} : {e}")

    def _extract_archive_7z(self, archive_path: Path, output_dir: Path) -> None:
        """
        Extracts a .rar or .7z archive using 7-Zip command-line tool.
        Requires 7z.exe to be in PATH or known location.
        """
        # Find 7z executable
        seven_zip = shutil.which("7z")
        if not seven_zip:
            raise FileNotFoundError(
                "7z.exe not found in PATH. Make sure 7-Zip is installed for .rar and .7z extraction."
            )

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Build and run extraction command
        command = [seven_zip, "x", archive_path, f"-o{output_dir}", "-y"]
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Extraction failed:\n{result.stderr}")

    def _shorten_omnivox_archive_name(self, name: str) -> str:
        """
        Garde seulement la partie du nom avant "_Remis_le_".
        """
        return name.split("_Remis_le_", maxsplit=1)[0]

    def _shorten_omnivox_file_name(self, name: Path) -> str:
        """
        Garde la partie du nom avant "_Remis_le_" et l'extension
        """
        return name.stem.split("_Remis_le_", maxsplit=1)[0] + name.suffix

    def _flatten_single_folders(self, path: Path):
        # Trouve d'abord le dossier le plus profond dans la chaîne de dossiers uniques
        current = path
        folders_to_remove: list[Path] = []

        while True:
            children = list(current.iterdir())
            dirs = [p for p in children if p.is_dir()]
            files = [p for p in children if p.is_file()]

            if len(dirs) == 1 and not files:
                folders_to_remove.append(dirs[0])
                current = dirs[0]
            else:
                break

        # Si on a trouvé des dossiers à aplatir
        if folders_to_remove:
            deepest_folder = current
            self._vprint(f"Aplatir: {deepest_folder} → {path}")

            # Déplace tout le contenu du dossier le plus profond vers le dossier cible
            rename_after_conflict = None
            for item in deepest_folder.iterdir():
                target_path = path / item.name

                # Gère les conflits de noms
                # Arrive lorsqu'un dossier dans deepest_folder a le même nom
                # que le premier dossier à aplatir
                if target_path.exists():
                    new_name = f"{item.stem}_temp{item.suffix}"
                    target_path = path / new_name
                    rename_after_conflict = (target_path, path / item.name)

                shutil.move(str(item), str(target_path))

            # Gère le conflit de noms
            if rename_after_conflict:
                shutil.move(rename_after_conflict[0], rename_after_conflict[1])
                folders_to_remove = folders_to_remove[1:]

            # Supprime tous les dossiers intermédiaires vides (en partant du plus profond)
            for folder in reversed(folders_to_remove):
                print(folder)
                folder.rmdir()
