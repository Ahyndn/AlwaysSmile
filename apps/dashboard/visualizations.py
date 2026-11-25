from decimal import Decimal, InvalidOperation

from matplotlib.ticker import FuncFormatter

from .chart_base import BaseChartService


class DashboardChartService(BaseChartService):
    """Generates dashboard charts using Matplotlib."""

    COLORS = [
        "#2563eb",
        "#7c3aed",
        "#0891b2",
        "#059669",
        "#d97706",
        "#dc2626",
        "#9333ea",
        "#64748b",
    ]

    @staticmethod
    def _normalize_value(value):
        """Convert values into finite, non-negative Decimals."""

        try:
            result = Decimal(str(value))

            if not result.is_finite():
                return Decimal(0)

            return max(Decimal(0), result)

        except (InvalidOperation, TypeError, ValueError):
            return Decimal(0)

    @classmethod
    def prepare_bar_chart(cls, category_sales):
        """Return category data with normalized widths and chart image."""

        category_sales = category_sales or {}

        normalized = {
            category: cls._normalize_value(value)
            for category, value in category_sales.items()
        }

        categories = list(normalized)

        values = [float(normalized[category]) for category in categories]

        maximum = max(values, default=0)

        results = [
            {
                "category": category,
                "value": value,
                "width": (value / maximum * 100 if maximum > 0 else 0),
            }
            for category, value in zip(categories, values)
        ]

        def renderer(figure, axis):

            if not categories or not any(values):
                axis.text(
                    0.5,
                    0.5,
                    "No sales data available",
                    ha="center",
                    va="center",
                    transform=axis.transAxes,
                    color="#9ca3af",
                    fontsize=11,
                )

                axis.set_axis_off()

            else:
                bars = axis.barh(
                    categories,
                    values,
                    color="#2563eb",
                    height=0.55,
                )

                axis.invert_yaxis()

                axis.set_xlabel("Total Sales ($)")
                axis.set_ylabel("Category")

                cls.style_axis(axis)

                axis.set_xlim(
                    left=0,
                    right=maximum * 1.18,
                )

                for bar, value in zip(bars, values):
                    axis.annotate(
                        f"${value:,.2f}",
                        xy=(
                            bar.get_width(),
                            bar.get_y() + bar.get_height() / 2,
                        ),
                        xytext=(5, 0),
                        textcoords="offset points",
                        va="center",
                        fontsize=8,
                        color="#374151",
                    )

                axis.xaxis.set_major_formatter(
                    FuncFormatter(lambda value, position: f"${value:,.0f}")
                )

            figure.tight_layout()

            return results

        return cls.render(
            (8, max(3.5, len(categories) * 0.45)),
            renderer,
        )

    @classmethod
    def prepare_pie_chart(cls, category_sales):
        """Return category percentages and a pie chart image."""

        category_sales = category_sales or {}

        normalized = {
            category: cls._normalize_value(value)
            for category, value in category_sales.items()
        }

        total = sum(
            normalized.values(),
            Decimal(0),
        )

        results = []

        for category, value in normalized.items():
            percentage = float(value / total * 100) if total > 0 else 0

            results.append(
                {
                    "category": category,
                    "value": float(value),
                    "percentage": percentage,
                }
            )

        positive_items = [item for item in results if item["value"] > 0]

        def renderer(figure, axis):

            if not positive_items:
                axis.text(
                    0.5,
                    0.5,
                    "No sales data available",
                    ha="center",
                    va="center",
                    transform=axis.transAxes,
                    color="#9ca3af",
                    fontsize=11,
                )

                axis.set_axis_off()

            else:
                axis.pie(
                    [item["value"] for item in positive_items],
                    labels=None,
                    colors=[
                        cls.COLORS[index % len(cls.COLORS)]
                        for index in range(len(positive_items))
                    ],
                    startangle=90,
                    counterclock=False,
                    wedgeprops={
                        "edgecolor": "white",
                        "linewidth": 2,
                    },
                )

                axis.axis("equal")

            figure.tight_layout()

            return results

        return cls.render((5, 5), renderer)


# Backward-compatible public functions.


def prepare_bar_chart(category_sales):
    return DashboardChartService.prepare_bar_chart(category_sales)


def prepare_pie_chart(category_sales):
    return DashboardChartService.prepare_pie_chart(category_sales)
