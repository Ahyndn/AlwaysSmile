from collections import defaultdict
from datetime import date, datetime


class ReviewAnalyticsService:
    """Provide customer review analytics, summaries and filtering."""

    RATINGS = (1, 2, 3, 4, 5)

    @staticmethod
    def _get_reviews(products):
        reviews = []

        for product in products or []:
            if not isinstance(product, dict):
                continue

            product_reviews = product.get("reviews", [])

            if not isinstance(product_reviews, list):
                continue

            category = str(product.get("category") or "Unknown")

            for original_review in product_reviews:
                if not isinstance(original_review, dict):
                    continue

                review = {**original_review}

                review["product_id"] = product.get("id")
                review["product_title"] = product.get("title") or "Unknown Product"

                review["category"] = category
                review["_category"] = category

                review["reviewer_name"] = (
                    review.get("reviewer_name")
                    or review.get("reviewerName")
                    or "Anonymous"
                )

                review["reviewer_email"] = (
                    review.get("reviewer_email")
                    or review.get("reviewerEmail")
                    or "Unavailable"
                )

                reviews.append(review)

        return reviews

    @classmethod
    def _normalize_rating(cls, value):
        try:
            if isinstance(value, bool):
                return None

            rating = int(value)

            if isinstance(value, float) and not value.is_integer():
                return None

        except (TypeError, ValueError, OverflowError):
            return None

        return rating if rating in cls.RATINGS else None

    @staticmethod
    def _parse_date(value):
        if not value:
            return None

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        try:
            return date.fromisoformat(str(value)[:10])
        except TypeError, ValueError:
            return None

    @classmethod
    def _rating_counts(cls, reviews):
        distribution = dict.fromkeys(cls.RATINGS, 0)

        for review in reviews:
            rating = cls._normalize_rating(review.get("rating"))

            if rating is not None:
                distribution[rating] += 1

        return distribution

    @classmethod
    def calculate_rating_distribution(cls, products):
        return cls._rating_counts(cls._get_reviews(products))

    @classmethod
    def calculate_category_review_distribution(cls, products):
        distribution = defaultdict(lambda: dict.fromkeys(cls.RATINGS, 0))

        for review in cls._get_reviews(products):
            rating = cls._normalize_rating(review.get("rating"))

            if rating is None:
                continue

            distribution[review["_category"]][rating] += 1

        return dict(distribution)

    @classmethod
    def analyze(cls, products):
        reviews = cls._get_reviews(products)

        rating_counts = cls._rating_counts(reviews)

        category_counts = defaultdict(lambda: dict.fromkeys(cls.RATINGS, 0))

        for review in reviews:
            rating = cls._normalize_rating(review.get("rating"))

            if rating is not None:
                category_counts[review["_category"]][rating] += 1

        categories = sorted(
            category_counts.keys(),
            key=str.casefold,
        )

        star_distribution = [
            {
                "rating": rating,
                "count": rating_counts[rating],
            }
            for rating in cls.RATINGS
        ]

        category_distribution = [
            {
                "category": category,
                "ratings": [
                    {
                        "rating": rating,
                        "count": category_counts[category][rating],
                    }
                    for rating in cls.RATINGS
                ],
            }
            for category in categories
        ]

        positive = rating_counts[4] + rating_counts[5]
        neutral = rating_counts[3]
        negative = rating_counts[1] + rating_counts[2]

        return {
            "total_reviews": len(reviews),
            "positive_reviews": positive,
            "neutral_reviews": neutral,
            "negative_reviews": negative,
            "categories": categories,
            "rating_distribution": rating_counts,
            "star_distribution": star_distribution,
            "category_distribution": category_distribution,
            "category_star_distribution": category_distribution,
        }

    @classmethod
    def get_review_categories(cls, products):
        categories = {review["_category"] for review in cls._get_reviews(products)}

        return sorted(categories, key=str.casefold)

    @classmethod
    def filter_reviews(
        cls,
        products,
        search="",
        rating="",
        category="",
        start_date="",
        end_date="",
    ):
        reviews = cls._get_reviews(products)

        search = str(search or "").strip().casefold()
        category = str(category or "").strip().casefold()

        selected_rating = None

        if rating not in ("", None):
            selected_rating = cls._normalize_rating(rating)

        start = cls._parse_date(start_date)
        end = cls._parse_date(end_date)

        filtered = []

        for review in reviews:
            comment = str(review.get("comment") or "").casefold()

            if search and search not in comment:
                continue

            review_rating = cls._normalize_rating(review.get("rating"))

            if review_rating is None:
                continue

            if selected_rating is not None and review_rating != selected_rating:
                continue

            if category and review["_category"].casefold() != category:
                continue

            review_date = cls._parse_date(review.get("date"))

            if start or end:
                if review_date is None:
                    continue

                if start and review_date < start:
                    continue

                if end and review_date > end:
                    continue

            filtered.append(review)

        filtered.sort(
            key=lambda review: cls._parse_date(review.get("date")) or date.min,
            reverse=True,
        )

        return filtered


def calculate_review_summary(products):
    result = ReviewAnalyticsService.analyze(products)

    return {
        key: result[key]
        for key in (
            "total_reviews",
            "positive_reviews",
            "neutral_reviews",
            "negative_reviews",
        )
    }


# Backward compatibility.
CustomerReviewAnalytics = ReviewAnalyticsService

