from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.dashboard.services import APIError


class DashboardViewTests(TestCase):
    # --------------------------------------------------
    # OVERVIEW TESTS
    # --------------------------------------------------

    @patch("apps.dashboard.views.fetch_products")
    def test_overview_loads(self, mock_fetch):

        mock_fetch.return_value = []

        response = self.client.get(reverse("dashboard:overview"))

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Overview")

        mock_fetch.assert_called_once()

    # --------------------------------------------------
    # INVENTORY TESTS
    # --------------------------------------------------

    @patch("apps.dashboard.views.fetch_products")
    def test_inventory_destination_loads(self, mock_fetch):

        mock_fetch.return_value = [
            {
                "id": 1,
                "title": "Cooking Oil",
                "category": "groceries",
                "price": 4.99,
                "stock": 10,
                "minimumOrderQuantity": 15,
                "sku": "COOK001",
                "meta": {
                    "barcode": "123456789",
                },
            }
        ]

        response = self.client.get(reverse("dashboard:inventory"))

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "dashboard/inventory.html",
        )

        self.assertContains(response, "Inventory Dashboard")
        self.assertContains(response, "Total Products")
        self.assertContains(response, "Inventory Records")
        self.assertContains(response, "Inventory Products")
        self.assertContains(response, "Cooking Oil")
        self.assertContains(response, "groceries")

        mock_fetch.assert_called_once()

    @patch("apps.dashboard.views.fetch_products")
    def test_inventory_handles_api_error(self, mock_fetch):

        mock_fetch.side_effect = APIError("Connection unavailable")

        response = self.client.get(reverse("dashboard:inventory"))

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "dashboard/inventory.html",
        )

        self.assertContains(response, "Inventory Dashboard")
        self.assertContains(response, "Connection unavailable")

        mock_fetch.assert_called_once()

    @patch("apps.dashboard.views.fetch_products")
    def test_inventory_empty_products(self, mock_fetch):

        mock_fetch.return_value = []

        response = self.client.get(reverse("dashboard:inventory"))

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "No inventory records available.",
        )

        self.assertContains(response, "Total Products")

        mock_fetch.assert_called_once()

    # --------------------------------------------------
    # CUSTOMER REVIEW TESTS
    # --------------------------------------------------

    @patch("apps.dashboard.views.fetch_products")
    def test_customer_review_loads(self, mock_fetch):

        mock_fetch.return_value = []

        response = self.client.get(reverse("dashboard:customer_review"))

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "dashboard/customer_review.html",
        )

        mock_fetch.assert_called_once()

    @patch("apps.dashboard.views.fetch_products")
    def test_customer_review_handles_api_error(self, mock_fetch):

        mock_fetch.side_effect = APIError("Connection unavailable")

        response = self.client.get(reverse("dashboard:customer_review"))

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            "Connection unavailable",
        )

    # --------------------------------------------------
    # SAVED ORDERS TEST HELPERS
    # --------------------------------------------------

    def save_inventory_order(self):

        session = self.client.session

        session["inventory_orders"] = {
            "101": {
                "product_id": "101",
                "title": "Cooking Oil",
                "price": "4.99",
                "quantity": 2,
                "sku": "COOK001",
            }
        }

        session.save()

    # --------------------------------------------------
    # UNIFIED SAVED ORDERS TESTS
    # --------------------------------------------------
    @patch("apps.dashboard.views.get_unified_saved_orders")
    @patch("apps.dashboard.views.fetch_products")
    @patch("apps.dashboard.views.get_in_stock_orders")
    @patch("apps.dashboard.views.get_low_stock_orders")
    @patch("apps.dashboard.views.get_out_of_stock_orders")
    def test_saved_orders_loads(
        self, mock_out, mock_low, mock_in, mock_fetch, mock_unified
    ):

        mock_unified.return_value = [
            {
                "product_id": "101",
                "title": "Cooking Oil",
                "price": Decimal("4.99"),
                "quantity": 2,
                "line_total": Decimal("9.98"),
            }
        ]

        response = self.client.get(reverse("dashboard:saved_orders"))

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "dashboard/saved_orders.html",
        )

        self.assertContains(response, "Cooking Oil")

        self.assertEqual(response.context["total_items"], 1)
        self.assertEqual(response.context["total_quantity"], 2)
        self.assertEqual(
            response.context["cart_total"],
            Decimal("9.98"),
        )

        self.assertEqual(
            response.context["counts"]["in_stock"],
            1,
        )

    @patch("apps.dashboard.views.fetch_products")
    @patch("apps.dashboard.views.get_in_stock_orders")
    @patch("apps.dashboard.views.get_low_stock_orders")
    @patch("apps.dashboard.views.get_out_of_stock_orders")
    def test_saved_orders_filter_by_status(
        self,
        mock_out,
        mock_low,
        mock_in,
        mock_fetch,
    ):

        self.save_inventory_order()

        mock_out.return_value = {}
        mock_low.return_value = {}
        mock_in.return_value = {}

        mock_fetch.return_value = [
            {
                "id": 101,
                "title": "Cooking Oil",
                "price": 4.99,
                "stock": 10,
            }
        ]

        response = self.client.get(
            reverse("dashboard:saved_orders"),
            {"status": "in_stock"},
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            len(response.context["orders"]),
            1,
        )

        self.assertEqual(
            response.context["selected_status"],
            "in_stock",
        )

    @patch("apps.dashboard.views.fetch_products")
    @patch("apps.dashboard.views.get_in_stock_orders")
    @patch("apps.dashboard.views.get_low_stock_orders")
    @patch("apps.dashboard.views.get_out_of_stock_orders")
    def test_saved_orders_search(
        self,
        mock_out,
        mock_low,
        mock_in,
        mock_fetch,
    ):

        self.save_inventory_order()

        mock_out.return_value = {}
        mock_low.return_value = {}
        mock_in.return_value = {}

        mock_fetch.return_value = [
            {
                "id": 101,
                "title": "Cooking Oil",
                "price": 4.99,
                "stock": 10,
            }
        ]

        response = self.client.get(
            reverse("dashboard:saved_orders"),
            {"q": "Cooking"},
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            len(response.context["orders"]),
            1,
        )

        self.assertEqual(
            response.context["search_query"],
            "Cooking",
        )

    # --------------------------------------------------
    # REMOVE SAVED ORDER TESTS
    # --------------------------------------------------

    def test_remove_inventory_saved_order(self):

        self.save_inventory_order()

        response = self.client.post(
            reverse(
                "dashboard:remove_saved_order",
                kwargs={
                    "source": "inventory",
                    "product_id": "101",
                },
            ),
            {
                "status": "all",
                "q": "",
                "page": "1",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.assertRedirects(
            response,
            reverse("dashboard:saved_orders") + "?status=all&q=&page=1",
            fetch_redirect_response=False,
        )

        session = self.client.session

        self.assertNotIn(
            "101",
            session.get("inventory_orders", {}),
        )

    def test_remove_saved_order_rejects_get_request(self):

        response = self.client.get(
            reverse(
                "dashboard:remove_saved_order",
                kwargs={
                    "source": "inventory",
                    "product_id": "101",
                },
            )
        )

        self.assertEqual(response.status_code, 302)

    def test_remove_saved_order_rejects_invalid_source(self):

        response = self.client.post(
            reverse(
                "dashboard:remove_saved_order",
                kwargs={
                    "source": "invalid",
                    "product_id": "101",
                },
            )
        )

        self.assertEqual(response.status_code, 302)

    # --------------------------------------------------
    # PRINT SAVED ORDERS TESTS
    # --------------------------------------------------
    @patch("apps.dashboard.views.get_unified_saved_orders")
    def test_submit_saved_orders_loads_print_template(
        self,
        mock_unified,
    ):
        self.save_inventory_order()

        mock_unified.return_value = [
            {
                "product_id": "101",
                "product_name": "Cooking Oil",
                "title": "Cooking Oil",
                "price": Decimal("4.99"),
                "unit_price": Decimal("4.99"),
                "quantity": 2,
                "stock_status": "in_stock",
                "line_total": Decimal("9.98"),
            }
        ]

        response = self.client.post(reverse("dashboard:submit_saved_orders"))

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "dashboard/print_orders.html",
        )

        self.assertContains(response, "Cooking Oil")

        self.assertEqual(response.context["total_items"], 1)
        self.assertEqual(response.context["total_quantity"], 2)

        self.assertEqual(
            response.context["cart_total"],
            Decimal("9.98"),
        )

        # Printing must not clear Browser Memory.
        session = self.client.session

        self.assertIn(
            "101",
            session["inventory_orders"],
        )

    def test_submit_saved_orders_rejects_get_request(self):

        response = self.client.get(reverse("dashboard:submit_saved_orders"))

        self.assertEqual(response.status_code, 302)

    @patch("apps.dashboard.views.fetch_products")
    @patch("apps.dashboard.views.get_in_stock_orders")
    @patch("apps.dashboard.views.get_low_stock_orders")
    @patch("apps.dashboard.views.get_out_of_stock_orders")
    def test_submit_saved_orders_empty_cart(
        self,
        mock_out,
        mock_low,
        mock_in,
        mock_fetch,
    ):

        mock_out.return_value = {}
        mock_low.return_value = {}
        mock_in.return_value = {}

        mock_fetch.return_value = []

        response = self.client.post(reverse("dashboard:submit_saved_orders"))

        self.assertEqual(response.status_code, 302)

        self.assertRedirects(
            response,
            reverse("dashboard:saved_orders"),
            fetch_redirect_response=False,
        )


from apps.dashboard.logistics_analytics import (
    calculate_logistics_analytics,
    parse_shipping_days,
    parse_warranty_days,
)


class LogisticsAnalyticsTests(TestCase):
    def test_shipping_conversion(self):
        self.assertEqual(
            parse_shipping_days("Ships overnight"),
            1.0,
        )

        self.assertEqual(
            parse_shipping_days("Ships in 1-2 business days"),
            2.1,
        )

        self.assertAlmostEqual(
            parse_shipping_days("Ships in 3 business days"),
            4.2,
            places=2,
        )

    def test_warranty_conversion(self):
        self.assertEqual(
            parse_warranty_days("1 week warranty"),
            7.0,
        )

        self.assertEqual(
            parse_warranty_days("1 month warranty"),
            30.0,
        )

        self.assertEqual(
            parse_warranty_days("1 year warranty"),
            365.0,
        )

        self.assertEqual(
            parse_warranty_days("No warranty"),
            0.0,
        )

    def test_lifetime_warranty_excluded_from_numeric_value(self):
        self.assertIsNone(parse_warranty_days("Lifetime warranty"))

    def test_category_medians(self):

        products = [
            {
                "category": "electronics",
                "price": 100,
                "rating": 4.0,
                "shippingInformation": "Ships overnight",
                "warrantyInformation": "1 year warranty",
            },
            {
                "category": "electronics",
                "price": 200,
                "rating": 5.0,
                "shippingInformation": "Ships overnight",
                "warrantyInformation": "1 month warranty",
            },
        ]

        records = calculate_logistics_analytics(products)

        electronics = records[0]

        self.assertEqual(
            electronics["median_price"],
            150,
        )

        self.assertEqual(
            electronics["median_rating"],
            4.5,
        )

        self.assertEqual(
            electronics["median_shipping_days"],
            1.0,
        )

        self.assertEqual(
            electronics["median_warranty_days"],
            197.5,
        )

    def test_lifetime_products_are_counted_separately(self):

        products = [
            {
                "category": "electronics",
                "price": 100,
                "rating": 4.0,
                "shippingInformation": "Ships overnight",
                "warrantyInformation": "1 year warranty",
            },
            {
                "category": "electronics",
                "price": 200,
                "rating": 5.0,
                "shippingInformation": "Ships overnight",
                "warrantyInformation": "Lifetime warranty",
            },
        ]

        records = calculate_logistics_analytics(products)

        electronics = records[0]

        self.assertEqual(
            electronics["lifetime_count"],
            1,
        )

        self.assertEqual(
            electronics["median_warranty_days"],
            365.0,
        )

        self.assertEqual(
            electronics["lifetime_median_price"],
            200,
        )

        self.assertEqual(
            electronics["lifetime_median_rating"],
            5.0,
        )


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

    self.assertEqual(
        response.context["product_count"],
        2,
    )

    self.assertEqual(
        response.context["lifetime_product_count"],
        1,
    )

    self.assertEqual(
        len(response.context["chart_data"]),
        7,
    )

    mock_fetch.assert_called_once()
