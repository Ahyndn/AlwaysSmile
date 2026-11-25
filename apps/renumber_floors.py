import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django.setup()

from django.db import transaction

from apps.dashboard.models import Building, Floor


@transaction.atomic
def renumber_alwayssmile_floors():

    building = Building.objects.get(
        pk=1,
        name="AlwaysSmile Merchandise Centre",
    )

    floors = {floor.number: floor for floor in Floor.objects.filter(building=building)}

    expected = {1, 2, 3, 4, 5, 6, 7}

    if set(floors) != expected:
        raise ValueError("Unexpected floor numbers. Renumbering cancelled.")

    # Check temporary numbers are unused.
    if Floor.objects.filter(
        building=building,
        number__in=[100, 101, 102],
    ).exists():
        raise ValueError("Temporary floor numbers already exist.")

    # Move basement floors to temporary numbers.
    for old_number, temporary_number in {
        5: 100,
        6: 101,
        7: 102,
    }.items():
        Floor.objects.filter(pk=floors[old_number].pk).update(number=temporary_number)

    # Assign final architectural numbers.
    for temporary_number, new_number in {
        100: 0,
        101: -1,
        102: -2,
    }.items():
        Floor.objects.filter(
            building=building,
            number=temporary_number,
        ).update(number=new_number)

    print("\nFloor renumbering completed.")

    for floor in Floor.objects.filter(building=building).order_by("-number"):
        print(floor.id, floor.number, floor.name)


if __name__ == "__main__":
    renumber_alwayssmile_floors()
