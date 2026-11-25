"""
AlwaysSmile Department Store - Building Service

Responsibilities:
- Create and retrieve the department store.
- Create and retrieve its seven physical floors.
- Support independently configurable floor dimensions.
- Preserve existing building and floor records by default.
- Update existing records only when explicitly requested.
- Provide floor lookup and serialization helpers.

Internal floor numbering:
    1  = Level 1
    2  = Level 2
    3  = Level 3
    4  = Level 4
    0  = Basement 1
    -1 = Basement 2
    -2 = Basement 3

floor_config.py is the authoritative floor configuration.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.dashboard.models import Building, Floor

from .floor_config import (
    DEFAULT_BUILDING,
    FLOOR_BY_CODE,
    FLOOR_BY_NUMBER,
    FLOORS,
    validate_floor_code,
    validate_floor_number,
)

# ============================================================
# BUILDING CONFIGURATION
# ============================================================

BUILDING_NAME = DEFAULT_BUILDING["name"]

DEFAULT_BUILDING_WIDTH = DEFAULT_BUILDING["width"]
DEFAULT_BUILDING_HEIGHT = DEFAULT_BUILDING["height"]

def validate_existing_floor_numbers(building):
    """
    Prevent initialization from silently accepting legacy
    or unexpected floor numbers.
    """

    expected = set(FLOOR_BY_NUMBER.keys())

    existing = set(
        Floor.objects.filter(
            building=building
        ).values_list("number", flat=True)
    )

    unexpected = existing - expected

    if unexpected:
        raise ValidationError(
            "Unexpected floor numbers detected: "
            f"{sorted(unexpected)}. "
            "Remove or reconcile legacy floors before initialization."
        )

# ============================================================
# GENERAL VALIDATION
# ============================================================


def validate_positive_dimension(value, field_name):
    """
    Validate a positive integer dimension.

    Building and Floor dimensions use PositiveIntegerField,
    so decimal dimensions are not accepted.
    """

    if isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a positive integer.")

    try:
        converted_value = int(value)
    except (TypeError, ValueError, OverflowError):
        raise ValidationError(f"{field_name} must be a positive integer.")

    if str(converted_value) != str(value).strip():
        raise ValidationError(f"{field_name} must be a positive integer.")

    if converted_value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")

    return converted_value


def validate_building(building):
    """Ensure the supplied object is a Building instance."""

    if not isinstance(building, Building):
        raise ValidationError("A valid building is required.")

    return building


def validate_floor(floor):
    """Ensure the supplied object is a Floor instance."""

    if not isinstance(floor, Floor):
        raise ValidationError("A valid floor is required.")

    return floor


# ============================================================
# BUILDING CREATION AND RETRIEVAL
# ============================================================


@transaction.atomic
def get_or_create_building(
    name=BUILDING_NAME,
    width=DEFAULT_BUILDING_WIDTH,
    height=DEFAULT_BUILDING_HEIGHT,
):
    """
    Retrieve the building or create it when it does not exist.

    Existing building dimensions are preserved.
    """

    if not isinstance(name, str) or not name.strip():
        raise ValidationError("A valid building name is required.")

    name = name.strip()

    width = validate_positive_dimension(
        width,
        "Building width",
    )

    height = validate_positive_dimension(
        height,
        "Building height",
    )

    building, created = Building.objects.get_or_create(
        name=name,
        defaults={
            "width": width,
            "height": height,
        },
    )

    return building


def get_building(building_id=None, name=BUILDING_NAME):
    """Retrieve a building using its ID or name."""

    if building_id is not None:
        if isinstance(building_id, bool):
            raise ValidationError("A valid building ID is required.")

        try:
            building_id = int(building_id)
        except (TypeError, ValueError, OverflowError):
            raise ValidationError("A valid building ID is required.")

        if building_id < 1:
            raise ValidationError("A valid building ID is required.")

        try:
            return Building.objects.get(pk=building_id)

        except Building.DoesNotExist:
            raise ValidationError("Building not found.")

    if not isinstance(name, str) or not name.strip():
        raise ValidationError("A valid building name is required.")

    try:
        return Building.objects.get(name=name.strip())

    except Building.DoesNotExist:
        raise ValidationError("Building not found.")

    except Building.MultipleObjectsReturned:
        raise ValidationError("Multiple buildings have this name. Use the building ID.")


@transaction.atomic
def update_building_dimensions(building, width, height):
    """Update the overall building dimensions."""

    validate_building(building)

    width = validate_positive_dimension(
        width,
        "Building width",
    )

    height = validate_positive_dimension(
        height,
        "Building height",
    )

    building = Building.objects.select_for_update().get(pk=building.pk)

    building.width = width
    building.height = height

    building.save(
        update_fields=[
            "width",
            "height",
        ]
    )

    return building


# ============================================================
# FLOOR CREATION
# ============================================================


@transaction.atomic
def create_floor(
    building,
    floor_code,
    width=None,
    height=None,
):
    """
    Create one physical floor.

    Existing floor records are returned without overwriting
    their names or dimensions.
    """

    validate_building(building)

    floor_code = validate_floor_code(floor_code)

    floor_config = FLOOR_BY_CODE[floor_code]

    if width is None:
        width = floor_config["width"]

    if height is None:
        height = floor_config["height"]

    width = validate_positive_dimension(
        width,
        "Floor width",
    )

    height = validate_positive_dimension(
        height,
        "Floor height",
    )

    building = Building.objects.select_for_update().get(pk=building.pk)

    floor, created = Floor.objects.get_or_create(
        building=building,
        number=floor_config["number"],
        defaults={
            "name": floor_config["name"],
            "width": width,
            "height": height,
        },
    )

    return floor


# ============================================================
# INITIALIZE ALL SEVEN FLOORS
# ============================================================


@transaction.atomic
def initialize_building(
    name=BUILDING_NAME,
    building_width=DEFAULT_BUILDING_WIDTH,
    building_height=DEFAULT_BUILDING_HEIGHT,
    floor_dimensions=None,
    update_existing=False,
):
    """
    Initialize the building and its seven physical floors.

    This function creates building and floor records only.
    Room creation belongs to floor_generator.py.

    Example floor_dimensions:

        {
            "L1": {"width": 45, "height": 35},
            "L2": {"width": 40, "height": 30},
            "L3": {"width": 38, "height": 32},
            "L4": {"width": 42, "height": 35},
            "B1": {"width": 40, "height": 30},
            "B2": {"width": 45, "height": 35},
            "B3": {"width": 50, "height": 40},
        }

    Existing records are preserved unless update_existing=True.

    Returns:
        {
            "building": Building instance,
            "floors": list of Floor instances,
            "created": bool,
        }
    """
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("A valid building name is required.")

    if not isinstance(update_existing, bool):
        raise ValidationError("update_existing must be True or False.")

    if floor_dimensions is None:
        floor_dimensions = {}

    if not isinstance(floor_dimensions, dict):
        raise ValidationError("Floor dimensions must be a dictionary.")

    building_width = validate_positive_dimension(
        building_width,
        "Building width",
    )

    building_height = validate_positive_dimension(
        building_height,
        "Building height",
    )

    # Validate all supplied floor dimensions first.
    normalized_dimensions = {}

    for floor_code, dimensions in floor_dimensions.items():
        floor_code = validate_floor_code(floor_code)

        if not isinstance(dimensions, dict):
            raise ValidationError(f"Dimensions for {floor_code} must be a dictionary.")

        unexpected_fields = set(dimensions) - {
            "width",
            "height",
        }

        if unexpected_fields:
            raise ValidationError(
                f"Unsupported dimension fields for {floor_code}: "
                f"{', '.join(sorted(unexpected_fields))}."
            )

        normalized_dimensions[floor_code] = {
            "width": dimensions.get("width"),
            "height": dimensions.get("height"),
        }

    # --------------------------------------------------------
    # BUILDING
    # --------------------------------------------------------

    building, building_created = Building.objects.get_or_create(
        name=name.strip(),
        defaults={
            "width": building_width,
            "height": building_height,
        },
    )

    building = Building.objects.select_for_update().get(pk=building.pk)

    validate_existing_floor_numbers(building)

    if update_existing and not building_created:
        building.width = building_width
        building.height = building_height

        building.save(
            update_fields=[
                "width",
                "height",
            ]
        )

    # --------------------------------------------------------
    # SEVEN FLOORS
    # --------------------------------------------------------

    floors = []
    records_created = building_created

    for floor_config in FLOORS:
        floor_code = floor_config["code"]

        dimensions = normalized_dimensions.get(
            floor_code,
            {},
        )

        width = dimensions.get("width")

        if width is None:
            width = floor_config["width"]

        height = dimensions.get("height")

        if height is None:
            height = floor_config["height"]

        width = validate_positive_dimension(
            width,
            f"{floor_code} width",
        )

        height = validate_positive_dimension(
            height,
            f"{floor_code} height",
        )

        floor, floor_created = Floor.objects.get_or_create(
            building=building,
            number=floor_config["number"],
            defaults={
                "name": floor_config["name"],
                "width": width,
                "height": height,
            },
        )

        if floor_created:
            records_created = True

        elif update_existing:
            floor = Floor.objects.select_for_update().get(pk=floor.pk)

            floor.name = floor_config["name"]
            floor.width = width
            floor.height = height

            floor.save(
                update_fields=[
                    "name",
                    "width",
                    "height",
                ]
            )

        floors.append(floor)

    return {
        "building": building,
        "floors": floors,
        "created": records_created,
    }


# ============================================================
# FLOOR RETRIEVAL
# ============================================================


def get_building_floors(building):
    """Retrieve all floors belonging to a building."""

    validate_building(building)

    return Floor.objects.filter(building=building).order_by("number")


def get_floor(building, floor_number):
    """Retrieve a floor using its internal number."""

    validate_building(building)

    floor_number = validate_floor_number(floor_number)

    try:
        return Floor.objects.get(
            building=building,
            number=floor_number,
        )

    except Floor.DoesNotExist:
        raise ValidationError("Floor not found.")


def get_floor_by_code(building, floor_code):
    """
    Retrieve a floor using its physical code.

    Examples:
        L1 = Level 1
        L4 = Level 4
        B1 = Basement 1
        B3 = Basement 3
    """

    floor_code = validate_floor_code(floor_code)

    floor_number = FLOOR_BY_CODE[floor_code]["number"]

    return get_floor(
        building,
        floor_number,
    )


# ============================================================
# FLOOR INFORMATION
# ============================================================


def serialize_floor(floor):
    """Return JSON-compatible floor information."""

    validate_floor(floor)

    floor_config = FLOOR_BY_NUMBER.get(
        floor.number,
        {},
    )

    return {
        "id": floor.id,
        "building_id": floor.building_id,
        "number": floor.number,
        "code": floor_config.get("code"),
        "name": floor.name,
        "width": floor.width,
        "height": floor.height,
        "description": floor_config.get("description", ""),
    }


def serialize_building(building):
    """Return building information and its physical floors."""

    validate_building(building)

    floors = get_building_floors(building)

    return {
        "id": building.id,
        "name": building.name,
        "width": building.width,
        "height": building.height,
        "floor_count": floors.count(),
        "floors": [serialize_floor(floor) for floor in floors],
    }

