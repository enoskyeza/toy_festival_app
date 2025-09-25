# Generated migration for adding timestamp fields to ProgramForm

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0012_add_is_active_to_program_form'),
    ]

    operations = [
        migrations.AddField(
            model_name='programform',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='programform',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
