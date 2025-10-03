from django.db import migrations, models


def populate_step_metadata(apps, schema_editor):
    ProgramForm = apps.get_model('register', 'ProgramForm')
    FormField = apps.get_model('register', 'FormField')

    for form in ProgramForm.objects.all():
        fields = list(FormField.objects.filter(form=form).order_by('order', 'id'))
        if not fields:
            form.step_metadata = []
            form.layout_config = {'columns': 4}
            form.save(update_fields=['step_metadata', 'layout_config'])
            continue

        buckets = {}
        step_list = []
        for field in fields:
            bucket = field.order // 100
            key = f"step-{bucket + 1}"
            if key not in buckets:
                title_suffix = len(buckets) + 1
                buckets[key] = {
                    'key': key,
                    'title': f'Additional Information {title_suffix}',
                    'description': 'Program-specific requirements',
                    'order': title_suffix,
                    'per_participant': True,
                    'layout': {'columns': 4},
                }
                step_list.append(buckets[key])
            field.step_key = key
            field.column_span = 4
            field.save(update_fields=['step_key', 'column_span'])

        form.step_metadata = step_list
        form.layout_config = {'columns': 4}
        form.save(update_fields=['step_metadata', 'layout_config'])


def unpopulate_step_metadata(apps, schema_editor):
    ProgramForm = apps.get_model('register', 'ProgramForm')
    FormField = apps.get_model('register', 'FormField')
    FormField.objects.update(step_key='', column_span=4)
    ProgramForm.objects.update(step_metadata=[], layout_config={})


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0014_formresponse_registration'),
    ]

    operations = [
        migrations.AddField(
            model_name='formfield',
            name='column_span',
            field=models.PositiveSmallIntegerField(default=4, help_text='Width of the field within a 4-column grid (1-4)'),
        ),
        migrations.AddField(
            model_name='formfield',
            name='step_key',
            field=models.CharField(blank=True, default='', help_text='Identifier of the step this field belongs to', max_length=120),
        ),
        migrations.AddField(
            model_name='programform',
            name='layout_config',
            field=models.JSONField(blank=True, default=dict, help_text='Global layout configuration for dynamic steps'),
        ),
        migrations.AddField(
            model_name='programform',
            name='step_metadata',
            field=models.JSONField(blank=True, default=list, help_text='Ordered step definitions for dynamic fields'),
        ),
        migrations.RunPython(populate_step_metadata, unpopulate_step_metadata, elidable=True),
    ]
