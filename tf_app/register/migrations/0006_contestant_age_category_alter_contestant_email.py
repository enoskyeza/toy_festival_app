# Generated by Django 4.1 on 2023-12-15 03:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0005_rename_child_contestant_alter_payment_pay_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='contestant',
            name='age_category',
            field=models.CharField(blank=True, choices=[('young', 'Young'), ('middle', 'Middle'), ('old', 'Old'), ('Unknown', 'Unknown')], default='Unknown', max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='contestant',
            name='email',
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]