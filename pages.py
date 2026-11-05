import logging
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import ScraperConfig, Selectors
from models import ReleaseSummary, TrackRecord

logger = logging.getLogger(__name__)


class ReleaseListPage:
    """Verantwortlich für das Auslesen der Release-Tabelle und die Pagination."""

    def __init__(self, driver: WebDriver, config: ScraperConfig):
        self.driver = driver
        self.config = config
        self.wait = WebDriverWait(driver, config.element_timeout)

    def wait_for_table(self) -> None:
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.TABLE_ROW))
        )

    @staticmethod
    def parse_table_html(html: str, base_url: str) -> list[ReleaseSummary]:
        """Reine Funktion: Parst den HTML-Code der Tabelle ohne Selenium-Abhängigkeit."""
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select(Selectors.TABLE_ROW)
        releases: list[ReleaseSummary] = []

        for row in rows:
            href = row.get("href", "")
            full_url = urljoin(base_url, str(href))

            title_el = row.select_one(Selectors.CELL_TITLE)
            artist_el = row.select_one(Selectors.CELL_ARTIST)
            count_el = row.select_one(Selectors.CELL_TRACK_COUNT)
            date_el = row.select_one(Selectors.CELL_RELEASE_DATE)
            id_el = row.select_one(Selectors.CELL_RELEASE_ID)
            upc_el = row.select_one(Selectors.CELL_UPC)

            # Track-Anzahl aus dem 'count'-Attribut (Fallback: Text parsen)
            track_count = 1
            if count_el:
                if count_el.has_attr("count"):
                    track_count = int(count_el["count"])
                else:
                    digits = "".join(filter(str.isdigit, count_el.get_text()))
                    track_count = int(digits) if digits else 1

            releases.append(
                ReleaseSummary(
                    release_id=id_el.get_text(strip=True) if id_el else "",
                    title=title_el.get_text(strip=True) if title_el else "Unknown",
                    artist=artist_el.get_text(strip=True) if artist_el else "",
                    track_count=track_count,
                    release_date=date_el.get_text(strip=True) if date_el else "",
                    upc=upc_el.get_text(strip=True) if upc_el else "",
                    url=full_url,
                )
            )

        return releases

    def parse_current_page_releases(self) -> list[ReleaseSummary]:
        self.wait_for_table()
        return self.parse_table_html(self.driver.page_source, self.config.base_url)

    def get_pagination_info(self) -> str:
        try:
            el = self.driver.find_element(By.CSS_SELECTOR, Selectors.PAGINATION_LABEL)
            return el.text.strip()
        except Exception:
            return "Unbekannte Seite"

    def go_to_next_page(self) -> bool:
        """
        Klickt auf den 'Nächste Seite'-Button, sofern dieser nicht 'disabled' ist.
        Wartet anschließend, bis sich das Pagination-Label aktualisiert hat.
        """
        try:
            next_btn = self.driver.find_element(By.XPATH, Selectors.NEXT_PAGE_BTN_XPATH)
        except Exception:
            logger.info("Kein Pagination-Next-Button gefunden (nur 1 Seite vorhanden).")
            return False

        # Prüfen, ob das Ende erreicht ist (disabled="" im HTML)
        if next_btn.get_attribute("disabled") is not None:
            return False

        old_label = self.get_pagination_info()

        # Per JavaScript klicken verhindert Scroll-/Overlay-Probleme
        self.driver.execute_script("arguments[0].click();", next_btn)

        # Warten, bis sich der Pagination-Text ändert (z.B. von "101 - 110" auf "111 - 112")
        try:
            self.wait.until(
                lambda d: d.find_element(
                    By.CSS_SELECTOR, Selectors.PAGINATION_LABEL
                ).text.strip() != old_label
            )
            # Kurze Beruhigungspause für das Neu-Rendern der Tabellenzeilen
            time.sleep(0.5)
        except TimeoutException:
            logger.warning("Timeout beim Warten auf Seitenwechsel der Tabelle.")
            return False

        return True


class ReleaseDetailPage:
    """Verantwortlich für das Auslesen der Tracklist und ISRCs auf einer Release-Detailseite."""

    def __init__(self, driver: WebDriver, config: ScraperConfig):
        self.driver = driver
        self.config = config
        self.wait = WebDriverWait(driver, config.element_timeout)

    @staticmethod
    def parse_detail_html(html: str, release: ReleaseSummary) -> list[TrackRecord]:
        """Reine Funktion: Parst die Tracklist & ISRCs aus dem HTML-String."""
        soup = BeautifulSoup(html, "html.parser")
        isrc_labels = soup.select(Selectors.ISRC_LABEL)
        tracks: list[TrackRecord] = []

        for idx, isrc_label in enumerate(isrc_labels, start=1):
            # 1. ISRC aus dem direkten Nachbar-Span (<span class="font-light">) lesen
            isrc_value_span = isrc_label.find_next_sibling("span")
            isrc = isrc_value_span.get_text(strip=True) if isrc_value_span else "N/A"

            # 2. Zugehörigen Track-Header (<h4>) im selben Track-Container finden
            track_num = f"{idx:02d}"
            track_title = release.title  # Fallback bei Singles ohne explizites h4

            # Wir navigieren im DOM vom ISRC-Span nach oben zum umschließenden Track-Block
            track_card = isrc_label.find_parent(
                lambda tag: tag.name == "div" and tag.find(Selectors.TRACK_HEADER_H4) is not None
            )
            if track_card:
                h4 = track_card.find(Selectors.TRACK_HEADER_H4)
                if h4:
                    num_span = h4.select_one(Selectors.TRACK_NUMBER_SPAN)
                    name_span = h4.select_one(Selectors.TRACK_NAME_SPAN)
                    if num_span:
                        track_num = num_span.get_text(strip=True)
                    if name_span:
                        track_title = name_span.get_text(strip=True)

            tracks.append(
                TrackRecord(
                    release_title=release.title,
                    release_type=release.release_type,
                    release_date=release.release_date,
                    upc=release.upc,
                    track_number=track_num,
                    track_title=track_title,
                    isrc=isrc,
                    amuse_release_url=release.url,
                )
            )

        return tracks

    def extract_tracks(self, release: ReleaseSummary) -> list[TrackRecord]:
        self.driver.get(release.url)

        try:
            # Warten, bis mindestens ein ISRC-Label im DOM präsent ist
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.ISRC_LABEL))
            )
        except TimeoutException:
            logger.warning(
                f"Kein ISRC-Feld auf {release.url} gefunden (evtl. noch 'In Progress' ohne ISRC?)."
            )
            return [
                TrackRecord(
                    release_title=release.title,
                    release_type=release.release_type,
                    release_date=release.release_date,
                    upc=release.upc,
                    track_number="01",
                    track_title=release.title,
                    isrc="N/A",
                    amuse_release_url=release.url,
                )
            ]

        return self.parse_detail_html(self.driver.page_source, release)