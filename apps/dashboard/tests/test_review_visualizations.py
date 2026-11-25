from django.test import SimpleTestCase

from apps.dashboard.review_visualizations import ReviewChartService


class ReviewChartServiceTests(SimpleTestCase):
    def test_pie_chart_handles_invalid_ratings(self):
        results, _ = ReviewChartService.prepare_pie_chart(
            [
                {"rating": 6, "count": 10},
                {"rating": "invalid", "count": 5},
                {"rating": 5, "count": 3},
            ]
        )

        self.assertEqual(
            sum(item["count"] for item in results),
            3,
        )

        self.assertEqual(results[4]["count"], 3)

    def test_pie_chart_aggregates_duplicate_ratings(self):
        results, _ = ReviewChartService.prepare_pie_chart(
            [
                {"rating": 5, "count": 10},
                {"rating": 5, "count": 5},
            ]
        )

        self.assertEqual(results[4]["count"], 15)

    def test_category_chart_handles_empty_ratings(self):
        results, image = ReviewChartService.prepare_category_bar_chart(
            [
                {"category": "Beauty", "ratings": []},
            ]
        )

        self.assertEqual(len(results), 1)

        self.assertEqual(
            [item["count"] for item in results[0]["ratings"]],
            [0, 0, 0, 0, 0],
        )

        self.assertTrue(image.startswith("data:image/png;base64,"))
