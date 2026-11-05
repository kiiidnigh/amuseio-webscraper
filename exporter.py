import csv
from pathlib import Path
from models import TrackRecord


class CSVExporter:
    FIELDNAMES = [
        "Release Title",
        "Release Type",
        "Release Date",
        "UPC",
        "Track Number",
        "Track Title",
        "ISRC",
        "Amuse Release URL",
    ]

    def __init__(self, filepath: Path):
        self.filepath = filepath

    def get_already_scraped_urls(self) -> set[str]:
        """Liest bereits gespeicherte Release-URLs ein, um nach einem Abbruch nahtlos fortzusetzen."""
        if not self.filepath.exists():
            return set()

        scraped_urls: set[str] = set()
        with self.filepath.open(mode="r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get("Amuse Release URL")
                if url:
                    scraped_urls.add(url)
        return scraped_urls

    def append_tracks(self, tracks: list[TrackRecord]) -> None:
        """Schreibt die Tracks eines Releases sofort auf die Festplatte (Inkrementelles Speichern)."""
        if not tracks:
            return

        file_exists = self.filepath.exists() and self.filepath.stat().st_size > 0

        with self.filepath.open(mode="a", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            if not file_exists:
                writer.writeheader()
            for track in tracks:
                writer.writerow(track.to_csv_row())