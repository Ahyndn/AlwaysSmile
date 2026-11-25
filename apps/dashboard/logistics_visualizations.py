"""Plotly visualizations for logistics analytics."""

import math

import numpy as np
import plotly.graph_objects as go


class LogisticsChartService:
    """Generate independent logistics scatterplots and regressions."""

    BLUE = "#2563EB"
    RED = "#DC2626"
    GRID = "#E5E7EB"

    @staticmethod
    def _valid_number(value):
        """Check whether a value is a finite, non-negative number."""

        if isinstance(value, bool) or value is None:
            return False

        try:
            number = float(value)
            return math.isfinite(number) and number >= 0

        except (TypeError, ValueError, OverflowError):
            return False

    @classmethod
    def _valid_records(cls, records, x_key, y_key):
        """Return records with valid numeric X and Y measurements."""

        valid = []

        if not isinstance(records, (list, tuple)):
            return valid

        for item in records:
            if not isinstance(item, dict):
                continue

            x_value = item.get(x_key)
            y_value = item.get(y_key)

            if not cls._valid_number(x_value):
                continue

            if not cls._valid_number(y_value):
                continue

            valid.append(
                {
                    "category": str(item.get("category") or "Uncategorized"),
                    "x": float(x_value),
                    "y": float(y_value),
                }
            )

        return valid

    @staticmethod
    def _add_empty_annotation(figure, message):
        """Display a message when a chart has insufficient data."""

        figure.add_annotation(
            text=message,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"size": 14, "color": "#6B7280"},
        )

    @classmethod
    def _add_regression(cls, figure, x_values, y_values):
        """
        Add an ordinary least-squares regression line
        and display its coefficient of determination (R²).
        """

        if len(x_values) < 2:
            return

        x_array = np.asarray(x_values, dtype=float)
        y_array = np.asarray(y_values, dtype=float)

        if not np.isfinite(x_array).all():
            return

        if not np.isfinite(y_array).all():
            return

        if np.unique(x_array).size < 2:
            return

        try:
            slope, intercept = np.polyfit(
                x_array,
                y_array,
                1,
            )

            if not math.isfinite(slope):
                return

            if not math.isfinite(intercept):
                return

            line_x = np.linspace(
                float(x_array.min()),
                float(x_array.max()),
                100,
            )

            line_y = slope * line_x + intercept

            if not np.isfinite(line_y).all():
                return

            # Calculate coefficient of determination (R²).
            predicted_y = slope * x_array + intercept

            ss_res = float(np.sum((y_array - predicted_y) ** 2))
            ss_tot = float(np.sum((y_array - np.mean(y_array)) ** 2))

            if not math.isfinite(ss_res) or not math.isfinite(ss_tot):
                return

            # Pearson correlation is undefined if either variable
            # has zero variation.
            if ss_tot > 0:
                correlation_r = float(np.corrcoef(x_array, y_array)[0, 1])

                if not math.isfinite(correlation_r):
                    return

                # Protect against tiny floating-point rounding errors.
                correlation_r = max(-1.0, min(1.0, correlation_r))

                r_squared = 1.0 - (ss_res / ss_tot)
                r_squared = max(0.0, min(1.0, r_squared))

                stats_text = (
                    f"<b>Pearson r = {correlation_r:.3f}</b><br>"
                    f"<b>R² = {r_squared:.3f}</b>"
                )

            else:
                # Constant Y values have no defined Pearson r or R².
                stats_text = "<b>Pearson r = N/A</b><br><b>R² = N/A</b>"

        except (
            ValueError,
            TypeError,
            np.linalg.LinAlgError,
            OverflowError,
        ):
            return

        # Preserve the existing regression trace name
        # so existing tests remain compatible.
        figure.add_trace(
            go.Scatter(
                x=line_x,
                y=line_y,
                mode="lines",
                name="Overall linear regression",
                showlegend=False,
                line={
                    "color": cls.RED,
                    "width": 2,
                    "dash": "dash",
                },
                hoverinfo="skip",
            )
        )

        # Display Pearson's r and R² inside the chart.
        figure.add_annotation(
            text=stats_text,
            x=0.98,
            y=0.98,
            xref="paper",
            yref="paper",
            xanchor="right",
            yanchor="top",
            showarrow=False,
            font={
                "size": 13,
                "color": cls.RED,
            },
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor=cls.RED,
            borderwidth=1,
            borderpad=5,
        )

    @classmethod
    def _update_layout(
        cls,
        figure,
        title,
        x_title,
        y_title,
        height=390,
    ):
        """Apply consistent dashboard chart styling."""

        figure.update_layout(
            title={
                "text": title,
                "x": 0.03,
                "xanchor": "left",
            },
            template="plotly_white",
            height=height,
            margin={
                "l": 65,
                "r": 30,
                "t": 75,
                "b": 65,
            },
            xaxis_title=x_title,
            yaxis_title=y_title,
            hovermode="closest",
            legend={
                "orientation": "h",
                "y": -0.23,
            },
            font={
                "family": "Arial, sans-serif",
                "color": "#374151",
            },
            xaxis={
                "gridcolor": cls.GRID,
                "zeroline": False,
            },
            yaxis={
                "gridcolor": cls.GRID,
                "zeroline": False,
            },
        )

    @classmethod
    def prepare_scatter(
        cls,
        records,
        x_key,
        y_key,
        title,
        x_title,
        y_title,
        regression=True,
    ):
        """Create a scatterplot with an optional regression line."""

        figure = go.Figure()

        valid = cls._valid_records(
            records,
            x_key,
            y_key,
        )

        if valid:
            x_values = [item["x"] for item in valid]
            y_values = [item["y"] for item in valid]
            categories = [item["category"] for item in valid]

            figure.add_trace(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="markers",
                    name="Category median",
                    text=categories,
                    marker={
                        "size": 11,
                        "color": cls.BLUE,
                        "opacity": 0.85,
                        "line": {
                            "width": 1,
                            "color": "#FFFFFF",
                        },
                    },
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        + x_title
                        + ": %{x:.2f}<br>"
                        + y_title
                        + ": %{y:.2f}"
                        + "<extra></extra>"
                    ),
                )
            )

            if regression:
                cls._add_regression(
                    figure,
                    x_values,
                    y_values,
                )

        else:
            cls._add_empty_annotation(
                figure,
                "Insufficient data for this visualization.",
            )

        cls._update_layout(
            figure,
            title,
            x_title,
            y_title,
        )

        return figure

    @classmethod
    def prepare_lifetime_scatter(
        cls,
        records,
        x_key,
        title,
        x_title,
    ):
        """Display lifetime warranty products by category."""

        figure = go.Figure()

        valid = []

        if isinstance(records, (list, tuple)):
            for item in records:
                if not isinstance(item, dict):
                    continue

                count = item.get("lifetime_count", 0)

                if (
                    isinstance(count, bool)
                    or not isinstance(count, (int, float))
                    or not math.isfinite(count)
                    or count <= 0
                ):
                    continue

                x_value = item.get(x_key)

                if not cls._valid_number(x_value):
                    continue

                valid.append(
                    {
                        "category": str(item.get("category") or "Uncategorized"),
                        "x": float(x_value),
                        "count": int(count),
                    }
                )

        if valid:
            figure.add_trace(
                go.Scatter(
                    x=[item["x"] for item in valid],
                    y=["Lifetime warranty"] * len(valid),
                    mode="markers",
                    name="Lifetime warranty",
                    text=[item["category"] for item in valid],
                    customdata=[[item["count"]] for item in valid],
                    marker={
                        "size": [12 + min(item["count"] * 3, 24) for item in valid],
                        "color": cls.BLUE,
                        "opacity": 0.85,
                        "line": {
                            "width": 1,
                            "color": "#FFFFFF",
                        },
                    },
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        + x_title
                        + ": %{x:.2f}<br>"
                        + "Lifetime warranty products: %{customdata[0]}"
                        + "<extra></extra>"
                    ),
                )
            )

        else:
            cls._add_empty_annotation(
                figure,
                "No lifetime warranty products available.",
            )

        cls._update_layout(
            figure,
            title,
            x_title,
            "Warranty classification",
            height=350,
        )

        figure.update_layout(
            yaxis={
                "categoryorder": "array",
                "categoryarray": ["Lifetime warranty"],
                "gridcolor": cls.GRID,
            },
            showlegend=False,
        )

        return figure

    @classmethod
    def prepare_dashboard(cls, records):
        """Generate all seven independent dashboard charts."""

        return {
            "price_rating": cls.prepare_scatter(
                records,
                "median_price",
                "median_rating",
                "Price vs Rating",
                "Median Price",
                "Median Rating",
            ),
            "rating_shipping": cls.prepare_scatter(
                records,
                "median_rating",
                "median_shipping_days",
                "Rating vs Shipping Time",
                "Median Rating",
                "Median Shipping Time (Days)",
            ),
            "price_shipping": cls.prepare_scatter(
                records,
                "median_price",
                "median_shipping_days",
                "Price vs Shipping Time",
                "Median Price",
                "Median Shipping Time (Days)",
            ),
            "warranty_rating": cls.prepare_scatter(
                records,
                "median_warranty_days",
                "median_rating",
                "Warranty vs Rating",
                "Median Warranty (Days)",
                "Median Rating",
            ),
            "warranty_price": cls.prepare_scatter(
                records,
                "median_warranty_days",
                "median_price",
                "Warranty vs Price",
                "Median Warranty (Days)",
                "Median Price",
            ),
            "lifetime_rating": cls.prepare_lifetime_scatter(
                records,
                "lifetime_median_rating",
                "Lifetime Warranty vs Rating",
                "Median Rating",
            ),
            "lifetime_price": cls.prepare_lifetime_scatter(
                records,
                "lifetime_median_price",
                "Lifetime Warranty vs Price",
                "Median Price",
            ),
        }

