from django.test import SimpleTestCase

from apps.dashboard.review_analytics import (
    ReviewAnalyticsService,
    calculate_review_summary,
)


class ReviewAnalyticsTests(SimpleTestCase):
    def setUp(self):
        self.products = [
            {
                "category": "beauty",
                "reviews": [
                    {
                        "rating": 1,
                        "comment": "Poor",
                        "date": "2026-10-01",
                    },
                    {
                        "rating": 2,
                        "comment": "Below average",
                        "date": "2026-10-02",
                    },
                    {
                        "rating": 3,
                        "comment": "Average",
                        "date": "2026-10-03",
                    },
                    {
                        "rating": 4,
                        "comment": "Good",
                        "date": "2026-10-04",
                    },
                    {
                        "rating": 5,
                        "comment": "Excellent",
                        "date": "2026-10-05",
                    },
                ],
            }
        ]

    def test_rating_distribution(self):
        result = ReviewAnalyticsService.calculate_rating_distribution(self.products)

        self.assertEqual(
            result,
            {
                1: 1,
                2: 1,
                3: 1,
                4: 1,
                5: 1,
            },
        )

    def test_rating_distribution_includes_zero_counts(self):
        result = ReviewAnalyticsService.calculate_rating_distribution([])

        self.assertEqual(
            result,
            {
                1: 0,
                2: 0,
                3: 0,
                4: 0,
                5: 0,
            },
        )

    def test_review_summary(self):
        result = calculate_review_summary(self.products)

        self.assertEqual(
            result,
            {
                "total_reviews": 5,
                "positive_reviews": 2,
                "neutral_reviews": 1,
                "negative_reviews": 2,
            },
        )

    def test_category_rating_distribution(self):
        result = ReviewAnalyticsService.calculate_category_review_distribution(
            self.products
        )

        self.assertEqual(
            result["beauty"],
            {1: 1, 2: 1, 3: 1, 4: 1, 5: 1},
        )

    def test_filter_by_rating(self):
        result = ReviewAnalyticsService.filter_reviews(
            self.products,
            rating="5",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["rating"], 5)

    def test_filter_by_keyword(self):
        result = ReviewAnalyticsService.filter_reviews(
            self.products,
            search="excellent",
        )

        self.assertEqual(len(result), 1)

    def test_filter_by_category(self):
        result = ReviewAnalyticsService.filter_reviews(
            self.products,
            category="beauty",
        )

        self.assertEqual(len(result), 5)
