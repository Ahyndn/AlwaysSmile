from decimal import Decimal
from types import SimpleNamespace

from django.test import TestCase

from apps.dashboard.low_stock_orders import (
    SESSION_KEY,
    add_low_stock_order,
    build_low_stock_orders,
    calculate_order_totals,
    clear_low_stock_orders,
    delete_low_stock_order,
    get_low_stock_orders,
    save_low_stock_orders,
)


class TestSession(dict):
    """Dictionary-backed session for service unit tests."""

    modified = False

    def save(self):
        self.modified = False


def make_request():
    """Create a request-like object with a stable session."""
    return SimpleNamespace(session=TestSession())


class LowStockOrderTests(TestCase):
    """Regression tests for low-stock order services."""

    def setUp(self):
        self.request = make_request()

        self.product = {
            "id": 1,
            "title": "Cooking Oil",
            "category": "groceries",
            "sku": "COOK001",
            "price": "4.99",
            "stock": 3,
            "reorderLevel": 5,
            "minimumOrderQuantity": 15,
            "availabilityStatus": "Low Stock",
            "meta": {
                "barcode": "123456789",
            },
        }

    # --------------------------------------------------
    # Session tests
    # --------------------------------------------------

    def test_session_key_is_independent(self):
        self.assertEqual(SESSION_KEY, "low_stock_orders")

        self.request.session["in_stock_orders"] = {"99": {"quantity": 5}}

        add_low_stock_order(self.request, self.product, 2)

        self.assertIn("99", self.request.session["in_stock_orders"])
        self.assertIn("1", self.request.session[SESSION_KEY])

    def test_get_empty_orders(self):
        orders = get_low_stock_orders(self.request)

        self.assertEqual(orders, {})

    def test_save_low_stock_orders(self):
        orders = {
            "1": {
                "product_id": "1",
                "title": "Cooking Oil",
                "price": "4.99",
                "quantity": 5,
            }
        }

        save_low_stock_orders(self.request, orders)

        self.assertEqual(
            self.request.session[SESSION_KEY]["1"]["quantity"],
            5,
        )

    def test_save_orders_rejects_non_dictionary(self):
        with self.assertRaises(ValueError):
            save_low_stock_orders(self.request, [])

    def test_get_orders_rejects_corrupted_session(self):
        self.request.session[SESSION_KEY] = []

        with self.assertRaises(ValueError):
            get_low_stock_orders(self.request)

    def test_get_orders_rejects_corrupted_saved_order(self):
        self.request.session[SESSION_KEY] = {
            "1": None,
        }

        with self.assertRaises(ValueError):
            get_low_stock_orders(self.request)

    def test_get_orders_rejects_mismatched_product_id(self):
        self.request.session[SESSION_KEY] = {
            "1": {
                "product_id": "2",
                "title": "Cooking Oil",
                "price": "4.99",
                "quantity": 5,
            }
        }

        with self.assertRaises(ValueError):
            get_low_stock_orders(self.request)

    # --------------------------------------------------
    # Add order tests
    # --------------------------------------------------

    def test_add_low_stock_order(self):
        add_low_stock_order(self.request, self.product, 5)

        order = self.request.session[SESSION_KEY]["1"]

        self.assertEqual(order["product_id"], "1")
        self.assertEqual(order["title"], "Cooking Oil")
        self.assertEqual(order["price"], "4.99")
        self.assertEqual(order["quantity"], 5)

    def test_add_order_accumulates_quantity(self):
        add_low_stock_order(self.request, self.product, 5)
        add_low_stock_order(self.request, self.product, 10)

        order = self.request.session[SESSION_KEY]["1"]

        self.assertEqual(order["quantity"], 15)

    def test_add_multiple_products(self):
        second_product = {
            **self.product,
            "id": 2,
            "title": "Rice",
            "price": "10.50",
        }

        add_low_stock_order(self.request, self.product, 2)
        add_low_stock_order(self.request, second_product, 3)

        orders = get_low_stock_orders(self.request)

        self.assertEqual(len(orders), 2)

    def test_reject_zero_quantity(self):
        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, self.product, 0)

    def test_reject_negative_quantity(self):
        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, self.product, -1)

    def test_reject_invalid_quantity(self):
        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, self.product, "abc")

    def test_reject_fractional_quantity(self):
        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, self.product, 2.5)

    def test_reject_boolean_quantity(self):
        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, self.product, True)

    def test_reject_missing_product_id(self):
        product = {**self.product}
        del product["id"]

        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, product, 5)

    def test_reject_invalid_product(self):
        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, None, 5)

    def test_reject_zero_stock_product(self):
        product = {**self.product, "stock": 0}

        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, product, 5)

    def test_reject_negative_stock_product(self):
        product = {**self.product, "stock": -1}

        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, product, 5)

    def test_reject_product_above_reorder_level(self):
        product = {**self.product, "stock": 10}

        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, product, 5)

    def test_reject_invalid_stock(self):
        product = {**self.product, "stock": "invalid"}

        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, product, 5)

    def test_reject_negative_reorder_level(self):
        product = {**self.product, "reorderLevel": -1}

        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, product, 5)

    def test_reject_invalid_reorder_level(self):
        product = {**self.product, "reorderLevel": "invalid"}

        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, product, 5)

    def test_reject_negative_price(self):
        product = {**self.product, "price": "-10"}

        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, product, 5)

    def test_reject_invalid_price(self):
        product = {**self.product, "price": "invalid"}

        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, product, 5)

    def test_reject_infinite_price(self):
        product = {**self.product, "price": "Infinity"}

        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, product, 5)

    def test_reject_nan_price(self):
        product = {**self.product, "price": "NaN"}

        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, product, 5)

    def test_add_order_rejects_corrupted_existing_order(self):
        self.request.session[SESSION_KEY] = {
            "1": "invalid",
        }

        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, self.product, 5)

    def test_add_order_rejects_corrupted_session(self):
        self.request.session[SESSION_KEY] = []

        with self.assertRaises(ValueError):
            add_low_stock_order(self.request, self.product, 5)

    # --------------------------------------------------
    # Build low-stock products
    # --------------------------------------------------

    def test_build_low_stock_orders(self):
        products = [
            {
                "id": 1,
                "title": "Low",
                "stock": 3,
                "reorderLevel": 5,
                "minimumOrderQuantity": 15,
                "price": 10,
            },
            {
                "id": 2,
                "title": "In Stock",
                "stock": 20,
                "reorderLevel": 5,
                "minimumOrderQuantity": 10,
                "price": 10,
            },
            {
                "id": 3,
                "title": "Out",
                "stock": 0,
                "reorderLevel": 5,
                "minimumOrderQuantity": 10,
                "price": 10,
            },
            {
                "id": 4,
                "title": "Boundary",
                "stock": 5,
                "reorderLevel": 5,
                "minimumOrderQuantity": 10,
                "price": 10,
            },
        ]

        result = build_low_stock_orders(products)

        self.assertEqual(
            [item["id"] for item in result],
            ["1", "4"],
        )

    def test_build_orders_uses_reorder_level(self):
        result = build_low_stock_orders([self.product])

        self.assertEqual(result[0]["reorder_level"], 5)

    def test_build_orders_falls_back_to_minimum_order_quantity(self):
        product = {
            "id": 1,
            "title": "Fallback Product",
            "stock": 3,
            "minimumOrderQuantity": 5,
            "price": 10,
        }

        result = build_low_stock_orders([product])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["reorder_level"], 5)

    def test_build_orders_prefers_reorder_level(self):
        product = {
            "id": 1,
            "title": "Preferred Threshold",
            "stock": 5,
            "reorderLevel": 5,
            "minimumOrderQuantity": 20,
            "price": 10,
        }

        result = build_low_stock_orders([product])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["reorder_level"], 5)

    def test_build_orders_calculates_quantity_to_order(self):
        result = build_low_stock_orders([self.product])

        self.assertEqual(result[0]["quantity_to_order"], 12)

    def test_build_orders_uses_minimum_quantity_when_stock_is_high(self):
        product = {
            **self.product,
            "stock": 5,
            "minimumOrderQuantity": 2,
        }

        result = build_low_stock_orders([product])

        self.assertEqual(result[0]["quantity_to_order"], 1)

    def test_build_orders_returns_decimal_price(self):
        result = build_low_stock_orders([self.product])

        self.assertEqual(result[0]["price"], Decimal("4.99"))

    def test_build_orders_returns_product_metadata(self):
        result = build_low_stock_orders([self.product])

        self.assertEqual(result[0]["barcode"], "123456789")
        self.assertEqual(result[0]["sku"], "COOK001")
        self.assertEqual(result[0]["category"], "groceries")

    def test_build_orders_handles_empty_products(self):
        self.assertEqual(build_low_stock_orders([]), [])

    def test_build_orders_skips_invalid_products(self):
        products = [
            None,
            {"id": 1, "stock": "invalid", "reorderLevel": 5, "price": 10},
            {"id": 2, "stock": -1, "reorderLevel": 5, "price": 10},
            {"id": 3, "stock": 2, "reorderLevel": -1, "price": 10},
            {"id": 4, "stock": 2, "reorderLevel": 5, "price": "invalid"},
            {
                "id": 5,
                "stock": 2,
                "reorderLevel": 5,
                "price": 10,
                "minimumOrderQuantity": -1,
            },
        ]

        self.assertEqual(build_low_stock_orders(products), [])

    def test_build_orders_rejects_infinite_price(self):
        product = {
            "id": 1,
            "stock": 2,
            "reorderLevel": 5,
            "price": "Infinity",
        }

        self.assertEqual(build_low_stock_orders([product]), [])

    def test_build_orders_rejects_fractional_stock(self):
        product = {
            "id": 1,
            "stock": 1.5,
            "reorderLevel": 5,
            "price": 10,
        }

        self.assertEqual(build_low_stock_orders([product]), [])

    def test_build_orders_rejects_fractional_reorder_level(self):
        product = {
            "id": 1,
            "stock": 2,
            "reorderLevel": 5.5,
            "price": 10,
        }

        self.assertEqual(build_low_stock_orders([product]), [])

    def test_build_orders_skips_missing_product_id(self):
        product = {
            "title": "Missing ID",
            "stock": 2,
            "reorderLevel": 5,
            "price": 10,
        }

        self.assertEqual(build_low_stock_orders([product]), [])

    def test_build_orders_handles_invalid_metadata(self):
        product = {
            **self.product,
            "meta": "invalid",
        }

        result = build_low_stock_orders([product])

        self.assertEqual(result[0]["barcode"], "")

    # --------------------------------------------------
    # Delete and clear tests
    # --------------------------------------------------

    def test_delete_low_stock_order(self):
        add_low_stock_order(self.request, self.product, 5)

        delete_low_stock_order(self.request, "1")

        self.assertNotIn(
            "1",
            get_low_stock_orders(self.request),
        )

    def test_delete_missing_order(self):
        delete_low_stock_order(self.request, "999")

        self.assertEqual(
            get_low_stock_orders(self.request),
            {},
        )

    def test_clear_low_stock_orders(self):
        add_low_stock_order(self.request, self.product, 5)

        clear_low_stock_orders(self.request)

        self.assertNotIn(SESSION_KEY, self.request.session)

    def test_clear_empty_orders(self):
        clear_low_stock_orders(self.request)

        self.assertNotIn(SESSION_KEY, self.request.session)

    # --------------------------------------------------
    # Order totals tests
    # --------------------------------------------------

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

        self.assertEqual(
            totals["total_order_value"],
            Decimal("56.45"),
        )

    def test_empty_order_totals(self):
        totals = calculate_order_totals({})

        self.assertEqual(totals["total_order_quantity"], 0)
        self.assertEqual(
            totals["total_order_value"],
            Decimal(0),
        )

    def test_reject_invalid_order_totals(self):
        orders = {
            "1": {
                "product_id": "1",
                "title": "Cooking Oil",
                "price": "invalid",
                "quantity": 2,
            }
        }

        with self.assertRaises(ValueError):
            calculate_order_totals(orders)

    def test_reject_zero_saved_quantity(self):
        orders = {
            "1": {
                "product_id": "1",
                "title": "Cooking Oil",
                "price": "10.00",
                "quantity": 0,
            }
        }

        with self.assertRaises(ValueError):
            calculate_order_totals(orders)

    def test_reject_negative_saved_quantity(self):
        orders = {
            "1": {
                "product_id": "1",
                "title": "Cooking Oil",
                "price": "10.00",
                "quantity": -5,
            }
        }

        with self.assertRaises(ValueError):
            calculate_order_totals(orders)

    def test_reject_fractional_saved_quantity(self):
        orders = {
            "1": {
                "product_id": "1",
                "title": "Cooking Oil",
                "price": "10.00",
                "quantity": 2.5,
            }
        }

        with self.assertRaises(ValueError):
            calculate_order_totals(orders)

    def test_reject_corrupted_saved_order(self):
        with self.assertRaises(ValueError):
            calculate_order_totals({"1": None})

    def test_reject_non_dictionary_totals(self):
        with self.assertRaises(ValueError):
            calculate_order_totals([])

    def test_reject_mismatched_product_id_in_totals(self):
        orders = {
            "1": {
                "product_id": "2",
                "title": "Cooking Oil",
                "price": "10.00",
                "quantity": 2,
            }
        }

        with self.assertRaises(ValueError):
            calculate_order_totals(orders)

    # --------------------------------------------------
    # Session modification tests
    # --------------------------------------------------

    def test_session_modified_after_adding(self):
        add_low_stock_order(self.request, self.product, 1)

        self.assertTrue(self.request.session.modified)

    def test_session_modified_after_saving(self):
        orders = {
            "1": {
                "product_id": "1",
                "title": "Cooking Oil",
                "price": "4.99",
                "quantity": 1,
            }
        }

        save_low_stock_orders(self.request, orders)

        self.assertTrue(self.request.session.modified)

    def test_session_modified_after_deleting(self):
        add_low_stock_order(self.request, self.product, 1)

        self.request.session.modified = False

        delete_low_stock_order(self.request, "1")

        self.assertTrue(self.request.session.modified)

    def test_session_modified_after_clearing(self):
        add_low_stock_order(self.request, self.product, 1)

        self.request.session.modified = False

        clear_low_stock_orders(self.request)

        self.assertTrue(self.request.session.modified)
