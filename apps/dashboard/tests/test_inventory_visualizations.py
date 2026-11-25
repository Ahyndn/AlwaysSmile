"""Tests for inventory visualization functionality."""

from decimal import Decimal

import plotly.graph_objects as go
from django.test import SimpleTestCase

from apps.dashboard.inventory_analytics import (
    InventoryAnalyticsService,
)
from apps.dashboard.inventory_visualizations import (
    InventoryChartService,
)


def make_product(
    product_id=1,
    title="Test Product",
    price=10,
    stock=0,
    minimum_order_quantity=1,
):
    """Create a consistent product for visualization tests."""

    return {
        "id": product_id,
        "title": title,
        "category": "beauty",
        "price": price,
        "stock": stock,
        "minimumOrderQuantity": minimum_order_quantity,
        "rating": 4.5,
        "sku": f"SKU-{product_id}",
        "meta": {
            "barcode": f"BAR-{product_id}",
        },
        "availabilityStatus": "In Stock",
    }


class InventoryVisualizationTests(SimpleTestCase):
    """Tests for inventory visualization components."""

    def setUp(self):
        self.sales = {
            "beauty": Decimal(100),
            "groceries": Decimal(300),
            "laptops": Decimal(200),
        }

        self.stock_distribution = {
            "Out of Stock": 5,
            "Low Stock": 10,
            "In Stock": 15,
        }

        self.products = [
            make_product(1, "Product A", 80, 0, 1),
            make_product(2, "Product B", 15, 0, 1),
            make_product(3, "Product C", 5, 0, 1),
        ]

        self.analytics = InventoryAnalyticsService(self.products)

    # --------------------------------------------------
    # 1. CATEGORY SALES CHART
    # --------------------------------------------------

    def test_category_sales_chart_returns_data_and_image(self):
        result, image = InventoryChartService.prepare_category_sales_chart(self.sales)

        self.assertEqual(len(result), 3)

        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_category_sales_chart_preserves_values(self):
        result, image = InventoryChartService.prepare_category_sales_chart(self.sales)

        values = {item["category"]: item["value"] for item in result}

        self.assertEqual(values["beauty"], 100)
        self.assertEqual(values["groceries"], 300)
        self.assertEqual(values["laptops"], 200)

    def test_category_sales_chart_handles_empty_data(self):
        result, image = InventoryChartService.prepare_category_sales_chart({})

        self.assertEqual(result, [])

        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_category_sales_chart_handles_negative_values(self):
        result, image = InventoryChartService.prepare_category_sales_chart(
            {
                "beauty": Decimal(-100),
                "groceries": Decimal(200),
            }
        )

        self.assertEqual(result[0]["value"], 0)
        self.assertEqual(result[1]["value"], 200)

    def test_category_sales_chart_handles_zero_values(self):
        result, image = InventoryChartService.prepare_category_sales_chart(
            {
                "beauty": Decimal(0),
                "groceries": Decimal(0),
            }
        )

        self.assertEqual(len(result), 2)

        self.assertEqual(
            [item["value"] for item in result],
            [0, 0],
        )

    # --------------------------------------------------
    # 2. STOCK DISTRIBUTION CHART
    # --------------------------------------------------

    def test_stock_chart_returns_data_and_image(self):
        result, image = InventoryChartService.prepare_stock_distribution_chart(
            self.stock_distribution
        )

        self.assertEqual(len(result), 3)

        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_stock_chart_preserves_counts(self):
        result, image = InventoryChartService.prepare_stock_distribution_chart(
            self.stock_distribution
        )

        counts = {item["status"]: item["count"] for item in result}

        self.assertEqual(counts["Out of Stock"], 5)
        self.assertEqual(counts["Low Stock"], 10)
        self.assertEqual(counts["In Stock"], 15)

    def test_stock_chart_percentages(self):
        result, image = InventoryChartService.prepare_stock_distribution_chart(
            self.stock_distribution
        )

        percentages = {item["status"]: item["percentage"] for item in result}

        self.assertAlmostEqual(percentages["Out of Stock"], 100 / 6)

        self.assertAlmostEqual(percentages["Low Stock"], 100 / 3)

        self.assertAlmostEqual(percentages["In Stock"], 50)

        self.assertAlmostEqual(sum(percentages.values()), 100)

    def test_stock_chart_handles_empty_data(self):
        result, image = InventoryChartService.prepare_stock_distribution_chart({})

        self.assertEqual(len(result), 3)

        self.assertEqual(
            sum(item["count"] for item in result),
            0,
        )

        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_stock_chart_handles_zero_values(self):
        result, image = InventoryChartService.prepare_stock_distribution_chart(
            {
                "Out of Stock": 0,
                "Low Stock": 0,
                "In Stock": 0,
            }
        )

        self.assertEqual(
            sum(item["percentage"] for item in result),
            0,
        )

    # --------------------------------------------------
    # 3. ABC ANALYSIS CHART
    # --------------------------------------------------

    def test_abc_chart_returns_plotly_figure(self):
        abc = self.analytics.get_abc_analysis()

        figure = InventoryChartService.prepare_abc_chart(abc)

        self.assertIsInstance(
            figure,
            go.Figure,
        )

    def test_abc_chart_contains_product_titles(self):
        abc = self.analytics.get_abc_analysis()

        figure = InventoryChartService.prepare_abc_chart(abc)

        trace = figure.data[0]

        self.assertEqual(
            list(trace.x),
            ["Product A", "Product B", "Product C"],
        )

    def test_abc_chart_contains_cumulative_percentages(self):
        abc = self.analytics.get_abc_analysis()

        figure = InventoryChartService.prepare_abc_chart(abc)

        trace = figure.data[0]

        self.assertEqual(
            list(trace.y),
            [80.0, 95.0, 100.0],
        )

    def test_abc_chart_contains_classifications(self):
        abc = self.analytics.get_abc_analysis()

        figure = InventoryChartService.prepare_abc_chart(abc)

        trace = figure.data[0]

        hover_text = " ".join(str(value) for row in trace.customdata for value in row)

        for classification in ["A", "B", "C"]:
            self.assertIn(
                classification,
                hover_text,
            )

    def test_abc_chart_contains_reference_thresholds(self):
        abc = self.analytics.get_abc_analysis()

        figure = InventoryChartService.prepare_abc_chart(abc)

        threshold_values = [shape.y0 for shape in figure.layout.shapes]

        for threshold in [80, 95, 100]:
            self.assertIn(
                threshold,
                threshold_values,
            )

    def test_abc_chart_handles_empty_dataframe(self):
        empty_service = InventoryAnalyticsService([])

        abc = empty_service.get_abc_analysis()

        figure = InventoryChartService.prepare_abc_chart(abc)

        self.assertIsInstance(
            figure,
            go.Figure,
        )

        self.assertEqual(
            len(figure.data),
            0,
        )

    def test_abc_chart_contains_interactive_hover_information(self):
        abc = self.analytics.get_abc_analysis()

        figure = InventoryChartService.prepare_abc_chart(abc)

        trace = figure.data[0]

        self.assertIsNotNone(
            trace.hovertemplate,
        )

    def test_abc_chart_has_correct_axis_titles(self):
        abc = self.analytics.get_abc_analysis()

        figure = InventoryChartService.prepare_abc_chart(abc)

        self.assertIsNotNone(figure.layout.xaxis.title.text)

        self.assertIsNotNone(figure.layout.yaxis.title.text)

    def test_abc_chart_serializes_to_json(self):
        abc = self.analytics.get_abc_analysis()

        figure = InventoryChartService.prepare_abc_chart(abc)

        chart_json = figure.to_json()

        self.assertIsInstance(chart_json, str)
        self.assertIn("Product A", chart_json)
