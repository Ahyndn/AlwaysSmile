
from django.apps import apps
from apps.dashboard.models import Building, Floor, Room, Fixture

obsolete_floor_ids = [3, 4, 5, 6, 7, 8, 9, 12, 13, 14]

print("\n=== OBSOLETE FLOOR DETAILS ===")

for floor in Floor.objects.filter(id__in=obsolete_floor_ids).order_by("id"):
    print(
        f"\nFloor ID: {floor.id}",
        f"\nBuilding ID: {floor.building_id}",
        f"\nFloor number: {floor.number}",
        f"\nRooms: {Room.objects.filter(floor=floor).count()}",
        f"\nFixtures: {Fixture.objects.filter(floor=floor).count()}",
    )

    for room in Room.objects.filter(floor=floor):
        print(
            f"  Room {room.id}: {room.name}",
            f"| Fixtures: {Fixture.objects.filter(room=room).count()}"
        )

print("\n=== FOREIGN KEY DEPENDENCY AUDIT ===")

for model in apps.get_models():
    for field in model._meta.get_fields():
        if not getattr(field, "many_to_one", False) and not getattr(
            field, "one_to_one", False
        ):
            continue

        if field.related_model not in (Floor, Building, Room):
            continue

        ids = {
            Floor: obsolete_floor_ids,
            Building: [2],
            Room: list(
                Room.objects.filter(floor_id__in=obsolete_floor_ids)
                .values_list("id", flat=True)
            ),
        }[field.related_model]

        if not ids:
            continue

        count = model.objects.filter(
            **{f"{field.name}_id__in": ids}
        ).count()

        if count:
            print(
                f"{model._meta.label}: "
                f"{field.name} -> {field.related_model.__name__}: "
                f"{count} references"
            )

print("\n=== BUILDING SUMMARY ===")

for building in Building.objects.all():
    print(
        building.id,
        building.name,
        "Floors:",
        Floor.objects.filter(building=building).count()
    )

print("\nAudit complete. No records modified.")
