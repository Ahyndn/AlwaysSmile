from django.urls import path

from . import views
from .planogram import planogram_views

app_name = "dashboard"

urlpatterns = [
    # MAIN DASHBOARD
    path("", views.overview, name="overview"),
    path("inventory/", views.inventory, name="inventory"),
    path("abc-analysis/", views.abc_analysis, name="abc_analysis"),
    # SAVED ORDERS
    path("saved-orders/", views.saved_orders, name="saved_orders"),
    path(
        "saved-orders/remove/<str:source>/<str:product_id>/",
        views.remove_saved_order,
        name="remove_saved_order",
    ),
    path("print-orders/", views.submit_saved_orders, name="submit_saved_orders"),
    # INVENTORY
    path("out-of-stock/", views.out_of_stock, name="out_of_stock"),
    path("low-stock/", views.low_stock, name="low_stock"),
    path("in-stock/", views.in_stock, name="in_stock"),
    # CUSTOMER REVIEWS
    path("customer-reviews/", views.customer_review, name="customer_review"),
    # LOGISTICS
    path("logistics/", views.logistics, name="logistics"),
    # MERCHANDISE
    path("merchandise/", views.merchandise, name="merchandise"),
    path(
        "merchandise/floor/<int:floor_id>/",
        views.merchandise_floor_data,
        name="merchandise_floor_data",
    ),
    path(
        "merchandise/products/",
        views.merchandise_products,
        name="merchandise_products",
    ),
    path(
        "merchandise/floor/<int:floor_id>/fixtures/add/",
        views.merchandise_add_fixture,
        name="merchandise_add_fixture",
    ),
    path(
        "merchandise/fixtures/<int:fixture_id>/delete/",
        views.merchandise_delete_fixture,
        name="merchandise_delete_fixture",
    ),
    path(
        "merchandise/floor/<int:floor_id>/clear/",
        views.merchandise_clear_floor,
        name="merchandise_clear_floor",
    ),
    path(
        "merchandise/fixtures/<int:fixture_id>/planogram/add/",
        views.merchandise_add_planogram_item,
        name="merchandise_add_planogram_item",
    ),
    path(
        "merchandise/planogram-items/<int:item_id>/delete/",
        views.merchandise_delete_planogram_item,
        name="merchandise_delete_planogram_item",
    ),
    path(
        "merchandise/floor/<int:floor_id>/export/",
        views.merchandise_export_floor,
        name="merchandise_export_floor",
    ),
    # PLANOGRAM
    path(
        "planogram/",
        planogram_views.planogram_dashboard,
        name="planogram_dashboard",
    ),
    path(
        "planogram/products/",
        planogram_views.product_catalog,
        name="product_catalog",
    ),
    path(
        "planogram/products/synchronize/",
        planogram_views.synchronize_product_catalog,
        name="synchronize_product_catalog",
    ),
    path(
        "planogram/fixture/<int:fixture_id>/",
        planogram_views.fixture_planogram,
        name="fixture_planogram",
    ),
    path(
        "planogram/fixture/<int:fixture_id>/add/",
        planogram_views.add_fixture_product,
        name="add_fixture_product",
    ),
    path(
        "planogram/fixture/<int:fixture_id>/remove/<int:item_id>/",
        planogram_views.remove_fixture_product,
        name="remove_fixture_product",
    ),
    path(
        "planogram/fixture/<int:fixture_id>/update/<int:item_id>/",
        planogram_views.update_fixture_product,
        name="update_fixture_product",
    ),
    path(
        "planogram/fixture/<int:fixture_id>/data/",
        planogram_views.fixture_planogram_data,
        name="fixture_planogram_data",
    ),
    path(
        "planogram/fixture/<int:fixture_id>/reorder/",
        planogram_views.reorder_fixture_products,
        name="reorder_fixture_products",
    ),
]
