# Generated migration for adding PARTIALLY_PAID status to Registration model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0001_initial'),  # Replace with your actual latest migration
    ]

    operations = [
        migrations.AlterField(
            model_name='registration',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('partially_paid', 'Partially Paid'),
                    ('paid', 'Paid'),
                    ('cancelled', 'Cancelled'),
                    ('refunded', 'Refunded')
                ],
                default='pending',
                max_length=20  # Increased to accommodate 'partially_paid'
            ),
        ),
    ]
