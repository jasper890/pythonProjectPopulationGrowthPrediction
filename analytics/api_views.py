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
from datetime import datetime
from io import BytesIO
import base64
import numpy as np


 # Use non-interactive backend BEFORE importing pyplot

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
        Predict next year's population using Linear Regression (scikit-learn),
        starting from the current year, not the last year in the data.
        """
        data = list(population_history.order_by('year'))

        if len(data) < 2:
            if data:
                # If less than 2 data points, return current year + 1 with last known population
                current_year = datetime.now().year
                return current_year + 1, int(data[-1].population_count)
            return None, 0

        # Prepare training data
        years = np.array([d.year for d in data]).reshape(-1, 1)
        populations = np.array([d.population_count for d in data])

        # Train the linear regression model
        model = LinearRegression()
        model.fit(years, populations)

        # Predict for next year starting from current year
        current_year = datetime.now().year
        next_year = current_year + 1
        predicted_population = model.predict([[next_year]])[0]

        return int(next_year), int(predicted_population)


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


@api_view(['GET'])
@permission_classes([AllowAny])
def generate_ml_summary_report(request):
    """
    Generate a comprehensive paragraph summary of population predictions
    for the next year using machine learning analysis.
    """
    base = BasePopulationView()
    cities = City.objects.all()

    if not cities.exists():
        return Response({
            'summary': 'No city data available for analysis.',
            'year': datetime.now().year + 1
        }, status=status.HTTP_200_OK)

    # Collect predictions and analysis data
    total_predicted_population = 0
    city_predictions = []
    growth_rates = []
    current_year = datetime.now().year
    next_year = current_year + 1

    for city in cities:
        population_data = PopulationData.objects.filter(city=city).order_by('year')

        if population_data.exists():
            predicted_year, predicted_population = base.predict_next_year_population(population_data)

            # Calculate average historical growth rate
            history = base.calculate_growth(population_data)
            valid_growth = [h['growth'] for h in history if h['growth'] is not None]
            avg_growth = np.mean(valid_growth) if valid_growth else 0

            # Get latest actual population
            latest_data = population_data.last()
            latest_population = latest_data.population_count

            # Calculate predicted change
            predicted_change = predicted_population - latest_population
            predicted_growth_rate = (predicted_change / latest_population * 100) if latest_population > 0 else 0

            city_predictions.append({
                'name': city.city_name,
                'region': city.region,
                'current_population': latest_population,
                'predicted_population': predicted_population,
                'predicted_change': predicted_change,
                'predicted_growth_rate': predicted_growth_rate,
                'avg_historical_growth': avg_growth
            })

            total_predicted_population += predicted_population
            growth_rates.append(predicted_growth_rate)

    # Sort cities by predicted population
    city_predictions.sort(key=lambda x: x['predicted_population'], reverse=True)

    # Identify key insights
    fastest_growing = max(city_predictions, key=lambda x: x['predicted_growth_rate']) if city_predictions else None
    slowest_growing = min(city_predictions, key=lambda x: x['predicted_growth_rate']) if city_predictions else None
    largest_city = city_predictions[0] if city_predictions else None
    avg_growth_rate = np.mean(growth_rates) if growth_rates else 0

    # Generate comprehensive paragraph summary
    summary_parts = []

    # Opening statement
    summary_parts.append(
        f"Based on machine learning analysis using Linear Regression models trained on historical population data, "
        f"the total projected population across all {len(city_predictions)} cities for {next_year} is estimated at "
        f"{total_predicted_population:,} people, representing an overall average growth rate of {avg_growth_rate:.2f}%."
    )

    # Largest city insight
    if largest_city:
        summary_parts.append(
            f"{largest_city['name']} in {largest_city['region']} is predicted to remain the most populous city "
            f"with {largest_city['predicted_population']:,} residents, growing by {largest_city['predicted_change']:,} "
            f"people ({largest_city['predicted_growth_rate']:.2f}%) from its current population of {largest_city['current_population']:,}."
        )

    # Growth dynamics
    if fastest_growing and slowest_growing:
        summary_parts.append(
            f"Population dynamics vary significantly across regions, with {fastest_growing['name']} "
            f"experiencing the most rapid growth at {fastest_growing['predicted_growth_rate']:.2f}%, "
            f"while {slowest_growing['name']} shows the slowest expansion at {slowest_growing['predicted_growth_rate']:.2f}%."
        )

    # Top 3 cities breakdown
    if len(city_predictions) >= 3:
        top_three = city_predictions[:3]
        top_three_text = ", ".join([
            f"{c['name']} ({c['predicted_population']:,})" for c in top_three[:2]
        ]) + f", and {top_three[2]['name']} ({top_three[2]['predicted_population']:,})"

        summary_parts.append(
            f"The three most populous cities projected for {next_year} are {top_three_text}, "
            f"collectively accounting for a substantial portion of the total urban population."
        )

    # Methodology note
    summary_parts.append(
        f"These predictions are generated through supervised machine learning algorithms that analyze "
        f"year-over-year population trends, historical growth patterns, and demographic trajectories, "
        f"providing data-driven forecasts to support urban planning and policy decisions for the upcoming year."
    )

    # Combine all parts into one paragraph
    full_summary = " ".join(summary_parts)

    return Response({
        'summary': full_summary,
        'year': next_year,
        'total_cities': len(city_predictions),
        'total_predicted_population': total_predicted_population,
        'average_growth_rate': round(avg_growth_rate, 2),
        'methodology': 'Linear Regression Machine Learning Model',
        'generated_at': datetime.now().isoformat()
    }, status=status.HTTP_200_OK)