import json
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from apps.dashboard.planogram.fixture_service import (
    serialize_fixture,
    serialize_fixture_geometry,
)
from apps.dashboard.planogram.planogram_service import (
    add_product_to_fixture,
)

from .analytics import (
    calculate_api_category_sales,
    calculate_category_sales,
    calculate_total_sales,
    get_category_details,
    get_inventory_items,
)
from .in_stock_orders import (
    add_in_stock_order,
    build_in_stock_orders,
    calculate_in_stock_order_totals,
    clear_in_stock_orders,
    delete_in_stock_order,
    get_in_stock_orders,
)
from .inventory_analytics import InventoryAnalyticsService
from .inventory_visualizations import InventoryChartService
from .logistics_analytics import calculate_logistics_analytics
from .logistics_visualizations import LogisticsChartService
from .low_stock_orders import (
    add_low_stock_order,
    build_low_stock_orders,
    clear_low_stock_orders,
    delete_low_stock_order,
    get_low_stock_orders,
)
from .low_stock_orders import (
    calculate_order_totals as calculate_low_stock_order_totals,
)
from .models import (
    Fixture,
    Floor,
    MerchandiseProduct,
    PlanogramItem,
)
from .out_of_stock_orders import (
    add_out_of_stock_order,
    build_out_of_stock_orders,
    calculate_order_totals,
    clear_out_of_stock_orders,
    delete_out_of_stock_order,
    get_out_of_stock_orders,
)
from .planogram.floor_generator import initialize_building
from .planogram.product_service import (
    get_products,
    synchronize_products,
)
from .planogram.renovation_adapter import export_floor_plan
from .planogram.validators import (
    validate_fixture_data,
    validate_fixture_overlap,
    validate_fixture_position,
)
from .review_analytics import (
    ReviewAnalyticsService,
    calculate_review_summary,
)
from .review_visualizations import ReviewChartService
from .services import APIError, fetch_products
from .visualizations import (
    prepare_bar_chart,
    prepare_pie_chart,
)

# ==========================================================
# CONSTANTS
# ==========================================================

ZERO = Decimal("0.00")

VALID_STOCK_STATUSES = {
    "all",
    "in_stock",
    "low_stock",
    "out_of_stock",
}


# ==========================================================
# SHARED VALIDATION HELPERS
# ==========================================================


def safe_decimal(value, default=ZERO):
    """Convert a value into a finite Decimal."""

    try:
        result = Decimal(str(value))

        if not result.is_finite():
            return default

        return result

    except (
        TypeError,
        ValueError,
        InvalidOperation,
        OverflowError,
    ):
        return default


def safe_quantity(value, default=0):
    """Convert a value into a whole-number quantity."""

    if isinstance(value, bool):
        return default

    try:
        result = int(value)

        if str(value).strip() != str(result):
            return default

        return result

    except TypeError, ValueError, OverflowError:
        return default


# ==========================================================
# ORDER NORMALIZATION
# ==========================================================


def normalize_order(item, product_id=None, source=None):
    """Normalize an order from any Browser Memory collection."""

    if not isinstance(item, dict):
        return None

    product_id = str(product_id or item.get("product_id") or item.get("id") or "")

    product_name = item.get("product_name") or item.get("title") or "Unknown Product"

    price = safe_decimal(
        item.get("unit_price", item.get("price", 0)),
        default=None,
    )

    quantity = safe_quantity(item.get("quantity"))

    if not product_id or price is None:
        return None

    if price < ZERO or quantity < 1:
        return None

    stock_status = item.get("stock_status") or "in_stock"

    if stock_status not in VALID_STOCK_STATUSES - {"all"}:
        stock_status = "in_stock"

    return {
        **item,
        "id": product_id,
        "product_id": product_id,
        "product_name": str(product_name),
        "title": str(product_name),
        "sku": str(item.get("sku") or ""),
        "stock_status": stock_status,
        "source": source or item.get("source", ""),
        "price": price,
        "unit_price": price,
        "quantity": quantity,
        "line_total": price * quantity,
    }


def normalize_orders(orders, source=None):
    """Normalize a dictionary or list of saved orders."""

    if isinstance(orders, dict):
        iterable = orders.items()

    elif isinstance(orders, (list, tuple)):
        iterable = [
            (
                item.get("product_id", item.get("id", "")),
                item,
            )
            for item in orders
            if isinstance(item, dict)
        ]

    else:
        return []

    normalized = []

    for product_id, item in iterable:
        order = normalize_order(
            item,
            product_id,
            source,
        )

        if order is not None:
            normalized.append(order)

    return normalized


def calculate_order_summary(orders):
    """Calculate common order totals."""

    return {
        "total_items": len(orders),
        "total_quantity": sum(order["quantity"] for order in orders),
        "cart_total": sum(
            (order["line_total"] for order in orders),
            ZERO,
        ),
    }


# ==========================================================
# BROWSER MEMORY HELPERS
# ==========================================================


def get_browser_memory(request):
    """Retrieve inventory Browser Memory safely."""

    orders = request.session.get("inventory_orders", {})

    return orders if isinstance(orders, dict) else {}


def calculate_browser_memory_total(orders):
    """Calculate the total value of valid inventory orders."""

    normalized = normalize_orders(orders, "inventory")

    return sum(
        (order["line_total"] for order in normalized),
        ZERO,
    )


def get_safe_orders(getter, request):
    """Retrieve a service order collection safely."""

    try:
        orders = getter(request)

        return orders if isinstance(orders, dict) else {}

    except ValueError, TypeError, KeyError, InvalidOperation:
        return {}


# ==========================================================
# OVERVIEW
# ==========================================================


def overview(request):
    context = {
        "api_error": None,
        "total_sales": 0,
        "inventory": [],
        "unknown_categories": [],
        "bar_chart_image": None,
        "pie_chart": [],
        "pie_chart_image": None,
        "category_details": [],
        "review_summary": {
            "total_reviews": 0,
            "positive_reviews": 0,
            "neutral_reviews": 0,
            "negative_reviews": 0,
        },
    }

    try:
        products = fetch_products()

        total_sales = calculate_total_sales(products)

        category_sales, unknown_categories = calculate_category_sales(products)

        api_category_sales = calculate_api_category_sales(products)

        _, bar_chart_image = prepare_bar_chart(api_category_sales)

        pie_chart, pie_chart_image = prepare_pie_chart(category_sales)

        context.update(
            {
                "total_sales": total_sales,
                "inventory": get_inventory_items(products),
                "unknown_categories": unknown_categories,
                "review_summary": calculate_review_summary(products),
                "bar_chart_image": bar_chart_image,
                "pie_chart": pie_chart,
                "pie_chart_image": pie_chart_image,
                "category_details": get_category_details(),
                "product_count": len(products),
            }
        )

    except APIError as error:
        context["api_error"] = str(error)

    return render(
        request,
        "dashboard/overview.html",
        context,
    )


# ==========================================================
# INVENTORY
# ==========================================================


def inventory(request):

    context = {
        "page_title": "Inventory Dashboard",
        "inventory": [],
        "product_count": 0,
        "api_error": None,
        "cart_items": [],
        "cart_total": ZERO,
        "cart_quantity": 0,
        "saved_orders": {},
        "memory_notice": "",
        "in_stock_count": 0,
        "low_stock_count": 0,
        "out_of_stock_count": 0,
    }

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "clear_memory":
            request.session.pop("inventory_orders", None)
            request.session.modified = True

            messages.success(
                request,
                "Browser Memory has been cleared successfully.",
            )

            return redirect("dashboard:inventory")

    orders = get_browser_memory(request)

    normalized = normalize_orders(
        orders,
        "inventory",
    )

    context.update(
        {
            "saved_orders": orders,
            "cart_items": normalized,
            "cart_total": sum(
                (item["line_total"] for item in normalized),
                ZERO,
            ),
            "cart_quantity": sum(item["quantity"] for item in normalized),
        }
    )

    try:
        products = fetch_products()

        if request.method == "POST" and request.POST.get("action") == "add_order":
            product_id = request.POST.get("product_id", "").strip()

            quantity = safe_quantity(request.POST.get("quantity"))

            product = next(
                (item for item in products if str(item.get("id")) == product_id),
                None,
            )

            if product is None or quantity < 1:
                raise ValueError("Invalid product or quantity.")

            price = safe_decimal(
                product.get("price"),
                default=None,
            )

            if price is None or price < ZERO:
                raise ValueError("Invalid product price.")

            existing = normalize_order(
                orders.get(product_id, {}),
                product_id,
                "inventory",
            )

            existing_quantity = existing["quantity"] if existing else 0

            orders[product_id] = {
                "product_id": product_id,
                "title": product.get(
                    "title",
                    "Unknown Product",
                ),
                "price": str(price),
                "quantity": existing_quantity + quantity,
                "sku": product.get("sku", ""),
            }

            request.session["inventory_orders"] = orders
            request.session.modified = True

            messages.success(
                request,
                f"{product.get('title', 'Product')} saved to Browser Memory.",
            )

            return redirect("dashboard:inventory")

        inventory_items = get_inventory_items(products)

        context.update(
            {
                "inventory": inventory_items,
                "product_count": len(products),
                "in_stock_count": sum(
                    1
                    for item in inventory_items
                    if safe_quantity(item.get("stock")) > 5
                ),
                "low_stock_count": sum(
                    1
                    for item in inventory_items
                    if 0 < safe_quantity(item.get("stock")) <= 5
                ),
                "out_of_stock_count": sum(
                    1
                    for item in inventory_items
                    if safe_quantity(item.get("stock")) <= 0
                ),
            }
        )

    except APIError as error:
        context["api_error"] = str(error)

        context["memory_notice"] = (
            "Previously saved Browser Memory orders remain available."
        )

    except (
        ValueError,
        TypeError,
        InvalidOperation,
        OverflowError,
    ) as error:
        messages.error(request, str(error))

        return redirect("dashboard:inventory")

    return render(
        request,
        "dashboard/inventory.html",
        context,
    )


# ==========================================================
# CUSTOMER REVIEWS
# ==========================================================


def customer_review(request):

    context = {
        "api_error": None,
        "review_summary": {
            "total_reviews": 0,
            "positive_reviews": 0,
            "neutral_reviews": 0,
            "negative_reviews": 0,
        },
        "rating_distribution": {},
        "category_review_distribution": {},
        "latest_reviews": [],
        "pie_chart": [],
        "pie_chart_image": None,
        "category_chart": [],
        "category_chart_image": None,
        "search_query": "",
        "selected_rating": "",
        "selected_category": "",
        "start_date": "",
        "end_date": "",
        "review_categories": [],
        "matching_review_count": 0,
        "page_obj": None,
        "pagination_query": "",
    }

    try:
        products = fetch_products()

        context["review_summary"] = calculate_review_summary(products)

        rating_distribution = ReviewAnalyticsService.calculate_rating_distribution(
            products
        )

        category_distribution = (
            ReviewAnalyticsService.calculate_category_review_distribution(products)
        )

        context["rating_distribution"] = rating_distribution

        context["category_review_distribution"] = category_distribution

        pie_input = [
            {
                "rating": rating,
                "count": count,
            }
            for rating, count in rating_distribution.items()
        ]

        pie_chart, pie_chart_image = ReviewChartService.prepare_pie_chart(pie_input)

        category_input = [
            {
                "category": category,
                "ratings": [
                    {
                        "rating": rating,
                        "count": count,
                    }
                    for rating, count in ratings.items()
                ],
            }
            for category, ratings in category_distribution.items()
        ]

        category_chart, category_chart_image = (
            ReviewChartService.prepare_category_bar_chart(category_input)
        )

        search_query = request.GET.get("search", "").strip()

        selected_rating = request.GET.get("rating", "").strip()

        selected_category = request.GET.get("category", "").strip()

        start_date = request.GET.get("start_date", "").strip()

        end_date = request.GET.get("end_date", "").strip()

        categories = ReviewAnalyticsService.get_review_categories(products)

        filtered_reviews = ReviewAnalyticsService.filter_reviews(
            products,
            search=search_query,
            rating=selected_rating,
            category=selected_category,
            start_date=start_date,
            end_date=end_date,
        )

        paginator = Paginator(filtered_reviews, 10)

        page_obj = paginator.get_page(request.GET.get("page"))

        query_params = QueryDict(
            request.GET.urlencode(),
            mutable=True,
        )
        query_params.pop("page", None)

        context.update(
            {
                "pie_chart": pie_chart,
                "pie_chart_image": pie_chart_image,
                "category_chart": category_chart,
                "category_chart_image": category_chart_image,
                "review_categories": categories,
                "matching_review_count": len(filtered_reviews),
                "page_obj": page_obj,
                "latest_reviews": page_obj.object_list,
                "pagination_query": query_params.urlencode(),
                "search_query": search_query,
                "selected_rating": selected_rating,
                "selected_category": selected_category,
                "start_date": start_date,
                "end_date": end_date,
            }
        )

    except APIError as error:
        context["api_error"] = str(error)

    return render(
        request,
        "dashboard/customer_review.html",
        context,
    )


# ==========================================================
# ABC ANALYSIS
# ==========================================================


def abc_analysis(request):
    """
    Display ABC product classification and
    interactive cumulative sales value chart.
    """

    context = {
        "inventory": [],
        "abc_records": [],
        "abc_summary": {
            "A": {
                "product_count": 0,
                "sales_value": Decimal(0),
                "sales_percentage": 0,
            },
            "B": {
                "product_count": 0,
                "sales_value": Decimal(0),
                "sales_percentage": 0,
            },
            "C": {
                "product_count": 0,
                "sales_value": Decimal(0),
                "sales_percentage": 0,
            },
        },
        "total_products": 0,
        "total_sales_value": Decimal(0),
        "abc_chart_json": None,
        "api_error": None,
    }

    try:
        # --------------------------------------------------
        # FETCH PRODUCT CATALOGUE
        # --------------------------------------------------

        products = fetch_products()

        # --------------------------------------------------
        # INITIALIZE ANALYTICS SERVICE
        # --------------------------------------------------

        analytics = InventoryAnalyticsService(products)

        # --------------------------------------------------
        # ABC ANALYSIS
        # --------------------------------------------------

        abc_dataframe = analytics.get_abc_analysis()

        # --------------------------------------------------
        # ABC SUMMARY
        # --------------------------------------------------

        abc_summary = analytics.get_abc_summary()

        # --------------------------------------------------
        # TOTAL SALES VALUE
        # --------------------------------------------------

        total_sales_value = sum(
            abc_dataframe["sales_value"],
            Decimal(0),
        )

        # --------------------------------------------------
        # GENERATE PLOTLY CHART
        # --------------------------------------------------

        figure = InventoryChartService.prepare_abc_chart(abc_dataframe)

        # Convert Plotly figure into a JSON-compatible
        # Python dictionary for Django's json_script filter.

        import json

        figure_json = json.loads(figure.to_json())

        # --------------------------------------------------
        # PREPARE TABLE DATA
        # --------------------------------------------------

        abc_records = abc_dataframe.to_dict(orient="records")

        # --------------------------------------------------
        # PAGE CONTEXT
        # --------------------------------------------------

        context.update(
            {
                "inventory": products,
                "abc_records": abc_records,
                "abc_summary": abc_summary,
                "total_products": len(abc_dataframe),
                "total_sales_value": total_sales_value,
                "chart_data": figure_json,
                "abc_products": abc_records,
                "class_a_count": abc_summary["A"]["product_count"],
                "class_b_count": abc_summary["B"]["product_count"],
                "class_c_count": abc_summary["C"]["product_count"],
            }
        )

    except APIError as error:
        context["api_error"] = str(error)

    except (
        ValueError,
        TypeError,
        InvalidOperation,
        OverflowError,
    ) as error:
        context["api_error"] = "Unable to generate ABC analysis: " + str(error)

    return render(
        request,
        "dashboard/abc_analysis.html",
        context,
    )


# ==========================================================
# STOCK PAGE CONFIGURATION
# ==========================================================

STOCK_CONFIG = {
    "in_stock": {
        "getter": get_in_stock_orders,
        "builder": build_in_stock_orders,
        "adder": add_in_stock_order,
        "deleter": delete_in_stock_order,
        "clearer": clear_in_stock_orders,
        "totals": calculate_in_stock_order_totals,
        "template": "dashboard/in_stock.html",
        "redirect": "dashboard:in_stock",
        "title": "In Stock Orders",
        "success": "Order saved to In Stock Browser Memory.",
        "clear_message": "In Stock Browser Memory cleared successfully.",
        "error": "Some saved In Stock orders contain invalid information.",
    },
    "low_stock": {
        "getter": get_low_stock_orders,
        "builder": build_low_stock_orders,
        "adder": add_low_stock_order,
        "deleter": delete_low_stock_order,
        "clearer": clear_low_stock_orders,
        "totals": calculate_low_stock_order_totals,
        "template": "dashboard/low_stock.html",
        "redirect": "dashboard:low_stock",
        "title": "Low Stock Orders",
        "success": "Order saved to Low Stock Browser Memory.",
        "clear_message": "Low Stock Browser Memory cleared successfully.",
        "error": "Some saved Low Stock orders contain invalid information.",
    },
    "out_of_stock": {
        "getter": get_out_of_stock_orders,
        "builder": build_out_of_stock_orders,
        "adder": add_out_of_stock_order,
        "deleter": delete_out_of_stock_order,
        "clearer": clear_out_of_stock_orders,
        "totals": calculate_order_totals,
        "template": "dashboard/out_of_stock.html",
        "redirect": "dashboard:out_of_stock",
        "title": "Out of Stock Orders",
        "success": "Order saved to Out of Stock Browser Memory.",
        "clear_message": "Out of Stock Browser Memory cleared successfully.",
        "error": "Some saved Out of Stock orders contain invalid information.",
    },
}


# ==========================================================
# SHARED STOCK ORDERS VIEW
# ==========================================================


def stock_orders_page(request, stock_type):
    """Shared view for all three stock categories."""

    config = STOCK_CONFIG[stock_type]

    context = {
        "page_title": config["title"],
        "inventory": [],
        "saved_orders": [],
        "total_order_quantity": 0,
        "total_order_value": ZERO,
        "api_error": None,
        "memory_notice": "",
    }

    # ------------------------------------------------------
    # CLEAR OR DELETE ORDERS
    # ------------------------------------------------------

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "clear_memory":
            config["clearer"](request)

            messages.success(
                request,
                config["clear_message"],
            )

            return redirect(config["redirect"])

        if action == "delete_order":
            try:
                config["deleter"](
                    request,
                    request.POST.get("product_id", ""),
                )

                messages.success(
                    request,
                    "Order deleted successfully.",
                )

            except (
                ValueError,
                TypeError,
                KeyError,
                InvalidOperation,
            ):
                messages.error(
                    request,
                    "Unable to delete the selected order.",
                )

            return redirect(config["redirect"])

    # ------------------------------------------------------
    # LOAD SAVED ORDERS BEFORE API REQUEST
    # ------------------------------------------------------

    orders = get_safe_orders(
        config["getter"],
        request,
    )

    saved_orders = normalize_orders(
        orders,
        stock_type,
    )

    context.update(
        {
            "saved_orders": saved_orders,
            "total_order_quantity": sum(order["quantity"] for order in saved_orders),
            "total_order_value": sum(
                (order["line_total"] for order in saved_orders),
                ZERO,
            ),
        }
    )

    # ------------------------------------------------------
    # FETCH CURRENT INVENTORY
    # ------------------------------------------------------

    try:
        products = fetch_products()

        context["inventory"] = config["builder"](products)

        if request.method == "POST" and request.POST.get("action") == "add_order":
            product_id = request.POST.get("product_id", "").strip()

            product = next(
                (item for item in products if str(item.get("id")) == product_id),
                None,
            )

            if product is None:
                messages.error(
                    request,
                    "Invalid product.",
                )

            else:
                try:
                    quantity = safe_quantity(
                        request.POST.get("quantity"),
                        default=None,
                    )

                    if quantity is None or quantity < 1:
                        raise ValueError("Invalid order quantity.")

                    config["adder"](
                        request,
                        product,
                        quantity,
                    )

                    messages.success(
                        request,
                        config["success"],
                    )

                except (
                    TypeError,
                    ValueError,
                    InvalidOperation,
                    OverflowError,
                    KeyError,
                ) as error:
                    messages.error(
                        request,
                        str(error),
                    )

            return redirect(config["redirect"])

    except APIError as error:
        context["api_error"] = str(error)

        context["memory_notice"] = (
            "Previously saved Browser Memory orders remain available."
        )

    return render(
        request,
        config["template"],
        context,
    )


# ==========================================================
# INDIVIDUAL STOCK VIEWS
# ==========================================================


def in_stock(request):
    return stock_orders_page(
        request,
        "in_stock",
    )


def low_stock(request):
    return stock_orders_page(
        request,
        "low_stock",
    )


def out_of_stock(request):
    return stock_orders_page(
        request,
        "out_of_stock",
    )


# ==========================================================
# UNIFIED SAVED ORDERS
# ==========================================================


def get_unified_saved_orders(request):
    """
    Combine all four Browser Memory collections.

    Original session collections remain unchanged.
    """

    sources = {
        "inventory": get_browser_memory(request),
        "in_stock": get_safe_orders(
            get_in_stock_orders,
            request,
        ),
        "low_stock": get_safe_orders(
            get_low_stock_orders,
            request,
        ),
        "out_of_stock": get_safe_orders(
            get_out_of_stock_orders,
            request,
        ),
    }

    stock_lookup = {}

    # ------------------------------------------------------
    # OPTIONAL CURRENT STOCK INFORMATION
    # ------------------------------------------------------

    try:
        products = fetch_products()

        for product in products:
            try:
                product_id = str(product.get("id"))

                stock = safe_quantity(
                    product.get("stock"),
                    default=None,
                )

                if stock is not None:
                    stock_lookup[product_id] = stock

            except TypeError, ValueError, OverflowError:
                continue

    except APIError:
        pass

    # ------------------------------------------------------
    # NORMALIZE ALL SAVED ORDERS
    # ------------------------------------------------------

    all_orders = []

    for source, saved_orders in sources.items():
        if not isinstance(saved_orders, dict):
            continue

        for product_id, item in saved_orders.items():
            order = normalize_order(
                item,
                product_id,
                source,
            )

            if order is None:
                continue

            # The original stock-order collection determines
            # the status for stock-specific orders.

            if source == "in_stock":
                order["stock_status"] = "in_stock"

            elif source == "low_stock":
                order["stock_status"] = "low_stock"

            elif source == "out_of_stock":
                order["stock_status"] = "out_of_stock"

            else:
                stock = stock_lookup.get(str(product_id))

                if stock is None:
                    order["stock_status"] = item.get("stock_status") or "in_stock"

                elif stock <= 0:
                    order["stock_status"] = "out_of_stock"

                elif stock <= 5:
                    order["stock_status"] = "low_stock"

                else:
                    order["stock_status"] = "in_stock"

            all_orders.append(order)

    return all_orders


# ==========================================================
# SAVED ORDERS PAGE
# ==========================================================


def saved_orders(request):
    """Display all saved orders in one unified page."""

    status_filter = request.GET.get(
        "status",
        "all",
    ).strip()

    search_query = request.GET.get(
        "search",
        request.GET.get("q", ""),
    ).strip()

    if status_filter not in VALID_STOCK_STATUSES:
        status_filter = "all"

    fallback_url = reverse("dashboard:inventory")

    referer = request.META.get(
        "HTTP_REFERER",
        "",
    )

    if url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return_url = referer

    else:
        return_url = fallback_url

    # ------------------------------------------------------
    # LOAD AND NORMALIZE ORDERS
    # ------------------------------------------------------

    all_orders = get_unified_saved_orders(request)

    normalized_orders = normalize_orders(all_orders)

    # ------------------------------------------------------
    # COUNTS BEFORE FILTERING
    # ------------------------------------------------------

    counts = {
        "all": len(normalized_orders),
        "in_stock": sum(
            order["stock_status"] == "in_stock" for order in normalized_orders
        ),
        "low_stock": sum(
            order["stock_status"] == "low_stock" for order in normalized_orders
        ),
        "out_of_stock": sum(
            order["stock_status"] == "out_of_stock" for order in normalized_orders
        ),
    }

    filtered_orders = normalized_orders

    # ------------------------------------------------------
    # STATUS FILTER
    # ------------------------------------------------------

    if status_filter != "all":
        filtered_orders = [
            order for order in filtered_orders if order["stock_status"] == status_filter
        ]

    # ------------------------------------------------------
    # SEARCH FILTER
    # ------------------------------------------------------

    if search_query:
        query = search_query.casefold()

        filtered_orders = [
            order
            for order in filtered_orders
            if (
                query in order["product_name"].casefold()
                or query in order["sku"].casefold()
                or query in order["product_id"].casefold()
            )
        ]

    # ------------------------------------------------------
    # TOTALS
    # ------------------------------------------------------

    summary = calculate_order_summary(normalized_orders)

    # ------------------------------------------------------
    # PAGINATION
    # ------------------------------------------------------

    paginator = Paginator(
        filtered_orders,
        10,
    )

    page_obj = paginator.get_page(request.GET.get("page"))

    # ------------------------------------------------------
    # TEMPLATE CONTEXT
    # ------------------------------------------------------

    context = {
        # Order collections
        "orders": page_obj.object_list,
        "saved_orders": page_obj.object_list,
        # Pagination
        "page_obj": page_obj,
        # Status information
        "counts": counts,
        "order_counts": counts,
        "selected_status": status_filter,
        # Search
        "search_query": search_query,
        # Totals
        "total_items": summary["total_items"],
        "total_orders_count": summary["total_items"],
        "total_quantity": summary["total_quantity"],
        "total_order_quantity": summary["total_quantity"],
        "cart_total": summary["cart_total"],
        "total_order_value": summary["cart_total"],
        # Navigation
        "return_url": return_url,
    }

    return render(
        request,
        "dashboard/saved_orders.html",
        context,
    )


# ==========================================================
# REMOVE SAVED ORDER
# ==========================================================


def remove_saved_order(request, source, product_id):
    """Remove an order from its original Browser Memory collection."""

    if request.method != "POST":
        return redirect("dashboard:saved_orders")

    try:
        if source == "inventory":
            orders = get_browser_memory(request)

            orders.pop(str(product_id), None)

            request.session["inventory_orders"] = orders
            request.session.modified = True

        elif source in STOCK_CONFIG:
            STOCK_CONFIG[source]["deleter"](
                request,
                product_id,
            )

        else:
            messages.error(
                request,
                "Invalid order source.",
            )

            return redirect("dashboard:saved_orders")

        messages.success(
            request,
            "Order removed successfully.",
        )

    except (
        ValueError,
        TypeError,
        KeyError,
        InvalidOperation,
    ):
        messages.error(
            request,
            "Unable to remove the selected order.",
        )

    # Preserve the active filter and pagination.

    status = request.POST.get("status", "all")

    if status not in VALID_STOCK_STATUSES:
        status = "all"

    params = urlencode(
        {
            "status": status,
            "q": request.POST.get("q", ""),
            "page": request.POST.get("page", "1"),
        }
    )

    return redirect(f"{reverse('dashboard:saved_orders')}?{params}")


# ==========================================================
# PRINT SAVED ORDERS
# ==========================================================


def submit_saved_orders(request):
    """
    Generate a printable order document.

    Printing never clears or modifies Browser Memory.
    """

    if request.method != "POST":
        return redirect("dashboard:saved_orders")

    orders = get_unified_saved_orders(request)
    normalized_orders = normalize_orders(orders)

    if not normalized_orders:
        messages.warning(
            request,
            "There are no saved orders to print.",
        )
        return redirect("dashboard:saved_orders")

    summary = calculate_order_summary(normalized_orders)

    context = {
        # Order collections
        "orders": normalized_orders,
        "saved_orders": normalized_orders,
        # Order counts
        "total_items": summary["total_items"],
        "total_orders_count": summary["total_items"],
        # Quantities
        "total_quantity": summary["total_quantity"],
        "total_order_quantity": summary["total_quantity"],
        # Financial totals
        "cart_total": summary["cart_total"],
        "total_order_value": summary["cart_total"],
    }

    return render(
        request,
        "dashboard/print_orders.html",
        context,
    )


# ==========================================================
# LOGISTICS DASHBOARD
# ==========================================================


def logistics(request):
    """Display category-level logistics analytics and charts."""

    context = {
        "page_title": "Logistics Dashboard",
        "api_error": None,
        "logistics_records": [],
        "product_count": 0,
        "category_count": 0,
        "lifetime_product_count": 0,
        "chart_data": {},
        "numeric_warranty_category_count": 0,
    }

    try:
        products = fetch_products() or []

        # Ignore invalid product entries.
        valid_products = [product for product in products if isinstance(product, dict)]

        # Calculate analytics using valid products only.
        records = calculate_logistics_analytics(valid_products)

        context.update(
            {
                "logistics_records": records,
                "product_count": len(valid_products),
                "category_count": len(records),
                "lifetime_product_count": sum(
                    item["lifetime_count"] for item in records
                ),
                "numeric_warranty_category_count": sum(
                    item["median_warranty_days"] is not None for item in records
                ),
            }
        )

    except APIError as error:
        context["api_error"] = str(error)

    except (
        ValueError,
        TypeError,
        OverflowError,
    ) as error:
        context["api_error"] = "Unable to generate logistics analytics: " + str(error)

    # Always generate all seven charts, even after an API failure.
    figures = LogisticsChartService.prepare_dashboard(context["logistics_records"])

    context["chart_data"] = {
        name: json.loads(figure.to_json()) for name, figure in figures.items()
    }

    return render(
        request,
        "dashboard/logistics.html",
        context,
    )


# ==========================================================
# MERCHANDISE FLOOR PLAN
# ==========================================================


# ==========================================================
# MERCHANDISE FLOOR PLAN
# ==========================================================


def merchandise(request):
    building = initialize_building()

    # Attempt synchronization without losing existing cached products.
    try:
        synchronize_products()
        product_error = None
    except Exception:
        product_error = (
            "Product API temporarily unavailable. "
            "Previously cached products remain available."
        )

    floors = building.floors.prefetch_related(
        "rooms",
        "fixtures",
    ).all()

    context = {
        "page_title": "Merchandise Planogram",
        "building": building,
        "floors": floors,
        "product_count": MerchandiseProduct.objects.count(),
        "product_error": product_error,
    }

    return render(
        request,
        "dashboard/merchandise.html",
        context,
    )


def merchandise_floor_data(request, floor_id):
    floor = get_object_or_404(
        Floor.objects.select_related("building"),
        id=floor_id,
    )

    rooms = [
        {
            "id": room.id,
            "name": room.name,
            "type": room.room_type,
            "x": float(room.x),
            "y": float(room.y),
            "width": float(room.width),
            "height": float(room.height),
            "color": room.color,
        }
        for room in floor.rooms.all()
    ]

    fixtures = [serialize_fixture_geometry(fixture) for fixture in floor.fixtures.all()]

    return JsonResponse(
        {
            "floor": {
                "id": floor.id,
                "name": floor.name,
                "number": floor.number,
                "width": float(floor.width),
                "height": float(floor.height),
            },
            "rooms": rooms,
            "fixtures": fixtures,
        }
    )


@require_GET
def merchandise_products(request):
    search = request.GET.get("search", "").strip()[:100]

    products = get_products(search)[:100]

    return JsonResponse(
        {
            "products": [
                {
                    "id": product.external_id,
                    "title": product.title,
                    "category": product.category,
                    "brand": product.brand,
                    "price": str(product.price),
                    "weight": float(product.weight),
                    "width": float(product.width),
                    "height": float(product.height),
                    "depth": float(product.depth),
                    "thumbnail": product.thumbnail,
                    "stock": product.stock,
                }
                for product in products
            ]
        }
    )


@require_POST
def merchandise_add_fixture(request, floor_id):
    floor = get_object_or_404(Floor, id=floor_id)

    try:
        data = json.loads(request.body or "{}")

        fixture_data = validate_fixture_data(data)

        validate_fixture_position(
            floor,
            fixture_data["x"],
            fixture_data["y"],
            fixture_data["width"],
            fixture_data["depth"],
        )

        validate_fixture_overlap(
            floor,
            fixture_data["x"],
            fixture_data["y"],
            fixture_data["width"],
            fixture_data["depth"],
        )

        fixture = Fixture.objects.create(
            floor=floor,
            **fixture_data,
        )

        return JsonResponse(
            {
                "success": True,
                "fixture": serialize_fixture(fixture),
            },
            status=201,
        )

    except (ValueError, TypeError, KeyError) as error:
        return JsonResponse(
            {
                "success": False,
                "error": str(error),
            },
            status=400,
        )


@require_POST
def merchandise_delete_fixture(request, fixture_id):
    fixture = get_object_or_404(Fixture, id=fixture_id)

    fixture.delete()

    return JsonResponse(
        {
            "success": True,
            "message": "Fixture and its planogram removed.",
        }
    )


@require_POST
def merchandise_clear_floor(request, floor_id):
    floor = get_object_or_404(Floor, id=floor_id)

    floor.fixtures.all().delete()

    return JsonResponse(
        {
            "success": True,
            "message": "All fixtures on this floor have been removed.",
        }
    )


@require_POST
def merchandise_add_planogram_item(request, fixture_id):
    """Add a product to a fixture planogram."""

    fixture = get_object_or_404(
        Fixture.objects.select_related("floor"),
        id=fixture_id,
    )

    try:
        data = json.loads(request.body or "{}")

        if not isinstance(data, dict):
            raise ValueError("Invalid request data.")

        external_id = int(data.get("product_id"))

        quantity = int(data.get("quantity", 1))

        facings = int(data.get("facings", 1))

        if external_id < 1:
            raise ValueError("Invalid product ID.")

        if quantity < 1 or quantity > 10000:
            raise ValueError("Quantity must be between 1 and 10000.")

        if facings < 1 or facings > quantity:
            raise ValueError("Facings must be between 1 and the product quantity.")

        item = add_product_to_fixture(
            fixture,
            external_id,
            quantity,
            facings=facings,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Product added to planogram successfully.",
                "item": {
                    "id": item.id,
                    "product_id": item.product.external_id,
                    "title": item.product.title,
                    "thumbnail": item.product.thumbnail,
                    "quantity": item.quantity,
                    "facings": item.facings,
                    "position": item.position,
                },
            },
            status=201,
        )

    except (
        ValueError,
        TypeError,
        KeyError,
        OverflowError,
    ) as error:
        return JsonResponse(
            {
                "success": False,
                "error": str(error),
            },
            status=400,
        )


@require_POST
def merchandise_delete_planogram_item(request, item_id):
    item = get_object_or_404(
        PlanogramItem.objects.select_related("planogram__fixture"),
        id=item_id,
    )

    item.delete()

    return JsonResponse(
        {
            "success": True,
            "message": "Product removed from planogram.",
        }
    )


@require_POST
def merchandise_export_floor(request, floor_id):
    floor = get_object_or_404(Floor, id=floor_id)

    try:
        result = export_floor_plan(floor)

        return JsonResponse(
            {
                "success": True,
                "message": "Floor-plan drawing generated.",
                "config": result["config"],
            }
        )

    except (RuntimeError, OSError, ValueError) as error:
        return JsonResponse(
            {
                "success": False,
                "error": str(error),
            },
            status=500,
        )
