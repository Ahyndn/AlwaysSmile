"""Tests for logistics analytics and regression visualizations."""

from django.test import SimpleTestCase

from apps.dashboard.logistics_analytics import (
    calculate_logistics_analytics,
    is_lifetime_warranty,
    parse_shipping_days,
    parse_warranty_days,
    safe_number,
)
from apps.dashboard.logistics_visualizations import (
    LogisticsChartService,
)


class LogisticsDurationTests(SimpleTestCase):
    """Test shipping and warranty duration conversions."""

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
        )

        self.assertEqual(
            parse_shipping_days("Ships in 5 days"),
            5.0,
        )

        self.assertEqual(
            parse_shipping_days("Ships in 2 weeks"),
            14.0,
        )

    def test_shipping_conversion_is_case_insensitive(self):

        self.assertEqual(
            parse_shipping_days("SHIPS OVERNIGHT"),
            1.0,
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

    def test_lifetime_warranty_is_not_numeric(self):

        self.assertIsNone(parse_warranty_days("Lifetime warranty"))

        self.assertIsNone(parse_warranty_days("Lifelong warranty"))

    def test_lifetime_classification(self):

        self.assertTrue(is_lifetime_warranty("Lifetime warranty"))

        self.assertTrue(is_lifetime_warranty("Lifelong warranty"))

        self.assertFalse(is_lifetime_warranty("1 year warranty"))

    def test_invalid_shipping_values(self):

        invalid_values = [
            None,
            "",
            "Unknown",
            "Free shipping",
            -1,
            123,
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertIsNone(parse_shipping_days(value))

    def test_invalid_warranty_values(self):

        invalid_values = [
            None,
            "",
            "Unknown warranty",
            "Lifetime warranty",
            -1,
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertIsNone(parse_warranty_days(value))

    def test_safe_number(self):

        self.assertEqual(safe_number(10), 10.0)
        self.assertEqual(safe_number("15.5"), 15.5)

        self.assertIsNone(safe_number(None))
        self.assertIsNone(safe_number(True))
        self.assertIsNone(safe_number(-1))
        self.assertIsNone(safe_number(float("nan")))
        self.assertIsNone(safe_number(float("inf")))
        self.assertIsNone(safe_number("invalid"))


class LogisticsAnalyticsTests(SimpleTestCase):
    """Test category-level logistics calculations."""

    def setUp(self):

        self.products = [
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
                "warrantyInformation": "1 month warranty",
            },
        ]

    def test_category_medians(self):

        records = calculate_logistics_analytics(self.products)

        electronics = records[0]

        self.assertEqual(electronics["product_count"], 2)
        self.assertEqual(electronics["median_price"], 150)
        self.assertEqual(electronics["median_rating"], 4.5)
        self.assertEqual(
            electronics["median_shipping_days"],
            1.0,
        )
        self.assertEqual(
            electronics["median_warranty_days"],
            197.5,
        )

    def test_lifetime_products_are_counted_separately(self):

        products = self.products + [
            {
                "id": 3,
                "category": "electronics",
                "price": 300,
                "rating": 5.0,
                "shippingInformation": "Ships overnight",
                "warrantyInformation": "Lifetime warranty",
            }
        ]

        records = calculate_logistics_analytics(products)

        electronics = records[0]

        self.assertEqual(electronics["product_count"], 3)
        self.assertEqual(electronics["lifetime_count"], 1)

        self.assertEqual(
            electronics["median_warranty_days"],
            197.5,
        )

        self.assertEqual(
            electronics["lifetime_median_price"],
            300,
        )

        self.assertEqual(
            electronics["lifetime_median_rating"],
            5.0,
        )

    def test_missing_values_are_excluded_from_medians(self):

        products = [
            {
                "category": "electronics",
                "price": 100,
                "rating": None,
                "shippingInformation": None,
                "warrantyInformation": None,
            },
            {
                "category": "electronics",
                "price": None,
                "rating": 4.0,
                "shippingInformation": "Ships overnight",
                "warrantyInformation": "1 year warranty",
            },
        ]

        record = calculate_logistics_analytics(products)[0]

        self.assertEqual(record["product_count"], 2)
        self.assertEqual(record["median_price"], 100)
        self.assertEqual(record["median_rating"], 4.0)
        self.assertEqual(record["median_shipping_days"], 1.0)
        self.assertEqual(record["median_warranty_days"], 365.0)

    def test_invalid_products_are_ignored(self):

        products = [
            None,
            "invalid",
            123,
            {
                "category": "electronics",
                "price": -10,
                "rating": float("nan"),
                "shippingInformation": "Unknown",
                "warrantyInformation": "Unknown",
            },
        ]

        records = calculate_logistics_analytics(products)

        self.assertEqual(len(records), 1)

        record = records[0]

        self.assertEqual(record["product_count"], 1)
        self.assertIsNone(record["median_price"])
        self.assertIsNone(record["median_rating"])
        self.assertIsNone(record["median_shipping_days"])
        self.assertIsNone(record["median_warranty_days"])

    def test_uncategorized_products(self):

        products = [
            {
                "price": 10,
                "rating": 4.0,
            }
        ]

        records = calculate_logistics_analytics(products)

        self.assertEqual(
            records[0]["category"],
            "Uncategorized",
        )

    def test_empty_and_invalid_collections(self):

        self.assertEqual(
            calculate_logistics_analytics([]),
            [],
        )

        self.assertEqual(
            calculate_logistics_analytics(None),
            [],
        )

        self.assertEqual(
            calculate_logistics_analytics("invalid"),
            [],
        )


class LogisticsRegressionTests(SimpleTestCase):
    """Test scatterplots and linear regression generation."""

    def setUp(self):

        self.records = [
            {
                "category": "electronics",
                "median_price": 100,
                "median_rating": 3.0,
                "median_shipping_days": 2.0,
                "median_warranty_days": 30.0,
                "lifetime_count": 1,
                "lifetime_median_rating": 5.0,
                "lifetime_median_price": 200,
            },
            {
                "category": "groceries",
                "median_price": 200,
                "median_rating": 4.0,
                "median_shipping_days": 4.0,
                "median_warranty_days": 60.0,
                "lifetime_count": 2,
                "lifetime_median_rating": 4.5,
                "lifetime_median_price": 300,
            },
            {
                "category": "furniture",
                "median_price": 300,
                "median_rating": 5.0,
                "median_shipping_days": 6.0,
                "median_warranty_days": 90.0,
                "lifetime_count": 0,
                "lifetime_median_rating": None,
                "lifetime_median_price": None,
            },
        ]

    def test_scatterplot_contains_category_points(self):

        figure = LogisticsChartService.prepare_scatter(
            self.records,
            "median_price",
            "median_rating",
            "Price vs Rating",
            "Median Price",
            "Median Rating",
        )

        self.assertEqual(len(figure.data), 2)

        scatter = figure.data[0]

        self.assertEqual(scatter.mode, "markers")
        self.assertEqual(len(scatter.x), 3)
        self.assertEqual(len(scatter.y), 3)

    def test_regression_line_is_generated(self):

        figure = LogisticsChartService.prepare_scatter(
            self.records,
            "median_price",
            "median_rating",
            "Price vs Rating",
            "Median Price",
            "Median Rating",
        )

        regression = figure.data[1]

        self.assertEqual(
            regression.name,
            "Overall linear regression",
        )

        self.assertEqual(regression.mode, "lines")

        self.assertEqual(len(regression.x), 100)
        self.assertEqual(len(regression.y), 100)

    def test_regression_can_be_disabled(self):

        figure = LogisticsChartService.prepare_scatter(
            self.records,
            "median_price",
            "median_rating",
            "Price vs Rating",
            "Median Price",
            "Median Rating",
            regression=False,
        )

        self.assertEqual(len(figure.data), 1)

    def test_regression_requires_two_observations(self):

        figure = LogisticsChartService.prepare_scatter(
            self.records[:1],
            "median_price",
            "median_rating",
            "Price vs Rating",
            "Median Price",
            "Median Rating",
        )

        self.assertEqual(len(figure.data), 1)

    def test_regression_requires_distinct_x_values(self):

        records = [
            {
                "category": "electronics",
                "median_price": 100,
                "median_rating": 4.0,
            },
            {
                "category": "groceries",
                "median_price": 100,
                "median_rating": 5.0,
            },
        ]

        figure = LogisticsChartService.prepare_scatter(
            records,
            "median_price",
            "median_rating",
            "Price vs Rating",
            "Median Price",
            "Median Rating",
        )

        self.assertEqual(len(figure.data), 1)

    def test_invalid_scatter_values_are_excluded(self):

        records = [
            {
                "category": "electronics",
                "median_price": 100,
                "median_rating": 4.0,
            },
            {
                "category": "groceries",
                "median_price": float("nan"),
                "median_rating": 5.0,
            },
            {
                "category": "furniture",
                "median_price": 200,
                "median_rating": float("inf"),
            },
        ]

        figure = LogisticsChartService.prepare_scatter(
            records,
            "median_price",
            "median_rating",
            "Price vs Rating",
            "Median Price",
            "Median Rating",
        )

        self.assertEqual(len(figure.data), 1)
        self.assertEqual(len(figure.data[0].x), 1)

    def test_empty_scatterplot_displays_annotation(self):

        figure = LogisticsChartService.prepare_scatter(
            [],
            "median_price",
            "median_rating",
            "Price vs Rating",
            "Median Price",
            "Median Rating",
        )

        self.assertEqual(len(figure.data), 0)
        self.assertGreater(len(figure.layout.annotations), 0)

    def test_lifetime_scatterplot(self):

        figure = LogisticsChartService.prepare_lifetime_scatter(
            self.records,
            "lifetime_median_rating",
            "Lifetime Warranty vs Rating",
            "Median Rating",
        )

        self.assertEqual(len(figure.data), 1)

        scatter = figure.data[0]

        self.assertEqual(len(scatter.x), 2)
        self.assertEqual(scatter.mode, "markers")

    def test_lifetime_scatter_excludes_invalid_counts(self):

        records = [
            {
                "category": "electronics",
                "lifetime_count": 0,
                "lifetime_median_rating": 5.0,
            },
            {
                "category": "groceries",
                "lifetime_count": 1,
                "lifetime_median_rating": float("nan"),
            },
        ]

        figure = LogisticsChartService.prepare_lifetime_scatter(
            records,
            "lifetime_median_rating",
            "Lifetime Warranty vs Rating",
            "Median Rating",
        )

        self.assertEqual(len(figure.data), 0)

    def test_dashboard_generates_seven_charts(self):

        charts = LogisticsChartService.prepare_dashboard(self.records)

        expected_keys = {
            "price_rating",
            "rating_shipping",
            "price_shipping",
            "warranty_rating",
            "warranty_price",
            "lifetime_rating",
            "lifetime_price",
        }

        self.assertEqual(set(charts.keys()), expected_keys)
        self.assertEqual(len(charts), 7)

    def test_dashboard_handles_empty_records(self):

        charts = LogisticsChartService.prepare_dashboard([])

        self.assertEqual(len(charts), 7)

        for figure in charts.values():
            with self.subTest(figure=figure.layout.title.text):
                self.assertIsNotNone(figure)
