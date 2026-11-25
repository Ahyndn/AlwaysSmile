import base64
import threading
from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


class BaseChartService:
    """
    Shared functionality for dashboard chart services.

    Responsibilities:
    - Thread-safe chart rendering.
    - Matplotlib figure management.
    - PNG image generation.
    - Base64 data URI conversion.
    - Consistent chart styling.
    """

    _render_lock = threading.RLock()

    @staticmethod
    def figure_to_data_uri(figure):
        """
        Convert a Matplotlib figure into a PNG data URI.

        This method does not close the figure.
        Figure lifecycle is managed by render().
        """
        buffer = BytesIO()

        try:
            figure.savefig(
                buffer,
                format="png",
                dpi=150,
                bbox_inches="tight",
                facecolor="white",
            )

            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

            return f"data:image/png;base64,{encoded}"

        finally:
            buffer.close()

    @staticmethod
    def create_figure(figsize):
        """Create a Matplotlib figure and axis."""
        return plt.subplots(figsize=figsize)

    @classmethod
    def render(cls, figsize, renderer):
        """
        Safely render a chart.

        renderer receives (figure, axis) and returns chart data.

        This method exclusively owns figure cleanup.
        """
        with cls._render_lock:
            figure, axis = cls.create_figure(figsize)

            try:
                result = renderer(figure, axis)

                image = cls.figure_to_data_uri(figure)

                return result, image

            finally:
                plt.close(figure)

    @staticmethod
    def style_axis(axis):
        """Apply consistent dashboard chart styling."""

        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.spines["left"].set_visible(False)
        axis.spines["bottom"].set_color("#e5e7eb")

        axis.tick_params(
            axis="both",
            labelsize=9,
            colors="#6b7280",
        )

        axis.grid(
            axis="y",
            linestyle="--",
            alpha=0.2,
        )

        axis.set_axisbelow(True)
