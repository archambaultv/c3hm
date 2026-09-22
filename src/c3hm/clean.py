import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Cleaner:
    folder: Path
    paths_to_delete: list[str]
    verbose: bool = False

    def clean_folders(self):
        """
        Supprime les fichiers et dossiers indésirables.
        """
        if not self.folder.exists():
            raise FileNotFoundError(f"Le dossier {self.folder} n'existe pas.")

        self._vprint(f"Début du nettoyage de {self.folder}")

        for archive in self.folder.glob("*"):
            if archive.is_dir():
                self._clean_folder(archive)

    def _clean_folder(self, path: Path):
        """
        Supprime les fichiers et dossiers indésirables dans le dossier spécifié.
        """
        self._vprint(f"Nettoyage de l'archive : {path}")

        # Supprime les fichiers et dossiers indésirables
        for item in path.rglob("*"):
            if any(item.match(pat) for pat in self.paths_to_delete):
                if item.is_dir():
                    self._vprint(f"Suppression du dossier: {item}")
                    shutil.rmtree(item, ignore_errors=True)
                elif item.is_file():
                    self._vprint(f"Suppression du fichier: {item}")
                    item.unlink()

    def _vprint(self, *args):
        if self.verbose:
            print(*args)
