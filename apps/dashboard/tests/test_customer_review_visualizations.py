from django.test import SimpleTestCase

from apps.dashboard.review_visualizations import ReviewChartService


class CustomerReviewVisualizationTests(SimpleTestCase):
    def test_pie_chart_generates_image(self):

        distribution = [
            {"rating": 1, "count": 2},
            {"rating": 2, "count": 3},
            {"rating": 3, "count": 5},
            {"rating": 4, "count": 10},
            {"rating": 5, "count": 20},
        ]

        results, image = ReviewChartService.prepare_pie_chart(distribution)

        self.assertEqual(len(results), 5)
        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_category_chart_generates_image(self):

        distribution = [
            {
                "category": "beauty",
                "ratings": [
                    {"rating": 1, "count": 1},
                    {"rating": 2, "count": 2},
                    {"rating": 3, "count": 3},
                    {"rating": 4, "count": 4},
                    {"rating": 5, "count": 5},
                ],
            }
        ]

        results, image = ReviewChartService.prepare_category_bar_chart(distribution)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["category"], "beauty")
        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_empty_pie_chart(self):

        results, image = ReviewChartService.prepare_pie_chart([])

        self.assertEqual(sum(item["count"] for item in results), 0)
        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_empty_category_chart(self):

        results, image = ReviewChartService.prepare_category_bar_chart([])

        self.assertEqual(results, [])
        self.assertTrue(image.startswith("data:image/png;base64,"))
