from django.test import SimpleTestCase

from apps.dashboard.review_analytics import ReviewAnalyticsService


class ReviewFilteringTests(SimpleTestCase):
    def setUp(self):

        self.products = [
            {
                "title": "Beauty Product",
                "category": "beauty",
                "reviews": [
                    {
                        "rating": 5,
                        "comment": "Excellent quality",
                        "date": "2026-02-10T10:00:00Z",
                        "reviewerName": "Alice",
                        "reviewerEmail": "alice@example.com",
                    },
                    {
                        "rating": 3,
                        "comment": "Average product",
                        "date": "2026-03-15T10:00:00Z",
                        "reviewerName": "Bob",
                        "reviewerEmail": "bob@example.com",
                    },
                ],
            },
            {
                "title": "Electronic Product",
                "category": "electronics",
                "reviews": [
                    {
                        "rating": 5,
                        "comment": "Excellent performance",
                        "date": "2026-04-20T10:00:00Z",
                        "reviewerName": "Charlie",
                        "reviewerEmail": "charlie@example.com",
                    },
                    {
                        "rating": 2,
                        "comment": "Poor quality",
                        "date": "2026-05-10T10:00:00Z",
                        "reviewerName": "David",
                        "reviewerEmail": "david@example.com",
                    },
                ],
            },
        ]

    def test_keyword_search(self):

        results = ReviewAnalyticsService.filter_reviews(
            self.products,
            search="excellent",
        )

        self.assertEqual(len(results), 2)

    def test_rating_filter(self):

        results = ReviewAnalyticsService.filter_reviews(
            self.products,
            rating="5",
        )

        self.assertEqual(len(results), 2)

        self.assertTrue(all(review["rating"] == 5 for review in results))

    def test_category_filter(self):

        results = ReviewAnalyticsService.filter_reviews(
            self.products,
            category="beauty",
        )

        self.assertEqual(len(results), 2)

        self.assertTrue(all(review["category"] == "beauty" for review in results))

    def test_date_range_filter(self):

        results = ReviewAnalyticsService.filter_reviews(
            self.products,
            start_date="2026-03-01",
            end_date="2026-04-30",
        )

        self.assertEqual(len(results), 2)

    def test_combined_filters(self):

        results = ReviewAnalyticsService.filter_reviews(
            self.products,
            search="excellent",
            rating="5",
            category="beauty",
        )

        self.assertEqual(len(results), 1)

        self.assertEqual(
            results[0]["reviewer_name"],
            "Alice",
        )

    def test_no_matching_reviews(self):

        results = ReviewAnalyticsService.filter_reviews(
            self.products,
            search="nonexistent",
        )

        self.assertEqual(results, [])

    def test_invalid_rating_does_not_crash(self):

        results = ReviewAnalyticsService.filter_reviews(
            self.products,
            rating="invalid",
        )

        self.assertEqual(len(results), 4)

    def test_category_list(self):

        categories = ReviewAnalyticsService.get_review_categories(self.products)

        self.assertEqual(
            categories,
            ["beauty", "electronics"],
        )
