from django.db import models

class Building(models.Model):
    name = models.CharField(max_length=150, default="AlwaysSmile")
    width = models.PositiveIntegerField(default=40)
    height = models.PositiveIntegerField(default=30)

    def __str__(self):
        return self.name


class Floor(models.Model):
    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name="floors",
    )
    number = models.SmallIntegerField()
    name = models.CharField(max_length=100)
    width = models.PositiveIntegerField(default=40)
    height = models.PositiveIntegerField(default=30)

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(
                fields=["building", "number"],
                name="unique_building_floor",
            )
        ]

    def __str__(self):
        return f"{self.building.name} - {self.name}"


class Room(models.Model):
    ROOM_TYPES = (
        ("sales", "Merchandise Sales"),
        ("storage", "Storage"),
        ("fitting", "Fitting Rooms"),
        ("management", "Management"),
        ("mess", "Staff Mess Hall"),
        ("lounge", "Staff Lounge"),
        ("corridor", "Customer Corridor"),
        ("entrance", "Entrance"),
        ("service", "Service Area"),
    )

    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        related_name="rooms",
    )

    name = models.CharField(max_length=100)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)

    x = models.DecimalField(max_digits=7, decimal_places=2)
    y = models.DecimalField(max_digits=7, decimal_places=2)
    width = models.DecimalField(max_digits=7, decimal_places=2)
    height = models.DecimalField(max_digits=7, decimal_places=2)

    color = models.CharField(max_length=20, default="#E5E7EB")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} ({self.floor.name})"


class Fixture(models.Model):
    FIXTURE_TYPES = (
        ("shelf", "Retail Shelf"),
        ("rack", "Clothing Rack"),
        ("table", "Display Table"),
        ("cabinet", "Display Cabinet"),
        ("island", "Promotional Island"),
    )

    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        related_name="fixtures",
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="fixtures",
        null=True,
        blank=True,
    )

    name = models.CharField(max_length=100)
    fixture_type = models.CharField(
        max_length=20,
        choices=FIXTURE_TYPES,
        default="shelf",
    )

    x = models.DecimalField(max_digits=7, decimal_places=2, default=5)
    y = models.DecimalField(max_digits=7, decimal_places=2, default=5)

    width = models.DecimalField(max_digits=7, decimal_places=2, default=1.2)
    depth = models.DecimalField(max_digits=7, decimal_places=2, default=0.8)

    color = models.CharField(max_length=20, default="#2563EB")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class SalesChannel(models.Model):
    CHANNEL_CHOICES = (
        ("online", "Online"),
        ("in_person", "In Person"),
        ("mobile", "Mobile"),
    )

    code = models.CharField(
        max_length=30,
        choices=CHANNEL_CHOICES,
        unique=True,
    )

    def __str__(self):
        return self.get_code_display()


class MerchandiseProduct(models.Model):
    external_id = models.PositiveIntegerField(unique=True)

    title = models.CharField(max_length=250)
    category = models.CharField(max_length=100, blank=True)
    brand = models.CharField(max_length=150, blank=True)

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    depth = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    thumbnail = models.URLField(max_length=500, blank=True)

    # Overall inventory stock from DummyJSON
    stock = models.PositiveIntegerField(default=0)

    # Independently selectable sales channels
    sales_channels = models.ManyToManyField(
        SalesChannel,
        related_name="products",
        blank=True,
    )

    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_available_in_store(self):
        return self.sales_channels.filter(code="in_person").exists()

    @property
    def is_available_online(self):
        return self.sales_channels.filter(code__in=["online", "mobile"]).exists()

    def __str__(self):
        return self.title


class Planogram(models.Model):
    fixture = models.OneToOneField(
        Fixture,
        on_delete=models.CASCADE,
        related_name="planogram",
    )

    name = models.CharField(max_length=150, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or f"Planogram - {self.fixture.name}"


class PlanogramItem(models.Model):
    planogram = models.ForeignKey(
        Planogram,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        MerchandiseProduct,
        on_delete=models.CASCADE,
        related_name="planogram_items",
    )

    quantity = models.PositiveIntegerField(default=1)

    facings = models.PositiveIntegerField(default=1)

    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["planogram", "product"],
                name="unique_product_per_planogram",
            )
        ]

    def __str__(self):
        return f"{self.product.title} x {self.quantity}"
