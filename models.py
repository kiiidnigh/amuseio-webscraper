from dataclasses import dataclass


@dataclass
class ReleaseSummary:
    release_id: str
    title: str
    artist: str
    track_count: int
    release_date: str
    upc: str
    url: str

    @property
    def release_type(self) -> str:
        """Leitet den Release-Typ anhand branchenüblicher Track-Anzahlen ab."""
        if self.track_count <= 2:
            return "Single"
        elif 3 <= self.track_count <= 6:
            return "EP"
        return "Album"


@dataclass
class TrackRecord:
    release_title: str
    release_type: str
    release_date: str
    upc: str
    track_number: str
    track_title: str
    isrc: str
    amuse_release_url: str

    def to_csv_row(self) -> dict[str, str]:
        return {
            "Release Title": self.release_title,
            "Release Type": self.release_type,
            "Release Date": self.release_date,
            "UPC": self.upc,
            "Track Number": self.track_number,
            "Track Title": self.track_title,
            "ISRC": self.isrc,
            "Amuse Release URL": self.amuse_release_url,
        }