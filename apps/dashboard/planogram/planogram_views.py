"""
AlwaysSmile Department Store - Planogram Views.

Responsibilities:
- Display the planogram dashboard.
- Display individual fixture planograms.
- Display merchandise catalogue.
- Synchronize DummyJSON products.
- Add products to fixtures.
- Update quantities and facings.
- Remove products.
- Return planogram JSON data.
- Reorder planogram products.

Business logic belongs in the service layer.
"""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from apps.dashboard.models import (
    Building,
    Fixture,
    PlanogramItem,
)
from apps.dashboard.planogram.planogram_service import (
    add_product_to_fixture,
    get_fixture_planogram,
    get_or_create_planogram,
    remove_planogram_item,
    reorder_planogram_items,
    serialize_planogram_item,
    update_planogram_item,
)
from apps.dashboard.planogram.product_service import (
    get_product_by_external_id,
    get_products,
    synchronize_products,
)

# ============================================================
# DASHBOARD
# ============================================================


@login_required
def planogram_dashboard(request):
    """
    Display buildings, floors and available fixtures.
    """

    buildings = Building.objects.prefetch_related(
        "floors__rooms",
        "floors__fixtures",
    ).order_by("id")

    selected_fixture = None

    fixture_id = request.GET.get("fixture")

    if fixture_id:
        selected_fixture = get_object_or_404(
            Fixture.objects.select_related(
                "floor",
                "floor__building",
            ),
            pk=fixture_id,
        )

    return render(
        request,
        "dashboard/planogram/dashboard.html",
        {
            "buildings": buildings,
            "selected_fixture": selected_fixture,
        },
    )


# ============================================================
# FIXTURE PLANOGRAM PAGE
# ============================================================


@login_required
def fixture_planogram(request, fixture_id):
    """
    Display products assigned to a selected fixture.
    """

    fixture = get_object_or_404(
        Fixture.objects.select_related(
            "floor",
            "floor__building",
        ),
        pk=fixture_id,
    )

    planogram = get_fixture_planogram(fixture)

    planogram_items = planogram.items.select_related("product").order_by(
        "position", "id"
    )

    return render(
        request,
        "dashboard/planogram/fixture_planogram.html",
        {
            "fixture": fixture,
            "planogram": planogram,
            "planogram_items": planogram_items,
            "total_products": planogram_items.count(),
        },
    )


# ============================================================
# PRODUCT CATALOGUE
# ============================================================


@login_required
def product_catalog(request):
    """
    Display cached merchandise products.
    """

    search = request.GET.get("search", "").strip()

    products = get_products(search)

    return render(
        request,
        "dashboard/planogram/product_catalog.html",
        {
            "products": products,
            "search": search,
        },
    )


# ============================================================
# PRODUCT SYNCHRONIZATION
# ============================================================


@login_required
@require_POST
def synchronize_product_catalog(request):
    """
    Synchronize merchandise products from DummyJSON.
    """

    try:
        synchronize_products()

        messages.success(
            request,
            "Merchandise catalogue synchronized successfully.",
        )

    except Exception:
        messages.error(
            request,
            "Product synchronization failed. "
            "Please check the product service and try again.",
        )

    return redirect("product_catalog")


# ============================================================
# ADD PRODUCT TO FIXTURE
# ============================================================


@login_required
@require_POST
def add_fixture_product(request, fixture_id):
    """
    Add a merchandise product to a fixture.

    The submitted external_id identifies a
    MerchandiseProduct in the local database.
    """

    fixture = get_object_or_404(
        Fixture,
        pk=fixture_id,
    )

    try:
        external_id = request.POST.get("external_id")

        if not external_id:
            raise ValidationError("A product ID is required.")

        if not external_id.isdigit() or int(external_id) < 1:
            raise ValidationError("A valid product ID is required.")

        product = get_product_by_external_id(external_id)

        quantity = request.POST.get("quantity", "1")
        facings = request.POST.get("facings", "1")

        item = add_product_to_fixture(
            fixture=fixture,
            product=product,
            quantity=quantity,
            facings=facings,
        )

        messages.success(
            request,
            f"{item.product.title} added to {fixture.name}.",
        )

    except ValidationError as exc:
        messages.error(request, str(exc))

    return redirect(
        "fixture_planogram",
        fixture_id=fixture.id,
    )


# ============================================================
# REMOVE PRODUCT FROM FIXTURE
# ============================================================


@login_required
@require_POST
def remove_fixture_product(request, fixture_id, item_id):
    """
    Remove a product from a specific fixture.
    """

    fixture = get_object_or_404(
        Fixture,
        pk=fixture_id,
    )

    item = get_object_or_404(
        PlanogramItem.objects.select_related(
            "product",
            "planogram",
        ),
        pk=item_id,
        planogram__fixture=fixture,
    )

    product_name = item.product.title

    try:
        removed = remove_planogram_item(item)

        if removed:
            messages.success(
                request,
                f"{product_name} removed from {fixture.name}.",
            )
        else:
            messages.warning(
                request,
                "The product was already removed.",
            )

    except ValidationError as exc:
        messages.error(request, str(exc))

    return redirect(
        "fixture_planogram",
        fixture_id=fixture.id,
    )


# ============================================================
# UPDATE PRODUCT QUANTITY AND FACINGS
# ============================================================


@login_required
@require_POST
def update_fixture_product(request, fixture_id, item_id):
    """
    Update quantity and facings for a fixture product.
    """

    fixture = get_object_or_404(
        Fixture,
        pk=fixture_id,
    )

    item = get_object_or_404(
        PlanogramItem.objects.select_related(
            "product",
            "planogram",
        ),
        pk=item_id,
        planogram__fixture=fixture,
    )

    try:
        data = {
            "quantity": request.POST.get("quantity"),
            "facings": request.POST.get("facings"),
        }

        updated_item = update_planogram_item(
            item,
            data,
        )

        messages.success(
            request,
            f"{updated_item.product.title} updated successfully.",
        )

    except ValidationError as exc:
        messages.error(request, str(exc))

    return redirect(
        "fixture_planogram",
        fixture_id=fixture.id,
    )


# ============================================================
# FIXTURE PLANOGRAM JSON DATA
# ============================================================


@login_required
def fixture_planogram_data(request, fixture_id):
    """
    Return fixture planogram information as JSON.
    """

    fixture = get_object_or_404(
        Fixture.objects.select_related(
            "floor",
            "floor__building",
        ),
        pk=fixture_id,
    )

    planogram = get_fixture_planogram(fixture)

    items = planogram.items.select_related("product").order_by("position", "id")

    data = [serialize_planogram_item(item) for item in items]

    return JsonResponse(
        {
            "fixture": {
                "id": fixture.id,
                "name": fixture.name,
                "floor_id": fixture.floor_id,
                "floor_name": fixture.floor.name,
                "width": str(fixture.width),
                "depth": str(fixture.depth),
            },
            "planogram_id": planogram.id,
            "items": data,
            "total_items": len(data),
        }
    )


# ============================================================
# REORDER FIXTURE PRODUCTS
# ============================================================


@login_required
@require_POST
def reorder_fixture_products(request, fixture_id):
    """
    Reorder products within a fixture planogram.

    Expected JSON:

    {
        "items": [
            {"id": 1, "position": 0},
            {"id": 2, "position": 1}
        ]
    }

    Every existing planogram item must be submitted
    exactly once, with consecutive positions.
    """

    fixture = get_object_or_404(
        Fixture,
        pk=fixture_id,
    )

    try:
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError, UnicodeDecodeError:
            raise ValidationError("Request body must contain valid JSON.")

        if not isinstance(payload, dict):
            raise ValidationError("Invalid request data.")

        entries = payload.get("items")

        if not isinstance(entries, list):
            raise ValidationError("Items must be supplied as a list.")

        submitted = []
        positions = set()
        item_ids = set()

        for entry in entries:
            if not isinstance(entry, dict):
                raise ValidationError("Invalid item data.")

            if "id" not in entry or "position" not in entry:
                raise ValidationError("Each item requires an ID and position.")

            item_id = entry["id"]
            position = entry["position"]

            if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 1:
                raise ValidationError("Invalid planogram item ID.")

            if (
                isinstance(position, bool)
                or not isinstance(position, int)
                or position < 0
            ):
                raise ValidationError("Invalid item position.")

            if item_id in item_ids:
                raise ValidationError("Duplicate item IDs are not allowed.")

            if position in positions:
                raise ValidationError("Duplicate positions are not allowed.")

            item_ids.add(item_id)
            positions.add(position)

            submitted.append((item_id, position))

        expected_positions = set(range(len(submitted)))

        if positions != expected_positions:
            raise ValidationError("Positions must be consecutive, starting at zero.")

        ordered_ids = [
            item_id
            for item_id, position in sorted(
                submitted,
                key=lambda entry: entry[1],
            )
        ]

        planogram = get_or_create_planogram(fixture)

        reordered_items = reorder_planogram_items(
            planogram,
            ordered_ids,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Planogram positions updated.",
                "items": [
                    {
                        "id": item.id,
                        "position": item.position,
                    }
                    for item in reordered_items
                ],
            }
        )

    except ValidationError as exc:
        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=400,
        )
