from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.dispatch import receiver

User = get_user_model()

@receiver(post_migrate)
def create_default_superadmin(sender, **kwargs):
    if not User.objects.filter(username='superadmin').exists():
        User.objects.create_superuser(
            username='superadmin',
            email='superadmin@example.com',
            password='SuperSecret123!',
            role='superadmin'
        )
        print("Default superadmin created: superadmin / SuperSecret123!")

