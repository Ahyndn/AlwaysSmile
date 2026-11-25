from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from apps.dashboard.out_of_stock_orders import (
    SESSION_KEY,
    add_out_of_stock_order,
    build_out_of_stock_orders,
    calculate_order_totals,
    clear_out_of_stock_orders,
    delete_out_of_stock_order,
    get_out_of_stock_orders,
)


class TestSession(dict):
    """Dictionary-backed session for service unit tests."""

    modified = False

    def save(self):
        self.modified = False


def make_request():
    """Create a request-like object with a stable session."""
    return SimpleNamespace(session=TestSession())


class OutOfStockOrderServiceTests(TestCase):
    """Regression tests for out-of-stock order services."""

    def setUp(self):
        self.request = make_request()

        self.products = [
            {
                "id": 1,
                "title": "Cooking Oil",
                "category": "groceries",
                "sku": "COOK001",
                "price": 4.99,
                "stock": 0,
                "minimumOrderQuantity": 15,
            },
            {
                "id": 2,
                "title": "Rice",
                "category": "groceries",
                "sku": "RICE001",
                "price": 10.50,
                "stock": 20,
                "minimumOrderQuantity": 10,
            },
        ]

    def test_build_out_of_stock_orders_returns_zero_stock_products(self):
        result = build_out_of_stock_orders(self.products)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "1")
        self.assertEqual(result[0]["title"], "Cooking Oil")
        self.assertEqual(result[0]["stock"], 0)
        self.assertEqual(result[0]["minimum_order_quantity"], 15)

    def test_build_out_of_stock_orders_excludes_in_stock_products(self):
        result = build_out_of_stock_orders(self.products)

        product_ids = [item["id"] for item in result]

        self.assertNotIn("2", product_ids)

    def test_build_out_of_stock_orders_uses_minimum_quantity(self):
        result = build_out_of_stock_orders(self.products)

        self.assertEqual(result[0]["quantity_to_order"], 15)

    def test_build_out_of_stock_orders_returns_decimal_price(self):
        result = build_out_of_stock_orders(self.products)

        self.assertEqual(result[0]["price"], Decimal("4.99"))

    def test_build_out_of_stock_orders_handles_empty_products(self):
        self.assertEqual(build_out_of_stock_orders([]), [])

    def test_build_out_of_stock_orders_skips_invalid_products(self):
        products = [
            {
                "id": 1,
                "title": "Invalid Price",
                "stock": 0,
                "minimumOrderQuantity": 5,
                "price": "invalid",
            },
            {
                "id": 2,
                "title": "Negative Stock",
                "stock": -1,
                "minimumOrderQuantity": 5,
                "price": 10,
            },
            {
                "id": 3,
                "title": "Negative MOQ",
                "stock": 0,
                "minimumOrderQuantity": -5,
                "price": 10,
            },
        ]

        self.assertEqual(build_out_of_stock_orders(products), [])

    def test_build_orders_rejects_infinite_price(self):
        products = [
            {
                "id": 1,
                "title": "Invalid Price",
                "stock": 0,
                "minimumOrderQuantity": 5,
                "price": "Infinity",
            }
        ]

        self.assertEqual(build_out_of_stock_orders(products), [])

    def test_build_orders_rejects_fractional_stock(self):
        products = [
            {
                "id": 1,
                "title": "Invalid Stock",
                "stock": 1.5,
                "minimumOrderQuantity": 5,
                "price": 10,
            }
        ]

        self.assertEqual(build_out_of_stock_orders(products), [])

    def test_get_out_of_stock_orders_returns_empty_dictionary(self):
        orders = get_out_of_stock_orders(self.request)

        self.assertEqual(orders, {})

    def test_add_out_of_stock_order_saves_order(self):
        add_out_of_stock_order(self.request, self.products[0], 5)

        orders = self.request.session[SESSION_KEY]

        self.assertEqual(orders["1"]["quantity"], 5)
        self.assertEqual(orders["1"]["title"], "Cooking Oil")
        self.assertEqual(orders["1"]["price"], "4.99")

    def test_add_out_of_stock_order_accumulates_quantity(self):
        add_out_of_stock_order(self.request, self.products[0], 5)
        add_out_of_stock_order(self.request, self.products[0], 10)

        orders = self.request.session[SESSION_KEY]

        self.assertEqual(orders["1"]["quantity"], 15)

    def test_add_out_of_stock_order_rejects_zero_quantity(self):
        with self.assertRaises(ValueError):
            add_out_of_stock_order(self.request, self.products[0], 0)

    def test_add_out_of_stock_order_rejects_negative_quantity(self):
        with self.assertRaises(ValueError):
            add_out_of_stock_order(self.request, self.products[0], -5)

    def test_add_out_of_stock_order_rejects_fractional_quantity(self):
        with self.assertRaises(ValueError):
            add_out_of_stock_order(self.request, self.products[0], 2.5)

    def test_add_out_of_stock_order_rejects_boolean_quantity(self):
        with self.assertRaises(ValueError):
            add_out_of_stock_order(self.request, self.products[0], True)

    def test_add_out_of_stock_order_rejects_in_stock_product(self):
        with self.assertRaises(ValueError):
            add_out_of_stock_order(self.request, self.products[1], 5)

    def test_add_out_of_stock_order_rejects_missing_product_id(self):
        product = {
            "title": "Unknown Product",
            "stock": 0,
            "price": 10,
        }

        with self.assertRaises(ValueError):
            add_out_of_stock_order(self.request, product, 5)

    def test_add_out_of_stock_order_rejects_invalid_price(self):
        product = {
            "id": 10,
            "title": "Invalid Product",
            "stock": 0,
            "price": "invalid",
        }

        with self.assertRaises((ValueError, TypeError)):
            add_out_of_stock_order(self.request, product, 5)

    def test_add_out_of_stock_order_rejects_infinite_price(self):
        product = {
            "id": 10,
            "title": "Invalid Price",
            "stock": 0,
            "price": "Infinity",
        }

        with self.assertRaises(ValueError):
            add_out_of_stock_order(self.request, product, 5)

    def test_add_order_rejects_invalid_stock(self):
        product = {
            "id": 10,
            "title": "Invalid Stock",
            "stock": "invalid",
            "price": 10,
        }

        with self.assertRaises(ValueError):
            add_out_of_stock_order(self.request, product, 5)

    def test_delete_out_of_stock_order(self):
        add_out_of_stock_order(self.request, self.products[0], 5)

        delete_out_of_stock_order(self.request, "1")

        self.assertEqual(get_out_of_stock_orders(self.request), {})

    def test_delete_missing_order_does_not_fail(self):
        delete_out_of_stock_order(self.request, "999")

        self.assertEqual(self.request.session[SESSION_KEY], {})

    def test_clear_out_of_stock_orders(self):
        add_out_of_stock_order(self.request, self.products[0], 5)

        clear_out_of_stock_orders(self.request)

    def test_calculate_order_totals(self):
        orders = {
            "1": {
                "product_id": "1",
                "title": "Cooking Oil",
                "price": "4.99",
                "quantity": 5,
            },
            "2": {
                "product_id": "2",
                "title": "Rice",
                "price": "10.50",
                "quantity": 3,
            },
        }

        totals = calculate_order_totals(orders)

        self.assertEqual(totals["total_order_quantity"], 8)
        self.assertEqual(
            totals["total_order_value"],
            Decimal("56.45"),
        )

    def test_calculate_order_totals_empty_orders(self):
        totals = calculate_order_totals({})

        self.assertEqual(totals["total_order_quantity"], 0)
        self.assertEqual(
            totals["total_order_value"],
            Decimal(0),
        )

    def test_calculate_order_totals_rejects_negative_quantity(self):
        orders = {
            "1": {
                "price": "10.00",
                "quantity": -5,
            }
        }

        with self.assertRaises(ValueError):
            calculate_order_totals(orders)

    def test_calculate_totals_rejects_corrupted_order(self):
        with self.assertRaises(ValueError):
            calculate_order_totals({"1": None})

    def test_calculate_totals_rejects_fractional_quantity(self):
        orders = {
            "1": {
                "price": "10.00",
                "quantity": 2.5,
            }
        }

        with self.assertRaises(ValueError):
            calculate_order_totals(orders)

    def test_add_order_rejects_corrupted_existing_order(self):
        self.request.session[SESSION_KEY] = {
            "1": "invalid",
        }

        with self.assertRaises(ValueError):
            add_out_of_stock_order(self.request, self.products[0], 5)

    def test_add_order_rejects_corrupted_session_value(self):
        self.request.session[SESSION_KEY] = ["invalid"]

        with self.assertRaises(ValueError):
            add_out_of_stock_order(self.request, self.products[0], 5)


class OutOfStockOrderViewTests(TestCase):
    """Regression tests for out-of-stock dashboard views."""

    def setUp(self):
        self.url = reverse("dashboard:out_of_stock")

        self.products = [
            {
                "id": 1,
                "title": "Cooking Oil",
                "category": "groceries",
                "sku": "COOK001",
                "price": 4.99,
                "stock": 0,
                "minimumOrderQuantity": 15,
            },
            {
                "id": 2,
                "title": "Rice",
                "category": "groceries",
                "sku": "RICE001",
                "price": 10.50,
                "stock": 20,
                "minimumOrderQuantity": 10,
            },
        ]

    @patch("apps.dashboard.views.fetch_products")
    def test_out_of_stock_page_loads(self, mock_fetch):
        mock_fetch.return_value = self.products

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/out_of_stock.html")
        self.assertContains(response, "Out of Stock Orders")
        self.assertContains(response, "Cooking Oil")

    @patch("apps.dashboard.views.fetch_products")
    def test_out_of_stock_page_displays_order_summary(self, mock_fetch):
        mock_fetch.return_value = self.products

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Total Order Quantity")
        self.assertContains(response, "Total Order Value")
        self.assertContains(response, "Browser Memory")

    @patch("apps.dashboard.views.fetch_products")
    def test_out_of_stock_page_handles_empty_inventory(self, mock_fetch):
        mock_fetch.return_value = []

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Out of Stock Products")

    @patch("apps.dashboard.views.fetch_products")
    def test_out_of_stock_page_handles_api_error(self, mock_fetch):
        from apps.dashboard.services import APIError

        mock_fetch.side_effect = APIError("Connection unavailable")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connection unavailable")
        self.assertContains(
            response,
            "Previously saved Browser Memory orders remain available.",
        )

    @patch("apps.dashboard.views.fetch_products")
    def test_add_order_post_saves_order(self, mock_fetch):
        mock_fetch.return_value = self.products

        response = self.client.post(
            self.url,
            {
                "action": "add_order",
                "product_id": "1",
                "quantity": "10",
            },
        )

        self.assertRedirects(response, self.url)

        orders = self.client.session[SESSION_KEY]

        self.assertEqual(orders["1"]["quantity"], 10)

    @patch("apps.dashboard.views.fetch_products")
    def test_add_order_post_rejects_invalid_quantity(self, mock_fetch):
        mock_fetch.return_value = self.products

        response = self.client.post(
            self.url,
            {
                "action": "add_order",
                "product_id": "1",
                "quantity": "-5",
            },
        )

        self.assertRedirects(response, self.url)

        message_texts = [
            str(message) for message in get_messages(response.wsgi_request)
        ]

        self.assertTrue(
            any("Invalid order quantity" in message for message in message_texts)
        )

    @patch("apps.dashboard.views.fetch_products")
    def test_add_order_post_rejects_unknown_product(self, mock_fetch):
        mock_fetch.return_value = self.products

        response = self.client.post(
            self.url,
            {
                "action": "add_order",
                "product_id": "999",
                "quantity": "5",
            },
        )

        self.assertRedirects(response, self.url)

    @patch("apps.dashboard.views.fetch_products")
    def test_add_order_post_accumulates_existing_order(self, mock_fetch):
        mock_fetch.return_value = self.products

        self.client.post(
            self.url,
            {
                "action": "add_order",
                "product_id": "1",
                "quantity": "5",
            },
        )

        response = self.client.post(
            self.url,
            {
                "action": "add_order",
                "product_id": "1",
                "quantity": "10",
            },
        )

        self.assertRedirects(response, self.url)

        orders = self.client.session[SESSION_KEY]

        self.assertEqual(orders["1"]["quantity"], 15)

    @patch("apps.dashboard.views.fetch_products")
    def test_saved_orders_are_displayed(self, mock_fetch):
        mock_fetch.return_value = self.products

        self.client.post(
            self.url,
            {
                "action": "add_order",
                "product_id": "1",
                "quantity": "5",
            },
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cooking Oil")
        self.assertContains(response, "5")
        self.assertContains(response, "24.95")

    @patch("apps.dashboard.views.fetch_products")
    def test_delete_order_post(self, mock_fetch):
        mock_fetch.return_value = self.products

        self.client.post(
            self.url,
            {
                "action": "add_order",
                "product_id": "1",
                "quantity": "5",
            },
        )

        response = self.client.post(
            self.url,
            {
                "action": "delete_order",
                "product_id": "1",
            },
        )

        self.assertRedirects(response, self.url)
        self.assertEqual(self.client.session[SESSION_KEY], {})

    @patch("apps.dashboard.views.fetch_products")
    def test_clear_memory_post(self, mock_fetch):
        mock_fetch.return_value = self.products

        self.client.post(
            self.url,
            {
                "action": "add_order",
                "product_id": "1",
                "quantity": "5",
            },
        )

        response = self.client.post(
            self.url,
            {"action": "clear_memory"},
        )

        self.assertRedirects(response, self.url)

    @patch("apps.dashboard.views.fetch_products")
    def test_saved_orders_remain_available_when_api_fails(self, mock_fetch):
        from apps.dashboard.services import APIError

        expected_order = {
            "1": {
                "product_id": "1",
                "title": "Cooking Oil",
                "price": "4.99",
                "quantity": 5,
            }
        }

        session = self.client.session

        session[SESSION_KEY] = {
            "1": {
                "product_id": "1",
                "title": "Cooking Oil",
                "price": "4.99",
                "quantity": 5,
            }
        }

        session.save()

        mock_fetch.side_effect = APIError("Connection unavailable")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cooking Oil")
        self.assertContains(response, "24.95")

        self.assertEqual(
            response.context["total_order_quantity"],
            5,
        )

        self.assertEqual(
            response.context["total_order_value"],
            Decimal("24.95"),
        )

        self.assertEqual(
            len(response.context["saved_orders"]),
            1,
        )
