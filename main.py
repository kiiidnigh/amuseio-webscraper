import logging
import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from config import ScraperConfig
from exporter import CSVExporter
from models import ReleaseSummary
from pages import ReleaseDetailPage, ReleaseListPage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--start-maximized")
    # Verhindert unnötige Browser-Logs in der Konsole
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return webdriver.Chrome(options=options)


def collect_all_releases(list_page: ReleaseListPage) -> list[ReleaseSummary]:
    """Phase 1: Blättert durch die Pagination und sammelt alle Release-Metadaten & Links."""
    all_releases: list[ReleaseSummary] = []
    seen_urls: set[str] = set()
    page_num = 1

    while True:
        pagination_info = list_page.get_pagination_info()
        logger.info(f"Lese Übersichtsseite {page_num} ({pagination_info})...")

        page_releases = list_page.parse_current_page_releases()
        for rel in page_releases:
            if rel.url not in seen_urls:
                seen_urls.add(rel.url)
                all_releases.append(rel)

        if not list_page.go_to_next_page():
            logger.info("Letzte Seite der Pagination erreicht.")
            break

        page_num += 1

    return all_releases


def main() -> None:
    config = ScraperConfig()
    exporter = CSVExporter(config.output_csv)
    already_scraped = exporter.get_already_scraped_urls()

    if already_scraped:
        logger.info(
            f"Checkpoint gefunden: {len(already_scraped)} Releases sind bereits in '{config.output_csv}' gespeichert."
        )

    driver = create_driver()

    try:
        logger.info(f"Öffne {config.start_url} ...")
        driver.get(config.start_url)

        print("\n" + "=" * 70)
        print("MANUELLE VORBEREITUNG IM BROWSER:")
        print("1. Bitte logge dich bei Amuse.io ein.")
        print("2. Wechsle oben auf dein gewünschtes Künstlerprofil (z. B. 'shadowghost').")
        print("3. Klicke auf die gewünschte Kategorie (z. B. 'Delivered or Live').")
        print("4. Stelle sicher, dass du auf Seite 1 der Tabelle bist.")
        print("=" * 70)
        input("\n>>> Drücke [ENTER] hier im Terminal, sobald die Tabelle sichtbar ist... ")

        list_page = ReleaseListPage(driver, config)
        detail_page = ReleaseDetailPage(driver, config)

        # --- PHASE 1: Alle Releases über die Pagination sammeln ---
        logger.info("Starte Phase 1: Indexierung aller Releases...")
        all_releases = collect_all_releases(list_page)
        logger.info(f"Insgesamt {len(all_releases)} Releases in dieser Kategorie gefunden.")

        # Filtere Releases heraus, die bei einem früheren Lauf schon gespeichert wurden
        pending_releases = [r for r in all_releases if r.url not in already_scraped]
        logger.info(f"Noch auszulesende Releases: {len(pending_releases)}")

        # --- PHASE 2: Detailseiten aufrufen & ISRCs extrahieren ---
        for idx, release in enumerate(pending_releases, start=1):
            logger.info(
                f"[{idx}/{len(pending_releases)}] Extrahiere '{release.title}' "
                f"({release.track_count} Track(s), {release.release_type})..."
            )

            tracks = detail_page.extract_tracks(release)
            exporter.append_tracks(tracks)

            for t in tracks:
                logger.info(f"   -> Track {t.track_number}: {t.track_title} | ISRC: {t.isrc}")

            # Höfliche Zufallspause (Jitter) zwischen Detail-Aufrufen
            delay = random.uniform(config.min_delay_sec, config.max_delay_sec)
            time.sleep(delay)

        logger.info(f"Fertig! Alle Daten wurden in '{config.output_csv.resolve()}' gespeichert.")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()