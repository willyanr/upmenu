import uuid
from django.db import migrations, models

def generate_uuids(apps, schema_editor):
    Restaurant = apps.get_model('core', 'Restaurant')
    for restaurant in Restaurant.objects.all():
        restaurant.restaurant_code = uuid.uuid4()
        restaurant.save()

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_restaurant_deliveryorder_restaurant_menu_restaurant_and_more'),  # Substitua pela última migração
    ]

    operations = [
        migrations.AddField(
            model_name='restaurant',
            name='restaurant_code',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.RunPython(generate_uuids, reverse_code=migrations.RunPython.noop),
    ]
