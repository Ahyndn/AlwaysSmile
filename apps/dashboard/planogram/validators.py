
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

from apps.dashboard.models import (
    Fixture,
    Floor,
    MerchandiseProduct,
    Room,
)


# ============================================================
# CONSTANTS
# ============================================================

ZERO = Decimal("0")
MIN_DIMENSION = Decimal("0.1")

MAX_FIXTURE_NAME_LENGTH = 100
MAX_PRODUCT_QUANTITY = 10000
MAX_COLOR_LENGTH = 20


# ============================================================
# DECIMAL CONVERSION
# ============================================================

def safe_decimal(value, field_name="Value"):
    """Convert input into a finite Decimal."""

    if isinstance(value, bool) or value is None:
        raise ValidationError(
            f"{field_name} must be a valid finite number."
        )

    try:
        result = Decimal(str(value))

        if not result.is_finite():
            raise InvalidOperation

        return result

    except (
        InvalidOperation,
        TypeError,
        ValueError,
        OverflowError,
    ):
        raise ValidationError(
            f"{field_name} must be a valid finite number."
        )


def nonnegative_decimal(value, field_name="Value"):
    """Validate a finite non-negative decimal."""

    result = safe_decimal(value, field_name)

    if result < ZERO:
        raise ValidationError(
            f"{field_name} cannot be negative."
        )

    return result


def positive_decimal(value, field_name="Value"):
    """Validate a finite positive dimension."""

    result = safe_decimal(value, field_name)

    if result < MIN_DIMENSION:
        raise ValidationError(
            f"{field_name} must be at least {MIN_DIMENSION}."
        )

    return result


# ============================================================
# POSITIVE INTEGER
# ============================================================

def positive_integer(value, field_name="Value", maximum=None):
    """Validate a positive whole number."""

    if isinstance(value, bool) or value is None:
        raise ValidationError(
            f"{field_name} must be a valid whole number."
        )

    try:
        number = Decimal(str(value).strip())

        if not number.is_finite():
            raise InvalidOperation

        if number != number.to_integral_value():
            raise ValueError

        result = int(number)

    except (
        InvalidOperation,
        TypeError,
        ValueError,
        OverflowError,
    ):
        raise ValidationError(
            f"{field_name} must be a valid whole number."
        )

    if result < 1:
        raise ValidationError(
            f"{field_name} must be greater than zero."
        )

    if maximum is not None and result > maximum:
        raise ValidationError(
            f"{field_name} cannot exceed {maximum}."
        )

    return result


# ============================================================
# FLOOR VALIDATION
# ============================================================

def validate_floor(floor):
    """Validate a Floor model instance."""

    if not isinstance(floor, Floor):
        raise ValidationError("A valid floor is required.")

    return floor


def validate_building(building):
    """Validate a Building model instance."""

    if not isinstance(building, Building):
        raise ValidationError("A valid building is required.")

    return building


def validate_floor_dimensions(floor):
    """Validate independently configurable floor dimensions."""

    validate_floor(floor)

    return {
        "width": positive_decimal(
            floor.width,
            "Floor width",
        ),
        "height": positive_decimal(
            floor.height,
            "Floor height",
        ),
    }


# ============================================================
# FIXTURE TYPE
# ============================================================

def validate_fixture_type(fixture_type):
    """Validate the fixture type against model choices."""

    if not isinstance(fixture_type, str):
        raise ValidationError("Invalid fixture type.")

    valid_types = {
        value
        for value, label in Fixture.FIXTURE_TYPES
    }

    fixture_type = fixture_type.strip()

    if fixture_type not in valid_types:
        raise ValidationError("Invalid fixture type.")

    return fixture_type


# ============================================================
# FIXTURE NAME
# ============================================================

def validate_fixture_name(name):
    """Validate and normalize a fixture name."""

    if not isinstance(name, str):
        raise ValidationError("Fixture name must be text.")

    name = name.strip()

    if not name:
        raise ValidationError("Fixture name cannot be empty.")

    if len(name) > MAX_FIXTURE_NAME_LENGTH:
        raise ValidationError(
            f"Fixture name cannot exceed "
            f"{MAX_FIXTURE_NAME_LENGTH} characters."
        )

    return name


# ============================================================
# FIXTURE COLOR
# ============================================================

def validate_fixture_color(color):
    """Validate a hexadecimal fixture color."""

    if not isinstance(color, str):
        raise ValidationError("Fixture color must be text.")

    color = color.strip()

    if not color:
        raise ValidationError("Fixture color cannot be empty.")

    if len(color) > MAX_COLOR_LENGTH:
        raise ValidationError("Fixture color is too long.")

    if not color.startswith("#") or len(color) not in (4, 7):
        raise ValidationError(
            "Fixture color must be a hexadecimal color."
        )

    try:
        int(color[1:], 16)
    except ValueError:
        raise ValidationError(
            "Invalid hexadecimal fixture color."
        )

    return color.upper()


# ============================================================
# COMPLETE FIXTURE DATA
# ============================================================

def validate_fixture_data(data):
    """Validate fixture creation or complete update data."""

    if not isinstance(data, dict):
        raise ValidationError("Invalid fixture data.")

    allowed_fields = {
        "name",
        "fixture_type",
        "x",
        "y",
        "width",
        "depth",
        "color",
    }

    if not all(isinstance(key, str) for key in data):
        raise ValidationError("Fixture field names must be text.")

    unexpected = set(data) - allowed_fields

    if unexpected:
        raise ValidationError(
            f"Unsupported fixture fields: "
            f"{', '.join(sorted(unexpected))}."
        )

    return {
        "name": validate_fixture_name(
            data.get("name", "New Fixture")
        ),
        "fixture_type": validate_fixture_type(
            data.get("fixture_type", "shelf")
        ),
        "x": nonnegative_decimal(
            data.get("x", 10),
            "X coordinate",
        ),
        "y": nonnegative_decimal(
            data.get("y", 10),
            "Y coordinate",
        ),
        "width": positive_decimal(
            data.get("width", 1.2),
            "Fixture width",
        ),
        "depth": positive_decimal(
            data.get("depth", 0.8),
            "Fixture depth",
        ),
        "color": validate_fixture_color(
            data.get("color", "#2563EB")
        ),
    }


# ============================================================
# FIXTURE POSITION
# ============================================================

def validate_fixture_position(
    floor,
    x,
    y,
    width,
    depth,
):
    """Ensure a fixture fits within floor boundaries."""

    validate_floor(floor)

    x = nonnegative_decimal(x, "X coordinate")
    y = nonnegative_decimal(y, "Y coordinate")

    width = positive_decimal(
        width,
        "Fixture width",
    )

    depth = positive_decimal(
        depth,
        "Fixture depth",
    )

    dimensions = validate_floor_dimensions(floor)

    if x + width > dimensions["width"]:
        raise ValidationError(
            "Fixture extends beyond the right floor boundary."
        )

    if y + depth > dimensions["height"]:
        raise ValidationError(
            "Fixture extends beyond the bottom floor boundary."
        )

    return {
        "x": x,
        "y": y,
        "width": width,
        "depth": depth,
    }


# ============================================================
# SALES ROOM CONTAINMENT
# ============================================================

def validate_fixture_room(
    floor,
    x,
    y,
    width,
    depth,
):
    """
    Ensure the entire fixture is inside one sales room.

    Fixtures cannot be placed in storage, corridors,
    entrances or other non-sales rooms.
    """

    validate_floor(floor)

    x = nonnegative_decimal(x, "X coordinate")
    y = nonnegative_decimal(y, "Y coordinate")

    width = positive_decimal(
        width,
        "Fixture width",
    )

    depth = positive_decimal(
        depth,
        "Fixture depth",
    )

    sales_rooms = Room.objects.filter(
        floor=floor,
        room_type="sales",
    ).order_by("id")

    if not sales_rooms.exists():
        raise ValidationError(
            "This floor has no merchandise sales room."
        )

    for room in sales_rooms:
        room_x = nonnegative_decimal(
            room.x,
            "Room X coordinate",
        )

        room_y = nonnegative_decimal(
            room.y,
            "Room Y coordinate",
        )

        room_width = positive_decimal(
            room.width,
            "Room width",
        )

        room_height = positive_decimal(
            room.height,
            "Room height",
        )

        # Reject invalid room geometry.
        if (
            room_x + room_width > Decimal(str(floor.width))
            or room_y + room_height > Decimal(str(floor.height))
        ):
            raise ValidationError(
                f'Room "{room.name}" has invalid floor geometry.'
            )

        inside = (
            x >= room_x
            and y >= room_y
            and x + width <= room_x + room_width
            and y + depth <= room_y + room_height
        )

        if inside:
            return room

    raise ValidationError(
        "Fixtures must be completely contained within "
        "a merchandise sales room."
    )


# ============================================================
# FIXTURE OVERLAP
# ============================================================

def validate_fixture_overlap(
    floor,
    x,
    y,
    width,
    depth,
    exclude_fixture_id=None,
):
    """
    Prevent overlapping fixtures on the same floor.

    Touching edges are permitted.
    """

    validate_floor(floor)

    x = nonnegative_decimal(x, "X coordinate")
    y = nonnegative_decimal(y, "Y coordinate")

    width = positive_decimal(
        width,
        "Fixture width",
    )

    depth = positive_decimal(
        depth,
        "Fixture depth",
    )

    fixtures = Fixture.objects.filter(
        floor=floor
    ).order_by("id")

    if exclude_fixture_id is not None:
        exclude_fixture_id = positive_integer(
            exclude_fixture_id,
            "Fixture ID",
        )

        fixtures = fixtures.exclude(
            pk=exclude_fixture_id
        )

    for fixture in fixtures:
        existing_x = Decimal(str(fixture.x))
        existing_y = Decimal(str(fixture.y))

        existing_width = Decimal(str(fixture.width))
        existing_depth = Decimal(str(fixture.depth))

        separated = (
            x + width <= existing_x
            or existing_x + existing_width <= x
            or y + depth <= existing_y
            or existing_y + existing_depth <= y
        )

        if not separated:
            raise ValidationError(
                f"Fixture overlaps with '{fixture.name}'."
            )

    return True


# ============================================================
# COMPLETE FIXTURE PLACEMENT
# ============================================================

def validate_fixture_placement(
    floor,
    x,
    y,
    width,
    depth,
    exclude_fixture_id=None,
):
    """
    Validate floor boundaries, sales room containment
    and fixture overlaps.

    Returns normalized geometry and the containing room.
    """

    position = validate_fixture_position(
        floor,
        x,
        y,
        width,
        depth,
    )

    room = validate_fixture_room(
        floor,
        **position,
    )

    validate_fixture_overlap(
        floor,
        **position,
        exclude_fixture_id=exclude_fixture_id,
    )

    return {
        **position,
        "room": room,
    }


# ============================================================
# PRODUCT VALIDATION
# ============================================================

def validate_product(external_id):
    """Retrieve a product using its DummyJSON external ID."""

    external_id = positive_integer(
        external_id,
        "Product ID",
    )

    try:
        return MerchandiseProduct.objects.get(
            external_id=external_id
        )

    except MerchandiseProduct.DoesNotExist:
        raise ValidationError(
            "Product does not exist in the merchandise catalogue."
        )


# ============================================================
# PLANOGRAM QUANTITY
# ============================================================

def validate_planogram_quantity(quantity):
    """Validate planogram product quantity."""

    return positive_integer(
        quantity,
        "Product quantity",
        maximum=MAX_PRODUCT_QUANTITY,
    )


# ============================================================
# PLANOGRAM FACINGS
# ============================================================

def validate_planogram_facings(facings, quantity):
    """Validate facings against the assigned product quantity."""

    facings = positive_integer(
        facings,
        "Product facings",
        maximum=MAX_PRODUCT_QUANTITY,
    )

    quantity = validate_planogram_quantity(quantity)

    if facings > quantity:
        raise ValidationError(
            "Product facings cannot exceed product quantity."
        )

    return facings


# ============================================================
# PLANOGRAM POSITION
# ============================================================

def validate_planogram_position(position):
    """Validate a non-negative integer product position."""

    if isinstance(position, bool) or position is None:
        raise ValidationError(
            "Invalid product position."
        )

    try:
        number = Decimal(str(position).strip())

        if (
            not number.is_finite()
            or number != number.to_integral_value()
            or number < ZERO
        ):
            raise ValueError

        return int(number)

    except (
        InvalidOperation,
        TypeError,
        ValueError,
        OverflowError,
    ):
        raise ValidationError(
            "Product position must be a non-negative integer."
        )
