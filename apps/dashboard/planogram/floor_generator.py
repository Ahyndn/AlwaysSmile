from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, IntegerField, When

from apps.dashboard.models import Building, Floor, Room

from . import building as building_service

from .floor_config import (
    DEFAULT_BUILDING,
    FLOORS,
    FLOOR_BY_NUMBER,
    validate_floor_number,
)


ROOM_COLORS = {
    "sales": "#DBEAFE",
    "storage": "#FDE68A",
    "fitting": "#FCE7F3",
    "management": "#EDE9FE",
    "mess": "#D1FAE5",
    "lounge": "#CCFBF1",
    "corridor": "#F3F4F6",
    "entrance": "#BFDBFE",
    "service": "#E5E7EB",
}

CENT = Decimal("0.01")

ARCHITECTURAL_ORDER = [1, 2, 3, 4, 0, -1, -2]


def decimal_value(value, field_name):
    if isinstance(value, bool) or value is None:
        raise ValidationError(
            f"{field_name} must be a valid number."
        )

    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(
            f"{field_name} must be a valid number."
        )

    if not result.is_finite():
        raise ValidationError(
            f"{field_name} must be finite."
        )

    return result.quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def validate_positive_dimension(value, field_name):
    result = decimal_value(value, field_name)

    if result <= 0:
        raise ValidationError(
            f"{field_name} must be greater than zero."
        )

    return result


def validate_coordinate(value, field_name):
    result = decimal_value(value, field_name)

    if result < 0:
        raise ValidationError(
            f"{field_name} cannot be negative."
        )

    return result


def validate_update_flag(update_existing):
    if not isinstance(update_existing, bool):
        raise ValidationError(
            "update_existing must be True or False."
        )


def room_color(room_type):
    return ROOM_COLORS.get(
        room_type,
        "#E5E7EB",
    )


def architectural_floor_order(queryset):
    ordering = Case(
        *[
            When(number=number, then=position)
            for position, number in enumerate(ARCHITECTURAL_ORDER)
        ],
        default=len(ARCHITECTURAL_ORDER),
        output_field=IntegerField(),
    )

    return queryset.order_by(ordering, "id")

def validate_room_data(room_data, floor):
    """Validate configured room data against actual floor dimensions."""

    if not isinstance(room_data, dict):
        raise ValidationError(
            "Room configuration must be a dictionary."
        )

    if not isinstance(floor, Floor):
        raise ValidationError(
            "A valid floor is required."
        )

    required_fields = {
        "name", "type", "x", "y", "width", "height"
    }

    missing = required_fields - set(room_data)

    if missing:
        raise ValidationError(
            f"Missing room fields: {', '.join(sorted(missing))}."
        )

    name = room_data["name"]

    if not isinstance(name, str) or not name.strip():
        raise ValidationError("Room name is required.")

    name = name.strip()
    room_type = room_data["type"]

    allowed_types = {
        choice[0] for choice in Room.ROOM_TYPES
    }

    if room_type not in allowed_types:
        raise ValidationError(
            f"Invalid room type: {room_type}."
        )

    x = validate_coordinate(
        room_data["x"],
        "Room X coordinate",
    )

    y = validate_coordinate(
        room_data["y"],
        "Room Y coordinate",
    )

    width = validate_positive_dimension(
        room_data["width"],
        "Room width",
    )

    height = validate_positive_dimension(
        room_data["height"],
        "Room height",
    )

    floor_width = Decimal(str(floor.width))
    floor_height = Decimal(str(floor.height))

    if x + width > floor_width:
        raise ValidationError(
            f"Room '{name}' exceeds the floor width."
        )

    if y + height > floor_height:
        raise ValidationError(
            f"Room '{name}' exceeds the floor height."
        )

    return {
        "name": name,
        "room_type": room_type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "color": room_color(room_type),
    }


def rooms_overlap(room_a, room_b):
    """Check whether two room interiors overlap."""

    ax = Decimal(str(room_a.x))
    ay = Decimal(str(room_a.y))
    aw = Decimal(str(room_a.width))
    ah = Decimal(str(room_a.height))

    bx = Decimal(str(room_b.x))
    by = Decimal(str(room_b.y))
    bw = Decimal(str(room_b.width))
    bh = Decimal(str(room_b.height))

    return (
        ax < bx + bw
        and ax + aw > bx
        and ay < by + bh
        and ay + ah > by
    )


def validate_room_collection(floor, rooms):
    """Validate room boundaries and overlaps."""

    room_list = list(rooms)

    for room in room_list:
        if room.floor_id != floor.pk:
            raise ValidationError(
                "A room belongs to the wrong floor."
            )

        x = Decimal(str(room.x))
        y = Decimal(str(room.y))
        width = Decimal(str(room.width))
        height = Decimal(str(room.height))

        if (
            x < 0
            or y < 0
            or width <= 0
            or height <= 0
            or x + width > Decimal(str(floor.width))
            or y + height > Decimal(str(floor.height))
        ):
            raise ValidationError(
                f"Room '{room.name}' has invalid geometry "
                f"on floor '{floor.name}'."
            )

    for index, room_a in enumerate(room_list):
        for room_b in room_list[index + 1:]:
            if rooms_overlap(room_a, room_b):
                raise ValidationError(
                    f"Room '{room_a.name}' overlaps with "
                    f"room '{room_b.name}' on floor '{floor.name}'."
                )

    return True

def validate_existing_fixtures(floor, width=None, height=None):
    """Ensure existing fixtures fit inside their floor."""

    floor_width = Decimal(
        str(width if width is not None else floor.width)
    )

    floor_height = Decimal(
        str(height if height is not None else floor.height)
    )

    for fixture in floor.fixtures.select_for_update():

        if fixture.room_id:
            if fixture.room.floor_id != floor.pk:
                raise ValidationError(
                    f"Fixture '{fixture.name}' belongs to an invalid room."
                )

        x = Decimal(str(fixture.x))
        y = Decimal(str(fixture.y))
        fixture_width = Decimal(str(fixture.width))
        fixture_depth = Decimal(str(fixture.depth))

        if (
            x < 0
            or y < 0
            or fixture_width <= 0
            or fixture_depth <= 0
            or x + fixture_width > floor_width
            or y + fixture_depth > floor_height
        ):
            raise ValidationError(
                f"Fixture '{fixture.name}' exceeds floor "
                f"'{floor.name}' boundaries."
            )

    return True


def validate_floor_resize(floor, width, height):
    """Prevent resizing beyond existing room or fixture bounds."""

    width = Decimal(str(width))
    height = Decimal(str(height))

    for room in floor.rooms.select_for_update():
        if (
            Decimal(str(room.x)) + Decimal(str(room.width)) > width
            or Decimal(str(room.y)) + Decimal(str(room.height)) > height
        ):
            raise ValidationError(
                f"Cannot resize '{floor.name}': "
                f"room '{room.name}' would exceed the floor."
            )

    validate_existing_fixtures(
        floor,
        width=width,
        height=height,
    )


def generate_floor_rooms(floor, update_existing=False):
    """Generate configured rooms while preserving custom rooms."""

    validate_update_flag(update_existing)

    floor_data = FLOOR_BY_NUMBER.get(floor.number)

    if floor_data is None:
        raise ValidationError(
            "The floor has no authoritative configuration."
        )

    configured_rooms = [
        validate_room_data(room_data, floor)
        for room_data in floor_data["rooms"]
    ]

    existing_rooms = list(
        Room.objects.select_for_update()
        .filter(floor=floor)
        .order_by("id")
    )

    existing_by_name = {}

    for room in existing_rooms:
        existing_by_name.setdefault(room.name, room)

    configured_names = {
        item["name"] for item in configured_rooms
    }

    custom_rooms = [
        room
        for room in existing_rooms
        if room.name not in configured_names
    ]

    proposed_rooms = []

    for data in configured_rooms:
        existing = existing_by_name.get(data["name"])

        if existing is None:
            proposed = Room(floor=floor, **data)

        elif update_existing:
            proposed = existing

            for field, value in data.items():
                setattr(proposed, field, value)

        else:
            proposed = existing

        proposed_rooms.append(proposed)

    final_rooms = custom_rooms + proposed_rooms

    validate_room_collection(
        floor,
        final_rooms,
    )

    for room in proposed_rooms:
        if room.pk:
            if update_existing:
                room.save(
                    update_fields=[
                        "name",
                        "room_type",
                        "x",
                        "y",
                        "width",
                        "height",
                        "color",
                    ]
                )
        else:
            room.save(force_insert=True)

    return list(
        Room.objects.filter(floor=floor).order_by("id")
    )

@transaction.atomic
def initialize_building(update_existing=False):
    """Initialize the building and generate all seven floors."""

    validate_update_flag(update_existing)

    result = building_service.initialize_building(
        name=DEFAULT_BUILDING["name"],
        building_width=DEFAULT_BUILDING["width"],
        building_height=DEFAULT_BUILDING["height"],
        update_existing=update_existing,
    )

    building = result["building"]

    building = Building.objects.select_for_update().get(
        pk=building.pk
    )

    floors = architectural_floor_order(
        Floor.objects.select_for_update().filter(
            building=building
        )
    )

    for floor in floors:
        floor_data = FLOOR_BY_NUMBER.get(floor.number)

        if floor_data is None:
            raise ValidationError(
                f"Unexpected floor number: {floor.number}."
            )

        if update_existing:
            validate_floor_resize(
                floor,
                floor_data["width"],
                floor_data["height"],
            )

        generate_floor_rooms(
            floor,
            update_existing=update_existing,
        )

        validate_existing_fixtures(floor)

    return building


@transaction.atomic
def initialize_floor(
    building,
    floor_number,
    update_existing=False,
):
    """Initialize one floor and its configured rooms."""

    if not isinstance(building, Building):
        raise ValidationError("A valid building is required.")

    validate_update_flag(update_existing)

    try:
        floor_number = validate_floor_number(floor_number)
    except ValueError as exc:
        raise ValidationError(str(exc))

    floor_data = FLOOR_BY_NUMBER[floor_number]

    floor = building_service.create_floor(
        building=building,
        floor_code=floor_data["code"],
    )

    floor = Floor.objects.select_for_update().get(
        pk=floor.pk
    )

    if update_existing:
        validate_floor_resize(
            floor,
            floor_data["width"],
            floor_data["height"],
        )

        if (
            floor.name != floor_data["name"]
            or floor.width != floor_data["width"]
            or floor.height != floor_data["height"]
        ):
            floor.name = floor_data["name"]
            floor.width = floor_data["width"]
            floor.height = floor_data["height"]

            floor.save(
                update_fields=[
                    "name",
                    "width",
                    "height",
                ]
            )

    generate_floor_rooms(
        floor,
        update_existing=update_existing,
    )

    validate_existing_fixtures(floor)

    return floor


def get_floor(building, floor_number):
    """Retrieve a floor using its internal number."""

    if not isinstance(building, Building):
        raise ValidationError("A valid building is required.")

    try:
        floor_number = validate_floor_number(floor_number)
    except ValueError as exc:
        raise ValidationError(str(exc))

    return building_service.get_floor(
        building,
        floor_number,
    )


def get_all_floors(building):
    """Return all floors in architectural order."""

    if not isinstance(building, Building):
        raise ValidationError("A valid building is required.")

    return architectural_floor_order(
        Floor.objects.filter(building=building)
    )


def get_floor_rooms(floor):
    """Return rooms belonging to a floor."""

    if not isinstance(floor, Floor):
        raise ValidationError("A valid floor is required.")

    return Room.objects.filter(
        floor=floor
    ).order_by("id")


def serialize_room(room):
    """Return JSON-compatible room information."""

    if not isinstance(room, Room):
        raise ValidationError("A valid room is required.")

    return {
        "id": room.id,
        "floor_id": room.floor_id,
        "name": room.name,
        "type": room.room_type,
        "room_type": room.room_type,
        "x": float(room.x),
        "y": float(room.y),
        "width": float(room.width),
        "height": float(room.height),
        "color": room.color,
    }


def serialize_floor(floor):
    """Return floor information and its rooms."""

    if not isinstance(floor, Floor):
        raise ValidationError("A valid floor is required.")

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
        "width": float(floor.width),
        "height": float(floor.height),
        "description": floor_config.get("description", ""),
        "rooms": [
            serialize_room(room)
            for room in get_floor_rooms(floor)
        ],
    }


def serialize_building(building):
    """Return building information and all seven floors."""

    if not isinstance(building, Building):
        raise ValidationError("A valid building is required.")

    floors = get_all_floors(building)

    return {
        "id": building.id,
        "name": building.name,
        "width": float(building.width),
        "height": float(building.height),
        "floor_count": floors.count(),
        "floors": [
            serialize_floor(floor)
            for floor in floors
        ],
    }
