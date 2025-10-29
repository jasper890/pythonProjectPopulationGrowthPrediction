from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission

class User(AbstractUser):
    ROLE_CHOICES = (
        ('superadmin', 'Super Admin'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    # Fix reverse accessor clash
    groups = models.ManyToManyField(
        Group,
        related_name='analytics_users',  # changed from default 'user_set'
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='analytics_users_permissions',  # changed
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

class City(models.Model):
    city_name = models.CharField(max_length=100, unique=True)
    region = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.city_name

class PopulationData(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    year = models.IntegerField()
    population_count = models.BigIntegerField()
    source = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.city.city_name} - {self.year}"
