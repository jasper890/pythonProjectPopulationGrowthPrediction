from django.urls import path
from . import views  # relative import works because this urls.py is inside analytics
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),  # public home page
    path('dashboard/', views.dashboard, name='dashboard'),  # protected dashboard
    path('export/<int:city_id>/', views.export_city_csv, name='export_city_csv'),
    # Superadmin forms
    path('add_admin/', views.add_admin, name='add_admin'),
    path('add_city/', views.add_city, name='add_city'),
    path('add_population/', views.add_population, name='add_population'),
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='analytics/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),


]
