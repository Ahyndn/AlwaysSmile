from django.db import transaction
from django.db.models import F

from apps.dashboard.models import (
    MerchandiseProduct,
    Planogram,
    PlanogramItem,
)


@transaction.atomic
def add_product_to_fixture(fixture, external_id, quantity=1):
    """Add a product to a fixture's planogram."""

    product = MerchandiseProduct.objects.get(external_id=external_id)

    if type(quantity) is not int or not 1 <= quantity <= 10000:
        raise ValueError("Quantity must be between 1 and 10,000.")

    planogram, _ = Planogram.objects.get_or_create(
        fixture=fixture,
        defaults={"name": f"{fixture.name} Planogram"},
    )

    item, created = PlanogramItem.objects.get_or_create(
        planogram=planogram,
        product=product,
        defaults={
            "quantity": quantity,
            "facings": 1,
        },
    )

    if not created:
        PlanogramItem.objects.filter(pk=item.pk).update(
            quantity=F("quantity") + quantity
        )
        item.refresh_from_db()

    return item



def serialize_fixture(fixture):
    """Serialize a fixture and all its planogram products."""

    validate_fixture(fixture)

    try:
        persisted_fixture = (
            Fixture.objects
            .select_related("floor")
            .get(pk=fixture.pk)
        )
    except Fixture.DoesNotExist:
        raise ValidationError("Fixture no longer exists.")

    planogram = (
        Planogram.objects
        .filter(fixture_id=persisted_fixture.pk)
        .prefetch_related("items__product", "items__product__sales_channels")
        .first()
    )

    serialized_items = []

    if planogram:
        serialized_items = [
            serialize_planogram_item(item)
            for item in planogram.items.all().order_by("position", "id")
        ]

    return {
        "id": persisted_fixture.id,
        "name": persisted_fixture.name,
        "type": persisted_fixture.fixture_type,
        "fixture_type": persisted_fixture.fixture_type,
        "floor_id": persisted_fixture.floor_id,
        "x": str(persisted_fixture.x),
        "y": str(persisted_fixture.y),
        "width": str(persisted_fixture.width),
        "depth": str(persisted_fixture.depth),
        "color": persisted_fixture.color,
        "planogram": serialized_items,
    }
