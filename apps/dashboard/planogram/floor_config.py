"""
AlwaysSmile Department Store
Unified Seven-Level Building Configuration.

Internal floor numbering:
    1  = Level 1
    2  = Level 2
    3  = Level 3
    4  = Level 4
    0  = Basement 1
    -1 = Basement 2
    -2 = Basement 3
"""
import math

from decimal import Decimal
from django.core.exceptions import ValidationError
# ============================================================
# BUILDING CONFIGURATION
# ============================================================
DEFAULT_BUILDING = {
    "name": "AlwaysSmile Merchandise Centre",
    "width": 50,
    "height": 40,
}
# ============================================================
# FLOOR CONFIGURATION
# ============================================================
FLOORS = [
    # ========================================================
    # LEVEL 1 - MAIN SHOPPING FLOOR
    # ========================================================
    {
        "number": 1,
        "code": "L1",
        "name": "Level 1 - Main Shopping Floor",
        "width": 40,
        "height": 30,
        "description": (
            "Main entrances, customer service, general retail and management."
        ),
        "rooms": [
            {
                "name": "Main Entrance",
                "type": "entrance",
                "x": 0,
                "y": 0,
                "width": 10,
                "height": 5,
            },
            {
                "name": "Customer Entrance Corridor",
                "type": "corridor",
                "x": 10,
                "y": 0,
                "width": 25,
                "height": 5,
            },
            {
                "name": "Service Entrance",
                "type": "service",
                "x": 35,
                "y": 0,
                "width": 5,
                "height": 5,
            },
            {
                "name": "Main Sales Floor",
                "type": "sales",
                "x": 0,
                "y": 5,
                "width": 30,
                "height": 20,
            },
            {
                "name": "Management Office",
                "type": "management",
                "x": 30,
                "y": 5,
                "width": 10,
                "height": 8,
            },
            {
                "name": "Customer Service",
                "type": "service",
                "x": 30,
                "y": 13,
                "width": 10,
                "height": 6,
            },
            {
                "name": "Ground Floor Storage",
                "type": "storage",
                "x": 30,
                "y": 19,
                "width": 10,
                "height": 6,
            },
            {
                "name": "Lower Service Corridor",
                "type": "corridor",
                "x": 0,
                "y": 25,
                "width": 40,
                "height": 5,
            },
        ],
    },
    # ========================================================
    # LEVEL 2 - GENERAL MERCHANDISE
    # ========================================================
    {
        "number": 2,
        "code": "L2",
        "name": "Level 2 - General Merchandise",
        "width": 40,
        "height": 30,
        "description": ("Electronics, toys, sports, books and seasonal merchandise."),
        "rooms": [
            {
                "name": "Electronics Department",
                "type": "sales",
                "x": 0,
                "y": 0,
                "width": 20,
                "height": 14,
            },
            {
                "name": "Toys Department",
                "type": "sales",
                "x": 20,
                "y": 0,
                "width": 20,
                "height": 14,
            },
            {
                "name": "Sports Department",
                "type": "sales",
                "x": 0,
                "y": 14,
                "width": 20,
                "height": 11,
            },
            {
                "name": "Books and Stationery",
                "type": "sales",
                "x": 20,
                "y": 14,
                "width": 20,
                "height": 11,
            },
            {
                "name": "Electronics Storage",
                "type": "storage",
                "x": 0,
                "y": 25,
                "width": 12,
                "height": 5,
            },
            {
                "name": "Seasonal Storage",
                "type": "storage",
                "x": 12,
                "y": 25,
                "width": 12,
                "height": 5,
            },
            {
                "name": "Customer Corridor",
                "type": "corridor",
                "x": 24,
                "y": 25,
                "width": 16,
                "height": 5,
            },
        ],
    },
    # ========================================================
    # LEVEL 3 - FASHION AND PERSONAL CARE
    # ========================================================
    {
        "number": 3,
        "code": "L3",
        "name": "Level 3 - Fashion and Personal Care",
        "width": 40,
        "height": 30,
        "description": ("Clothing, footwear, cosmetics, jewellery and fitting rooms."),
        "rooms": [
            {
                "name": "Women's Fashion",
                "type": "sales",
                "x": 0,
                "y": 0,
                "width": 20,
                "height": 15,
            },
            {
                "name": "Men's Fashion",
                "type": "sales",
                "x": 20,
                "y": 0,
                "width": 20,
                "height": 15,
            },
            {
                "name": "Footwear Department",
                "type": "sales",
                "x": 0,
                "y": 15,
                "width": 12,
                "height": 10,
            },
            {
                "name": "Cosmetics and Jewellery",
                "type": "sales",
                "x": 12,
                "y": 15,
                "width": 16,
                "height": 10,
            },
            {
                "name": "Fitting Rooms",
                "type": "fitting",
                "x": 28,
                "y": 15,
                "width": 12,
                "height": 10,
            },
            {
                "name": "Fashion Storage",
                "type": "storage",
                "x": 0,
                "y": 25,
                "width": 15,
                "height": 5,
            },
            {
                "name": "Customer Corridor",
                "type": "corridor",
                "x": 15,
                "y": 25,
                "width": 25,
                "height": 5,
            },
        ],
    },
    # ========================================================
    # LEVEL 4 - HOME AND APARTMENT CONNECTION
    # ========================================================
    {
        "number": 4,
        "code": "L4",
        "name": "Level 4 - Home and Apartment Connection",
        "width": 40,
        "height": 30,
        "description": (
            "Furniture, homeware, household merchandise and secure residential access."
        ),
        "rooms": [
            {
                "name": "Furniture Showroom",
                "type": "sales",
                "x": 0,
                "y": 0,
                "width": 25,
                "height": 18,
            },
            {
                "name": "Homeware Department",
                "type": "sales",
                "x": 25,
                "y": 0,
                "width": 15,
                "height": 18,
            },
            {
                "name": "Household Display Area",
                "type": "sales",
                "x": 0,
                "y": 18,
                "width": 15,
                "height": 7,
            },
            {
                "name": "Furniture Storage",
                "type": "storage",
                "x": 15,
                "y": 18,
                "width": 10,
                "height": 7,
            },
            {
                "name": "Secure Apartment Access Lobby",
                "type": "service",
                "x": 25,
                "y": 18,
                "width": 15,
                "height": 7,
            },
            {
                "name": "Customer Corridor",
                "type": "corridor",
                "x": 0,
                "y": 25,
                "width": 40,
                "height": 5,
            },
        ],
    },
    # ========================================================
    # BASEMENT 1 - LOWER-LEVEL DEPARTMENT STORE
    # ========================================================
    {
        "number": 0,
        "code": "B1",
        "name": "Basement 1 - Lower-Level Department Store",
        "width": 40,
        "height": 30,
        "description": ("Household essentials, bulk goods, discounts and clearance."),
        "rooms": [
            {
                "name": "Household Essentials",
                "type": "sales",
                "x": 0,
                "y": 0,
                "width": 20,
                "height": 15,
            },
            {
                "name": "Bulk Goods Department",
                "type": "sales",
                "x": 20,
                "y": 0,
                "width": 20,
                "height": 15,
            },
            {
                "name": "Discount Merchandise",
                "type": "sales",
                "x": 0,
                "y": 15,
                "width": 20,
                "height": 10,
            },
            {
                "name": "Clearance Department",
                "type": "sales",
                "x": 20,
                "y": 15,
                "width": 20,
                "height": 10,
            },
            {
                "name": "Bulk Storage",
                "type": "storage",
                "x": 0,
                "y": 25,
                "width": 15,
                "height": 5,
            },
            {
                "name": "Customer Corridor",
                "type": "corridor",
                "x": 15,
                "y": 25,
                "width": 25,
                "height": 5,
            },
        ],
    },
    # ========================================================
    # BASEMENT 2 - OPERATIONS AND SUPPORTING FACILITIES
    # ========================================================
    {
        "number": -1,
        "code": "B2",
        "name": "Basement 2 - Operations and Supporting Facilities",
        "width": 45,
        "height": 35,
        "description": (
            "Receiving, inspection, dispatch, maintenance and staff facilities."
        ),
        "rooms": [
            {
                "name": "Goods Receiving",
                "type": "service",
                "x": 0,
                "y": 0,
                "width": 15,
                "height": 15,
            },
            {
                "name": "Merchandise Inspection",
                "type": "service",
                "x": 15,
                "y": 0,
                "width": 15,
                "height": 15,
            },
            {
                "name": "Dispatch Preparation",
                "type": "service",
                "x": 30,
                "y": 0,
                "width": 15,
                "height": 15,
            },
            {
                "name": "Operations Storage",
                "type": "storage",
                "x": 0,
                "y": 15,
                "width": 15,
                "height": 10,
            },
            {
                "name": "Maintenance Workshop",
                "type": "service",
                "x": 15,
                "y": 15,
                "width": 15,
                "height": 10,
            },
            {
                "name": "Staff Mess Hall",
                "type": "mess",
                "x": 30,
                "y": 15,
                "width": 15,
                "height": 10,
            },
            {
                "name": "Staff Lounge",
                "type": "lounge",
                "x": 0,
                "y": 25,
                "width": 10,
                "height": 10,
            },
            {
                "name": "Management Office",
                "type": "management",
                "x": 10,
                "y": 25,
                "width": 10,
                "height": 10,
            },
            {
                "name": "Goods Movement Corridor",
                "type": "corridor",
                "x": 20,
                "y": 25,
                "width": 25,
                "height": 10,
            },
        ],
    },
    # ========================================================
    # BASEMENT 3 - CENTRAL MERCHANDISE WAREHOUSE
    # ========================================================
    {
        "number": -2,
        "code": "B3",
        "name": "Basement 3 - Central Merchandise Warehouse",
        "width": 50,
        "height": 40,
        "description": (
            "Central warehouse, inventory zones and merchandise distribution."
        ),
        "rooms": [
            {
                "name": "Receiving and Unloading",
                "type": "service",
                "x": 0,
                "y": 0,
                "width": 15,
                "height": 12,
            },
            {
                "name": "General Merchandise Warehouse",
                "type": "storage",
                "x": 15,
                "y": 0,
                "width": 20,
                "height": 20,
            },
            {
                "name": "Electronics Inventory",
                "type": "storage",
                "x": 35,
                "y": 0,
                "width": 15,
                "height": 12,
            },
            {
                "name": "Fashion Inventory",
                "type": "storage",
                "x": 0,
                "y": 12,
                "width": 15,
                "height": 13,
            },
            {
                "name": "Household Inventory",
                "type": "storage",
                "x": 35,
                "y": 12,
                "width": 15,
                "height": 13,
            },
            {
                "name": "Bulk Merchandise Storage",
                "type": "storage",
                "x": 0,
                "y": 25,
                "width": 20,
                "height": 10,
            },
            {
                "name": "Picking and Distribution",
                "type": "service",
                "x": 20,
                "y": 20,
                "width": 15,
                "height": 15,
            },
            {
                "name": "Dispatch and Goods Elevator",
                "type": "service",
                "x": 35,
                "y": 25,
                "width": 15,
                "height": 10,
            },
            {
                "name": "Warehouse Operations Corridor",
                "type": "corridor",
                "x": 0,
                "y": 35,
                "width": 50,
                "height": 5,
            },
        ],
    },
]


# ============================================================
# VALID CONFIGURATION CONSTANTS
# ============================================================

VALID_FLOOR_NUMBERS = {1, 2, 3, 4, 0, -1, -2}


EXPECTED_FLOOR_CODES = {
    1: "L1",
    2: "L2",
    3: "L3",
    4: "L4",
    0: "B1",
    -1: "B2",
    -2: "B3",
}


VALID_ROOM_TYPES = {
    "sales",
    "storage",
    "fitting",
    "management",
    "mess",
    "lounge",
    "corridor",
    "entrance",
    "service",
}


# ============================================================
# BASIC VALIDATION HELPERS
# ============================================================


def validate_positive_dimension(value, field_name):
    """Validate a finite positive dimension."""

    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a positive number.")

    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{field_name} must be a positive number.")

    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{field_name} must be a positive finite number.")

    return number


def validate_positive_coordinate(value, field_name):
    """Validate a finite non-negative coordinate."""

    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a non-negative number.")

    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{field_name} must be a non-negative number.")

    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{field_name} must be a non-negative finite number.")

    return number


# ============================================================
# FLOOR NUMBER VALIDATION
# ============================================================


def validate_floor_number(floor_number):
    """Validate and normalize an internal floor number."""

    if isinstance(floor_number, bool):
        raise ValueError("Invalid floor number.")

    if isinstance(floor_number, int):
        number = floor_number

    elif isinstance(floor_number, str):
        normalized = floor_number.strip()

        try:
            number = int(normalized)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("Invalid floor number.")

        if str(number) != normalized:
            raise ValueError("Invalid floor number.")

    else:
        raise ValueError("Invalid floor number.")

    if number not in VALID_FLOOR_NUMBERS:
        raise ValueError("Floor number must be one of -2, -1, 0, 1, 2, 3 or 4.")

    return number


# ============================================================
# ROOM OVERLAP VALIDATION
# ============================================================


def validate_room_overlap(floor_code, rooms):
    """
    Detect overlapping room interiors on one floor.

    Touching edges and boundaries are permitted.

    An overlap occurs only when the interiors of two
    rectangular rooms intersect with positive area.
    """

    if not isinstance(rooms, list):
        raise ValueError(f"Rooms on floor {floor_code} must be a list.")

    for index, room_a in enumerate(rooms):
        ax = float(room_a["x"])
        ay = float(room_a["y"])
        aw = float(room_a["width"])
        ah = float(room_a["height"])

        for room_b in rooms[index + 1 :]:
            bx = float(room_b["x"])
            by = float(room_b["y"])
            bw = float(room_b["width"])
            bh = float(room_b["height"])

            overlaps = ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by

            if overlaps:
                raise ValueError(
                    f'Room "{room_a["name"]}" overlaps with '
                    f'"{room_b["name"]}" on floor {floor_code}.'
                )

    return True


# ============================================================
# AUTHORITATIVE CONFIGURATION VALIDATION
# ============================================================


def validate_configuration():
    """
    Validate the complete master building configuration.

    Checks:
        1. Building configuration.
        2. Building dimensions.
        3. Exactly seven physical floors.
        4. Unique floor numbers.
        5. Unique floor codes.
        6. Correct floor number-to-code mapping.
        7. Positive floor dimensions.
        8. Valid room names and room types.
        9. Positive room dimensions.
       10. Non-negative room coordinates.
       11. Room boundaries against individual floor dimensions.
       12. Room-to-room interior overlap prevention.

    This function validates DEFAULT_BUILDING and FLOORS directly.
    """

    # --------------------------------------------------------
    # Validate building
    # --------------------------------------------------------

    if not isinstance(DEFAULT_BUILDING, dict):
        raise ValueError("Building configuration must be a dictionary.")

    if not isinstance(DEFAULT_BUILDING.get("name"), str):
        raise ValueError("Building name must be a string.")

    if not DEFAULT_BUILDING["name"].strip():
        raise ValueError("Building name cannot be empty.")

    validate_positive_dimension(
        DEFAULT_BUILDING.get("width"),
        "Building width",
    )

    validate_positive_dimension(
        DEFAULT_BUILDING.get("height"),
        "Building height",
    )

    # --------------------------------------------------------
    # Validate floor collection
    # --------------------------------------------------------

    if not isinstance(FLOORS, list):
        raise ValueError("FLOORS must be a list.")

    if len(FLOORS) != 7:
        raise ValueError("The building must contain exactly seven floors.")

    numbers = []
    codes = []

    for floor in FLOORS:
        if not isinstance(floor, dict):
            raise ValueError("Every floor configuration must be a dictionary.")

        number = floor.get("number")
        code = floor.get("code")

        if isinstance(number, bool) or not isinstance(number, int):
            raise ValueError(f"Invalid internal floor number: {number!r}.")

        if number not in VALID_FLOOR_NUMBERS:
            raise ValueError(f"Invalid physical floor number: {number!r}.")

        if not isinstance(code, str) or not code.strip():
            raise ValueError("Every floor must have a valid floor code.")

        code = code.strip()

        numbers.append(number)
        codes.append(code)

    # --------------------------------------------------------
    # Validate uniqueness
    # --------------------------------------------------------

    if len(set(numbers)) != 7:
        raise ValueError("Duplicate floor numbers detected.")

    if len(set(codes)) != 7:
        raise ValueError("Duplicate floor codes detected.")

    if set(numbers) != VALID_FLOOR_NUMBERS:
        raise ValueError(
            "The configuration must contain floor numbers -2, -1, 0, 1, 2, 3 and 4."
        )

    # --------------------------------------------------------
    # Validate floor number-to-code correspondence
    # --------------------------------------------------------

    for floor in FLOORS:
        expected_code = EXPECTED_FLOOR_CODES[floor["number"]]

        if floor["code"] != expected_code:
            raise ValueError(
                f"Floor number {floor['number']} must use floor code {expected_code}."
            )

        if not isinstance(floor.get("name"), str):
            raise ValueError(f"{floor['code']} must have a valid name.")

        if not floor["name"].strip():
            raise ValueError(f"{floor['code']} cannot have an empty name.")

        # ----------------------------------------------------
        # Validate independent floor dimensions
        # ----------------------------------------------------

        floor_width = validate_positive_dimension(
            floor.get("width"),
            f"{floor['code']} width",
        )

        floor_height = validate_positive_dimension(
            floor.get("height"),
            f"{floor['code']} height",
        )

        # ----------------------------------------------------
        # Validate room collection
        # ----------------------------------------------------

        rooms = floor.get("rooms")

        if not isinstance(rooms, list):
            raise ValueError(f"{floor['code']} rooms must be a list.")

        # ----------------------------------------------------
        # Validate individual rooms
        # ----------------------------------------------------

        for room in rooms:
            if not isinstance(room, dict):
                raise ValueError(f"Invalid room definition on {floor['code']}.")

            room_name = room.get("name")

            if not isinstance(room_name, str):
                raise ValueError(f"A room on {floor['code']} must have a name.")

            if not room_name.strip():
                raise ValueError(f"A room on {floor['code']} has an empty name.")

            room_type = room.get("type")

            if not isinstance(room_type, str) or room_type not in VALID_ROOM_TYPES:
                raise ValueError(
                    f"Invalid room type in {floor['code']}: {room_type!r}."
                )

            # Room coordinates

            x = validate_positive_coordinate(
                room.get("x"),
                f"{room_name} X coordinate",
            )

            y = validate_positive_coordinate(
                room.get("y"),
                f"{room_name} Y coordinate",
            )

            # Room dimensions

            width = validate_positive_dimension(
                room.get("width"),
                f"{room_name} width",
            )

            height = validate_positive_dimension(
                room.get("height"),
                f"{room_name} height",
            )

            # ------------------------------------------------
            # Validate room boundaries
            # ------------------------------------------------

            if x + width > floor_width:
                raise ValueError(f'Room "{room_name}" exceeds {floor["code"]} width.')

            if y + height > floor_height:
                raise ValueError(f'Room "{room_name}" exceeds {floor["code"]} height.')

        # ----------------------------------------------------
        # Validate room-to-room overlaps
        # ----------------------------------------------------

        validate_room_overlap(
            floor["code"],
            rooms,
        )

    return True


# ============================================================
# FLOOR LOOKUP INDEXES
# ============================================================

FLOOR_BY_NUMBER = {floor["number"]: floor for floor in FLOORS}

FLOOR_BY_CODE = {floor["code"]: floor for floor in FLOORS}


# ============================================================
# FLOOR CODE VALIDATION
# ============================================================


def validate_floor_code(floor_code):
    """Validate and normalize a physical floor code."""

    if not isinstance(floor_code, str):
        raise ValueError("A valid floor code is required.")

    code = floor_code.strip().upper()

    if code not in FLOOR_BY_CODE:
        raise ValueError("Unknown floor code.")

    return code

def build_floor_config(floor):
    """
    Build an independent floor configuration.

    Creates new dictionaries and lists so changes to returned
    configurations cannot modify the master configuration.
    """

    return {
        "number": floor["number"],
        "code": floor["code"],
        "name": floor["name"],
        "width": floor["width"],
        "height": floor["height"],
        "description": floor["description"],
        "rooms": [
            {
                "name": room["name"],
                "type": room["type"],
                "x": room["x"],
                "y": room["y"],
                "width": room["width"],
                "height": room["height"],
            }
            for room in floor["rooms"]
        ],
    }

# ============================================================
# FLOOR LOOKUP HELPERS
# ============================================================

def get_floor_config(floor_number):
    """
    Retrieve a floor using its internal floor number.

    Returns an independent configuration.
    """

    number = validate_floor_number(floor_number)

    return build_floor_config(
        FLOOR_BY_NUMBER[number]
    )


def get_floor_config_by_code(floor_code):
    """
    Retrieve a floor using its architectural code.

    Returns an independent configuration.
    """

    code = validate_floor_code(floor_code)

    return build_floor_config(
        FLOOR_BY_CODE[code]
    )


def get_all_floor_configs():
    """
    Return independent configurations of all seven floors.
    """

    return [
        build_floor_config(floor)
        for floor in FLOORS
    ]


def get_floor_dimensions(floor_number):
    """
    Return the independently configured dimensions of a floor.
    """

    floor = FLOOR_BY_NUMBER[
        validate_floor_number(floor_number)
    ]

    return {
        "width": floor["width"],
        "height": floor["height"],
    }


def get_floor_codes():
    """Return all physical floor codes."""

    return list(FLOOR_BY_CODE.keys())


def get_floor_numbers():
    """Return all internal floor numbers in architectural order."""

    return [
        floor["number"]
        for floor in FLOORS
    ]


def get_floor_code(floor_number):
    """Convert an internal floor number into its physical code."""

    number = validate_floor_number(floor_number)

    return FLOOR_BY_NUMBER[number]["code"]


def get_floor_number(floor_code):
    """Convert a physical floor code into its internal number."""

    code = validate_floor_code(floor_code)

    return FLOOR_BY_CODE[code]["number"]

# ============================================================
# MASTER CONFIGURATION VALIDATION
# ============================================================

# Validate the complete master configuration exactly once
# when this module is imported.

validate_configuration()

