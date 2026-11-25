from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.dashboard.planogram import floor_config


class FloorConfigurationTests(SimpleTestCase):

    def setUp(self):
        self.expected_floors = [
            (1, "L1"),
            (2, "L2"),
            (3, "L3"),
            (4, "L4"),
            (0, "B1"),
            (-1, "B2"),
            (-2, "B3"),
        ]

    def _get_test_floors(self):
        floors = []

        for floor in floor_config.FLOORS:
            item = {key: value for key, value in floor.items() if key != "rooms"}
            item["rooms"] = [dict(room) for room in floor["rooms"]]
            floors.append(item)

        return floors

    # ========================================================
    # BUILDING CONFIGURATION
    # ========================================================

    def test_default_building_configuration(self):
        self.assertEqual(
            floor_config.DEFAULT_BUILDING["name"],
            "AlwaysSmile Merchandise Centre",
        )
        self.assertEqual(
            floor_config.DEFAULT_BUILDING["width"],
            50,
        )
        self.assertEqual(
            floor_config.DEFAULT_BUILDING["height"],
            40,
        )

    def test_complete_configuration_is_valid(self):
        self.assertTrue(floor_config.validate_configuration())

    def test_building_name_cannot_be_empty(self):
        building = dict(floor_config.DEFAULT_BUILDING)
        building["name"] = "   "

        with patch.object(
            floor_config,
            "DEFAULT_BUILDING",
            building,
        ):
            with self.assertRaises(ValueError):
                floor_config.validate_configuration()

    def test_invalid_building_dimension_is_rejected(self):
        building = dict(floor_config.DEFAULT_BUILDING)
        building["width"] = 0

        with patch.object(
            floor_config,
            "DEFAULT_BUILDING",
            building,
        ):
            with self.assertRaises(ValueError):
                floor_config.validate_configuration()

    # ========================================================
    # SEVEN-FLOOR ARCHITECTURE
    # ========================================================

    def test_exactly_seven_floors_exist(self):
        self.assertEqual(
            len(floor_config.FLOORS),
            7,
        )

    def test_architectural_floor_ordering(self):
        actual = [(floor["number"], floor["code"]) for floor in floor_config.FLOORS]

        self.assertEqual(
            actual,
            self.expected_floors,
        )

    def test_all_required_floor_numbers_exist(self):
        self.assertEqual(
            {floor["number"] for floor in floor_config.FLOORS},
            floor_config.VALID_FLOOR_NUMBERS,
        )

    def test_all_floor_codes_are_unique(self):
        codes = [floor["code"] for floor in floor_config.FLOORS]

        self.assertEqual(
            len(codes),
            len(set(codes)),
        )

    def test_all_floor_numbers_are_unique(self):
        numbers = [floor["number"] for floor in floor_config.FLOORS]

        self.assertEqual(
            len(numbers),
            len(set(numbers)),
        )

    def test_each_floor_has_correct_code(self):
        for number, code in self.expected_floors:
            with self.subTest(number=number):
                floor = floor_config.FLOOR_BY_NUMBER[number]

                self.assertEqual(
                    floor["code"],
                    code,
                )

    def test_floor_collection_must_contain_seven_floors(self):
        floors = self._get_test_floors()
        floors.pop()

        with patch.object(
            floor_config,
            "FLOORS",
            floors,
        ):
            with self.assertRaises(ValueError):
                floor_config.validate_configuration()

    def test_duplicate_floor_numbers_are_rejected(self):
        floors = self._get_test_floors()
        floors[1]["number"] = 1

        with patch.object(
            floor_config,
            "FLOORS",
            floors,
        ):
            with self.assertRaises(ValueError):
                floor_config.validate_configuration()

    def test_duplicate_floor_codes_are_rejected(self):
        floors = self._get_test_floors()
        floors[1]["code"] = floors[0]["code"]

        with patch.object(
            floor_config,
            "FLOORS",
            floors,
        ):
            with self.assertRaises(ValueError):
                floor_config.validate_configuration()

    def test_incorrect_floor_code_mapping_is_rejected(self):
        floors = self._get_test_floors()
        floors[0]["code"] = "B1"

        with patch.object(
            floor_config,
            "FLOORS",
            floors,
        ):
            with self.assertRaises(ValueError):
                floor_config.validate_configuration()

    # ========================================================
    # FLOOR NUMBER VALIDATION
    # ========================================================

    def test_valid_floor_numbers(self):
        for number, code in self.expected_floors:
            with self.subTest(number=number):
                self.assertEqual(
                    floor_config.validate_floor_number(number),
                    number,
                )

    def test_valid_string_floor_numbers(self):
        for number, code in self.expected_floors:
            with self.subTest(number=number):
                self.assertEqual(
                    floor_config.validate_floor_number(str(number)),
                    number,
                )

    def test_floor_number_whitespace_is_accepted(self):
        self.assertEqual(
            floor_config.validate_floor_number(" 1 "),
            1,
        )
        self.assertEqual(
            floor_config.validate_floor_number(" -2 "),
            -2,
        )

    def test_invalid_floor_numbers_are_rejected(self):
        invalid_numbers = [
            5,
            -3,
            100,
            "5",
            "-3",
            "1.5",
            "abc",
            "",
            "01",
            "+1",
            None,
            1.5,
            True,
            False,
        ]

        for number in invalid_numbers:
            with self.subTest(number=number):
                with self.assertRaises(ValueError):
                    floor_config.validate_floor_number(number)

    # ========================================================
    # FLOOR CODE VALIDATION
    # ========================================================

    def test_valid_floor_codes(self):
        for number, code in self.expected_floors:
            with self.subTest(code=code):
                self.assertEqual(
                    floor_config.validate_floor_code(code),
                    code,
                )

    def test_floor_codes_are_case_insensitive(self):
        self.assertEqual(
            floor_config.validate_floor_code("l1"),
            "L1",
        )
        self.assertEqual(
            floor_config.validate_floor_code("b3"),
            "B3",
        )

    def test_floor_code_whitespace_is_accepted(self):
        self.assertEqual(
            floor_config.validate_floor_code(" L1 "),
            "L1",
        )

    def test_invalid_floor_codes_are_rejected(self):
        invalid_codes = [
            "L5",
            "B4",
            "LEVEL1",
            "",
            "UNKNOWN",
            None,
            1,
        ]

        for code in invalid_codes:
            with self.subTest(code=code):
                with self.assertRaises(ValueError):
                    floor_config.validate_floor_code(code)

    # ========================================================
    # FLOOR LOOKUPS
    # ========================================================

    def test_floor_lookup_by_number(self):
        for number, code in self.expected_floors:
            with self.subTest(number=number):
                result = floor_config.get_floor_config(number)

                self.assertEqual(
                    result["number"],
                    number,
                )
                self.assertEqual(
                    result["code"],
                    code,
                )

    def test_floor_lookup_by_code(self):
        for number, code in self.expected_floors:
            with self.subTest(code=code):
                result = floor_config.get_floor_config_by_code(code)

                self.assertEqual(
                    result["number"],
                    number,
                )
                self.assertEqual(
                    result["code"],
                    code,
                )

    def test_all_floor_configurations_are_returned(self):
        results = floor_config.get_all_floor_configs()

        self.assertEqual(
            len(results),
            7,
        )

        self.assertEqual(
            [(floor["number"], floor["code"]) for floor in results],
            self.expected_floors,
        )

    def test_floor_dimensions_are_independent(self):
        expected_dimensions = {
            1: {"width": 40, "height": 30},
            2: {"width": 40, "height": 30},
            3: {"width": 40, "height": 30},
            4: {"width": 40, "height": 30},
            0: {"width": 40, "height": 30},
            -1: {"width": 45, "height": 35},
            -2: {"width": 50, "height": 40},
        }

        for number, dimensions in expected_dimensions.items():
            with self.subTest(number=number):
                self.assertEqual(
                    floor_config.get_floor_dimensions(number),
                    dimensions,
                )

    def test_invalid_floor_dimension_lookup_is_rejected(self):
        with self.assertRaises(ValueError):
            floor_config.get_floor_dimensions(5)

        with self.assertRaises(ValueError):
            floor_config.get_floor_config(5)

    def test_floor_codes_preserve_architectural_order(self):
        self.assertEqual(
            floor_config.get_floor_codes(),
            ["L1", "L2", "L3", "L4", "B1", "B2", "B3"],
        )

    def test_floor_numbers_preserve_architectural_order(self):
        self.assertEqual(
            floor_config.get_floor_numbers(),
            [1, 2, 3, 4, 0, -1, -2],
        )

    # ========================================================
    # POSITIVE DIMENSION VALIDATION
    # ========================================================

    def test_valid_positive_dimensions(self):
        self.assertEqual(
            floor_config.validate_positive_dimension(10, "Width"),
            10.0,
        )

        self.assertEqual(
            floor_config.validate_positive_dimension(Decimal("12.5"), "Width"),
            12.5,
        )

    def test_invalid_positive_dimensions_are_rejected(self):
        invalid_values = [
            0,
            -1,
            -10.5,
            float("inf"),
            float("-inf"),
            float("nan"),
            True,
            None,
            "invalid",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    floor_config.validate_positive_dimension(
                        value,
                        "Width",
                    )

    # ========================================================
    # COORDINATE VALIDATION
    # ========================================================

    def test_valid_non_negative_coordinates(self):
        self.assertEqual(
            floor_config.validate_positive_coordinate(0, "X"),
            0.0,
        )

        self.assertEqual(
            floor_config.validate_positive_coordinate(10.5, "X"),
            10.5,
        )

    def test_invalid_coordinates_are_rejected(self):
        invalid_values = [
            -1,
            -10.5,
            float("inf"),
            float("-inf"),
            float("nan"),
            True,
            None,
            "invalid",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    floor_config.validate_positive_coordinate(
                        value,
                        "X",
                    )

    # ========================================================
    # ROOM CONFIGURATION
    # ========================================================

    def test_every_floor_contains_a_room_list(self):
        for floor in floor_config.FLOORS:
            with self.subTest(code=floor["code"]):
                self.assertIsInstance(
                    floor["rooms"],
                    list,
                )

                self.assertGreater(
                    len(floor["rooms"]),
                    0,
                )

    def test_all_room_types_are_valid(self):
        for floor in floor_config.FLOORS:
            for room in floor["rooms"]:
                with self.subTest(
                    floor=floor["code"],
                    room=room["name"],
                ):
                    self.assertIn(
                        room["type"],
                        floor_config.VALID_ROOM_TYPES,
                    )

    def test_invalid_room_type_is_rejected(self):
        floors = self._get_test_floors()
        floors[0]["rooms"][0]["type"] = "unknown"

        with patch.object(
            floor_config,
            "FLOORS",
            floors,
        ):
            with self.assertRaises(ValueError):
                floor_config.validate_configuration()

    def test_empty_room_name_is_rejected(self):
        floors = self._get_test_floors()
        floors[0]["rooms"][0]["name"] = "   "

        with patch.object(
            floor_config,
            "FLOORS",
            floors,
        ):
            with self.assertRaises(ValueError):
                floor_config.validate_configuration()

    def test_missing_room_name_is_rejected(self):
        floors = self._get_test_floors()
        floors[0]["rooms"][0]["name"] = None

        with patch.object(
            floor_config,
            "FLOORS",
            floors,
        ):
            with self.assertRaises(ValueError):
                floor_config.validate_configuration()

    def test_invalid_room_dimensions_are_rejected(self):
        floors = self._get_test_floors()
        floors[0]["rooms"][0]["width"] = 0

        with patch.object(
            floor_config,
            "FLOORS",
            floors,
        ):
            with self.assertRaises(ValueError):
                floor_config.validate_configuration()

    def test_negative_room_coordinates_are_rejected(self):
        floors = self._get_test_floors()
        floors[0]["rooms"][0]["x"] = -1

        with patch.object(
            floor_config,
            "FLOORS",
            floors,
        ):
            with self.assertRaises(ValueError):
                floor_config.validate_configuration()

    # ========================================================
    # ROOM BOUNDARY VALIDATION
    # ========================================================

    def test_all_rooms_remain_within_floor_boundaries(self):
        for floor in floor_config.FLOORS:
            floor_width = floor["width"]
            floor_height = floor["height"]

            for room in floor["rooms"]:
                with self.subTest(
                    floor=floor["code"],
                    room=room["name"],
                ):
                    self.assertLessEqual(
                        room["x"] + room["width"],
                        floor_width,
                    )

                    self.assertLessEqual(
                        room["y"] + room["height"],
                        floor_height,
                    )

    def test_room_exceeding_floor_width_is_rejected(self):
        floors = self._get_test_floors()
        floors[0]["rooms"][0]["width"] = 41

        with patch.object(
            floor_config,
            "FLOORS",
            floors,
        ):
            with self.assertRaises(ValueError):
                floor_config.validate_configuration()

    def test_room_exceeding_floor_height_is_rejected(self):
        floors = self._get_test_floors()
        floors[0]["rooms"][0]["height"] = 31

        with patch.object(
            floor_config,
            "FLOORS",
            floors,
        ):
            with self.assertRaises(ValueError):
                floor_config.validate_configuration()

    # ========================================================
    # ROOM OVERLAP VALIDATION
    # ========================================================

    def test_valid_room_layout_has_no_overlaps(self):
        for floor in floor_config.FLOORS:
            with self.subTest(floor=floor["code"]):
                self.assertTrue(
                    floor_config.validate_room_overlap(
                        floor["code"],
                        floor["rooms"],
                    )
                )

    def test_overlapping_rooms_are_rejected(self):
        rooms = [
            {
                "name": "Room A",
                "x": 0,
                "y": 0,
                "width": 10,
                "height": 10,
            },
            {
                "name": "Room B",
                "x": 5,
                "y": 5,
                "width": 10,
                "height": 10,
            },
        ]

        with self.assertRaises(ValueError):
            floor_config.validate_room_overlap(
                "L1",
                rooms,
            )

    def test_touching_room_edges_are_permitted(self):
        rooms = [
            {
                "name": "Room A",
                "x": 0,
                "y": 0,
                "width": 10,
                "height": 10,
            },
            {
                "name": "Room B",
                "x": 10,
                "y": 0,
                "width": 10,
                "height": 10,
            },
        ]

        self.assertTrue(
            floor_config.validate_room_overlap(
                "L1",
                rooms,
            )
        )

    def test_touching_room_boundaries_are_permitted(self):
        rooms = [
            {
                "name": "Room A",
                "x": 0,
                "y": 0,
                "width": 10,
                "height": 10,
            },
            {
                "name": "Room B",
                "x": 0,
                "y": 10,
                "width": 10,
                "height": 10,
            },
        ]

        self.assertTrue(
            floor_config.validate_room_overlap(
                "L1",
                rooms,
            )
        )

    def test_empty_room_list_is_valid(self):
        self.assertTrue(
            floor_config.validate_room_overlap(
                "L1",
                [],
            )
        )

    def test_invalid_room_collection_is_rejected(self):
        with self.assertRaises(ValueError):
            floor_config.validate_room_overlap(
                "L1",
                None,
            )

        with self.assertRaises(ValueError):
            floor_config.validate_room_overlap(
                "L1",
                (),
            )

    def test_configuration_validation_detects_room_overlap(self):
        floors = self._get_test_floors()

        floors[0]["rooms"][1]["x"] = 5

        with patch.object(
            floor_config,
            "FLOORS",
            floors,
        ):
            with self.assertRaises(ValueError):
                floor_config.validate_configuration()

    # ========================================================
    # CONFIGURATION ISOLATION
    # ========================================================

    def test_floor_result_does_not_change_master_configuration(self):
        original_name = floor_config.FLOORS[0]["rooms"][0]["name"]

        result = floor_config.get_floor_config(1)

        result["rooms"][0]["name"] = "Modified Room"
        result["rooms"].append(
            {
                "name": "Additional Room",
                "type": "sales",
                "x": 0,
                "y": 0,
                "width": 1,
                "height": 1,
            }
        )

        self.assertEqual(
            floor_config.FLOORS[0]["rooms"][0]["name"],
            original_name,
        )

        self.assertEqual(
            len(result["rooms"]),
            len(floor_config.FLOORS[0]["rooms"]) + 1,
        )

    def test_floor_lookup_results_are_independent(self):
        first = floor_config.get_floor_config(1)
        second = floor_config.get_floor_config(1)

        first["rooms"][0]["name"] = "Changed"

        self.assertNotEqual(
            first["rooms"][0]["name"],
            second["rooms"][0]["name"],
        )

    def test_all_floor_results_are_independent(self):
        results = floor_config.get_all_floor_configs()

        original_name = results[0]["rooms"][0]["name"]

        results[0]["rooms"][0]["name"] = "Changed"

        fresh_results = floor_config.get_all_floor_configs()

        self.assertEqual(
            fresh_results[0]["rooms"][0]["name"],
            original_name,
        )

    def test_floor_code_lookup_results_are_independent(self):
        first = floor_config.get_floor_config_by_code("L1")
        second = floor_config.get_floor_config_by_code("L1")

        first["rooms"][0]["name"] = "Changed"

        self.assertNotEqual(
            first["rooms"][0]["name"],
            second["rooms"][0]["name"],
        )

    def test_floor_dimension_results_are_independent(self):
        first = floor_config.get_floor_dimensions(1)
        second = floor_config.get_floor_dimensions(1)

        first["width"] = 999

        self.assertEqual(
            second["width"],
            40,
        )

        self.assertEqual(
            floor_config.get_floor_dimensions(1)["width"],
            40,
        )
