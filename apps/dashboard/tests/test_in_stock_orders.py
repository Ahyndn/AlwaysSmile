from decimal import Decimal

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase

from apps.dashboard.in_stock_orders import (
    SESSION_KEY,
    add_in_stock_order,
    build_in_stock_orders,
    calculate_in_stock_order_totals,
    clear_in_stock_orders,
    delete_in_stock_order,
    get_in_stock_orders,
)


class InStockOrderTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/in-stock/")

        middleware = SessionMiddleware(lambda request: None)
        middleware.process_request(self.request)
        self.request.session.save()

        self.product = {
            "id": 1,
            "title": "Test Product",
            "price": "25.50",
            "stock": 20,
        }

    def test_session_key_is_independent(self):
        self.assertEqual(SESSION_KEY, "in_stock_orders")

        self.request.session["out_of_stock_orders"] = {"99": {"quantity": 5}}

        add_in_stock_order(self.request, self.product, 2)

        self.assertIn("99", self.request.session["out_of_stock_orders"])
        self.assertIn("1", self.request.session[SESSION_KEY])

    def test_get_empty_orders(self):
        orders = get_in_stock_orders(self.request)

        self.assertEqual(orders, {})

    def test_add_order(self):
        order = add_in_stock_order(
            self.request,
            self.product,
            3,
        )

        self.assertEqual(order["product_id"], "1")
        self.assertEqual(order["title"], "Test Product")
        self.assertEqual(order["price"], "25.50")
        self.assertEqual(order["quantity"], 3)

    def test_add_order_accumulates_quantity(self):
        add_in_stock_order(self.request, self.product, 2)
        order = add_in_stock_order(self.request, self.product, 4)

        self.assertEqual(order["quantity"], 6)

    def test_add_multiple_products(self):
        second_product = {
            "id": 2,
            "title": "Second Product",
            "price": "10.00",
            "stock": 15,
        }

        add_in_stock_order(self.request, self.product, 2)
        add_in_stock_order(self.request, second_product, 3)

        orders = get_in_stock_orders(self.request)

        self.assertEqual(len(orders), 2)

    def test_reject_zero_quantity(self):
        with self.assertRaises(ValueError):
            add_in_stock_order(self.request, self.product, 0)

    def test_reject_negative_quantity(self):
        with self.assertRaises(ValueError):
            add_in_stock_order(self.request, self.product, -1)

    def test_reject_invalid_quantity(self):
        with self.assertRaises(ValueError):
            add_in_stock_order(self.request, self.product, "abc")

    def test_reject_low_stock_product(self):
        product = {**self.product, "stock": 5}

        with self.assertRaises(ValueError):
            add_in_stock_order(self.request, product, 1)

    def test_reject_out_of_stock_product(self):
        product = {**self.product, "stock": 0}

        with self.assertRaises(ValueError):
            add_in_stock_order(self.request, product, 1)

    def test_reject_negative_price(self):
        product = {**self.product, "price": "-10"}

        with self.assertRaises(ValueError):
            add_in_stock_order(self.request, product, 1)

    def test_reject_invalid_price(self):
        product = {**self.product, "price": "invalid"}

        with self.assertRaises(ValueError):
            add_in_stock_order(self.request, product, 1)

    def test_reject_missing_product_id(self):
        product = {**self.product}
        del product["id"]

        with self.assertRaises(ValueError):
            add_in_stock_order(self.request, product, 1)

    def test_build_in_stock_orders(self):
        products = [
            {"id": 1, "title": "Available", "stock": 20},
            {"id": 2, "title": "Low", "stock": 5},
            {"id": 3, "title": "Empty", "stock": 0},
            {"id": 4, "title": "Boundary", "stock": 6},
        ]

        result = build_in_stock_orders(products)

        self.assertEqual(
            [item["id"] for item in result],
            [1, 4],
        )

    def test_build_orders_ignores_invalid_stock(self):
        products = [
            {"id": 1, "stock": "invalid"},
            {"id": 2, "stock": None},
            {"id": 3, "stock": 10},
        ]

        result = build_in_stock_orders(products)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 3)

    def test_delete_order(self):
        add_in_stock_order(self.request, self.product, 2)

        delete_in_stock_order(self.request, "1")

        self.assertNotIn(
            "1",
            get_in_stock_orders(self.request),
        )

    def test_delete_missing_order(self):
        with self.assertRaises(ValueError):
            delete_in_stock_order(self.request, "999")

    def test_clear_orders(self):
        add_in_stock_order(self.request, self.product, 2)

        clear_in_stock_orders(self.request)

        self.assertNotIn(SESSION_KEY, self.request.session)

    def test_calculate_order_totals(self):
        orders = {
            "1": {
                "price": "25.50",
                "quantity": 2,
            },
            "2": {
                "price": "10.00",
                "quantity": 3,
            },
        }

        totals = calculate_in_stock_order_totals(orders)

        self.assertEqual(totals["total_order_quantity"], 5)
        self.assertEqual(
            totals["total_order_value"],
            Decimal("81.00"),
        )

    def test_empty_order_totals(self):
        totals = calculate_in_stock_order_totals({})

        self.assertEqual(totals["total_order_quantity"], 0)
        self.assertEqual(
            totals["total_order_value"],
            Decimal("0.00"),
        )

    def test_reject_invalid_order_totals(self):
        orders = {
            "1": {
                "price": "invalid",
                "quantity": 2,
            }
        }

        with self.assertRaises(ValueError):
            calculate_in_stock_order_totals(orders)

    def test_reject_zero_saved_quantity(self):
        orders = {
            "1": {
                "price": "10.00",
                "quantity": 0,
            }
        }

        with self.assertRaises(ValueError):
            calculate_in_stock_order_totals(orders)

    def test_reject_corrupted_session(self):
        self.request.session[SESSION_KEY] = []

        with self.assertRaises(ValueError):
            get_in_stock_orders(self.request)

    def test_session_modified_after_adding(self):
        add_in_stock_order(self.request, self.product, 1)

        self.assertTrue(self.request.session.modified)

    def test_session_modified_after_deleting(self):
        add_in_stock_order(self.request, self.product, 1)

        self.request.session.modified = False

        delete_in_stock_order(self.request, "1")

        self.assertTrue(self.request.session.modified)

    def test_session_modified_after_clearing(self):
        add_in_stock_order(self.request, self.product, 1)

        self.request.session.modified = False

        clear_in_stock_orders(self.request)

        self.assertTrue(self.request.session.modified)
