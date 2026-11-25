from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.dashboard.models import (
    Building,
    Fixture,
    Floor,
    Room,
)

from apps.dashboard.planogram.floor_config import (
    DEFAULT_BUILDING,
    FLOOR_BY_NUMBER,
)

from apps.dashboard.planogram.floor_generator import (
    ARCHITECTURAL_ORDER,
    ROOM_COLORS,
    architectural_floor_order,
    decimal_value,
    generate_floor_rooms,
    get_all_floors,
    get_floor,
    get_floor_rooms,
    initialize_building,
    initialize_floor,
    room_color,
    serialize_building,
    serialize_floor,
    serialize_room,
    validate_coordinate,
    validate_existing_fixtures,
    validate_floor_resize,
    validate_positive_dimension,
    validate_room_collection,
    validate_room_data,
    validate_update_flag,
    rooms_overlap,
)


class FloorGeneratorTests(TestCase):

    def setUp(self):
        self.floor_data = FLOOR_BY_NUMBER[1]

        self.building = Building.objects.create(
            name="AlwaysSmile",
            width=DEFAULT_BUILDING["width"],
            height=DEFAULT_BUILDING["height"],
        )

        self.floor = Floor.objects.create(
            building=self.building,
            number=1,
            name=self.floor_data["name"],
            width=self.floor_data["width"],
            height=self.floor_data["height"],
        )

    # ========================================================
    # DECIMAL CONVERSION
    # ========================================================

    def test_decimal_value_accepts_integer(self):
        result = decimal_value(10, "Value")

        self.assertEqual(result, Decimal("10.00"))

    def test_decimal_value_accepts_float(self):
        result = decimal_value(10.25, "Value")

        self.assertEqual(result, Decimal("10.25"))

    def test_decimal_value_accepts_decimal(self):
        result = decimal_value(
            Decimal("15.50"),
            "Value",
        )

        self.assertEqual(result, Decimal("15.50"))

    def test_decimal_value_rounds_half_up(self):
        result = decimal_value("10.125", "Value")

        self.assertEqual(result, Decimal("10.13"))

    def test_decimal_value_rejects_none(self):
        with self.assertRaises(ValidationError):
            decimal_value(None, "Value")

    def test_decimal_value_rejects_boolean(self):
        with self.assertRaises(ValidationError):
            decimal_value(True, "Value")

    def test_decimal_value_rejects_invalid_string(self):
        with self.assertRaises(ValidationError):
            decimal_value("invalid", "Value")

    def test_decimal_value_rejects_infinity(self):
        with self.assertRaises(ValidationError):
            decimal_value("Infinity", "Value")

    def test_decimal_value_rejects_nan(self):
        with self.assertRaises(ValidationError):
            decimal_value("NaN", "Value")

    # ========================================================
    # DIMENSION VALIDATION
    # ========================================================

    def test_positive_dimension_accepts_valid_value(self):
        result = validate_positive_dimension(
            "10.50",
            "Width",
        )

        self.assertEqual(result, Decimal("10.50"))

    def test_positive_dimension_rejects_zero(self):
        with self.assertRaises(ValidationError):
            validate_positive_dimension(0, "Width")

    def test_positive_dimension_rejects_negative_value(self):
        with self.assertRaises(ValidationError):
            validate_positive_dimension(-5, "Width")

    def test_coordinate_accepts_zero(self):
        result = validate_coordinate(0, "X coordinate")

        self.assertEqual(result, Decimal("0.00"))

    def test_coordinate_accepts_positive_value(self):
        result = validate_coordinate(
            "15.25",
            "X coordinate",
        )

        self.assertEqual(result, Decimal("15.25"))

    def test_coordinate_rejects_negative_value(self):
        with self.assertRaises(ValidationError):
            validate_coordinate(-1, "X coordinate")

    # ========================================================
    # UPDATE FLAG
    # ========================================================

    def test_update_flag_accepts_true(self):
        self.assertIsNone(validate_update_flag(True))

    def test_update_flag_accepts_false(self):
        self.assertIsNone(validate_update_flag(False))

    def test_update_flag_rejects_string(self):
        with self.assertRaises(ValidationError):
            validate_update_flag("True")

    def test_update_flag_rejects_integer(self):
        with self.assertRaises(ValidationError):
            validate_update_flag(1)

    # ========================================================
    # ROOM COLORS
    # ========================================================

    def test_room_color_returns_configured_sales_color(self):
        self.assertEqual(
            room_color("sales"),
            ROOM_COLORS["sales"],
        )

    def test_room_color_returns_configured_storage_color(self):
        self.assertEqual(
            room_color("storage"),
            ROOM_COLORS["storage"],
        )

    def test_room_color_returns_default_for_unknown_type(self):
        self.assertEqual(
            room_color("unknown"),
            "#E5E7EB",
        )

    # ========================================================
    # ARCHITECTURAL FLOOR ORDER
    # ========================================================

    def test_architectural_order_contains_seven_floors(self):
        self.assertEqual(
            ARCHITECTURAL_ORDER,
            [1, 2, 3, 4, 0, -1, -2],
        )

    def test_architectural_floor_order(self):
        from apps.dashboard.planogram.floor_generator import (
            architectural_floor_order,
        )

        expected_order = [1, 2, 3, 4, 0, -1, -2]

        for number in expected_order:
            Floor.objects.get_or_create(
                building=self.building,
                number=number,
                defaults={
                    "name": f"Floor {number}",
                    "width": 40,
                    "height": 30,
                },
            )

        floors = architectural_floor_order(
            Floor.objects.filter(building=self.building)
        )

        actual_order = [
            floor.number
            for floor in floors
        ]

        self.assertEqual(actual_order, expected_order)

    # ========================================================
    # ROOM DATA VALIDATION
    # ========================================================

    def test_validate_room_data_accepts_valid_configuration(self):
        room_data = self.floor_data["rooms"][0]

        result = validate_room_data(
            room_data,
            self.floor,
        )

        self.assertEqual(
            result["name"],
            room_data["name"],
        )

        self.assertEqual(
            result["room_type"],
            room_data["type"],
        )

        self.assertEqual(
            result["color"],
            ROOM_COLORS[room_data["type"]],
        )

    def test_validate_room_data_normalizes_room_name(self):
        room_data = {
            "name": "  Test Room  ",
            "type": "sales",
            "x": 0,
            "y": 0,
            "width": 5,
            "height": 5,
        }

        result = validate_room_data(
            room_data,
            self.floor,
        )

        self.assertEqual(
            result["name"],
            "Test Room",
        )

    def test_validate_room_data_rejects_non_dictionary(self):
        with self.assertRaises(ValidationError):
            validate_room_data(
                [],
                self.floor,
            )

    def test_validate_room_data_rejects_invalid_floor(self):
        with self.assertRaises(ValidationError):
            validate_room_data(
                self.floor_data["rooms"][0],
                self.building,
            )

    def test_validate_room_data_rejects_missing_fields(self):
        with self.assertRaises(ValidationError):
            validate_room_data(
                {"name": "Test Room"},
                self.floor,
            )

    def test_validate_room_data_rejects_empty_name(self):
        room_data = {
            "name": " ",
            "type": "sales",
            "x": 0,
            "y": 0,
            "width": 5,
            "height": 5,
        }

        with self.assertRaises(ValidationError):
            validate_room_data(
                room_data,
                self.floor,
            )

    def test_validate_room_data_rejects_invalid_room_type(self):
        room_data = {
            "name": "Test Room",
            "type": "invalid",
            "x": 0,
            "y": 0,
            "width": 5,
            "height": 5,
        }

        with self.assertRaises(ValidationError):
            validate_room_data(
                room_data,
                self.floor,
            )

    def test_validate_room_data_rejects_negative_coordinates(self):
        room_data = {
            "name": "Test Room",
            "type": "sales",
            "x": -1,
            "y": 0,
            "width": 5,
            "height": 5,
        }

        with self.assertRaises(ValidationError):
            validate_room_data(
                room_data,
                self.floor,
            )

    def test_validate_room_data_rejects_zero_width(self):
        room_data = {
            "name": "Test Room",
            "type": "sales",
            "x": 0,
            "y": 0,
            "width": 0,
            "height": 5,
        }

        with self.assertRaises(ValidationError):
            validate_room_data(
                room_data,
                self.floor,
            )

    def test_validate_room_data_rejects_floor_width_exceedance(self):
        room_data = {
            "name": "Oversized Room",
            "type": "sales",
            "x": 0,
            "y": 0,
            "width": self.floor.width + 1,
            "height": 5,
        }

        with self.assertRaises(ValidationError):
            validate_room_data(
                room_data,
                self.floor,
            )

    def test_validate_room_data_rejects_floor_height_exceedance(self):
        room_data = {
            "name": "Oversized Room",
            "type": "sales",
            "x": 0,
            "y": 0,
            "width": 5,
            "height": self.floor.height + 1,
        }

        with self.assertRaises(ValidationError):
            validate_room_data(
                room_data,
                self.floor,
            )

    # ========================================================
    # ROOM OVERLAP
    # ========================================================

    def test_rooms_overlap_detects_intersection(self):
        room_a = Room(
            floor=self.floor,
            name="Room A",
            room_type="sales",
            x=0,
            y=0,
            width=10,
            height=10,
        )

        room_b = Room(
            floor=self.floor,
            name="Room B",
            room_type="storage",
            x=5,
            y=5,
            width=10,
            height=10,
        )

        self.assertTrue(
            rooms_overlap(room_a, room_b)
        )

    def test_rooms_overlap_allows_separate_rooms(self):
        room_a = Room(
            floor=self.floor,
            name="Room A",
            room_type="sales",
            x=0,
            y=0,
            width=5,
            height=5,
        )

        room_b = Room(
            floor=self.floor,
            name="Room B",
            room_type="storage",
            x=10,
            y=10,
            width=5,
            height=5,
        )

        self.assertFalse(
            rooms_overlap(room_a, room_b)
        )

    def test_rooms_overlap_allows_touching_edges(self):
        room_a = Room(
            floor=self.floor,
            name="Room A",
            room_type="sales",
            x=0,
            y=0,
            width=5,
            height=5,
        )

        room_b = Room(
            floor=self.floor,
            name="Room B",
            room_type="storage",
            x=5,
            y=0,
            width=5,
            height=5,
        )

        self.assertFalse(
            rooms_overlap(room_a, room_b)
        )

    # ========================================================
    # ROOM COLLECTION VALIDATION
    # ========================================================

    def test_validate_room_collection_accepts_valid_rooms(self):
        rooms = [
            Room(
                floor=self.floor,
                name="Room A",
                room_type="sales",
                x=0,
                y=0,
                width=5,
                height=5,
            ),
            Room(
                floor=self.floor,
                name="Room B",
                room_type="storage",
                x=5,
                y=0,
                width=5,
                height=5,
            ),
        ]

        self.assertTrue(
            validate_room_collection(
                self.floor,
                rooms,
            )
        )

    def test_validate_room_collection_rejects_wrong_floor(self):
        other_floor = Floor.objects.create(
            building=self.building,
            number=2,
            name="Level 2",
            width=self.floor.width,
            height=self.floor.height,
        )

        room = Room(
            floor=other_floor,
            name="Wrong Floor Room",
            room_type="sales",
            x=0,
            y=0,
            width=5,
            height=5,
        )

        with self.assertRaises(ValidationError):
            validate_room_collection(
                self.floor,
                [room],
            )

    def test_validate_room_collection_rejects_negative_coordinates(self):
        room = Room(
            floor=self.floor,
            name="Invalid Room",
            room_type="sales",
            x=-1,
            y=0,
            width=5,
            height=5,
        )

        with self.assertRaises(ValidationError):
            validate_room_collection(
                self.floor,
                [room],
            )

    def test_validate_room_collection_rejects_floor_exceedance(self):
        room = Room(
            floor=self.floor,
            name="Oversized Room",
            room_type="sales",
            x=self.floor.width - 2,
            y=0,
            width=5,
            height=5,
        )

        with self.assertRaises(ValidationError):
            validate_room_collection(
                self.floor,
                [room],
            )

    def test_validate_room_collection_rejects_overlapping_rooms(self):
        rooms = [
            Room(
                floor=self.floor,
                name="Room A",
                room_type="sales",
                x=0,
                y=0,
                width=10,
                height=10,
            ),
            Room(
                floor=self.floor,
                name="Room B",
                room_type="storage",
                x=5,
                y=5,
                width=10,
                height=10,
            ),
        ]

        with self.assertRaises(ValidationError):
            validate_room_collection(
                self.floor,
                rooms,
            )

    # ========================================================
    # FIXTURE VALIDATION
    # ========================================================

    def create_fixture(self, **overrides):
        data = {
            "floor": self.floor,
            "name": "Test Fixture",
            "fixture_type": "shelf",
            "x": Decimal("5.00"),
            "y": Decimal("5.00"),
            "width": Decimal("1.00"),
            "depth": Decimal("1.00"),
        }

        data.update(overrides)

        return Fixture.objects.create(**data)

    def test_validate_existing_fixtures_accepts_valid_fixture(self):
        self.create_fixture()

        self.assertTrue(
            validate_existing_fixtures(self.floor)
        )

    def test_validate_existing_fixtures_rejects_negative_coordinates(self):
        fixture = self.create_fixture()

        Fixture.objects.filter(pk=fixture.pk).update(
            x=Decimal("-1.00")
        )

        with self.assertRaises(ValidationError):
            validate_existing_fixtures(self.floor)

    def test_validate_existing_fixtures_rejects_floor_exceedance(self):
        fixture = self.create_fixture()

        Fixture.objects.filter(pk=fixture.pk).update(
            x=Decimal(str(self.floor.width - 1)),
            width=Decimal("5.00"),
        )

        with self.assertRaises(ValidationError):
            validate_existing_fixtures(self.floor)

    def test_validate_existing_fixtures_rejects_invalid_dimensions(self):
        fixture = self.create_fixture()

        Fixture.objects.filter(pk=fixture.pk).update(
            width=Decimal("0.00")
        )

        with self.assertRaises(ValidationError):
            validate_existing_fixtures(self.floor)

    def test_validate_existing_fixtures_accepts_custom_dimensions(self):
        fixture = self.create_fixture()

        self.assertTrue(
            validate_existing_fixtures(
                self.floor,
                width=self.floor.width + 5,
                height=self.floor.height + 5,
            )
        )

    # ========================================================
    # FLOOR RESIZE VALIDATION
    # ========================================================

    def test_validate_floor_resize_accepts_existing_geometry(self):
        self.assertIsNone(
            validate_floor_resize(
                self.floor,
                self.floor.width,
                self.floor.height,
            )
        )

    def test_validate_floor_resize_rejects_room_exceedance(self):
        Room.objects.create(
            floor=self.floor,
            name="Boundary Room",
            room_type="sales",
            x=10,
            y=10,
            width=10,
            height=10,
        )

        with self.assertRaises(ValidationError):
            validate_floor_resize(
                self.floor,
                15,
                15,
            )

    def test_validate_floor_resize_rejects_fixture_exceedance(self):
        self.create_fixture(
            x=Decimal("20.00"),
            y=Decimal("5.00"),
            width=Decimal("5.00"),
        )

        with self.assertRaises(ValidationError):
            validate_floor_resize(
                self.floor,
                22,
                self.floor.height,
            )

    # ========================================================
    # ROOM GENERATION
    # ========================================================

    def test_generate_floor_rooms_creates_configured_rooms(self):
        rooms = generate_floor_rooms(self.floor)

        self.assertEqual(
            len(rooms),
            len(self.floor_data["rooms"]),
        )

        for configured_room in self.floor_data["rooms"]:
            self.assertTrue(
                Room.objects.filter(
                    floor=self.floor,
                    name=configured_room["name"],
                ).exists()
            )

    def test_generate_floor_rooms_returns_saved_rooms(self):
        rooms = generate_floor_rooms(self.floor)

        self.assertTrue(
            all(room.pk is not None for room in rooms)
        )

    def test_generate_floor_rooms_does_not_duplicate_rooms(self):
        generate_floor_rooms(self.floor)

        first_count = Room.objects.filter(
            floor=self.floor
        ).count()

        generate_floor_rooms(self.floor)

        second_count = Room.objects.filter(
            floor=self.floor
        ).count()

        self.assertEqual(first_count, second_count)

    def test_generate_floor_rooms_preserves_existing_configuration(self):
        configured_room = self.floor_data["rooms"][0]

        room = Room.objects.create(
            floor=self.floor,
            name=configured_room["name"],
            room_type=configured_room["type"],
            x=configured_room["x"],
            y=configured_room["y"],
            width=configured_room["width"],
            height=configured_room["height"],
            color="#123456",
        )

        generate_floor_rooms(
            self.floor,
            update_existing=False,
        )

        room.refresh_from_db()

        self.assertEqual(
            room.color,
            "#123456",
        )

    def test_generate_floor_rooms_updates_existing_configuration(self):
        configured_room = self.floor_data["rooms"][0]

        room = Room.objects.create(
            floor=self.floor,
            name=configured_room["name"],
            room_type=configured_room["type"],
            x=configured_room["x"],
            y=configured_room["y"],
            width=configured_room["width"],
            height=configured_room["height"],
            color="#123456",
        )

        generate_floor_rooms(
            self.floor,
            update_existing=True,
        )

        room.refresh_from_db()

        self.assertEqual(
            room.color,
            ROOM_COLORS[configured_room["type"]],
        )

    def test_generate_floor_rooms_rejects_invalid_update_flag(self):
        with self.assertRaises(ValidationError):
            generate_floor_rooms(
                self.floor,
                update_existing="yes",
            )

    def test_generate_floor_rooms_rejects_unknown_floor_number(self):
        self.floor.number = 99

        with self.assertRaises(ValidationError):
            generate_floor_rooms(self.floor)

    # ========================================================
    # BUILDING INITIALIZATION
    # ========================================================

    def test_initialize_building_creates_seven_floors(self):
        building = initialize_building()

        self.assertEqual(
            building.floors.count(),
            7,
        )

    def test_initialize_building_returns_building_instance(self):
        building = initialize_building()

        self.assertIsInstance(
            building,
            Building,
        )

    def test_initialize_building_uses_default_name(self):
        building = initialize_building()

        self.assertEqual(
            building.name,
            DEFAULT_BUILDING["name"],
        )

    def test_initialize_building_creates_configured_floor_numbers(self):
        building = initialize_building()

        actual_numbers = set(
            building.floors.values_list(
                "number",
                flat=True,
            )
        )

        self.assertEqual(
            actual_numbers,
            set(FLOOR_BY_NUMBER.keys()),
        )

    def test_initialize_building_generates_configured_rooms(self):
        building = initialize_building()

        for number, floor_data in FLOOR_BY_NUMBER.items():
            floor = building.floors.get(number=number)

            self.assertEqual(
                floor.rooms.count(),
                len(floor_data["rooms"]),
            )

    def test_initialize_building_is_idempotent(self):
        first = initialize_building()
        second = initialize_building()

        self.assertEqual(first.pk, second.pk)

        self.assertEqual(
            first.floors.count(),
            7,
        )

        self.assertEqual(
            second.floors.count(),
            7,
        )

    def test_initialize_building_rejects_invalid_update_flag(self):
        with self.assertRaises(ValidationError):
            initialize_building(
                update_existing="True",
            )

    # ========================================================
    # INDIVIDUAL FLOOR INITIALIZATION
    # ========================================================

    def test_initialize_floor_returns_floor_instance(self):
        building = initialize_building()

        floor = initialize_floor(
            building,
            1,
        )

        self.assertIsInstance(
            floor,
            Floor,
        )

    def test_initialize_floor_uses_configured_floor_name(self):
        building = initialize_building()

        floor = initialize_floor(
            building,
            1,
        )

        self.assertEqual(
            floor.name,
            FLOOR_BY_NUMBER[1]["name"],
        )

    def test_initialize_floor_generates_configured_rooms(self):
        building = initialize_building()

        floor = initialize_floor(
            building,
            1,
        )

        self.assertEqual(
            floor.rooms.count(),
            len(FLOOR_BY_NUMBER[1]["rooms"]),
        )

    def test_initialize_floor_rejects_invalid_building(self):
        with self.assertRaises(ValidationError):
            initialize_floor(
                self.floor,
                1,
            )

    def test_initialize_floor_rejects_invalid_floor_number(self):
        with self.assertRaises(ValidationError):
            initialize_floor(
                self.building,
                99,
            )

    def test_initialize_floor_rejects_invalid_update_flag(self):
        with self.assertRaises(ValidationError):
            initialize_floor(
                self.building,
                1,
                update_existing="yes",
            )

    # ========================================================
    # FLOOR RETRIEVAL
    # ========================================================

    def test_get_floor_returns_correct_floor(self):
        floor = get_floor(
            self.building,
            1,
        )

        self.assertEqual(
            floor.pk,
            self.floor.pk,
        )

    def test_get_floor_rejects_invalid_building(self):
        with self.assertRaises(ValidationError):
            get_floor(
                self.floor,
                1,
            )

    def test_get_floor_rejects_invalid_number(self):
        with self.assertRaises(ValidationError):
            get_floor(
                self.building,
                99,
            )

    def test_get_all_floors_returns_architectural_order(self):
        for number in ARCHITECTURAL_ORDER:
            if number == 1:
                continue

            data = FLOOR_BY_NUMBER[number]

            Floor.objects.create(
                building=self.building,
                number=number,
                name=data["name"],
                width=data["width"],
                height=data["height"],
            )

        floors = list(
            get_all_floors(self.building)
        )

        self.assertEqual(
            [floor.number for floor in floors],
            ARCHITECTURAL_ORDER,
        )

    def test_get_all_floors_rejects_invalid_building(self):
        with self.assertRaises(ValidationError):
            get_all_floors(self.floor)

    # ========================================================
    # ROOM RETRIEVAL
    # ========================================================

    def test_get_floor_rooms_returns_floor_rooms(self):
        generate_floor_rooms(self.floor)

        rooms = list(
            get_floor_rooms(self.floor)
        )

        self.assertTrue(rooms)

        self.assertTrue(
            all(
                room.floor_id == self.floor.pk
                for room in rooms
            )
        )

    def test_get_floor_rooms_rejects_invalid_floor(self):
        with self.assertRaises(ValidationError):
            get_floor_rooms(self.building)

    # ========================================================
    # ROOM SERIALIZATION
    # ========================================================

    def test_serialize_room_returns_expected_fields(self):
        configured_room = self.floor_data["rooms"][0]

        room = Room.objects.create(
            floor=self.floor,
            name=configured_room["name"],
            room_type=configured_room["type"],
            x=configured_room["x"],
            y=configured_room["y"],
            width=configured_room["width"],
            height=configured_room["height"],
            color=ROOM_COLORS[configured_room["type"]],
        )

        result = serialize_room(room)

        self.assertEqual(result["id"], room.pk)
        self.assertEqual(result["floor_id"], self.floor.pk)
        self.assertEqual(result["name"], room.name)
        self.assertEqual(result["type"], room.room_type)
        self.assertEqual(result["room_type"], room.room_type)
        self.assertEqual(result["color"], room.color)

    def test_serialize_room_returns_numeric_geometry(self):
        configured_room = self.floor_data["rooms"][0]

        room = Room.objects.create(
            floor=self.floor,
            name=configured_room["name"],
            room_type=configured_room["type"],
            x=configured_room["x"],
            y=configured_room["y"],
            width=configured_room["width"],
            height=configured_room["height"],
        )

        result = serialize_room(room)

        self.assertIsInstance(result["x"], float)
        self.assertIsInstance(result["y"], float)
        self.assertIsInstance(result["width"], float)
        self.assertIsInstance(result["height"], float)

    def test_serialize_room_rejects_invalid_instance(self):
        with self.assertRaises(ValidationError):
            serialize_room(self.floor)

    # ========================================================
    # FLOOR SERIALIZATION
    # ========================================================

    def test_serialize_floor_returns_expected_fields(self):
        generate_floor_rooms(self.floor)

        result = serialize_floor(self.floor)

        self.assertEqual(result["id"], self.floor.pk)
        self.assertEqual(result["building_id"], self.building.pk)
        self.assertEqual(result["number"], 1)
        self.assertEqual(result["code"], FLOOR_BY_NUMBER[1]["code"])
        self.assertEqual(result["name"], self.floor.name)

    def test_serialize_floor_includes_all_rooms(self):
        generate_floor_rooms(self.floor)

        result = serialize_floor(self.floor)

        self.assertEqual(
            len(result["rooms"]),
            self.floor.rooms.count(),
        )

    def test_serialize_floor_includes_description(self):
        result = serialize_floor(self.floor)

        self.assertEqual(
            result["description"],
            FLOOR_BY_NUMBER[1].get("description", ""),
        )

    def test_serialize_floor_rejects_invalid_instance(self):
        with self.assertRaises(ValidationError):
            serialize_floor(self.building)

    # ========================================================
    # BUILDING SERIALIZATION
    # ========================================================

    def test_serialize_building_returns_expected_fields(self):
        building = initialize_building()

        result = serialize_building(building)

        self.assertEqual(result["id"], building.pk)
        self.assertEqual(
            result["name"],
            building.name,
        )

        self.assertEqual(
            result["floor_count"],
            7,
        )

    def test_serialize_building_includes_all_floors(self):
        building = initialize_building()

        result = serialize_building(building)

        self.assertEqual(
            len(result["floors"]),
            7,
        )

    def test_serialize_building_preserves_architectural_order(self):
        building = initialize_building()

        result = serialize_building(building)

        self.assertEqual(
            [
                floor["number"]
                for floor in result["floors"]
            ],
            ARCHITECTURAL_ORDER,
        )

    def test_serialize_building_rejects_invalid_instance(self):
        with self.assertRaises(ValidationError):
            serialize_building(self.floor)
