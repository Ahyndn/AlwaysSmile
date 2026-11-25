from django.test import SimpleTestCase

from apps.dashboard.logistics_visualizations import (
    LogisticsChartService,
)


class LogisticsRegressionTests(SimpleTestCase):
    def setUp(self):
        self.records = [
            {
                "category": "Electronics",
                "median_price": 100,
                "median_rating": 3,
            },
            {
                "category": "Groceries",
                "median_price": 200,
                "median_rating": 4,
            },
            {
                "category": "Beauty",
                "median_price": 300,
                "median_rating": 5,
            },
        ]

    def test_regression_line_is_generated(self):
        figure = LogisticsChartService.prepare_scatter(
            self.records,
            "median_price",
            "median_rating",
            "Price vs Rating",
            "Median Price",
            "Median Rating",
        )

        self.assertEqual(len(figure.data), 2)

        self.assertEqual(
            figure.data[1].name,
            "Overall linear regression",
        )

        self.assertEqual(
            figure.data[1].mode,
            "lines",
        )

    def test_regression_line_has_100_points(self):
        figure = LogisticsChartService.prepare_scatter(
            self.records,
            "median_price",
            "median_rating",
            "Price vs Rating",
            "Median Price",
            "Median Rating",
        )

        self.assertEqual(
            len(figure.data[1].x),
            100,
        )

        self.assertEqual(
            len(figure.data[1].y),
            100,
        )

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

        self.assertEqual(
            figure.data[0].mode,
            "markers",
        )

    def test_regression_not_generated_with_one_record(self):
        figure = LogisticsChartService.prepare_scatter(
            self.records[:1],
            "median_price",
            "median_rating",
            "Price vs Rating",
            "Median Price",
            "Median Rating",
        )

        self.assertEqual(len(figure.data), 1)

    def test_regression_not_generated_with_constant_x(self):
        records = [
            {
                "category": "A",
                "median_price": 100,
                "median_rating": 3,
            },
            {
                "category": "B",
                "median_price": 100,
                "median_rating": 4,
            },
            {
                "category": "C",
                "median_price": 100,
                "median_rating": 5,
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

    def test_missing_values_are_excluded(self):
        records = [
            {
                "category": "A",
                "median_price": 100,
                "median_rating": 3,
            },
            {
                "category": "B",
                "median_price": None,
                "median_rating": 4,
            },
            {
                "category": "C",
                "median_price": 300,
                "median_rating": 5,
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

        self.assertEqual(len(figure.data[0].x), 2)
        self.assertEqual(len(figure.data), 2)
