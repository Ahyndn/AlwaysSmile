from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse


class CustomerReviewViewTests(SimpleTestCase):
    @patch("apps.dashboard.views.fetch_products")
    def test_customer_review_page_loads(self, mock_fetch):

        mock_fetch.return_value = []

        response = self.client.get(reverse("dashboard:customer_review"))

        self.assertEqual(response.status_code, 200)

    @patch("apps.dashboard.views.fetch_products")
    def test_customer_review_summary_is_available(self, mock_fetch):

        mock_fetch.return_value = [
            {
                "reviews": [
                    {"rating": 5},
                    {"rating": 4},
                    {"rating": 3},
                ]
            }
        ]

        response = self.client.get(reverse("dashboard:customer_review"))

        self.assertEqual(
            response.context["review_summary"]["total_reviews"],
            3,
        )

    @patch("apps.dashboard.views.fetch_products")
    def test_customer_review_rating_distribution(self, mock_fetch):

        mock_fetch.return_value = [
            {
                "category": "beauty",
                "reviews": [
                    {"rating": 5},
                    {"rating": 4},
                    {"rating": 5},
                ],
            }
        ]

        response = self.client.get(reverse("dashboard:customer_review"))

        self.assertEqual(
            response.context["rating_distribution"],
            {1: 0, 2: 0, 3: 0, 4: 1, 5: 2},
        )

    @patch("apps.dashboard.views.fetch_products")
    def test_customer_review_api_error(self, mock_fetch):

        from apps.dashboard.services import APIError

        mock_fetch.side_effect = APIError("Connection unavailable")

        response = self.client.get(reverse("dashboard:customer_review"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "API connection error")
