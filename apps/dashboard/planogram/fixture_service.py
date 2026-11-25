"""
AlwaysSmile Fixture Service.

Responsibilities:
- Create fixtures.
- Retrieve individual fixtures.
- Retrieve fixtures belonging to a floor.
- Update fixture properties.
- Move fixtures.
- Resize fixtures.
- Delete fixtures.
- Clear all fixtures from a floor.
- Validate floor boundaries.
- Validate merchandise sales-room containment.
- Prevent fixture overlaps.
- Serialize fixture geometry.

Business validation belongs in validators.py.
Planogram product management belongs in planogram_service.py.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.dashboard.models import Fixture, Floor
from apps.dashboard.planogram.validators import (
    validate_fixture_data,
    validate_fixture_placement,
)

# ============================================================
# CONFIGURATION
# ============================================================

ALLOWED_FIXTURE_FIELDS = {
    "name",
    "fixture_type",
    "x",
    "y",
    "width",
    "depth",
    "color",
}


# ============================================================
# GENERAL VALIDATION
# ============================================================


def validate_floor(floor):
    """Ensure a valid Floor instance is supplied."""

    if not isinstance(floor, Floor):
        raise ValidationError("A valid floor is required.")

    if floor.pk is None:
        raise ValidationError("The floor must be saved.")

    return floor


def validate_fixture(fixture):
    """Ensure a valid Fixture instance is supplied."""

    if not isinstance(fixture, Fixture):
        raise ValidationError("A valid fixture is required.")

    if fixture.pk is None:
        raise ValidationError("The fixture must be saved.")

    return fixture


def validate_service_data(data):
    """Validate the structure and supported fields of fixture data."""

    if not isinstance(data, dict):
        raise ValidationError("Fixture data must be an object.")

    if not all(isinstance(field, str) for field in data):
        raise ValidationError("Fixture field names must be strings.")

    unexpected = set(data) - ALLOWED_FIXTURE_FIELDS

    if unexpected:
        raise ValidationError(
            f"Unsupported fixture fields: {', '.join(sorted(unexpected))}."
        )

    return data


def convert_validation_error(function, *args, **kwargs):
    """
    Convert standard Python validation errors into
    Django ValidationError exceptions.
    """

    try:
        return function(*args, **kwargs)

    except (ValueError, TypeError) as exc:
        raise ValidationError(str(exc)) from exc


def validate_fixture_id(fixture_id):
    """Validate and normalize a fixture database ID."""

    if isinstance(fixture_id, bool):
        raise ValidationError("A valid fixture ID is required.")

    try:
        fixture_id = int(fixture_id)
    except (TypeError, ValueError, OverflowError):
        raise ValidationError("A valid fixture ID is required.")

    if fixture_id < 1:
        raise ValidationError("A valid fixture ID is required.")

    return fixture_id


# ============================================================
# FIXTURE PLACEMENT
# ============================================================


def validate_placement(
    floor,
    data,
    exclude_fixture_id=None,
):
    """
    Validate fixture placement against:

    1. Floor boundaries.
    2. Merchandise sales-room containment.
    3. Existing fixture overlaps.

    Touching fixture edges are permitted.
    """

    return convert_validation_error(
        validate_fixture_placement,
        floor=floor,
        x=data["x"],
        y=data["y"],
        width=data["width"],
        depth=data["depth"],
        exclude_fixture_id=exclude_fixture_id,
    )


# ============================================================
# CREATE FIXTURE
# ============================================================


@transaction.atomic
def create_fixture(floor, data):
    """Create a validated fixture on a selected floor."""

    validate_floor(floor)
    validate_service_data(data)

    validated = convert_validation_error(
        validate_fixture_data,
        data,
    )

    try:
        locked_floor = Floor.objects.select_for_update().get(
            pk=floor.pk,
        )
    except Floor.DoesNotExist:
        raise ValidationError("Floor no longer exists.")

    placement = validate_placement(
        locked_floor,
        validated,
    )

    return Fixture.objects.create(
        floor=locked_floor,
        room=placement["room"],
        name=validated["name"],
        fixture_type=validated["fixture_type"],
        x=placement["x"],
        y=placement["y"],
        width=placement["width"],
        depth=placement["depth"],
        color=validated["color"],
    )


# ============================================================
# GET FIXTURE
# ============================================================


def get_fixture(fixture_id):
    """Retrieve an individual fixture."""

    fixture_id = validate_fixture_id(fixture_id)

    try:
        return Fixture.objects.select_related(
            "floor",
            "floor__building",
            "room",
        ).get(pk=fixture_id)

    except Fixture.DoesNotExist:
        raise ValidationError("Fixture not found.")


# ============================================================
# GET FLOOR FIXTURES
# ============================================================


def get_floor_fixtures(floor):
    """Retrieve fixtures belonging exclusively to one floor."""

    validate_floor(floor)

    return (
        Fixture.objects.filter(floor_id=floor.pk)
        .select_related(
            "floor",
            "floor__building",
            "room",
        )
        .prefetch_related(
            "planogram__items__product",
        )
        .order_by("id")
    )


# ============================================================
# UPDATE FIXTURE
# ============================================================


@transaction.atomic
def update_fixture(fixture, data):
    """
    Update fixture properties.

    Supported changes:
    - Name.
    - Fixture type.
    - Coordinates.
    - Dimensions.
    - Color.

    The complete resulting fixture is validated before saving.
    """

    validate_fixture(fixture)
    validate_service_data(data)

    if not data:
        return fixture

    try:
        locked_floor = Floor.objects.select_for_update().get(
            pk=fixture.floor_id,
        )

    except Floor.DoesNotExist:
        raise ValidationError("Fixture floor no longer exists.")

    try:
        locked_fixture = Fixture.objects.select_for_update().get(
            pk=fixture.pk,
            floor=locked_floor,
        )

    except Fixture.DoesNotExist:
        raise ValidationError("Fixture no longer exists or has moved.")

    current_data = {
        "name": locked_fixture.name,
        "fixture_type": locked_fixture.fixture_type,
        "x": locked_fixture.x,
        "y": locked_fixture.y,
        "width": locked_fixture.width,
        "depth": locked_fixture.depth,
        "color": locked_fixture.color,
    }

    current_data.update(data)

    validated = convert_validation_error(
        validate_fixture_data,
        current_data,
    )

    placement = validate_placement(
        locked_floor,
        validated,
        exclude_fixture_id=locked_fixture.pk,
    )

    validated.update(
        {
            "x": placement["x"],
            "y": placement["y"],
            "width": placement["width"],
            "depth": placement["depth"],
        }
    )

    locked_fixture.room = placement["room"]

    for field, value in validated.items():
        setattr(locked_fixture, field, value)

    locked_fixture.save(
        update_fields=[
            *validated.keys(),
            "room",
        ]
    )

    return locked_fixture


# ============================================================
# MOVE FIXTURE
# ============================================================


def move_fixture(fixture, x, y):
    """Move a fixture while preserving its existing dimensions."""

    return update_fixture(
        fixture,
        {
            "x": x,
            "y": y,
        },
    )


# ============================================================
# RESIZE FIXTURE
# ============================================================


def resize_fixture(fixture, width, depth):
    """Resize a fixture while preserving its coordinates."""

    return update_fixture(
        fixture,
        {
            "width": width,
            "depth": depth,
        },
    )


# ============================================================
# DELETE FIXTURE
# ============================================================


@transaction.atomic
def delete_fixture(fixture):
    """Delete one fixture and its configured dependent records."""

    validate_fixture(fixture)

    try:
        locked_floor = Floor.objects.select_for_update().get(
            pk=fixture.floor_id,
        )

    except Floor.DoesNotExist:
        raise ValidationError("Fixture floor no longer exists.")

    try:
        locked_fixture = Fixture.objects.select_for_update().get(
            pk=fixture.pk,
            floor=locked_floor,
        )

    except Fixture.DoesNotExist:
        return False

    locked_fixture.delete()

    return True


# ============================================================
# CLEAR FLOOR FIXTURES
# ============================================================


@transaction.atomic
def clear_floor_fixtures(floor):
    """Delete all fixtures from one selected floor."""

    validate_floor(floor)

    try:
        locked_floor = Floor.objects.select_for_update().get(
            pk=floor.pk,
        )

    except Floor.DoesNotExist:
        raise ValidationError("Floor no longer exists.")

    fixtures = Fixture.objects.filter(
        floor=locked_floor,
    )

    count = fixtures.count()

    fixtures.delete()

    return count


# ============================================================
# SERIALIZE FIXTURE GEOMETRY
# ============================================================


def serialize_fixture_geometry(fixture):
    """Return JSON-compatible fixture geometry."""

    validate_fixture(fixture)

    return {
        "id": fixture.id,
        "name": fixture.name,
        "type": fixture.fixture_type,
        "fixture_type": fixture.fixture_type,
        "floor_id": fixture.floor_id,
        "room_id": fixture.room_id,
        "x": str(fixture.x),
        "y": str(fixture.y),
        "width": str(fixture.width),
        "depth": str(fixture.depth),
        "color": fixture.color,
    }


# ============================================================
# SERIALIZE COMPLETE FIXTURE
# ============================================================


def serialize_fixture(fixture):
    """
    Serialize fixture geometry and planogram information.

    Product serialization remains the responsibility
    of planogram_service.py.
    """

    validate_fixture(fixture)

    from apps.dashboard.planogram.planogram_service import (
        serialize_fixture as serialize_planogram_fixture,
    )

    return serialize_planogram_fixture(fixture)
