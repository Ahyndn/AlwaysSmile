"""Tests for inventory analytics functionality."""

from decimal import Decimal

from django.test import TestCase

from apps.dashboard.analytics import (
    DASHBOARD_CATEGORIES,
    ProductSalesCalculator,
)
from apps.dashboard.inventory_analytics import (
    InventoryAnalyticsService,
)


def make_product(
    product_id=1,
    title="Test Product",
    category="beauty",
    price=10,
    stock=0,
    minimum_order_quantity=1,
    rating=4.5,
):
    """Create a consistent test product."""

    return {
        "id": product_id,
        "title": title,
        "category": category,
        "price": price,
        "stock": stock,
        "minimumOrderQuantity": minimum_order_quantity,
        "rating": rating,
        "sku": f"SKU-{product_id}",
        "meta": {
            "barcode": f"BAR-{product_id}",
        },
        "availabilityStatus": "In Stock",
    }


class InventoryAnalyticsServiceTests(TestCase):
    """Tests for inventory analytics operations."""

    def setUp(self):
        """Set up test data."""

        self.products = [
            make_product(1, "Product A", "beauty", 80, 0, 1),
            make_product(2, "Product B", "beauty", 15, 2, 5),
            make_product(3, "Product C", "beauty", 5, 10, 5),
        ]

        self.service = InventoryAnalyticsService(self.products)

    # --------------------------------------------------
    # 1. CLASS AND INITIALIZATION TESTS
    # --------------------------------------------------

    def test_service_has_abc_analysis_method(self):
        """ABC analysis must exist as a class method."""

        self.assertTrue(
            callable(
                getattr(
                    InventoryAnalyticsService,
                    "get_abc_analysis",
                    None,
                )
            ),
            "get_abc_analysis() is missing from InventoryAnalyticsService.",
        )

    def test_service_initializes_with_products(self):
        self.assertEqual(
            len(self.service.get_dataframe()),
            3,
        )

    def test_rejects_non_list_products(self):
        """Reject input that is not a list."""

        with self.assertRaises(TypeError):
            InventoryAnalyticsService({"id": 1})

    def test_rejects_non_dictionary_products(self):
        with self.assertRaises(TypeError):
            InventoryAnalyticsService(
                [
                    make_product(),
                    None,
                    "invalid",
                    123,
                ]
            )

    def test_empty_product_list(self):
        service = InventoryAnalyticsService([])

        summary = service.get_summary()

        self.assertEqual(summary["total_products"], 0)
        self.assertEqual(summary["total_units_sold"], 0)
        self.assertEqual(
            summary["total_sales_value"],
            Decimal(0),
        )
        self.assertEqual(
            summary["total_inventory_value"],
            Decimal(0),
        )

    # --------------------------------------------------
    # 2. DECIMAL AND FINANCIAL CALCULATIONS
    # --------------------------------------------------

    def test_financial_values_are_decimal(self):
        summary = self.service.get_summary()

        self.assertIsInstance(
            summary["total_sales_value"],
            Decimal,
        )

        self.assertIsInstance(
            summary["total_inventory_value"],
            Decimal,
        )

    def test_sales_value_calculation(self):
        product = make_product(
            price="19.99",
            stock=2,
            minimum_order_quantity=5,
        )

        service = InventoryAnalyticsService([product])

        summary = service.get_summary()

        self.assertEqual(
            summary["total_units_sold"],
            3,
        )

        self.assertEqual(
            summary["total_sales_value"],
            Decimal("59.97"),
        )

    def test_inventory_value_calculation(self):
        product = make_product(
            price="19.99",
            stock=5,
            minimum_order_quantity=10,
        )

        service = InventoryAnalyticsService([product])

        summary = service.get_summary()

        self.assertEqual(
            summary["total_inventory_value"],
            Decimal("99.95"),
        )

    def test_negative_prices_are_normalized(self):
        service = InventoryAnalyticsService([make_product(price=-50)])

        summary = service.get_summary()

        self.assertEqual(
            summary["total_sales_value"],
            Decimal(0),
        )

        self.assertEqual(
            summary["total_inventory_value"],
            Decimal(0),
        )

    def test_invalid_and_infinite_prices_are_safe(self):
        for price in ["invalid", float("inf"), float("nan")]:
            with self.subTest(price=price):
                service = InventoryAnalyticsService([make_product(price=price)])

                summary = service.get_summary()

                self.assertEqual(
                    summary["total_sales_value"],
                    Decimal(0),
                )

                self.assertEqual(
                    summary["total_inventory_value"],
                    Decimal(0),
                )

    def test_decimal_conversion_rejects_negative_values(self):
        self.assertEqual(
            InventoryAnalyticsService._to_decimal(-10),
            Decimal(0),
        )

    def test_decimal_conversion_handles_invalid_values(self):
        self.assertEqual(
            InventoryAnalyticsService._to_decimal("invalid"),
            Decimal(0),
        )

    # --------------------------------------------------
    # 3. STOCK CLASSIFICATION
    # --------------------------------------------------

    def test_out_of_stock_classification(self):
        service = InventoryAnalyticsService(
            [make_product(stock=0, minimum_order_quantity=5)]
        )

        self.assertEqual(
            service.get_stock_distribution()[InventoryAnalyticsService.STOCK_OUT],
            1,
        )

    def test_low_stock_classification(self):
        service = InventoryAnalyticsService(
            [make_product(stock=3, minimum_order_quantity=5)]
        )

        self.assertEqual(
            service.get_stock_distribution()[InventoryAnalyticsService.STOCK_LOW],
            1,
        )

    def test_in_stock_classification(self):
        service = InventoryAnalyticsService(
            [make_product(stock=10, minimum_order_quantity=5)]
        )

        self.assertEqual(
            service.get_stock_distribution()[InventoryAnalyticsService.STOCK_IN],
            1,
        )

    def test_stock_classifications_cover_all_products(self):
        summary = self.service.get_summary()

        self.assertEqual(
            summary["total_products"],
            (summary["out_of_stock"] + summary["low_stock"] + summary["in_stock"]),
        )

    def test_stock_items_filter(self):
        service = InventoryAnalyticsService(
            [
                make_product(1, stock=0),
                make_product(2, stock=2, minimum_order_quantity=5),
                make_product(3, stock=10, minimum_order_quantity=5),
            ]
        )

        out_of_stock = service.get_stock_items(InventoryAnalyticsService.STOCK_OUT)

        low_stock = service.get_stock_items(InventoryAnalyticsService.STOCK_LOW)

        in_stock = service.get_stock_items(InventoryAnalyticsService.STOCK_IN)

        self.assertEqual(len(out_of_stock), 1)
        self.assertEqual(len(low_stock), 1)
        self.assertEqual(len(in_stock), 1)

    def test_invalid_stock_filter_raises_error(self):
        with self.assertRaises(ValueError):
            self.service.get_stock_items("Invalid Status")

    # --------------------------------------------------
    # 4. CATEGORY SALES
    # --------------------------------------------------

    def test_category_sales_returns_dashboard_categories(self):
        result = self.service.get_category_sales()

        self.assertEqual(
            list(result.keys()),
            list(DASHBOARD_CATEGORIES),
        )

    def test_category_sales_values_are_decimal(self):
        result = self.service.get_category_sales()

        for value in result.values():
            self.assertIsInstance(value, Decimal)

    def test_api_category_sales_returns_original_categories(self):
        result = self.service.get_api_category_sales()

        self.assertEqual(
            list(result.keys()),
            sorted({product["category"] for product in self.products}),
        )

    def test_api_category_sales_are_decimal(self):
        result = self.service.get_api_category_sales()

        for value in result.values():
            self.assertIsInstance(value, Decimal)

    def test_category_sales_total_matches_sales_summary(self):
        """Verify category sales equal the sum of classified product sales."""

        result = self.service.get_category_sales()

        expected_total = sum(
            (
                value
                for category, value in zip(
                    self.service.dataframe["business_category"],
                    self.service.dataframe["sales_value"],
                    strict=True,
                )
                if category in DASHBOARD_CATEGORIES
            ),
            Decimal(0),
        )

        self.assertEqual(
            sum(result.values(), Decimal(0)),
            expected_total,
        )

    # --------------------------------------------------
    # 5. ABC ANALYSIS
    # --------------------------------------------------

    def test_abc_analysis_returns_dataframe(self):
        abc = self.service.get_abc_analysis()

        self.assertTrue(hasattr(abc, "columns"))

        self.assertIn("cumulative_sales_value", abc.columns)
        self.assertIn("cumulative_percentage", abc.columns)
        self.assertIn("abc_class", abc.columns)

    def test_abc_analysis_sorts_by_sales_descending(self):
        abc = self.service.get_abc_analysis()

        values = abc["sales_value"].tolist()

        self.assertEqual(
            values,
            sorted(values, reverse=True),
        )

    def test_abc_cumulative_sales_values(self):
        abc = self.service.get_abc_analysis()

        self.assertEqual(
            abc["cumulative_sales_value"].tolist(),
            [
                Decimal("80"),
                Decimal("125"),
                Decimal("125"),
            ],
        )

    def test_abc_cumulative_percentages(self):
        abc = self.service.get_abc_analysis()

        percentages = abc["cumulative_percentage"].tolist()

        self.assertEqual(
            percentages,
            [64.0, 100.0, 100.0],
        )

    def test_abc_classifications(self):
        abc = self.service.get_abc_analysis()

        self.assertEqual(
            abc["abc_class"].tolist(),
            ["A", "C", "C"],
        )

    def test_abc_analysis_empty_products(self):
        service = InventoryAnalyticsService([])

        abc = service.get_abc_analysis()

        self.assertTrue(abc.empty)

        self.assertIn("cumulative_sales_value", abc.columns)
        self.assertIn("cumulative_percentage", abc.columns)
        self.assertIn("abc_class", abc.columns)

    def test_abc_analysis_zero_sales(self):
        service = InventoryAnalyticsService(
            [
                make_product(1, price=0),
                make_product(2, price=0),
                make_product(3, price=0),
            ]
        )

        abc = service.get_abc_analysis()

        self.assertEqual(
            abc["cumulative_percentage"].tolist(),
            [0.0, 0.0, 0.0],
        )

        self.assertEqual(
            abc["abc_class"].tolist(),
            ["C", "C", "C"],
        )

    def test_abc_summary_has_all_classifications(self):
        result = self.service.get_abc_summary()

        self.assertEqual(
            list(result.keys()),
            ["A", "B", "C"],
        )

    def test_abc_summary_product_counts(self):
        result = self.service.get_abc_summary()

        self.assertEqual(
            result["A"]["product_count"],
            1,
        )

        self.assertEqual(
            result["B"]["product_count"],
            0,
        )

        self.assertEqual(
            result["C"]["product_count"],
            2,
        )

    def test_abc_summary_counts_equal_total_products(self):
        summary = self.service.get_summary()
        abc_summary = self.service.get_abc_summary()

        total_abc_products = sum(item["product_count"] for item in abc_summary.values())

        self.assertEqual(
            total_abc_products,
            summary["total_products"],
        )

    def test_abc_summary_sales_equal_total_sales(self):
        summary = self.service.get_summary()
        abc_summary = self.service.get_abc_summary()

        total_abc_sales = sum(
            (item["sales_value"] for item in abc_summary.values()),
            Decimal(0),
        )

        self.assertEqual(
            total_abc_sales,
            summary["total_sales_value"],
        )

    def test_abc_summary_sales_values_are_decimal(self):
        result = self.service.get_abc_summary()

        for classification in ["A", "B", "C"]:
            self.assertIsInstance(
                result[classification]["sales_value"],
                Decimal,
            )

    # --------------------------------------------------
    # 6. DATAFRAME INTEGRITY
    # --------------------------------------------------

    def test_dataframe_returns_independent_copy(self):
        first = self.service.get_dataframe()

        first.loc[0, "title"] = "Changed"

        second = self.service.get_dataframe()

        self.assertNotEqual(
            second.loc[0, "title"],
            "Changed",
        )

    def test_dataframe_contains_required_columns(self):
        required_columns = [
            "id",
            "title",
            "category",
            "business_category",
            "sku",
            "barcode",
            "price",
            "stock",
            "minimum_order_quantity",
            "unit_sold",
            "sales_value",
            "inventory_value",
            "stock_status",
            "rating",
            "availability_status",
        ]

        dataframe = self.service.get_dataframe()

        for column in required_columns:
            with self.subTest(column=column):
                self.assertIn(
                    column,
                    dataframe.columns,
                )

    def test_stock_quantities_are_non_negative_integers(self):
        service = InventoryAnalyticsService(
            [
                make_product(
                    stock=-5,
                    minimum_order_quantity=-10,
                )
            ]
        )

        dataframe = service.get_dataframe()

        self.assertEqual(
            int(dataframe.iloc[0]["stock"]),
            0,
        )

        self.assertEqual(
            int(dataframe.iloc[0]["minimum_order_quantity"]),
            0,
        )

    def test_zero_sales_abc_summary_places_every_product_in_c(self):
        service = InventoryAnalyticsService(
            [
                make_product(1, price=0),
                make_product(2, price=0),
                make_product(3, price=0),
            ]
        )

        result = service.get_abc_summary()

        self.assertEqual(result["A"]["product_count"], 0)
        self.assertEqual(result["B"]["product_count"], 0)
        self.assertEqual(result["C"]["product_count"], 3)

        self.assertEqual(
            result["C"]["sales_value"],
            Decimal(0),
        )

    def test_product_catalogue_fields_are_preserved(self):
        product = make_product()

        product["brand"] = "Test Brand"
        product["shippingInformation"] = "Ships in 2 days"
        product["meta"]["updatedAt"] = "2026-11-18T10:30:00Z"

        service = InventoryAnalyticsService([product])
        df = service.get_dataframe()

        self.assertEqual(df.iloc[0]["brand"], "Test Brand")
        self.assertEqual(
            df.iloc[0]["shipping_information"],
            "Ships in 2 days",
        )
        self.assertEqual(
            df.iloc[0]["updated_at"],
            "2026-11-18T10:30:00Z",
        )

    def test_empty_dataframe_contains_catalogue_fields(self):
        service = InventoryAnalyticsService([])

        df = service.get_dataframe()

        self.assertIn("brand", df.columns)
        self.assertIn("shipping_information", df.columns)
        self.assertIn("updated_at", df.columns)

    def test_units_sold_uses_shared_calculator(self):
        product = make_product(
            stock=2,
            minimum_order_quantity=10,
        )

        self.assertEqual(
            ProductSalesCalculator.calculate_units_sold(product),
            8,
        )

    def test_stock_items_rejects_invalid_classification(self):
        """Verify invalid stock classifications raise ValueError."""

        with self.assertRaises(ValueError):
            self.service.get_stock_items("Invalid")

    def test_stock_items_without_classification(self):
        """Verify all inventory records are returned without a filter."""

        result = self.service.get_stock_items()

        self.assertEqual(len(result), len(self.service.dataframe))
