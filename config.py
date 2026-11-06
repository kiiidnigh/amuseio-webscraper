from dataclasses import dataclass, field
from pathlib import Path
import sys


def get_app_directory() -> Path:
    """Gibt den Ordner der .exe zurück (oder den Skript-Ordner im Dev-Modus)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


@dataclass(frozen=True)
class ScraperConfig:
    start_url: str = "https://artist.amuse.io/studio/music/"
    base_url: str = "https://artist.amuse.io"
    output_csv: Path = field(
        default_factory=lambda: get_app_directory() / "amuse_isrc_export.csv"
    )

    element_timeout: int = 15
    min_delay_sec: float = 0.8
    max_delay_sec: float = 1.8


@dataclass(frozen=True)
class Selectors:
    # --- Übersichtsseite (Data Table) ---
    TABLE_CONTAINER = 'div[data-testid="data_table"]'
    TABLE_ROW = 'a[data-testid="data_table_row"]'

    CELL_TITLE = 'div.data-table-cell--name p'
    CELL_ARTIST = 'div.data-table-cell--main_primary_artist_name p'
    CELL_TRACK_COUNT = 'span[data-path="releases_list_track_count"]'
    CELL_RELEASE_DATE = 'span[data-testid="release_list_table_release_date"]'
    CELL_RELEASE_ID = 'div.data-table-cell--id span'
    CELL_UPC = 'div.data-table-cell--upc span'

    # --- Pagination ---
    PAGINATION_LABEL = 'span[data-path="pagination_lbl"]'
    # Der Next-Button ist der zweite Button im Pagination-Container (direkt nach dem Prev-Button)
    NEXT_PAGE_BTN_XPATH = '//span[@data-path="pagination_lbl"]/following-sibling::button[2]'

    # --- Detailseite (Tracks & ISRCs) ---
    ISRC_LABEL = 'span[data-path="core_lbl_isrc_text"]'
    TRACK_HEADER_H4 = 'h4'
    TRACK_NUMBER_SPAN = 'span.text-primary'
    TRACK_NAME_SPAN = 'span.name'