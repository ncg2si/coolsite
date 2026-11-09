import unittest
import warnings
from unittest.mock import patch

import validate


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "timezone": "GMT",
            "hourly": {
                "time": ["2026-06-01T00:00"] * 24,
                "temperature_2m": [10] * 24,
                "relative_humidity_2m": [70] * 24,
                "dew_point_2m": [5] * 24,
            },
        }

    def test_unexpected_field_warns_without_stopping_validation(self):
        self.data["hourly"]["extra_field"] = [1] * 24

        with patch("validate.load_bronze", return_value=self.data):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                validate.validate("frankfurt", "2026-06-01", "2026-06-01")

        self.assertEqual(len(caught), 1)
        self.assertIn("DQ-01 warning: unexpected fields", str(caught[0].message))

    def test_missing_time_field_raises_validation_error(self):
        del self.data["hourly"]["time"]

        with patch("validate.load_bronze", return_value=self.data):
            with self.assertRaisesRegex(ValueError, "DQ-01 failed: missing fields"):
                validate.validate("frankfurt", "2026-06-01", "2026-06-01")


if __name__ == "__main__":
    unittest.main()
