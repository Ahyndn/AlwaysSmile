from decimal import Decimal, InvalidOperation
from typing import ClassVar

import numpy as np
import pandas as pd

from .analytics import (
    CATEGORY_MAP,
    DASHBOARD_CATEGORIES,
    ProductSalesCalculator,
)


class InvalidProductsTypeError(TypeError):
    """Raised when the products collection has an invalid type."""


class InventoryAnalyticsService:
    # Process product catalogue data for inventory analytics.

    STOCK_OUT = "Out of Stock"
    STOCK_LOW = "Low Stock"
    STOCK_IN = "In Stock"

    ABC_A_LIMIT = 80.0
    ABC_B_LIMIT = 95.0

    DATAFRAME_COLUMNS: ClassVar[list[str]] = [
        "id",
        "title",
        "category",
        "business_category",
        "sku",
        "barcode",
        "brand",
        "shipping_information",
        "updated_at",
        "price",
        "stock",
        "minimum_order_quantity",
        "unit_sold",
        "sales_value",
        "inventory_value",
        "stock_status",
        "rating",
        "availability_status",
    ]

    # Raised when the products collection has an invalid type.
    def __init__(self, products: list[dict]):
        """Initialize inventory analytics with validated product records."""

        if not isinstance(products, list):
            raise InvalidProductsTypeError("Products must be a list.")

        if not all(isinstance(product, dict) for product in products):
            raise InvalidProductsTypeError("Every product must be a dictionary.")

        self.products = list(products)
        self.dataframe = self._build_dataframe()

    @staticmethod
    def _to_decimal(value):
        try:
            result = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal(0)

        if not result.is_finite():
            return Decimal(0)

        return max(Decimal(0), result)

    @staticmethod
    def _safe_numeric(series, default=0):
        return (
            pd.to_numeric(series, errors="coerce")
            .replace([np.inf, -np.inf], np.nan)
            .fillna(default)
        )

    @staticmethod
    def _get_metadata(product):
        metadata = product.get("meta") or {}
        return metadata if isinstance(metadata, dict) else {}

    @staticmethod
    def _get_business_category(category):
        return CATEGORY_MAP.get(category) or "Unknown"

    def _build_dataframe(self):
        if not self.products:
            return pd.DataFrame(columns=self.DATAFRAME_COLUMNS)

        records = []

        for product in self.products:
            metadata = self._get_metadata(product)
            category = product.get("category") or "Unknown"

            records.append(
                {
                    "id": product.get("id"),
                    "title": product.get("title") or "Unknown",
                    "category": category,
                    "business_category": self._get_business_category(
                        product.get("category")
                    ),
                    "sku": product.get("sku") or "N/A",
                    "barcode": metadata.get("barcode") or "",
                    # Product catalogue information
                    "brand": product.get("brand") or "Unknown",
                    "shipping_information": (
                        product.get("shippingInformation") or "Unknown"
                    ),
                    "updated_at": metadata.get("updatedAt") or "",
                    "price": product.get("price", 0),
                    "stock": product.get("stock", 0),
                    "minimum_order_quantity": product.get("minimumOrderQuantity", 0),
                    "rating": product.get("rating"),
                    "availability_status": (
                        product.get("availabilityStatus") or "Unknown"
                    ),
                }
            )

        df = pd.DataFrame(records)

        for column in [
            "price",
            "stock",
            "minimum_order_quantity",
            "rating",
        ]:
            df[column] = self._safe_numeric(df[column])

        for column in ["stock", "minimum_order_quantity"]:
            df[column] = df[column].clip(lower=0).apply(np.floor).astype("int64")

        df["price"] = df["price"].apply(self._to_decimal)

        df["unit_sold"] = [
            ProductSalesCalculator.calculate_units_sold(
                {
                    "stock": stock,
                    "minimumOrderQuantity": minimum,
                }
            )
            for stock, minimum in zip(
                df["stock"],
                df["minimum_order_quantity"],
                strict=True,
            )
        ]

        df["sales_value"] = [
            ProductSalesCalculator.calculate_product_sales_value(
                {
                    "price": price,
                    "stock": stock,
                    "minimumOrderQuantity": minimum,
                }
            )
            for price, stock, minimum in zip(
                df["price"],
                df["stock"],
                df["minimum_order_quantity"],
                strict=True,
            )
        ]

        df["inventory_value"] = [
            Decimal(int(stock)) * price
            for stock, price in zip(
                df["stock"],
                df["price"],
                strict=True,
            )
        ]

        conditions = [
            df["stock"] == 0,
            ((df["stock"] > 0) & (df["stock"] <= df["minimum_order_quantity"])),
            df["stock"] > df["minimum_order_quantity"],
        ]

        df["stock_status"] = np.select(
            conditions,
            [
                self.STOCK_OUT,
                self.STOCK_LOW,
                self.STOCK_IN,
            ],
            default=self.STOCK_OUT,
        )

        return df

    def get_dataframe(self):
        return self.dataframe.copy(deep=True)

    def get_summary(self):
        df = self.dataframe

        return {
            "total_products": len(df),
            "total_units_sold": int(df["unit_sold"].sum()),
            "total_sales_value": sum(df["sales_value"], Decimal(0)),
            "total_inventory_value": sum(df["inventory_value"], Decimal(0)),
            "out_of_stock": int((df["stock_status"] == self.STOCK_OUT).sum()),
            "low_stock": int((df["stock_status"] == self.STOCK_LOW).sum()),
            "in_stock": int((df["stock_status"] == self.STOCK_IN).sum()),
        }

    def get_stock_distribution(self):
        return {
            self.STOCK_OUT: int(
                (self.dataframe["stock_status"] == self.STOCK_OUT).sum()
            ),
            self.STOCK_LOW: int(
                (self.dataframe["stock_status"] == self.STOCK_LOW).sum()
            ),
            self.STOCK_IN: int((self.dataframe["stock_status"] == self.STOCK_IN).sum()),
        }

    def get_category_sales(self):
        totals = {category: Decimal(0) for category in DASHBOARD_CATEGORIES}

        for category, value in zip(
            self.dataframe["business_category"],
            self.dataframe["sales_value"],
            strict=True,
        ):
            if category in totals:
                totals[category] += value

        return totals

    def get_api_category_sales(self):
        totals = {}

        for category, value in zip(
            self.dataframe["category"],
            self.dataframe["sales_value"],
            strict=True,
        ):
            totals[category] = totals.get(category, Decimal(0)) + value

        return dict(sorted(totals.items()))

    def get_abc_analysis(self):

        # Calculate ABC product classification.

        # Products are ranked by estimated sales value.

        # A: Cumulative sales value <= 80%
        # B: Cumulative sales value > 80% and <= 95%
        # C: Cumulative sales value > 95%

        # Returns:
        #     Pandas DataFrame
        #

        df = self.dataframe.copy(deep=True)

        if df.empty:
            df["product_rank"] = pd.Series(dtype="int64")
            df["cumulative_sales_value"] = pd.Series(dtype=object)
            df["cumulative_percentage"] = pd.Series(dtype=float)
            df["abc_class"] = pd.Series(dtype=str)
            return df

        # Rank products from highest to lowest sales value.
        df = df.sort_values(
            by=["sales_value", "title"],
            ascending=[False, True],
            kind="stable",
        ).reset_index(drop=True)

        # Assign product ranking.
        df["product_rank"] = range(1, len(df) + 1)

        # Calculate total estimated sales value.
        total_sales = sum(
            df["sales_value"],
            Decimal(0),
        )

        # Calculate cumulative sales value.
        running_total = Decimal(0)
        cumulative_values = []

        for value in df["sales_value"]:
            running_total += value
            cumulative_values.append(running_total)

        df["cumulative_sales_value"] = cumulative_values

        # Handle catalogues without estimated sales.
        if total_sales <= Decimal(0):
            df["cumulative_percentage"] = 0.0
            df["abc_class"] = "C"

            return df

        # Calculate cumulative sales percentages.
        df["cumulative_percentage"] = [
            float(value / total_sales * Decimal(100)) for value in cumulative_values
        ]

        # Apply ABC classification.
        df["abc_class"] = np.select(
            [
                df["cumulative_percentage"] <= self.ABC_A_LIMIT,
                df["cumulative_percentage"] <= self.ABC_B_LIMIT,
            ],
            [
                "A",
                "B",
            ],
            default="C",
        )

        return df

    def get_abc_summary(self):
        """
        Calculate summary statistics for ABC classifications.

        Returns:
            Dictionary containing:
            - Product counts
            - Sales values
            - Sales percentages
        """

        abc = self.get_abc_analysis()

        total_sales = sum(
            abc["sales_value"],
            Decimal(0),
        )

        result = {}

        for classification in ["A", "B", "C"]:
            group = abc[abc["abc_class"] == classification]

            sales_value = sum(
                group["sales_value"],
                Decimal(0),
            )

            sales_percentage = (
                float(sales_value / total_sales * 100) if total_sales > 0 else 0.0
            )

            result[classification] = {
                "product_count": len(group),
                "sales_value": sales_value,
                "sales_percentage": sales_percentage,
            }

        return result

    def get_stock_items(self, classification=None):
        # Return inventory records filtered by stock classification.

        df = self.dataframe.copy(deep=True)

        valid_classifications = [
            self.STOCK_OUT,
            self.STOCK_LOW,
            self.STOCK_IN,
        ]

        if classification is None:
            return df.to_dict(orient="records")

        if classification not in valid_classifications:
            raise ValueError("Invalid stock classification.")

        df = df[df["stock_status"] == classification]

        return df.to_dict(orient="records")
