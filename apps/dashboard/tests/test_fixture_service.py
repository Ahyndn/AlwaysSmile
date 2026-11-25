
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.dashboard.models import (
    Building,
    Floor,
    Fixture,
    Room,
)

from apps.dashboard.planogram.fixture_service import (
    clear_floor_fixtures,
    create_fixture,
    delete_fixture,
    get_fixture,
    get_floor_fixtures,
    move_fixture,
    resize_fixture,
    serialize_fixture,
    serialize_fixture_geometry,
    update_fixture,
    validate_fixture,
    validate_fixture_id,
    validate_floor,
    validate_service_data,
)


class FixtureServiceTests(TestCase):

    def setUp(self):
        self.building = Building.objects.create(
            name="AlwaysSmile",
            width=40,
            height=30,
        )

        self.floor = Floor.objects.create(
            building=self.building,
            number=1,
            name="Level 1",
            width=40,
            height=30,
        )

        self.sales_room = Room.objects.create(
            floor=self.floor,
            name="Electronics Sales",
            room_type="sales",
            x=Decimal("0.00"),
            y=Decimal("0.00"),
            width=Decimal("30.00"),
            height=Decimal("25.00"),
        )

        self.storage_room = Room.objects.create(
            floor=self.floor,
            name="Storage",
            room_type="storage",
            x=Decimal("30.00"),
            y=Decimal("0.00"),
            width=Decimal("10.00"),
            height=Decimal("25.00"),
        )

        self.fixture = Fixture.objects.create(
            floor=self.floor,
            room=self.sales_room,
            name="Display Shelf A",
            fixture_type="shelf",
            x=Decimal("5.00"),
            y=Decimal("5.00"),
            width=Decimal("2.00"),
            depth=Decimal("1.00"),
        )

    # ========================================================
    # VALIDATION
    # ========================================================

    def test_validate_floor(self):
        self.assertEqual(
            validate_floor(self.floor),
            self.floor,
        )

    def test_validate_floor_rejects_invalid_object(self):
        with self.assertRaises(ValidationError):
            validate_floor("invalid")

    def test_validate_fixture(self):
        self.assertEqual(
            validate_fixture(self.fixture),
            self.fixture,
        )

    def test_validate_fixture_rejects_invalid_object(self):
        with self.assertRaises(ValidationError):
            validate_fixture("invalid")

    def test_validate_service_data(self):
        data = {
            "name": "New Shelf",
            "fixture_type": "shelf",
        }

        self.assertEqual(
            validate_service_data(data),
            data,
        )

    def test_validate_service_data_rejects_non_dictionary(self):
        with self.assertRaises(ValidationError):
            validate_service_data("invalid")

    def test_validate_service_data_rejects_unsupported_fields(self):
        with self.assertRaises(ValidationError):
            validate_service_data({
                "name": "Shelf",
                "floor": self.floor,
            })

    def test_validate_fixture_id(self):
        self.assertEqual(
            validate_fixture_id("10"),
            10,
        )

    def test_validate_fixture_id_rejects_zero(self):
        with self.assertRaises(ValidationError):
            validate_fixture_id(0)

    def test_validate_fixture_id_rejects_negative(self):
        with self.assertRaises(ValidationError):
            validate_fixture_id(-1)

    def test_validate_fixture_id_rejects_boolean(self):
        with self.assertRaises(ValidationError):
            validate_fixture_id(True)

    # ========================================================
    # CREATE FIXTURE
    # ========================================================

    def test_create_fixture(self):
        fixture = create_fixture(
            self.floor,
            {
                "name": "Display Shelf B",
                "fixture_type": "shelf",
                "x": 10,
                "y": 5,
                "width": 2,
                "depth": 1,
            },
        )

        self.assertIsNotNone(fixture.pk)

        self.assertEqual(
            fixture.name,
            "Display Shelf B",
        )

        self.assertEqual(
            fixture.floor,
            self.floor,
        )

        self.assertEqual(
            fixture.room,
            self.sales_room,
        )

    def test_create_fixture_uses_default_values(self):
        fixture = create_fixture(
            self.floor,
            {},
        )

        self.assertEqual(fixture.name, "New Fixture")
        self.assertEqual(fixture.fixture_type, "shelf")
        self.assertEqual(fixture.x, Decimal("10"))
        self.assertEqual(fixture.y, Decimal("10"))
        self.assertEqual(fixture.width, Decimal("1.2"))
        self.assertEqual(fixture.depth, Decimal("0.8"))

    def test_create_fixture_rejects_invalid_floor(self):
        with self.assertRaises(ValidationError):
            create_fixture(
                "invalid",
                {},
            )

    def test_create_fixture_rejects_invalid_data(self):
        with self.assertRaises(ValidationError):
            create_fixture(
                self.floor,
                {
                    "name": "",
                },
            )

    def test_create_fixture_rejects_outside_floor(self):
        with self.assertRaises(ValidationError):
            create_fixture(
                self.floor,
                {
                    "name": "Invalid Shelf",
                    "x": 39,
                    "y": 5,
                    "width": 2,
                    "depth": 1,
                },
            )

    def test_create_fixture_rejects_non_sales_room(self):
        with self.assertRaises(ValidationError):
            create_fixture(
                self.floor,
                {
                    "name": "Storage Shelf",
                    "x": 32,
                    "y": 5,
                    "width": 2,
                    "depth": 1,
                },
            )

    def test_create_fixture_rejects_overlap(self):
        with self.assertRaises(ValidationError):
            create_fixture(
                self.floor,
                {
                    "name": "Overlapping Shelf",
                    "x": 5,
                    "y": 5,
                    "width": 2,
                    "depth": 1,
                },
            )

    def test_create_fixture_allows_touching_edges(self):
        fixture = create_fixture(
            self.floor,
            {
                "name": "Adjacent Shelf",
                "x": 7,
                "y": 5,
                "width": 2,
                "depth": 1,
            },
        )

        self.assertIsNotNone(fixture.pk)

    # ========================================================
    # RETRIEVE FIXTURE
    # ========================================================

    def test_get_fixture(self):
        fixture = get_fixture(self.fixture.pk)

        self.assertEqual(
            fixture.pk,
            self.fixture.pk,
        )

    def test_get_fixture_rejects_invalid_id(self):
        with self.assertRaises(ValidationError):
            get_fixture("invalid")

    def test_get_fixture_rejects_missing_fixture(self):
        with self.assertRaises(ValidationError):
            get_fixture(99999)

    # ========================================================
    # RETRIEVE FLOOR FIXTURES
    # ========================================================

    def test_get_floor_fixtures(self):
        fixtures = get_floor_fixtures(self.floor)

        self.assertEqual(
            fixtures.count(),
            1,
        )

        self.assertEqual(
            fixtures.first(),
            self.fixture,
        )

    def test_get_floor_fixtures_rejects_invalid_floor(self):
        with self.assertRaises(ValidationError):
            get_floor_fixtures("invalid")

    def test_get_floor_fixtures_returns_only_selected_floor(self):
        other_floor = Floor.objects.create(
            building=self.building,
            number=2,
            name="Level 2",
            width=40,
            height=30,
        )

        Fixture.objects.create(
            floor=other_floor,
            name="Upper Floor Shelf",
            fixture_type="shelf",
            x=5,
            y=5,
            width=2,
            depth=1,
        )

        fixtures = get_floor_fixtures(self.floor)

        self.assertEqual(fixtures.count(), 1)

    # ========================================================
    # UPDATE FIXTURE
    # ========================================================

    def test_update_fixture_name(self):
        updated = update_fixture(
            self.fixture,
            {
                "name": "Updated Shelf",
            },
        )

        self.assertEqual(
            updated.name,
            "Updated Shelf",
        )

    def test_update_fixture_color(self):
        updated = update_fixture(
            self.fixture,
            {
                "color": "#FF0000",
            },
        )

        self.assertEqual(
            updated.color,
            "#FF0000",
        )

    def test_update_fixture_type(self):
        updated = update_fixture(
            self.fixture,
            {
                "fixture_type": "cabinet",
            },
        )

        self.assertEqual(
            updated.fixture_type,
            "cabinet",
        )

    def test_update_fixture_preserves_unspecified_fields(self):
        updated = update_fixture(
            self.fixture,
            {
                "name": "Updated Shelf",
            },
        )

        self.assertEqual(updated.x, Decimal("5.00"))
        self.assertEqual(updated.y, Decimal("5.00"))
        self.assertEqual(updated.width, Decimal("2.00"))
        self.assertEqual(updated.depth, Decimal("1.00"))

    def test_update_fixture_with_empty_data_returns_fixture(self):
        updated = update_fixture(
            self.fixture,
            {},
        )

        self.assertEqual(
            updated.pk,
            self.fixture.pk,
        )

    def test_update_fixture_rejects_invalid_data(self):
        with self.assertRaises(ValidationError):
            update_fixture(
                self.fixture,
                {
                    "width": -1,
                },
            )

    def test_update_fixture_rejects_overlap(self):
        other = create_fixture(
            self.floor,
            {
                "name": "Other Shelf",
                "x": 10,
                "y": 5,
                "width": 2,
                "depth": 1,
            },
        )

        with self.assertRaises(ValidationError):
            update_fixture(
                other,
                {
                    "x": 5,
                    "y": 5,
                },
            )

    # ========================================================
    # MOVE FIXTURE
    # ========================================================

    def test_move_fixture(self):
        moved = move_fixture(
            self.fixture,
            10,
            10,
        )

        self.assertEqual(moved.x, Decimal("10"))
        self.assertEqual(moved.y, Decimal("10"))

    def test_move_fixture_preserves_dimensions(self):
        moved = move_fixture(
            self.fixture,
            10,
            10,
        )

        self.assertEqual(moved.width, Decimal("2.00"))
        self.assertEqual(moved.depth, Decimal("1.00"))

    def test_move_fixture_rejects_invalid_position(self):
        with self.assertRaises(ValidationError):
            move_fixture(
                self.fixture,
                39,
                5,
            )

    # ========================================================
    # RESIZE FIXTURE
    # ========================================================

    def test_resize_fixture(self):
        resized = resize_fixture(
            self.fixture,
            4,
            2,
        )

        self.assertEqual(resized.width, Decimal("4"))
        self.assertEqual(resized.depth, Decimal("2"))

    def test_resize_fixture_preserves_coordinates(self):
        resized = resize_fixture(
            self.fixture,
            4,
            2,
        )

        self.assertEqual(resized.x, Decimal("5.00"))
        self.assertEqual(resized.y, Decimal("5.00"))

    def test_resize_fixture_rejects_invalid_dimensions(self):
        with self.assertRaises(ValidationError):
            resize_fixture(
                self.fixture,
                0,
                2,
            )

    # ========================================================
    # DELETE FIXTURE
    # ========================================================

    def test_delete_fixture(self):
        result = delete_fixture(self.fixture)

        self.assertTrue(result)

        self.assertFalse(
            Fixture.objects.filter(
                pk=self.fixture.pk,
            ).exists()
        )

    def test_delete_fixture_returns_false_when_already_deleted(self):
        fixture_id = self.fixture.pk

        self.fixture.delete()

        fixture = Fixture(
            pk=fixture_id,
            floor=self.floor,
        )

        self.assertFalse(
            delete_fixture(fixture)
        )

    # ========================================================
    # CLEAR FLOOR FIXTURES
    # ========================================================

    def test_clear_floor_fixtures(self):
        create_fixture(
            self.floor,
            {
                "name": "Shelf B",
                "x": 10,
                "y": 5,
                "width": 2,
                "depth": 1,
            },
        )

        deleted = clear_floor_fixtures(self.floor)

        self.assertEqual(deleted, 2)

        self.assertEqual(
            Fixture.objects.filter(
                floor=self.floor,
            ).count(),
            0,
        )

    def test_clear_floor_fixtures_returns_zero_when_empty(self):
        self.fixture.delete()

        deleted = clear_floor_fixtures(self.floor)

        self.assertEqual(deleted, 0)

    def test_clear_floor_fixtures_rejects_invalid_floor(self):
        with self.assertRaises(ValidationError):
            clear_floor_fixtures("invalid")

    # ========================================================
    # SERIALIZATION
    # ========================================================

    def test_serialize_fixture_geometry(self):
        result = serialize_fixture_geometry(self.fixture)

        self.assertEqual(
            result["id"],
            self.fixture.pk,
        )

        self.assertEqual(
            result["name"],
            "Display Shelf A",
        )

        self.assertEqual(
            result["type"],
            "shelf",
        )

        self.assertEqual(
            result["fixture_type"],
            "shelf",
        )

        self.assertEqual(
            result["floor_id"],
            self.floor.pk,
        )

        self.assertEqual(
            result["room_id"],
            self.sales_room.pk,
        )

        self.assertEqual(result["x"], "5.00")
        self.assertEqual(result["y"], "5.00")
        self.assertEqual(result["width"], "2.00")
        self.assertEqual(result["depth"], "1.00")

    def test_serialize_fixture_geometry_rejects_invalid_fixture(self):
        with self.assertRaises(ValidationError):
            serialize_fixture_geometry("invalid")

    def test_serialize_fixture(self):
        result = serialize_fixture(self.fixture)

        self.assertEqual(
            result["name"],
            "Display Shelf A",
        )

        self.assertIn(
            "planogram",
            result,
        )
