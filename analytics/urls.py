from django.urls import path
from . import views  # existing views
from . import api_views  # new API views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # ---------------- Template / Web Views ----------------
    # path('', views.home, name='home'),  # public home page
    # path('dashboard/', views.dashboard, name='dashboard'),  # protected dashboard
    # path('export/<int:city_id>/', views.export_city_csv, name='export_city_csv'),
    #
    # # Superadmin forms
    # path('add_admin/', views.add_admin, name='add_admin'),
    # path('add_city/', views.add_city, name='add_city'),
    # path('add_population/', views.add_population, name='add_population'),

    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='analytics/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

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
]
