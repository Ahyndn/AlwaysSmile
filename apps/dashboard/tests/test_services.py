from unittest.mock import Mock

import requests
from django.test import SimpleTestCase

from apps.dashboard.services import (
    APIError,
    DummyJSONProductClient,
)


class DummyJSONProductClientTests(SimpleTestCase):
    def setUp(self):
        self.session = Mock()

        self.client = DummyJSONProductClient(
            session=self.session,
            page_size=2,
            timeout=10,
        )

    @staticmethod
    def create_response(payload):
        response = Mock()
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        return response

    def test_fetch_products_returns_all_paginated_products(self):

        self.session.get.side_effect = [
            self.create_response(
                {
                    "products": [
                        {"id": 1, "title": "Product A"},
                        {"id": 2, "title": "Product B"},
                    ],
                    "total": 3,
                }
            ),
            self.create_response(
                {
                    "products": [
                        {"id": 3, "title": "Product C"},
                    ],
                    "total": 3,
                }
            ),
        ]

        products = self.client.fetch_products()

        self.assertEqual(len(products), 3)

        self.assertEqual(
            [product["id"] for product in products],
            [1, 2, 3],
        )

        self.assertEqual(self.session.get.call_count, 2)

    def test_fetch_products_uses_correct_pagination(self):

        self.session.get.side_effect = [
            self.create_response(
                {
                    "products": [
                        {"id": 1},
                        {"id": 2},
                    ],
                    "total": 3,
                }
            ),
            self.create_response(
                {
                    "products": [{"id": 3}],
                    "total": 3,
                }
            ),
        ]

        self.client.fetch_products()

        first_call = self.session.get.call_args_list[0]
        second_call = self.session.get.call_args_list[1]

        self.assertEqual(
            first_call.kwargs["params"],
            {"limit": 2, "skip": 0},
        )

        self.assertEqual(
            second_call.kwargs["params"],
            {"limit": 2, "skip": 2},
        )

    def test_fetch_products_handles_empty_response(self):

        self.session.get.return_value = self.create_response(
            {
                "products": [],
                "total": 0,
            }
        )

        self.assertEqual(
            self.client.fetch_products(),
            [],
        )

    def test_fetch_products_handles_connection_errors(self):

        self.session.get.side_effect = requests.Timeout()

        with self.assertRaises(APIError):
            self.client.fetch_products()

    def test_fetch_products_handles_http_errors(self):

        response = Mock()

        response.raise_for_status.side_effect = requests.HTTPError("HTTP error")

        self.session.get.return_value = response

        with self.assertRaises(APIError):
            self.client.fetch_products()

    def test_fetch_products_handles_invalid_json(self):

        response = Mock()

        response.raise_for_status.return_value = None
        response.json.side_effect = ValueError("Invalid JSON")

        self.session.get.return_value = response

        with self.assertRaises(APIError):
            self.client.fetch_products()

    def test_fetch_products_rejects_invalid_response_structure(self):

        self.session.get.return_value = self.create_response(
            {
                "products": "invalid",
                "total": 1,
            }
        )

        with self.assertRaises(APIError):
            self.client.fetch_products()

    def test_fetch_products_rejects_invalid_product_records(self):

        self.session.get.return_value = self.create_response(
            {
                "products": ["invalid product"],
                "total": 1,
            }
        )

        with self.assertRaises(APIError):
            self.client.fetch_products()

    def test_client_rejects_invalid_page_size(self):

        with self.assertRaises(ValueError):
            DummyJSONProductClient(page_size=0)

    def test_client_rejects_invalid_timeout(self):

        with self.assertRaises(ValueError):
            DummyJSONProductClient(timeout=0)
