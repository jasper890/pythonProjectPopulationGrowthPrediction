from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from io import BytesIO
import base64
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import csv

from .models import City, PopulationData, User
from .forms import LoginForm, AdminUserForm, CityForm, PopulationDataForm


def home(request):
    cities = City.objects.all()
    context = {'cities': []}

    for city in cities:
        data = PopulationData.objects.filter(city=city).order_by('year')
        if data.exists():
            years = np.array([d.year for d in data]).reshape(-1, 1)
            population = np.array([d.population_count for d in data])

            # Linear regression for prediction
            model = LinearRegression()
            model.fit(years, population)
            next_year = years[-1][0] + 1
            predicted = model.predict([[next_year]])[0]

            # Generate plot
            plt.figure()
            plt.plot(years, population, 'bo-', label='Actual')
            plt.plot(next_year, predicted, 'ro', label='Prediction')
            plt.title(f"{city.city_name} Population Growth")
            plt.xlabel("Year")
            plt.ylabel("Population")
            plt.legend()

            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            graphic = base64.b64encode(image_png).decode('utf-8')
            plt.close()

            # Prepare historical data with growth %
            history = []
            prev_pop = None
            for d in data:
                growth = None
                if prev_pop is not None:
                    growth = round((d.population_count - prev_pop) / prev_pop * 100, 2)
                prev_pop = d.population_count
                history.append({
                    'year': d.year,
                    'population': d.population_count,
                    'source': d.source,
                    'growth': growth
                })

            context['cities'].append({
                'id': city.id,
                'name': city.city_name,
                'region': city.region,
                'predicted_year': next_year,
                'predicted_population': int(predicted),
                'chart': graphic,
                'history': history
            })

    return render(request, 'analytics/home.html', context)

# Superadmin check decorator
def superadmin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.role == 'superadmin')(view_func)


# Login view
def login_view(request):
    form = LoginForm(request.POST or None)
    message = ""

    if request.method == "POST":
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                return redirect('dashboard')
            else:
                message = "Invalid username or password"

    return render(request, "analytics/login.html", {"form": form, "message": message})


# Logout view
def logout_view(request):
    logout(request)
    return redirect('login')


# Dashboard view
@login_required
def dashboard(request):
    cities = City.objects.all()
    context = {'cities': [], 'total_population': 0, 'total_cities': cities.count()}

    for city in cities:
        data = PopulationData.objects.filter(city=city).order_by('year')
        if data.exists():
            years = np.array([d.year for d in data]).reshape(-1, 1)
            population = np.array([d.population_count for d in data])

            # Linear regression for prediction
            model = LinearRegression()
            model.fit(years, population)
            next_year = years[-1][0] + 1
            predicted = model.predict([[next_year]])[0]

            # Update total population
            context['total_population'] += int(predicted)

            # Generate plot
            plt.figure(figsize=(4,3))
            plt.plot(years, population, 'bo-', label='Actual')
            plt.plot(next_year, predicted, 'ro', label='Predicted')
            plt.title(city.city_name)
            plt.xlabel("Year")
            plt.ylabel("Population")
            plt.tight_layout()
            plt.legend()

            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            chart = base64.b64encode(image_png).decode('utf-8')
            plt.close()

            context['cities'].append({
                'name': city.city_name,
                'region': city.region,
                'predicted_year': next_year,
                'predicted_population': int(predicted),
                'chart': chart
            })

    # Add forms for superadmin only
    if request.user.role == 'superadmin':
        context['admin_form'] = AdminUserForm()
        context['city_form'] = CityForm()
        context['population_form'] = PopulationDataForm()

    return render(request, 'analytics/dashboard.html', context)


# Add new admin (superadmin only)
@superadmin_required
def add_admin(request):
    if request.method == "POST":
        form = AdminUserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Admin added successfully!")
        else:
            messages.error(request, "Failed to add admin. Please check the form.")
    return redirect('dashboard')


# Add new city (superadmin only)
@superadmin_required
def add_city(request):
    if request.method == "POST":
        form = CityForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "City added successfully!")
        else:
            messages.error(request, "Failed to add city. Please check the form.")
    return redirect('dashboard')


# Add population data (superadmin only)
@superadmin_required
def add_population(request):
    if request.method == "POST":
        form = PopulationDataForm(request.POST)
        if form.is_valid():
            population = form.save(commit=False)  # don't save yet
            population.created_by = request.user  # assign current logged-in user
            population.save()  # now save
            messages.success(request, "Population data added successfully!")
        else:
            messages.error(request, "Failed to add population data. Please check the form.")
    return redirect('dashboard')

# Export city population CSV
@login_required
def export_city_csv(request, city_id):
    city = City.objects.get(id=city_id)
    data = PopulationData.objects.filter(city=city).order_by('year')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{city.city_name}_population.csv"'

    writer = csv.writer(response)
    writer.writerow(['Year', 'Population', 'Source'])
    for record in data:
        writer.writerow([record.year, record.population_count, record.source])

    return response
