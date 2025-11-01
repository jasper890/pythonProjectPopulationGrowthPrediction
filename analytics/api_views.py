# analytics/api_views.py
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
from io import BytesIO
import base64
import numpy as np
import matplotlib

matplotlib.use('Agg')  # Use non-interactive backend BEFORE importing pyplot
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import csv
import json

from .models import City, PopulationData, User


# ------------------ Helpers & Base Classes ------------------

# Superadmin check decorator
def superadmin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.role == 'superadmin')(view_func)


class BasePopulationView:
    """
    Base class to provide common functionality for population-related views.
    """
    allowed_roles = ['superadmin', 'admin']

    def __init__(self):
        # Create TensorFlow model once and reuse it
        self._tf_model = None

    def check_permissions(self, request):
        if getattr(request.user, 'role', None) not in self.allowed_roles:
            return False
        return True

    def get_city(self, city_id):
        try:
            return City.objects.get(id=city_id)
        except City.DoesNotExist:
            return None

    def get_population_data(self, population_id):
        try:
            return PopulationData.objects.get(id=population_id)
        except PopulationData.DoesNotExist:
            return None

    def calculate_growth(self, population_history):
        """
        Calculates year-over-year growth for a list of PopulationData objects
        """
        history = []
        prev_pop = None
        for data in population_history:
            growth = None
            if prev_pop is not None and prev_pop > 0:
                growth = round((data.population_count - prev_pop) / prev_pop * 100, 2)
            prev_pop = data.population_count
            history.append({
                'Historyid': data.id,
                'year': data.year,
                'population': data.population_count,
                'source': data.source,
                'growth': growth
            })
        return history

    # def _get_or_create_tf_model(self):
    #     """Create TensorFlow model once and reuse it"""
    #     if self._tf_model is None:
    #         self._tf_model = tf.keras.Sequential([
    #             tf.keras.layers.Dense(units=1, input_shape=[1])
    #         ])
    #         self._tf_model.compile(optimizer='adam', loss='mean_squared_error')
    #     return self._tf_model

    def predict_next_year_population(self, population_history):
        """
        Predict next year's population using Linear Regression (scikit-learn).
        Much faster and still accurate for population trends.
        """
        data = list(population_history.order_by('year'))

        if len(data) < 2:
            if data:
                return data[-1].year + 1, int(data[-1].population_count)
            return None, 0

        # Prepare training data
        years = np.array([d.year for d in data]).reshape(-1, 1)
        populations = np.array([d.population_count for d in data])

        # Train the linear regression model
        model = LinearRegression()
        model.fit(years, populations)

        # Predict for next year
        next_year = years[-1][0] + 1
        predicted_population = model.predict([[next_year]])[0]

        return int(next_year), int(predicted_population)

    def generate_chart_base64(self, city_name, population_history):
        """
        Generate a line chart of population data with a simple linear prediction
        """
        if not population_history.exists():
            return None

        years = np.array([d.year for d in population_history]).reshape(-1, 1)
        population = np.array([d.population_count for d in population_history])

        model = LinearRegression()
        model.fit(years, population)
        next_year = years[-1][0] + 1
        predicted = model.predict([[next_year]])[0]

        # Create figure with explicit backend
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.plot(years, population, 'bo-', label='Actual')
        ax.plot(next_year, predicted, 'ro', label='Predicted')
        ax.set_title(f"{city_name} Population Growth")
        ax.set_xlabel("Year")
        ax.set_ylabel("Population")
        ax.legend()
        fig.tight_layout()

        buffer = BytesIO()
        fig.savefig(buffer, format='png')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()

        # Close figure to free memory
        plt.close(fig)

        chart = base64.b64encode(image_png).decode('utf-8')
        return chart


# ------------------ API Views ------------------

# --- City APIs ---
@login_required
def cities_api(request):
    cities_data = []
    cities = City.objects.all()
    base = BasePopulationView()

    for city in cities:
        data = PopulationData.objects.filter(city=city).order_by('year')
        predicted_year, predicted_population = base.predict_next_year_population(data)
        chart = base.generate_chart_base64(city.city_name, data)

        history = base.calculate_growth(data)

        cities_data.append({
            'id': city.id,
            'name': city.city_name,
            'region': city.region,
            'predicted_year': predicted_year,
            'predicted_population': predicted_population,
            'chart': chart,
            'history': history
        })

    return JsonResponse({'cities': cities_data})


@login_required
def export_city_csv_api(request, city_id):
    base = BasePopulationView()
    city = base.get_city(city_id)
    if not city:
        return JsonResponse({'status': 'error', 'message': 'City not found'}, status=404)

    data = PopulationData.objects.filter(city=city).order_by('year')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{city.city_name}_population.csv"'
    writer = csv.writer(response)
    writer.writerow(['Year', 'Population', 'Source'])
    for record in data:
        writer.writerow([record.year, record.population_count, record.source])
    return response


@login_required
def stats_api(request):
    base = BasePopulationView()
    total_population = 0
    cities = City.objects.all()

    for city in cities:
        data = PopulationData.objects.filter(city=city).order_by('year')
        _, predicted_population = base.predict_next_year_population(data)
        total_population += predicted_population

    return JsonResponse({
        'total_cities': cities.count(),
        'predicted_total_population': total_population
    })


# --- Authentication ---
@csrf_exempt
def api_login(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST method required"}, status=405)

    try:
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            return JsonResponse({"status": "error", "message": "Username and password required"}, status=400)

        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return JsonResponse({
                "status": "success",
                "token": token.key,
                "role": user.role,
                "username": user.username,
                "email": user.email,
                "userID": user.id
            })
        else:
            return JsonResponse({"status": "error", "message": "Invalid credentials"}, status=401)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)


# --- City Details ---
@api_view(['GET'])
@permission_classes([AllowAny])
def get_cities_with_population(request):
    base = BasePopulationView()
    cities = City.objects.all()
    result = []

    for city in cities:
        population_data = PopulationData.objects.filter(city=city).order_by('year')
        history = base.calculate_growth(population_data)
        predicted_year, predicted_population = base.predict_next_year_population(population_data)

        city_data = {
            'id': city.id,
            'name': city.city_name,
            'region': city.region,
            'predicted_year': predicted_year,
            'predicted_population': predicted_population,
            'history': history
        }
        result.append(city_data)

    return Response(result, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_city_by_id(request, city_id):
    base = BasePopulationView()
    city = base.get_city(city_id)
    if not city:
        return Response({'error': 'City not found'}, status=status.HTTP_404_NOT_FOUND)

    population_data = PopulationData.objects.filter(city=city).order_by('year')
    history = base.calculate_growth(population_data)
    predicted_year, predicted_population = base.predict_next_year_population(population_data)

    city_data = {
        'id': city.id,
        'name': city.city_name,
        'region': city.region,
        'predicted_year': predicted_year,
        'predicted_population': predicted_population,
        'history': history
    }
    return Response(city_data, status=status.HTTP_200_OK)


# --- Admin Management ---
@api_view(['POST'])
@permission_classes([AllowAny])
def create_admin(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email')

    if not username or not password:
        return Response({'error': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)

    new_admin = User.objects.create_user(username=username, password=password, email=email, role='admin')
    return Response({'message': f'Admin {username} created successfully.'}, status=status.HTTP_201_CREATED)


# --- City Management ---
@api_view(['POST'])
def add_city(request):
    base = BasePopulationView()
    if not base.check_permissions(request):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    city_name = request.data.get('city_name')
    region = request.data.get('region', '')

    if not city_name:
        return Response({'error': 'City name is required.'}, status=status.HTTP_400_BAD_REQUEST)

    if City.objects.filter(city_name__iexact=city_name).exists():
        return Response({'error': 'City already exists.'}, status=status.HTTP_400_BAD_REQUEST)

    city = City.objects.create(city_name=city_name, region=region)
    return Response({'message': f'City {city_name} added successfully.'}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def add_population_data(request):
    base = BasePopulationView()
    if not base.check_permissions(request):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    city_id = request.data.get('city_id')
    year = request.data.get('year')
    population_count = request.data.get('population_count')
    source = request.data.get('source', '')

    city = base.get_city(city_id)
    if not city:
        return Response({'error': 'City not found.'}, status=status.HTTP_404_NOT_FOUND)

    data = PopulationData.objects.create(
        city=city,
        year=year,
        population_count=population_count,
        source=source,
        created_by=request.user
    )

    return Response({
        'success': True,
        'message': 'Population data added successfully.',
        'data': {
            'id': data.id,
            'year': data.year,
            'population_count': data.population_count,
            'source': data.source,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
def update_population_data(request, population_id):
    base = BasePopulationView()
    if not base.check_permissions(request):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    data = base.get_population_data(population_id)
    if not data:
        return Response({'error': 'Data not found.'}, status=status.HTTP_404_NOT_FOUND)

    data.year = request.data.get('year', data.year)
    data.population_count = request.data.get('population_count', data.population_count)
    data.source = request.data.get('source', data.source)
    data.save()

    return Response({'message': 'Population data updated successfully.'}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_city(request, city_id):
    base = BasePopulationView()
    city = base.get_city(city_id)
    if not city:
        return Response({'error': 'City not found.'}, status=status.HTTP_404_NOT_FOUND)

    city_name = city.city_name
    city.delete()
    return Response({'message': f'City "{city_name}" and its population data deleted successfully.'},
                    status=status.HTTP_200_OK)


@api_view(['DELETE'])
def delete_population_data(request, population_id):
    base = BasePopulationView()
    if not base.check_permissions(request):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    data = base.get_population_data(population_id)
    if not data:
        return Response({'error': 'Population data not found.'}, status=status.HTTP_404_NOT_FOUND)

    data.delete()
    return Response({'message': 'Population data deleted successfully.'}, status=status.HTTP_200_OK)


# --- Admin Helper APIs ---
def get_admins(request):
    admins = User.objects.filter(role='admin')
    data = [{'id': a.id, 'username': a.username, 'email': a.email, 'role': a.role} for a in admins]
    return JsonResponse(data, safe=False)


@api_view(['DELETE'])
def delete_admin(request, admin_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    try:
        user = User.objects.get(id=admin_id, role='admin')
        user.delete()
        return JsonResponse({'message': 'Admin deleted successfully'}, status=200)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Admin not found'}, status=404)

@api_view(['PUT']) # optional, can remove if you want open access
def update_city(request, city_id):
    """
    Update city name and region by ID.
    Example body: {"city_name": "Quezon City", "region": "NCR"}
    """
    city = get_object_or_404(City, id=city_id)
    data = request.data

    city_name = data.get('city_name')
    region = data.get('region')

    if city_name:
        city.city_name = city_name
    if region:
        city.region = region

    city.save()

    return Response({
        'message': 'City updated successfully',
        'city': {
            'id': city.id,
            'city_name': city.city_name,
            'region': city.region
        }
    }, status=status.HTTP_200_OK)