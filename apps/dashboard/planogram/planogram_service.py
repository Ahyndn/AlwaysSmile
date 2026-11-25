
"""
AlwaysSmile Merchandise Planogram Service.

Responsibilities:
- Create and retrieve fixture planograms.
- Assign merchandise products to fixtures.
- Update product quantities and facings.
- Remove individual products.
- Clear planograms.
- Reorder planogram items.
- Serialize fixtures and planogram contents.
- Generate fixture summaries.
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Sum

from apps.dashboard.models import (
    Fixture,
    MerchandiseProduct,
    Planogram,
    PlanogramItem,
)


# ============================================================
# CONFIGURATION
# ============================================================

MAX_QUANTITY = 10000
MAX_FACINGS = 10000

ALLOWED_ITEM_FIELDS = {
    "quantity",
    "facings",
    "position",
}


# ============================================================
# VALIDATION HELPERS
# ============================================================

def validate_saved_instance(instance, model, message):
    """Validate that an object is a saved model instance."""

    if not isinstance(instance, model):
        raise ValidationError(message)

    if instance.pk is None:
        raise ValidationError("The object must be saved first.")

    return instance


def validate_fixture(fixture):
    return validate_saved_instance(
        fixture,
        Fixture,
        "A valid fixture is required.",
    )


def validate_planogram(planogram):
    return validate_saved_instance(
        planogram,
        Planogram,
        "A valid planogram is required.",
    )


def validate_planogram_item(item):
    return validate_saved_instance(
        item,
        PlanogramItem,
        "A valid planogram item is required.",
    )


def validate_product(product):
    return validate_saved_instance(
        product,
        MerchandiseProduct,
        "A valid merchandise product is required.",
    )


def validate_item_data(data):
    """Validate supported planogram item update fields."""

    if not isinstance(data, dict):
        raise ValidationError(
            "Planogram item data must be an object."
        )

    if not all(isinstance(field, str) for field in data):
        raise ValidationError(
            "Planogram field names must be strings."
        )

    unexpected = set(data) - ALLOWED_ITEM_FIELDS

    if unexpected:
        raise ValidationError(
            f"Unsupported planogram fields: "
            f"{', '.join(sorted(unexpected))}."
        )

    return data


# ============================================================
# INTEGER VALIDATION
# ============================================================

def validate_integer(value, field_name, minimum, maximum=None):
    """Validate a finite whole number within specified limits."""

    if isinstance(value, bool) or value is None:
        raise ValidationError(
            f"{field_name} must be a valid integer."
        )

    try:
        number = Decimal(str(value).strip())

        if not number.is_finite():
            raise InvalidOperation

        if number != number.to_integral_value():
            raise ValueError

        converted = int(number)

    except (
        InvalidOperation,
        TypeError,
        ValueError,
        OverflowError,
    ):
        raise ValidationError(
            f"{field_name} must be a valid integer."
        )

    if converted < minimum:
        if minimum == 0:
            raise ValidationError(
                f"{field_name} cannot be negative."
            )

        raise ValidationError(
            f"{field_name} must be greater than zero."
        )

    if maximum is not None and converted > maximum:
        raise ValidationError(
            f"{field_name} cannot exceed {maximum}."
        )

    return converted


def validate_positive_integer(value, field_name, maximum=None):
    return validate_integer(
        value,
        field_name,
        minimum=1,
        maximum=maximum,
    )


def validate_position(value):
    return validate_integer(
        value,
        "Position",
        minimum=0,
    )


def validate_facings_quantity(facings, quantity):
    if facings > quantity:
        raise ValidationError(
            "Facings cannot exceed the allocated quantity."
        )


# ============================================================
# DATABASE RETRIEVAL HELPERS
# ============================================================

def get_locked_fixture(fixture):
    validate_fixture(fixture)

    try:
        return Fixture.objects.select_for_update().get(
            pk=fixture.pk
        )
    except Fixture.DoesNotExist:
        raise ValidationError("Fixture no longer exists.")


def get_locked_planogram(planogram):
    validate_planogram(planogram)

    try:
        return Planogram.objects.select_for_update().get(
            pk=planogram.pk
        )
    except Planogram.DoesNotExist:
        raise ValidationError("Planogram no longer exists.")


def get_locked_planogram_item(item):
    validate_planogram_item(item)

    try:
        return PlanogramItem.objects.select_for_update().get(
            pk=item.pk
        )
    except PlanogramItem.DoesNotExist:
        raise ValidationError("Planogram item no longer exists.")


# ============================================================
# PLANOGRAM CREATION AND RETRIEVAL
# ============================================================

@transaction.atomic
def get_or_create_planogram(fixture):
    """Retrieve or create the fixture's unique planogram."""

    locked_fixture = get_locked_fixture(fixture)

    planogram, _ = Planogram.objects.get_or_create(
        fixture=locked_fixture,
        defaults={
            "name": f"Planogram - {locked_fixture.name}"
        },
    )

    return planogram


def get_fixture_planogram(fixture):
    """Retrieve a fixture's planogram, or return None."""

    validate_fixture(fixture)

    if not Fixture.objects.filter(pk=fixture.pk).exists():
        raise ValidationError("Fixture no longer exists.")

    try:
        return (
            Planogram.objects
            .prefetch_related("items__product__sales_channels")
            .get(fixture_id=fixture.pk)
        )
    except Planogram.DoesNotExist:
        return None


# ============================================================
# ADD PRODUCT TO FIXTURE
# ============================================================

@transaction.atomic
def add_product_to_fixture(
    fixture,
    product,
    quantity=1,
    facings=1,
):
    """Add a product or update its existing allocation."""

    validate_fixture(fixture)
    validate_product(product)

    quantity = validate_positive_integer(
        quantity,
        "Quantity",
        MAX_QUANTITY,
    )

    facings = validate_positive_integer(
        facings,
        "Facings",
        MAX_FACINGS,
    )

    validate_facings_quantity(facings, quantity)

    locked_fixture = get_locked_fixture(fixture)

    try:
        locked_product = (
            MerchandiseProduct.objects
            .prefetch_related("sales_channels")
            .get(pk=product.pk)
        )
    except MerchandiseProduct.DoesNotExist:
        raise ValidationError(
            "Merchandise product no longer exists."
        )

    if not locked_product.is_available_in_store:
        raise ValidationError(
            "Products unavailable for in-store sales cannot "
            "be added to physical store fixtures."
        )

    planogram = get_or_create_planogram(locked_fixture)

    existing_item = (
        PlanogramItem.objects
        .select_for_update()
        .filter(
            planogram=planogram,
            product=locked_product,
        )
        .first()
    )

    if existing_item:
        existing_item.quantity = quantity
        existing_item.facings = facings

        existing_item.save(
            update_fields=["quantity", "facings"]
        )

        return existing_item

    last_position = (
        PlanogramItem.objects
        .filter(planogram=planogram)
        .order_by("-position")
        .values_list("position", flat=True)
        .first()
    )

    next_position = (
        last_position + 1
        if last_position is not None
        else 0
    )

    return PlanogramItem.objects.create(
        planogram=planogram,
        product=locked_product,
        quantity=quantity,
        facings=facings,
        position=next_position,
    )


# ============================================================
# UPDATE PLANOGRAM ITEM
# ============================================================

@transaction.atomic
def update_planogram_item(item, data):
    """
    Update an item's quantity, facings or position.

    Only explicitly supplied fields are modified.
    """

    validate_planogram_item(item)
    validate_item_data(data)

    if not data:
        return item

    try:
        current_item = (
            PlanogramItem.objects
            .only("planogram_id")
            .get(pk=item.pk)
        )
    except PlanogramItem.DoesNotExist:
        raise ValidationError(
            "Planogram item no longer exists."
        )

    locked_planogram = (
        Planogram.objects
        .select_for_update()
        .filter(pk=current_item.planogram_id)
        .first()
    )

    if locked_planogram is None:
        raise ValidationError("Planogram no longer exists.")

    try:
        locked_item = (
            PlanogramItem.objects
            .select_for_update()
            .get(
                pk=item.pk,
                planogram=locked_planogram,
            )
        )
    except PlanogramItem.DoesNotExist:
        raise ValidationError(
            "Planogram item no longer exists."
        )

    quantity = locked_item.quantity
    facings = locked_item.facings

    validated = {}

    if "quantity" in data:
        quantity = validate_positive_integer(
            data["quantity"],
            "Quantity",
            MAX_QUANTITY,
        )
        validated["quantity"] = quantity

    if "facings" in data:
        facings = validate_positive_integer(
            data["facings"],
            "Facings",
            MAX_FACINGS,
        )
        validated["facings"] = facings

    if "position" in data:
        validated["position"] = validate_position(
            data["position"]
        )

    validate_facings_quantity(facings, quantity)

    for field, value in validated.items():
        setattr(locked_item, field, value)

    if validated:
        locked_item.save(
            update_fields=list(validated.keys())
        )

    return locked_item


# ============================================================
# REMOVE PLANOGRAM ITEM
# ============================================================

@transaction.atomic
def remove_planogram_item(item):
    """Remove one product from its planogram."""

    validate_planogram_item(item)

    try:
        current_item = (
            PlanogramItem.objects
            .only("planogram_id")
            .get(pk=item.pk)
        )
    except PlanogramItem.DoesNotExist:
        return False

    locked_planogram = (
        Planogram.objects
        .select_for_update()
        .filter(pk=current_item.planogram_id)
        .first()
    )

    if locked_planogram is None:
        return False

    try:
        locked_item = (
            PlanogramItem.objects
            .select_for_update()
            .get(
                pk=item.pk,
                planogram=locked_planogram,
            )
        )
    except PlanogramItem.DoesNotExist:
        return False

    locked_item.delete()

    return True


# ============================================================
# CLEAR PLANOGRAM
# ============================================================

@transaction.atomic
def clear_planogram(planogram):
    """Remove all products without deleting the planogram."""

    locked_planogram = get_locked_planogram(planogram)

    items = PlanogramItem.objects.filter(
        planogram=locked_planogram
    )

    deleted_count = items.count()

    items.delete()

    return deleted_count


# ============================================================
# REORDER PLANOGRAM ITEMS
# ============================================================

@transaction.atomic
def reorder_planogram_items(planogram, item_ids):
    """
    Reorder all products within a planogram.

    Requirements:
    - Every existing item must be supplied.
    - Duplicate IDs are prohibited.
    - IDs must be valid positive integers.
    - Every item must belong to this planogram.
    - Positions start at zero and remain consecutive.
    """

    validate_planogram(planogram)

    if not isinstance(item_ids, (list, tuple)):
        raise ValidationError(
            "Item IDs must be supplied as a list."
        )

    try:
        requested_ids = [
            validate_positive_integer(
                item_id,
                "Item ID",
            )
            for item_id in item_ids
        ]
    except ValidationError:
        raise ValidationError(
            "All item IDs must be valid positive integers."
        )

    if len(requested_ids) != len(set(requested_ids)):
        raise ValidationError(
            "Duplicate item IDs are not allowed."
        )

    locked_planogram = get_locked_planogram(planogram)

    items = list(
        PlanogramItem.objects
        .select_for_update()
        .filter(planogram=locked_planogram)
        .order_by("position", "id")
    )

    existing_ids = {
        item.pk for item in items
    }

    if set(requested_ids) != existing_ids:
        raise ValidationError(
            "The supplied IDs must contain every item "
            "in this planogram exactly once."
        )

    items_by_id = {
        item.pk: item for item in items
    }

    for position, item_id in enumerate(requested_ids):
        item = items_by_id[item_id]

        if item.position != position:
            item.position = position

            item.save(
                update_fields=["position"]
            )

    return list(
        PlanogramItem.objects
        .filter(planogram=locked_planogram)
        .select_related("product")
        .prefetch_related("product__sales_channels")
        .order_by("position", "id")
    )


# ============================================================
# SERIALIZE PLANOGRAM ITEM
# ============================================================

def serialize_planogram_item(item):
    """Convert a planogram item into a JSON-compatible dictionary."""

    validate_planogram_item(item)

    product = item.product

    sales_channels = list(
        product.sales_channels.values_list(
            "code",
            flat=True,
        )
    )

    return {
        "id": item.pk,
        "planogram_id": item.planogram_id,

        "product_id": product.pk,
        "external_id": product.external_id,
        "title": product.title,
        "category": product.category,
        "brand": product.brand,

        "price": str(product.price),
        "thumbnail": product.thumbnail or None,
        "stock": product.stock,

        "quantity": item.quantity,
        "facings": item.facings,
        "position": item.position,

        "total_price": str(
            product.price * item.quantity
        ),

        "sales_channels": sales_channels,

        "is_available_online": (
            "online" in sales_channels
            or "mobile" in sales_channels
        ),

        "is_available_in_store": (
            "in_person" in sales_channels
        ),
    }


# ============================================================
# SERIALIZE FIXTURE
# ============================================================

def serialize_fixture(fixture):
    """Serialize fixture information and its planogram contents."""

    validate_fixture(fixture)

    try:
        persisted_fixture = (
            Fixture.objects
            .select_related("floor")
            .get(pk=fixture.pk)
        )
    except Fixture.DoesNotExist:
        raise ValidationError(
            "Fixture no longer exists."
        )

    planogram = (
        Planogram.objects
        .filter(fixture_id=persisted_fixture.pk)
        .prefetch_related(
            "items__product__sales_channels"
        )
        .first()
    )

    serialized_items = []

    if planogram is not None:
        serialized_items = [
            serialize_planogram_item(item)
            for item in planogram.items.all()
        ]

    return {
        "id": persisted_fixture.pk,
        "name": persisted_fixture.name,

        "type": persisted_fixture.fixture_type,
        "fixture_type": persisted_fixture.fixture_type,
        "room_id": persisted_fixture.room_id,
        "floor_id": persisted_fixture.floor_id,

        "x": str(persisted_fixture.x),
        "y": str(persisted_fixture.y),
        "width": str(persisted_fixture.width),
        "depth": str(persisted_fixture.depth),

        "color": persisted_fixture.color,

        "planogram": serialized_items,
    }


# ============================================================
# FIXTURE SUMMARY
# ============================================================

def get_fixture_summary(fixture):
    """Generate aggregate product statistics for a fixture."""

    validate_fixture(fixture)

    try:
        persisted_fixture = Fixture.objects.get(
            pk=fixture.pk
        )
    except Fixture.DoesNotExist:
        raise ValidationError(
            "Fixture no longer exists."
        )

    planogram = (
        Planogram.objects
        .filter(fixture_id=persisted_fixture.pk)
        .first()
    )

    if planogram is None:
        return {
            "fixture_id": persisted_fixture.pk,
            "fixture_name": persisted_fixture.name,
            "product_count": 0,
            "total_quantity": 0,
            "total_facings": 0,
        }

    summary = planogram.items.aggregate(
        product_count=Count("id"),
        total_quantity=Sum("quantity"),
        total_facings=Sum("facings"),
    )

    return {
        "fixture_id": persisted_fixture.pk,
        "fixture_name": persisted_fixture.name,

        "product_count": summary["product_count"] or 0,
        "total_quantity": summary["total_quantity"] or 0,
        "total_facings": summary["total_facings"] or 0,
    }
