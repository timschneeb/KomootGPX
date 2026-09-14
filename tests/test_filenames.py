import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import gpxpy
from PIL import Image

from komootgpx import komootgpx


class FilenameTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.output = Path(directory.name)
        hashes = patch.object(komootgpx, "HASHFILE", str(self.output / "hashes.json"))
        hashes.start()
        self.addCleanup(hashes.stop)
        self.api = Mock(spec=komootgpx.KomootApi)
        self.api.display_name = "Test rider"
        self.cfg = komootgpx.RunConfig(
            api=self.api,
            output_dir=str(self.output),
            filename_pattern="{date}_{time}_{title}.gpx",
            image_dir_pattern="{date}_{time}_{title}_images",
            no_poi=True,
            skip_existing=False,
            skip_unchanged=False,
            remove_deleted=False,
            max_title_length=-1,
            max_desc_length=-1,
            all_images=False,
            language="en",
            karoo=False,
        )

    def tour(self, tour_id, date):
        return {
            "id": tour_id,
            "name": "Ride",
            "type": "tour_recorded",
            "date": date,
            "changed_at": "2026-09-15T12:34:56.000Z",
            "distance": 1000,
            "duration": 600,
            "elevation_up": 10,
            "elevation_down": 10,
            "_embedded": {
                "coordinates": {"items": [{"lat": 51.0, "lng": 0.0, "t": 0}]},
                "creator": {"display_name": "Test rider", "username": "123"},
            },
        }

    def test_gpx_filenames_keep_distinct_tour_times(self):
        cases = (
            (1, "2026-09-14T00:00:00.000Z", "000000"),
            (2, "2026-09-14T09:18:27.123Z", "091827"),
            (3, "2026-09-14T23:59:59.000+02:00", "235959"),
        )
        for tour_id, date, expected_time in cases:
            with self.subTest(date=date):
                self.api.fetch_tour.return_value = self.tour(tour_id, date)
                komootgpx.make_gpx(self.cfg, tour_id, None)
                path = self.output / f"2026-09-14_{expected_time}_Ride.gpx"
                self.assertTrue(path.is_file(), sorted(p.name for p in self.output.glob("*.gpx")))
                gpx = gpxpy.parse(path.read_text(encoding="utf-8"))
                self.assertEqual(gpx.link, f"https://www.komoot.de/tour/{tour_id}")
        self.assertEqual(len(list(self.output.glob("*.gpx"))), len(cases))

    def test_image_directories_keep_distinct_tour_times(self):
        jpeg = io.BytesIO()
        Image.new("RGB", (1, 1)).save(jpeg, format="JPEG")
        self.api.fetch_tour_images.return_value = {
            7: {
                "id": 7,
                "src": "https://example.invalid/image.jpg",
                "created_at": "2026-09-14T10:20:30.000Z",
                "_embedded": {"creator": {"display_name": "Test rider"}},
            },
        }
        cases = (
            (1, "2026-09-14T00:00:00.000Z", "000000"),
            (2, "2026-09-14T09:18:27.123Z", "091827"),
            (3, "2026-09-14T23:59:59.000+02:00", "235959"),
        )
        with patch.object(
            komootgpx.ImageDownloaderWithExif,
            "_download_image_bytes",
            return_value=(jpeg.getvalue(), False),
        ):
            for tour_id, date, expected_time in cases:
                with self.subTest(date=date):
                    komootgpx.download_tour_images(self.cfg, tour_id, self.tour(tour_id, date))
                    directory = self.output / f"2026-09-14_{expected_time}_Ride_images"
                    self.assertTrue(directory.is_dir(), sorted(p.name for p in self.output.iterdir()))
                    with Image.open(directory / "20260914-102030-hl7.jpg") as image:
                        self.assertEqual(image.format, "JPEG")
        self.assertEqual(len(list(self.output.glob("*_images"))), len(cases))


if __name__ == "__main__":
    unittest.main()
