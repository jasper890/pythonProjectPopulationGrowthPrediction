from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import City, PopulationData

User = get_user_model()


@receiver(post_migrate)
def seed_initial_data(sender, **kwargs):
    # Stop running on apps that are not ours
    if sender.name not in ["analytics"]:
        return

    # ------------------------------------------------------
    # 1. CREATE SUPERADMIN (ONLY IF DOES NOT EXIST)
    # ------------------------------------------------------
    superadmin = User.objects.filter(username="superadmin").first()

    if not superadmin:
        superadmin = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.com",
            password="SuperSecret123!",
            role="superadmin",
        )
        print("✔ Default superadmin created: superadmin / SuperSecret123!")
    else:
        print("✔ Superadmin already exists.")

    # ------------------------------------------------------
    # 2. CREATE DEFAULT CITIES (ONLY IF MISSING)
    # ------------------------------------------------------
    default_cities = [
        {"city_name": "Manila", "region": "NCR"},
        {"city_name": "Quezon City", "region": "NCR"},
        {"city_name": "Caloocan", "region": "NCR"},
        {"city_name": "Pasig", "region": "NCR"},
        {"city_name": "Makati", "region": "NCR"},
        {"city_name": "Taguig", "region": "NCR"},
        {"city_name": "Marikina", "region": "NCR"},
        {"city_name": "Cebu City", "region": "Region VII"},
        {"city_name": "Mandaue", "region": "Region VII"},
        {"city_name": "Lapu-Lapu", "region": "Region VII"},
        {"city_name": "Davao City", "region": "Region XI"},
        {"city_name": "General Santos", "region": "Region XII"},
        {"city_name": "Zamboanga City", "region": "Region IX"},
        {"city_name": "Iloilo City", "region": "Region VI"},
        {"city_name": "Bacolod", "region": "Region VI"},
        {"city_name": "Cagayan de Oro", "region": "Region X"},
        {"city_name": "Baguio City", "region": "CAR"},
        {"city_name": "Dagupan", "region": "Region I"},
        {"city_name": "San Fernando", "region": "Region III"},
        {"city_name": "Angeles City", "region": "Region III"},
    ]

    city_objects = {}

    for data in default_cities:
        city, created = City.objects.get_or_create(
            city_name=data["city_name"],
            defaults={"region": data["region"]},
        )
        city_objects[data["city_name"]] = city

        if created:
            print(f"✔ Created city: {city.city_name}")
        else:
            print(f"✔ City already exists: {city.city_name}")

    # ------------------------------------------------------
    # 3. CREATE POPULATION DATA (ONLY IF MISSING)
    # ------------------------------------------------------
    years = list(range(2015, 2025))

    base_populations = {
        "Manila": 1750000,
        "Quezon City": 2930000,
        "Caloocan": 1600000,
        "Pasig": 755000,
        "Makati": 630000,
        "Taguig": 940000,
        "Marikina": 460000,
        "Cebu City": 980000,
        "Mandaue": 360000,
        "Lapu-Lapu": 500000,
        "Davao City": 1640000,
        "General Santos": 700000,
        "Zamboanga City": 850000,
        "Iloilo City": 460000,
        "Bacolod": 600000,
        "Cagayan de Oro": 720000,
        "Baguio City": 350000,
        "Dagupan": 180000,
        "San Fernando": 350000,
        "Angeles City": 550000,
    }

    for city_name, base_population in base_populations.items():
        city = city_objects[city_name]
        pop = base_population

        for year in years:
            # Check if not existing
            exists = PopulationData.objects.filter(city=city, year=year).exists()

            if not exists:
                PopulationData.objects.create(
                    city=city,
                    year=year,
                    population_count=pop,
                    source="Seeded Data",
                    created_by=superadmin,
                )
                print(f"✔ Created population {year} for {city_name}: {pop}")
            else:
                print(f"✔ Population data already exists: {city_name} / {year}")

            # Increase population 2% each year
            pop = int(pop * 1.02)

    print("✔ All default population data created if missing.")
