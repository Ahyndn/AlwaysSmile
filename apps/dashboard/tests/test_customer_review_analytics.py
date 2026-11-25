from django.test import SimpleTestCase

from apps.dashboard.review_analytics import CustomerReviewAnalytics


class CustomerReviewAnalyticsTests(SimpleTestCase):
    def setUp(self):
        self.products = [
            {
                "category": "beauty",
                "reviews": [
                    {"rating": 5},
                    {"rating": 4},
                    {"rating": 3},
                ],
            },
            {
                "category": "beauty",
                "reviews": [
                    {"rating": 2},
                    {"rating": 1},
                ],
            },
            {
                "category": "laptops",
                "reviews": [
                    {"rating": 5},
                    {"rating": 5},
                ],
            },
        ]

        self.analytics = CustomerReviewAnalytics()

    def test_total_reviews(self):
        result = self.analytics.analyze(self.products)

        self.assertEqual(result["total_reviews"], 7)

    def test_star_distribution(self):
        result = self.analytics.analyze(self.products)

        counts = {item["rating"]: item["count"] for item in result["star_distribution"]}

        self.assertEqual(
            counts,
            {
                1: 1,
                2: 1,
                3: 1,
                4: 1,
                5: 3,
            },
        )

    def test_reviews_are_grouped_by_api_category(self):
        result = self.analytics.analyze(self.products)

        self.assertEqual(
            result["categories"],
            ["beauty", "laptops"],
        )

    def test_category_star_distribution(self):
        result = self.analytics.analyze(self.products)

        beauty = result["category_distribution"][0]

        self.assertEqual(beauty["category"], "beauty")
        self.assertEqual(
            [item["count"] for item in beauty["ratings"]],
            [1, 1, 1, 1, 1],
        )

    def test_empty_products(self):
        result = self.analytics.analyze([])

        self.assertEqual(result["total_reviews"], 0)
        self.assertEqual(result["categories"], [])
        self.assertEqual(
            sum(item["count"] for item in result["star_distribution"]),
            0,
        )

    def test_invalid_ratings_are_excluded_from_star_distribution(self):
        products = [
            {
                "category": "beauty",
                "reviews": [
                    {"rating": 5},
                    {"rating": 6},
                    {"rating": "invalid"},
                ],
            }
        ]

        result = self.analytics.analyze(products)

        self.assertEqual(result["total_reviews"], 3)
        self.assertEqual(
            sum(item["count"] for item in result["star_distribution"]),
            1,
        )
