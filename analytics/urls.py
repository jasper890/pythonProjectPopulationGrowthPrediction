from django.urls import path,  re_path
from . import views  # existing views
from . import api_views  # new API views
from django.contrib.auth import views as auth_views
from . import views as analytics_views

urlpatterns = [

    # ---------------- API Endpoints ----------------
    path('api/cities/', api_views.get_cities_with_population, name='cities-list'),
    path('api/cities/<int:city_id>/', api_views.get_city_by_id, name='city-detail'),
    # path('api/add_population/', api_views.add_population_api, name='add_population_api'),
    path('api/export_city/<int:city_id>/', api_views.export_city_csv_api, name='export_city_csv_api'),
    path('api/stats/', api_views.stats_api, name='stats_api'),
    path('api/login/', api_views.api_login, name='api_login'),
    path('api/admin/create/', api_views.create_admin, name='create_admin'),
    path('api/city/add/', api_views.add_city, name='add_city'),
    path('api/city/delete/<int:city_id>/', api_views.delete_city, name='delete_city'),
    path('api/population/add/', api_views.add_population_data, name='add_population_data'),
    path('api/population/update/<int:population_id>/', api_views.update_population_data, name='update_population_data'),
    path('api/population/delete/<int:population_id>/', api_views.delete_population_data, name='delete_population_data'),
    path('api/admins/', api_views.get_admins, name='get_admins'),
    path('api/admins/delete/<int:admin_id>/', api_views.delete_admin, name='delete_admin'),
    path('api/city/update/<int:city_id>/', api_views.update_city, name='update_city'),
    path('api/overall_summary/', api_views.generate_ml_summary_report, name='overall-summary'),
    # Also accept requests without the /api prefix (some builds call endpoints like `/cities`)
    path('cities/', api_views.get_cities_with_population, name='cities-list-noapi'),
    path('cities/<int:city_id>/', api_views.get_city_by_id, name='city-detail-noapi'),
    path('city/add/', api_views.add_city, name='add_city-noapi'),
    path('city/delete/<int:city_id>/', api_views.delete_city, name='delete_city-noapi'),
    path('city/update/<int:city_id>/', api_views.update_city, name='update_city-noapi'),
    path('population/add/', api_views.add_population_data, name='add_population_data-noapi'),
    path('population/update/<int:population_id>/', api_views.update_population_data, name='update_population_data-noapi'),
    path('population/delete/<int:population_id>/', api_views.delete_population_data, name='delete_population_data-noapi'),
    path('admins/', api_views.get_admins, name='get_admins-noapi'),
    path('admins/delete/<int:admin_id>/', api_views.delete_admin, name='delete_admin-noapi'),
    path('admin/create/', api_views.create_admin, name='create_admin-noapi'),
    # Catch-all for frontend routes — but exclude API paths so API requests return JSON
    re_path(r'^(?!api/).*$', analytics_views.frontend, name='frontend'),

]
