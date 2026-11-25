
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


KEEP_NAME = "AlwaysSmile"
DELETE_NAME = "AlwaysSmile Merchandise Centre"

EXPECTED_FLOORS = {-2, -1, 0, 1, 2, 3, 4}


class Command(BaseCommand):
    help = (
        "Safely remove AlwaysSmile Merchandise Centre "
        "while preserving AlwaysSmile."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Actually delete the duplicate building.",
        )

    def handle(self, *args, **options):
        Building = apps.get_model("dashboard", "Building")
        Planogram = apps.get_model("dashboard", "Planogram")
        PlanogramItem = apps.get_model("dashboard", "PlanogramItem")

        execute = options["execute"]

        if execute:
            with transaction.atomic():
                keeper = self.get_keeper(Building)

                duplicates = list(
                    Building.objects.select_for_update().filter(
                        name=DELETE_NAME
                    ).order_by("pk")
                )

                if not duplicates:
                    self.stdout.write(
                        self.style.WARNING(
                            "No duplicate building found. Nothing to delete."
                        )
                    )
                    return

                self.show_records(
                    duplicates, Planogram, PlanogramItem
                )

                deleted_count = 0

                for building in duplicates:
                    count, details = building.delete()
                    deleted_count += count

                    self.stdout.write(
                        f"Deleted building ID {building.pk}: "
                        f"{count} database records."
                    )

                if Building.objects.filter(name=KEEP_NAME).count() != 1:
                    raise CommandError(
                        "Preserved building verification failed."
                    )

                if Building.objects.filter(name=DELETE_NAME).exists():
                    raise CommandError(
                        "Duplicate building still exists."
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Deletion completed. "
                        f"{deleted_count} total records removed."
                    )
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{KEEP_NAME} remains intact."
                    )
                )

        else:
            self.get_keeper(Building)

            duplicates = list(
                Building.objects.filter(
                    name=DELETE_NAME
                ).order_by("pk")
            )

            if not duplicates:
                self.stdout.write(
                    self.style.WARNING(
                        "No duplicate building found."
                    )
                )
                return

            self.stdout.write(
                self.style.WARNING("DRY RUN — NOTHING WILL BE DELETED")
            )

            self.show_records(
                duplicates, Planogram, PlanogramItem
            )

            self.stdout.write(
                "\nRun with --execute to perform the deletion."
            )

    def get_keeper(self, Building):
        keepers = Building.objects.filter(name=KEEP_NAME)

        if keepers.count() != 1:
            raise CommandError(
                f"Expected exactly one '{KEEP_NAME}' building. "
                f"Found {keepers.count()}. Aborting."
            )

        keeper = keepers.first()

        floor_numbers = set(
            keeper.floors.values_list("number", flat=True)
        )

        if (
            keeper.floors.count() != 7
            or floor_numbers != EXPECTED_FLOORS
        ):
            raise CommandError(
                "The original AlwaysSmile building does not "
                "have the expected seven floors. Aborting."
            )

        return keeper

    def show_records(self, buildings, Planogram, PlanogramItem):
        for building in buildings:
            floors = building.floors.all()

            rooms = sum(
                floor.rooms.count() for floor in floors
            )

            fixtures = sum(
                floor.fixtures.count() for floor in floors
            )

            planograms = Planogram.objects.filter(
                fixture__floor__building=building
            ).count()

            items = PlanogramItem.objects.filter(
                planogram__fixture__floor__building=building
            ).count()

            self.stdout.write(
                f"\nBuilding: {building.name}"
                f"\nID: {building.pk}"
                f"\nFloors: {floors.count()}"
                f"\nRooms: {rooms}"
                f"\nFixtures: {fixtures}"
                f"\nPlanograms: {planograms}"
                f"\nPlanogram items: {items}"
            )
