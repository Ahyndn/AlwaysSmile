"""Integration tests for the logistics dashboard view."""

from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.dashboard.services import APIError


class LogisticsDashboardViewTests(TestCase):
    """Test logistics dashboard responses and context."""

    @patch("apps.dashboard.views.fetch_products")
    def test_logistics_dashboard_loads(self, mock_fetch):

        mock_fetch.return_value = [
            {
                "id": 1,
                "title": "Laptop",
                "category": "electronics",
                "price": 1000,
                "rating": 4.5,
                "shippingInformation": "Ships overnight",
                "warrantyInformation": "1 year warranty",
            },
            {
                "id": 2,
                "title": "Monitor",
                "category": "electronics",
                "price": 500,
                "rating": 4.0,
                "shippingInformation": "Ships overnight",
                "warrantyInformation": "Lifetime warranty",
            },
        ]

        response = self.client.get(reverse("dashboard:logistics"))

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "dashboard/logistics.html",
        )

        self.assertContains(
            response,
            "Logistics Dashboard",
        )

        self.assertEqual(
            response.context["product_count"],
            2,
        )

        self.assertEqual(
            response.context["category_count"],
            1,
        )

        self.assertEqual(
            response.context["lifetime_product_count"],
            1,
        )

        self.assertEqual(
            response.context["numeric_warranty_category_count"],
            1,
        )

        self.assertEqual(
            len(response.context["logistics_records"]),
            1,
        )

        self.assertEqual(
            len(response.context["chart_data"]),
            7,
        )

        mock_fetch.assert_called_once()

    @patch("apps.dashboard.views.fetch_products")
    def test_logistics_dashboard_handles_empty_products(
        self,
        mock_fetch,
    ):

        mock_fetch.return_value = []

        response = self.client.get(reverse("dashboard:logistics"))

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "dashboard/logistics.html",
        )

        self.assertEqual(
            response.context["product_count"],
            0,
        )

        self.assertEqual(
            response.context["category_count"],
            0,
        )

        self.assertEqual(
            response.context["lifetime_product_count"],
            0,
        )

        self.assertEqual(
            response.context["numeric_warranty_category_count"],
            0,
        )

        self.assertEqual(
            len(response.context["logistics_records"]),
            0,
        )

        self.assertEqual(
            len(response.context["chart_data"]),
            7,
        )

        mock_fetch.assert_called_once()

    @patch("apps.dashboard.views.fetch_products")
    def test_logistics_dashboard_handles_api_error(
        self,
        mock_fetch,
    ):

        mock_fetch.side_effect = APIError("Connection unavailable")

        response = self.client.get(reverse("dashboard:logistics"))

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "dashboard/logistics.html",
        )

        self.assertContains(
            response,
            "Connection unavailable",
        )

        self.assertEqual(
            response.context["product_count"],
            0,
        )

        self.assertEqual(
            len(response.context["chart_data"]),
            7,
        )

        mock_fetch.assert_called_once()

    @patch("apps.dashboard.views.fetch_products")
    def test_logistics_dashboard_separates_lifetime_warranties(
        self,
        mock_fetch,
    ):

        mock_fetch.return_value = [
            {
                "id": 1,
                "category": "electronics",
                "price": 100,
                "rating": 4.0,
                "shippingInformation": "Ships overnight",
                "warrantyInformation": "1 year warranty",
            },
            {
                "id": 2,
                "category": "electronics",
                "price": 200,
                "rating": 5.0,
                "shippingInformation": "Ships overnight",
                "warrantyInformation": "Lifetime warranty",
            },
            {
                "id": 3,
                "category": "electronics",
                "price": 300,
                "rating": 4.5,
                "shippingInformation": "Ships overnight",
                "warrantyInformation": "Lifelong warranty",
            },
        ]

        response = self.client.get(reverse("dashboard:logistics"))

        self.assertEqual(response.status_code, 200)

        record = response.context["logistics_records"][0]

        self.assertEqual(record["product_count"], 3)
        self.assertEqual(record["lifetime_count"], 2)

        self.assertEqual(
            record["median_warranty_days"],
            365.0,
        )

        self.assertEqual(
            record["lifetime_median_price"],
            250,
        )

        self.assertEqual(
            record["lifetime_median_rating"],
            4.75,
        )

    @patch("apps.dashboard.views.fetch_products")
    def test_logistics_dashboard_contains_regression_charts(
        self,
        mock_fetch,
    ):

        mock_fetch.return_value = [
            {
                "id": 1,
                "category": "electronics",
                "price": 100,
                "rating": 3.0,
                "shippingInformation": "Ships overnight",
                "warrantyInformation": "1 month warranty",
            },
            {
                "id": 2,
                "category": "groceries",
                "price": 200,
                "rating": 4.0,
                "shippingInformation": "Ships in 2 days",
                "warrantyInformation": "2 months warranty",
            },
            {
                "id": 3,
                "category": "furniture",
                "price": 300,
                "rating": 5.0,
                "shippingInformation": "Ships in 3 days",
                "warrantyInformation": "1 year warranty",
            },
        ]

        response = self.client.get(reverse("dashboard:logistics"))

        self.assertEqual(response.status_code, 200)

        chart_data = response.context["chart_data"]

        numeric_chart_keys = [
            "price_rating",
            "rating_shipping",
            "price_shipping",
            "warranty_rating",
            "warranty_price",
        ]

        for key in numeric_chart_keys:
            with self.subTest(chart=key):
                figure = chart_data[key]

                self.assertEqual(
                    len(figure["data"]),
                    2,
                )

                self.assertEqual(
                    figure["data"][1]["name"],
                    "Overall linear regression",
                )

                self.assertEqual(
                    figure["data"][1]["mode"],
                    "lines",
                )

    @patch("apps.dashboard.views.fetch_products")
    def test_logistics_dashboard_ignores_invalid_products(
        self,
        mock_fetch,
    ):

        mock_fetch.return_value = [
            None,
            "invalid",
            {
                "id": 1,
                "category": "electronics",
                "price": -100,
                "rating": float("nan"),
                "shippingInformation": "Unknown",
                "warrantyInformation": "Unknown",
            },
        ]

        response = self.client.get(reverse("dashboard:logistics"))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.context["product_count"],
            1,
        )

        record = response.context["logistics_records"][0]

        self.assertIsNone(record["median_price"])
        self.assertIsNone(record["median_rating"])
        self.assertIsNone(record["median_shipping_days"])
        self.assertIsNone(record["median_warranty_days"])
