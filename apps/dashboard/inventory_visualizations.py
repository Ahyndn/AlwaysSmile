from decimal import Decimal, InvalidOperation
from typing import ClassVar

import plotly.graph_objects as go

from .chart_base import BaseChartService


class InventoryChartService(BaseChartService):
    """Generate inventory analytics visualizations."""

    STOCK_COLORS: ClassVar[dict[str, str]] = {
        "Out of Stock": "#dc2626",
        "Low Stock": "#d97706",
        "In Stock": "#059669",
    }

    CATEGORY_COLOR = "#2563eb"

    # --------------------------------------------------
    # NORMALIZATION HELPERS
    # --------------------------------------------------

    @classmethod
    def _to_decimal(cls, value):
        """Convert values to non-negative finite Decimals."""

        try:
            result = Decimal(str(value))

            if not result.is_finite() or result < 0:
                return Decimal(0)

            return result

        except (
            InvalidOperation,
            TypeError,
            ValueError,
            OverflowError,
        ):
            return Decimal(0)

    @classmethod
    def _normalize_distribution(cls, distribution):
        """Normalize category or stock distribution data."""

        if not isinstance(distribution, dict):
            return {}

        return {str(key): cls._to_decimal(value) for key, value in distribution.items()}

    # --------------------------------------------------
    # 1. CATEGORY SALES BAR CHART
    # --------------------------------------------------

    @classmethod
    def prepare_category_sales_chart(cls, category_sales):
        """
        Generate category sales bar chart.

        Returns:
            tuple: (chart_data, base64_image)
        """

        data = cls._normalize_distribution(category_sales)

        results = [
            {
                "category": category,
                "value": value,
            }
            for category, value in data.items()
        ]

        def renderer(figure, axis):

            if not results:
                axis.text(
                    0.5,
                    0.5,
                    "No sales data available",
                    ha="center",
                    va="center",
                    transform=axis.transAxes,
                    color="#9ca3af",
                    fontsize=10,
                )

                axis.set_axis_off()

            else:
                categories = [item["category"] for item in results]

                values = [float(item["value"]) for item in results]

                bars = axis.bar(
                    categories,
                    values,
                    color=cls.CATEGORY_COLOR,
                    width=0.6,
                )

                axis.set_xlabel("Product Category")
                axis.set_ylabel("Estimated Sales Value")
                axis.set_ylim(bottom=0)

                axis.tick_params(
                    axis="x",
                    rotation=35,
                )

                for label in axis.get_xticklabels():
                    label.set_horizontalalignment("right")

                axis.bar_label(
                    bars,
                    fmt="%.2f",
                    padding=3,
                    fontsize=8,
                )

                cls.style_axis(axis)

            figure.tight_layout()

            return results

        return cls.render(
            (max(7, len(results) * 1.1), 4.5),
            renderer,
        )

    # --------------------------------------------------
    # 2. STOCK DISTRIBUTION PIE CHART
    # --------------------------------------------------

    @classmethod
    def prepare_stock_distribution_chart(cls, stock_distribution):
        """
        Generate stock distribution pie chart.

        Returns:
            tuple: (chart_data, base64_image)
        """

        normalized = cls._normalize_distribution(stock_distribution)

        # Maintain a consistent order and include
        # all three stock classifications.

        results = [
            {
                "status": status,
                "count": normalized.get(
                    status,
                    Decimal(0),
                ),
                "percentage": 0,
                "color": color,
            }
            for status, color in cls.STOCK_COLORS.items()
        ]

        total = sum(
            (item["count"] for item in results),
            Decimal(0),
        )

        for item in results:
            item["percentage"] = float(item["count"] / total * 100) if total > 0 else 0

        positive_items = [item for item in results if item["count"] > 0]

        def renderer(figure, axis):

            if not positive_items:
                axis.text(
                    0.5,
                    0.5,
                    "No stock data available",
                    ha="center",
                    va="center",
                    transform=axis.transAxes,
                    color="#9ca3af",
                    fontsize=10,
                )

                axis.set_axis_off()

            else:
                axis.pie(
                    [float(item["count"]) for item in positive_items],
                    labels=[item["status"] for item in positive_items],
                    autopct="%1.1f%%",
                    startangle=90,
                    counterclock=False,
                    colors=[item["color"] for item in positive_items],
                    wedgeprops={
                        "edgecolor": "white",
                        "linewidth": 2,
                    },
                    textprops={
                        "fontsize": 8,
                    },
                )

                axis.axis("equal")

            figure.tight_layout()

            return results

        return cls.render(
            (5, 4),
            renderer,
        )

    # --------------------------------------------------
    # 3. ABC ANALYSIS PLOTLY CHART
    # --------------------------------------------------

    @classmethod
    def prepare_abc_chart(cls, abc_dataframe):
        """
        Generate interactive ABC analysis chart.

        Expected DataFrame columns:
            title
            sales_value
            cumulative_sales_value
            cumulative_percentage
            abc_class

        Returns:
            plotly.graph_objects.Figure
        """

        required_columns = {
            "title",
            "sales_value",
            "cumulative_sales_value",
            "cumulative_percentage",
            "abc_class",
        }

        if abc_dataframe is None:
            raise ValueError("ABC analysis data cannot be None.")

        missing_columns = required_columns - set(abc_dataframe.columns)

        if missing_columns:
            raise ValueError(
                "Missing ABC analysis columns: " + ", ".join(sorted(missing_columns))
            )

        dataframe = abc_dataframe.copy(deep=True)

        figure = go.Figure()

        if dataframe.empty:
            figure.update_layout(
                title="ABC Analysis",
                xaxis_title="Product Ranking",
                yaxis_title="Cumulative Sales Value (%)",
                annotations=[
                    {
                        "text": "No ABC analysis data available",
                        "xref": "paper",
                        "yref": "paper",
                        "x": 0.5,
                        "y": 0.5,
                        "showarrow": False,
                        "font": {
                            "color": "#9ca3af",
                            "size": 14,
                        },
                    }
                ],
            )

            return figure

        dataframe["sales_value"] = dataframe["sales_value"].apply(cls._to_decimal)

        dataframe["cumulative_sales_value"] = dataframe["cumulative_sales_value"].apply(
            cls._to_decimal
        )

        dataframe["cumulative_percentage"] = dataframe["cumulative_percentage"].apply(
            lambda value: float(cls._to_decimal(value))
        )

        dataframe["title"] = dataframe["title"].fillna("Unknown Product").astype(str)

        dataframe["abc_class"] = dataframe["abc_class"].fillna("C").astype(str)

        dataframe = dataframe.reset_index(drop=True)

        positions = dataframe["title"].tolist()

        colors = {
            "A": "#059669",
            "B": "#d97706",
            "C": "#2563eb",
        }

        marker_colors = [
            colors.get(classification, "#6b7280")
            for classification in dataframe["abc_class"]
        ]

        custom_data = [
            [
                row["title"],
                str(row["sales_value"]),
                str(row["cumulative_sales_value"]),
                row["abc_class"],
            ]
            for _, row in dataframe.iterrows()
        ]

        # Cumulative sales-value line.

        figure.add_trace(
            go.Scatter(
                x=positions,
                y=dataframe["cumulative_percentage"].tolist(),
                mode="lines+markers",
                name="Cumulative Sales %",
                line={
                    "color": "#2563eb",
                    "width": 3,
                },
                marker={
                    "size": 8,
                    "color": marker_colors,
                },
                customdata=custom_data,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Product: %{x}<br>"
                    "Sales Value: %{customdata[1]}<br>"
                    "Cumulative Sales Value: "
                    "%{customdata[2]}<br>"
                    "Cumulative Percentage: %{y:.2f}%<br>"
                    "ABC Classification: "
                    "%{customdata[3]}"
                    "<extra></extra>"
                ),
            )
        )

        # ABC reference thresholds.

        for threshold, label, color in [
            (80, "A Threshold (80%)", "#059669"),
            (95, "B Threshold (95%)", "#d97706"),
            (100, "C Threshold (100%)", "#dc2626"),
        ]:
            figure.add_hline(
                y=threshold,
                line_dash="dash",
                line_color=color,
                line_width=1.5,
                annotation_text=label,
                annotation_position="top right",
            )

        figure.update_layout(
            title="ABC Analysis - Cumulative Sales Value",
            xaxis_title="Product Ranking by Sales Value",
            yaxis_title="Cumulative Sales Value (%)",
            hovermode="closest",
            template="plotly_white",
            height=450,
            margin={
                "l": 60,
                "r": 40,
                "t": 80,
                "b": 80,
            },
            legend={
                "orientation": "h",
                "y": 1.12,
                "x": 0,
            },
        )

        figure.update_xaxes(
            type="category",
            categoryorder="array",
            categoryarray=positions,
        )

        figure.update_yaxes(
            range=[0, 105],
            ticksuffix="%",
            dtick=20,
        )

        return figure
