import base64

import matplotlib.pyplot as plt
from django.test import SimpleTestCase

from apps.dashboard.chart_base import BaseChartService


class BaseChartServiceTests(SimpleTestCase):
    def test_figure_to_data_uri_returns_valid_png(self):
        figure, axis = plt.subplots()

        try:
            axis.plot([1, 2, 3])

            image = BaseChartService.figure_to_data_uri(figure)

            self.assertTrue(image.startswith("data:image/png;base64,"))

            encoded = image.split(",", 1)[1]
            decoded = base64.b64decode(encoded)

            self.assertTrue(decoded.startswith(b"\x89PNG\r\n\x1a\n"))

        finally:
            plt.close(figure)

    def test_figure_conversion_does_not_close_figure(self):
        figure, axis = plt.subplots()

        try:
            BaseChartService.figure_to_data_uri(figure)

            self.assertIn(
                figure.number,
                plt.get_fignums(),
            )

        finally:
            plt.close(figure)

    def test_render_returns_renderer_result_and_image(self):

        def renderer(figure, axis):
            axis.plot([1, 2, 3])
            return {"success": True}

        result, image = BaseChartService.render(
            (5, 4),
            renderer,
        )

        self.assertEqual(result, {"success": True})

        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_render_closes_figure_after_success(self):
        figure_number = None

        def renderer(figure, axis):
            nonlocal figure_number

            figure_number = figure.number

            axis.plot([1, 2, 3])

            return {"success": True}

        BaseChartService.render(
            (4, 3),
            renderer,
        )

        self.assertNotIn(
            figure_number,
            plt.get_fignums(),
        )

    def test_render_closes_figure_when_renderer_fails(self):
        figure_number = None

        def renderer(figure, axis):
            nonlocal figure_number

            figure_number = figure.number

            raise ValueError("Rendering failed")

        with self.assertRaises(ValueError):
            BaseChartService.render(
                (5, 4),
                renderer,
            )

        self.assertNotIn(
            figure_number,
            plt.get_fignums(),
        )

    def test_render_closes_figure_when_image_conversion_fails(self):
        figure_number = None

        def renderer(figure, axis):
            nonlocal figure_number

            figure_number = figure.number

            return {"success": True}

        from unittest.mock import patch

        with (
            patch.object(
                BaseChartService,
                "figure_to_data_uri",
                side_effect=RuntimeError("Image conversion failed"),
            ),
            self.assertRaises(RuntimeError),
        ):
            BaseChartService.render(
                (4, 3),
                renderer,
            )

        self.assertNotIn(
            figure_number,
            plt.get_fignums(),
        )
