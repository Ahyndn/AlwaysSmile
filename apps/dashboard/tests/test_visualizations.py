from decimal import Decimal

from django.test import SimpleTestCase

from apps.dashboard.visualizations import (
    prepare_bar_chart,
    prepare_pie_chart,
)


class VisualizationTests(SimpleTestCase):
    def setUp(self):
        self.sales = {
            "Men": Decimal(100),
            "Women": Decimal(300),
            "Food": Decimal(100),
        }

    def test_bar_chart_returns_category_data_and_image(self):
        result, image = prepare_bar_chart(self.sales)

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["category"], "Men")
        self.assertAlmostEqual(result[0]["width"], 100 / 3)
        self.assertEqual(result[1]["width"], 100)
        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_pie_chart_returns_percentages_and_image(self):
        result, image = prepare_pie_chart(self.sales)

        self.assertEqual(len(result), 3)
        self.assertAlmostEqual(
            sum(item["percentage"] for item in result),
            100,
        )
        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_empty_pie_chart_returns_zero_percentages_and_image(self):
        result, image = prepare_pie_chart(
            {
                "Men": Decimal(0),
                "Women": Decimal(0),
            }
        )

        self.assertEqual(
            sum(item["percentage"] for item in result),
            0,
        )
        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_empty_bar_chart_returns_empty_data_and_image(self):
        result, image = prepare_bar_chart({})

        self.assertEqual(result, [])
        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_bar_chart_handles_zero_values(self):
        result, image = prepare_bar_chart(
            {
                "Men": Decimal(0),
                "Women": Decimal(0),
            }
        )

        self.assertEqual(len(result), 2)

        self.assertEqual(
            [item["width"] for item in result],
            [0, 0],
        )

        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_bar_chart_handles_negative_values(self):
        result, image = prepare_bar_chart(
            {
                "Men": Decimal(-100),
                "Women": Decimal(200),
            }
        )

        self.assertEqual(result[0]["value"], 0)
        self.assertEqual(result[1]["value"], 200)

    def test_pie_chart_handles_zero_values(self):
        result, image = prepare_pie_chart(
            {
                "Men": Decimal(0),
                "Women": Decimal(0),
            }
        )

        self.assertEqual(
            sum(item["percentage"] for item in result),
            0,
        )

        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_pie_chart_handles_negative_values(self):
        result, image = prepare_pie_chart(
            {
                "Men": Decimal(-100),
                "Women": Decimal(100),
            }
        )

        self.assertEqual(result[0]["value"], 0)
        self.assertEqual(result[1]["value"], 100)
        self.assertEqual(result[1]["percentage"], 100)
