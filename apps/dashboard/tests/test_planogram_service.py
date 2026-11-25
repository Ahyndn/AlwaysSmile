from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.dashboard.models import (
    Building,
    Floor,
    Fixture,
    MerchandiseProduct,
    Planogram,
    PlanogramItem,
    SalesChannel,
)

from apps.dashboard.planogram.planogram_service import (
    add_product_to_fixture,
    clear_planogram,
    get_fixture_planogram,
    get_fixture_summary,
    get_or_create_planogram,
    remove_planogram_item,
    reorder_planogram_items,
    serialize_fixture,
    serialize_planogram_item,
    update_planogram_item,
)


class PlanogramServiceTests(TestCase):
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

        self.fixture = Fixture.objects.create(
            floor=self.floor,
            name="Display Shelf A",
            fixture_type="shelf",
            x=Decimal("5.00"),
            y=Decimal("5.00"),
            width=Decimal("2.00"),
            depth=Decimal("1.00"),
        )

        self.in_person_channel = SalesChannel.objects.create(
            code="in_person"
        )

        self.product_a = MerchandiseProduct.objects.create(
            external_id=1001,
            title="Product A",
            category="Electronics",
            brand="AlwaysSmile",
            price=Decimal("19.99"),
            stock=100,
        )

        self.product_a.sales_channels.add(
            self.in_person_channel
        )

        self.product_b = MerchandiseProduct.objects.create(
            external_id=1002,
            title="Product B",
            category="Electronics",
            brand="AlwaysSmile",
            price=Decimal("29.99"),
            stock=100,
        )

        self.product_b.sales_channels.add(
            self.in_person_channel
        )

    def test_get_or_create_planogram(self):
        planogram = get_or_create_planogram(self.fixture)

        self.assertIsNotNone(planogram.pk)

        self.assertEqual(
            Planogram.objects.filter(fixture=self.fixture).count(),
            1,
        )

    def test_get_or_create_planogram_does_not_duplicate(self):
        first = get_or_create_planogram(self.fixture)
        second = get_or_create_planogram(self.fixture)

        self.assertEqual(first.pk, second.pk)

    def test_get_fixture_planogram_returns_none_when_missing(self):
        self.assertIsNone(get_fixture_planogram(self.fixture))

    def test_add_product_to_fixture(self):
        item = add_product_to_fixture(
            self.fixture,
            self.product_a,
            quantity=10,
            facings=5,
        )

        self.assertEqual(item.quantity, 10)
        self.assertEqual(item.facings, 5)
        self.assertEqual(item.position, 0)

    def test_add_existing_product_updates_item(self):
        first = add_product_to_fixture(
            self.fixture,
            self.product_a,
            quantity=10,
            facings=5,
        )

        second = add_product_to_fixture(
            self.fixture,
            self.product_a,
            quantity=20,
            facings=10,
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.quantity, 20)
        self.assertEqual(second.facings, 10)

        self.assertEqual(
            PlanogramItem.objects.count(),
            1,
        )

    def test_multiple_products_can_share_position(self):
        first = add_product_to_fixture(
            self.fixture,
            self.product_a,
        )

        second = add_product_to_fixture(
            self.fixture,
            self.product_b,
        )

        second.position = first.position
        second.save(update_fields=["position"])

        self.assertEqual(first.position, second.position)

    def test_invalid_quantity_is_rejected(self):
        with self.assertRaises(ValidationError):
            add_product_to_fixture(
                self.fixture,
                self.product_a,
                quantity=0,
            )

    def test_quantity_above_maximum_is_rejected(self):
        with self.assertRaises(ValidationError):
            add_product_to_fixture(
                self.fixture,
                self.product_a,
                quantity=10001,
            )

    def test_facings_cannot_exceed_quantity(self):
        with self.assertRaises(ValidationError):
            add_product_to_fixture(
                self.fixture,
                self.product_a,
                quantity=5,
                facings=6,
            )

    def test_update_planogram_item(self):
        item = add_product_to_fixture(
            self.fixture,
            self.product_a,
            quantity=10,
            facings=5,
        )

        updated = update_planogram_item(
            item,
            {
                "quantity": 20,
                "facings": 10,
            },
        )

        self.assertEqual(updated.quantity, 20)
        self.assertEqual(updated.facings, 10)

    def test_update_preserves_unspecified_fields(self):
        item = add_product_to_fixture(
            self.fixture,
            self.product_a,
            quantity=10,
            facings=5,
        )

        updated = update_planogram_item(
            item,
            {"quantity": 20},
        )

        self.assertEqual(updated.quantity, 20)
        self.assertEqual(updated.facings, 5)

    def test_remove_planogram_item(self):
        item = add_product_to_fixture(
            self.fixture,
            self.product_a,
        )

        self.assertTrue(remove_planogram_item(item))

        self.assertFalse(PlanogramItem.objects.filter(pk=item.pk).exists())

    def test_clear_planogram(self):
        add_product_to_fixture(self.fixture, self.product_a)
        add_product_to_fixture(self.fixture, self.product_b)

        planogram = Planogram.objects.get(fixture=self.fixture)

        deleted = clear_planogram(planogram)

        self.assertEqual(deleted, 2)

        self.assertEqual(
            planogram.items.count(),
            0,
        )

    def test_serialize_planogram_item(self):
        item = add_product_to_fixture(
            self.fixture,
            self.product_a,
            quantity=5,
            facings=2,
        )

        result = serialize_planogram_item(item)

        self.assertEqual(result["title"], "Product A")
        self.assertEqual(result["quantity"], 5)
        self.assertEqual(result["facings"], 2)
        self.assertEqual(result["price"], "19.99")
        self.assertEqual(result["total_price"], "99.95")

    def test_serialize_fixture(self):
        add_product_to_fixture(
            self.fixture,
            self.product_a,
        )

        result = serialize_fixture(self.fixture)

        self.assertEqual(
            result["name"],
            "Display Shelf A",
        )

        self.assertEqual(
            len(result["planogram"]),
            1,
        )

    def test_fixture_summary(self):
        add_product_to_fixture(
            self.fixture,
            self.product_a,
            quantity=10,
            facings=5,
        )

        add_product_to_fixture(
            self.fixture,
            self.product_b,
            quantity=20,
            facings=10,
        )

        summary = get_fixture_summary(self.fixture)

        self.assertEqual(summary["product_count"], 2)
        self.assertEqual(summary["total_quantity"], 30)
        self.assertEqual(summary["total_facings"], 15)

    def test_reorder_planogram_items(self):
        first = add_product_to_fixture(
            self.fixture,
            self.product_a,
        )

        second = add_product_to_fixture(
            self.fixture,
            self.product_b,
        )

        planogram = first.planogram

        reordered = reorder_planogram_items(
            planogram,
            [second.pk, first.pk],
        )

        self.assertEqual(reordered[0].pk, second.pk)
        self.assertEqual(reordered[1].pk, first.pk)

        self.assertEqual(reordered[0].position, 0)
        self.assertEqual(reordered[1].position, 1)

    def test_reorder_rejects_duplicate_ids(self):
        first = add_product_to_fixture(
            self.fixture,
            self.product_a,
        )

        planogram = first.planogram

        with self.assertRaises(ValidationError):
            reorder_planogram_items(
                planogram,
                [first.pk, first.pk],
            )

    def test_reorder_rejects_missing_ids(self):
        first = add_product_to_fixture(
            self.fixture,
            self.product_a,
        )

        second = add_product_to_fixture(
            self.fixture,
            self.product_b,
        )

        with self.assertRaises(ValidationError):
            reorder_planogram_items(
                first.planogram,
                [first.pk],
            )
