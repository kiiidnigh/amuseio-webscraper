import tempfile
import unittest
from pathlib import Path

from exporter import CSVExporter
from models import ReleaseSummary
from pages import ReleaseDetailPage, ReleaseListPage


class TestAmuseScraper(unittest.TestCase):
    def setUp(self):
        # Dein echtes HTML-Snippet für eine Tabellenzeile
        self.sample_row_html = """
        <div data-testid="data_table" class="data-table scroll-x" role="grid">
            <a href="/studio/music/4560833" class="data-table-row" data-testid="data_table_row">
                <div class="data-table-cell--name"><p id="release_name_4560833"><span><span>immer das gleiche</span></span></p></div>
                <div class="data-table-cell--main_primary_artist_name"><p><span><span>shadowghost</span></span></p></div>
                <div class="data-table-cell--songs_count"><span data-path="releases_list_track_count" count="1">1 track</span></div>
                <div class="data-table-cell--release_date"><span data-testid="release_list_table_release_date">1 May 2026</span></div>
                <div class="data-table-cell--id"><span>4560833 <button></button></span></div>
                <div class="data-table-cell--upc"><span>7300349759618 <button></button></span></div>
            </a>
        </div>
        """

        # Gekürztes, strukturell identisches Snippet deiner 4-Track-EP
        self.sample_ep_detail_html = """
        <div class="flex flex-col mt-6">
            <div class="px-4 bg-surface-3 rounded-lg mb-6">
                <div class="w-full">
                    <button><div class="flex-1"><h4 class="mb-1"><span class="text-primary mr-3">01</span><span class="name">nur so ein Gefühl</span></h4></div></button>
                    <div><div class="flex"><span data-path="core_lbl_isrc_text" class="w-1/2">ISRC</span><span class="font-light">SE6TI2632728</span></div></div>
                </div>
            </div>
            <div class="px-4 bg-surface-3 rounded-lg mb-6">
                <div class="w-full">
                    <button><div class="flex-1"><h4 class="mb-1"><span class="text-primary mr-3">02</span><span class="name">mit mir selbst</span></h4></div></button>
                    <div><div class="flex"><span data-path="core_lbl_isrc_text" class="w-1/2">ISRC</span><span class="font-light">SE6132694460</span></div></div>
                </div>
            </div>
            <div class="px-4 bg-surface-3 rounded-lg mb-6">
                <div class="w-full">
                    <button><div class="flex-1"><h4 class="mb-1"><span class="text-primary mr-3">03</span><span class="name">Gatekeepen</span></h4></div></button>
                    <div><div class="flex"><span data-path="core_lbl_isrc_text" class="w-1/2">ISRC</span><span class="font-light">SE6132694461</span></div></div>
                </div>
            </div>
            <div class="px-4 bg-surface-3 rounded-lg mb-6">
                <div class="w-full">
                    <button><div class="flex-1"><h4 class="mb-1"><span class="text-primary mr-3">04</span><span class="name">Standort</span></h4></div></button>
                    <div><div class="flex"><span data-path="core_lbl_isrc_text" class="w-1/2">ISRC</span><span class="font-light">SE6132676302</span></div></div>
                </div>
            </div>
        </div>
        """

    def test_parse_table_html(self):
        releases = ReleaseListPage.parse_table_html(
            self.sample_row_html, "https://artist.amuse.io"
        )
        self.assertEqual(len(releases), 1)
        rel = releases[0]
        self.assertEqual(rel.release_id, "4560833")
        self.assertEqual(rel.title, "immer das gleiche")
        self.assertEqual(rel.artist, "shadowghost")
        self.assertEqual(rel.track_count, 1)
        self.assertEqual(rel.release_type, "Single")
        self.assertEqual(rel.release_date, "1 May 2026")
        self.assertEqual(rel.upc, "7300349759618")
        self.assertEqual(rel.url, "https://artist.amuse.io/studio/music/4560833")

    def test_parse_multi_track_detail_html(self):
        ep_summary = ReleaseSummary(
            release_id="999999",
            title="Meine EP",
            artist="shadowghost",
            track_count=4,
            release_date="10 May 2026",
            upc="1234567890123",
            url="https://artist.amuse.io/studio/music/999999",
        )
        tracks = ReleaseDetailPage.parse_detail_html(
            self.sample_ep_detail_html, ep_summary
        )
        self.assertEqual(len(tracks), 4)
        self.assertEqual(tracks[0].Release_Type if hasattr(tracks[0], 'Release_Type') else tracks[0].release_type, "EP")

        expected = [
            ("01", "nur so ein Gefühl", "SE6TI2632728"),
            ("02", "mit mir selbst", "SE6132694460"),
            ("03", "Gatekeepen", "SE6132694461"),
            ("04", "Standort", "SE6132676302"),
        ]
        for track, (exp_num, exp_title, exp_isrc) in zip(tracks, expected):
            self.assertEqual(track.track_number, exp_num)
            self.assertEqual(track.track_title, exp_title)
            self.assertEqual(track.isrc, exp_isrc)

    def test_csv_exporter_and_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test_export.csv"
            exporter = CSVExporter(csv_path)

            ep_summary = ReleaseSummary(
                "1", "Test", "shadowghost", 4, "2026", "111", "https://artist.amuse.io/studio/music/1"
            )
            tracks = ReleaseDetailPage.parse_detail_html(self.sample_ep_detail_html, ep_summary)
            exporter.append_tracks(tracks)

            scraped = exporter.get_already_scraped_urls()
            self.assertIn("https://artist.amuse.io/studio/music/1", scraped)


if __name__ == "__main__":
    unittest.main()