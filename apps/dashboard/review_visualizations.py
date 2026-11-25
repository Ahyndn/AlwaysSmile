from typing import ClassVar

from .chart_base import BaseChartService


class ReviewChartService(BaseChartService):
    """Generates customer review charts using Matplotlib."""

    RATINGS = (1, 2, 3, 4, 5)

    RATING_COLORS: ClassVar[dict[int, str]] = {
        1: "#dc2626",
        2: "#ea5808",
        3: "#d97706",
        4: "#2563eb",
        5: "#059669",
    }

    # Backward-compatible aliases.
    STAR_RATINGS = RATINGS
    STAR_COLORS = RATING_COLORS

    @classmethod
    def _normalize_count(cls, value):
        """Convert review counts into non-negative integers."""

        try:
            return max(0, int(value))

        except (TypeError, ValueError, OverflowError):
            return 0

    @classmethod
    def _normalize_rating(cls, value):
        """Accept only valid whole-number ratings from 1 to 5."""

        try:
            rating = int(value)

            # Avoid accepting values such as 4.5 or "4.5".
            if isinstance(value, float) and not value.is_integer():
                return None

            if isinstance(value, str) and value.strip() not in {
                "1",
                "2",
                "3",
                "4",
                "5",
            }:
                return None

            return rating if rating in cls.RATINGS else None

        except (TypeError, ValueError, OverflowError):
            return None

    @classmethod
    def prepare_pie_chart(cls, rating_distribution):
        """Generate product rating distribution with percentages."""

        counts = dict.fromkeys(cls.RATINGS, 0)

        for item in rating_distribution or []:
            if not isinstance(item, dict):
                continue

            rating = cls._normalize_rating(item.get("rating"))

            if rating is not None:
                counts[rating] += cls._normalize_count(item.get("count", 0))

        total = sum(counts.values())

        results = [
            {
                "rating": rating,
                "label": f"{rating} Rating",
                "count": counts[rating],
                "percentage": (counts[rating] / total * 100 if total else 0),
                "color": cls.RATING_COLORS[rating],
            }
            for rating in cls.RATINGS
        ]

        positive_items = [item for item in results if item["count"] > 0]

        def renderer(figure, axis):

            if not positive_items:
                axis.text(
                    0.5,
                    0.5,
                    "No review data available",
                    ha="center",
                    va="center",
                    transform=axis.transAxes,
                    color="#9ca3af",
                    fontsize=10,
                )

                axis.set_axis_off()

            else:
                axis.pie(
                    [item["count"] for item in positive_items],
                    labels=[item["label"] for item in positive_items],
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

        return cls.render((4, 3.5), renderer)

    @classmethod
    def prepare_category_bar_chart(cls, category_distribution):
        """Generate grouped review counts by product category."""

        categories = []
        category_counts = {}

        for item in category_distribution or []:
            if not isinstance(item, dict):
                continue

            category = str(item.get("category") or "Unknown")

            if category in category_counts:
                continue

            rating_counts = dict.fromkeys(cls.RATINGS, 0)

            ratings = item.get("ratings") or []

            if not isinstance(ratings, list):
                ratings = []

            for rating_item in ratings:
                if not isinstance(rating_item, dict):
                    continue

                rating = cls._normalize_rating(rating_item.get("rating"))

                if rating is not None:
                    rating_counts[rating] += cls._normalize_count(
                        rating_item.get("count", 0)
                    )

            categories.append(category)

            category_counts[category] = rating_counts

        results = [
            {
                "category": category,
                "ratings": [
                    {
                        "rating": rating,
                        "count": category_counts[category][rating],
                        "color": cls.RATING_COLORS[rating],
                    }
                    for rating in cls.RATINGS
                ],
            }
            for category in categories
        ]

        def renderer(figure, axis):

            if not categories:
                axis.text(
                    0.5,
                    0.5,
                    "No review data available",
                    ha="center",
                    va="center",
                    transform=axis.transAxes,
                    color="#9ca3af",
                    fontsize=11,
                )

                axis.set_axis_off()

            else:
                positions = list(range(len(categories)))

                bar_width = 0.15

                for index, rating in enumerate(cls.RATINGS):
                    values = [
                        category_counts[category][rating] for category in categories
                    ]

                    offsets = [
                        position + (index - 2) * bar_width for position in positions
                    ]

                    axis.bar(
                        offsets,
                        values,
                        width=bar_width,
                        color=cls.RATING_COLORS[rating],
                        label=f"Rating {rating}",
                    )

                axis.set_xticks(positions)

                axis.set_xticklabels(
                    categories,
                    rotation=35,
                    ha="right",
                )

                axis.set_xlabel("Product Category")
                axis.set_ylabel("Number of Reviews")

                axis.set_ylim(bottom=0)

                axis.legend(
                    title="Product Rating",
                    frameon=False,
                    ncol=5,
                    loc="upper center",
                    bbox_to_anchor=(0.5, 1.15),
                )

                cls.style_axis(axis)

            figure.tight_layout()

            return results

        return cls.render(
            (max(9, len(categories) * 1.1), 5.5),
            renderer,
        )

