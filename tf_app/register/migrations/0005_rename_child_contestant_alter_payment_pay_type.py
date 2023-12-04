# Generated by Django 4.1 on 2023-12-04 12:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0004_child_identifier_alter_child_parent_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Child',
            new_name='Contestant',
        ),
        migrations.AlterField(
            model_name='payment',
            name='pay_type',
            field=models.CharField(choices=[('Mobile Money', 'MOBILE MONEY'), ('cash', 'CASH')], max_length=15),
        ),
    ]
