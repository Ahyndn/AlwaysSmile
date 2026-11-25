# Register your models here.

from django.contrib import admin

from .models import (
    Building,
    Fixture,
    Floor,
    MerchandiseProduct,
    Planogram,
    PlanogramItem,
    Room,
)

admin.site.register(Building)
admin.site.register(Floor)
admin.site.register(Room)
admin.site.register(Fixture)
admin.site.register(MerchandiseProduct)
admin.site.register(Planogram)
admin.site.register(PlanogramItem)
