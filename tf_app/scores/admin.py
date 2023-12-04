from django.contrib import admin
from .models import MainCategory, JudgingCriteria, Score


# Individual Register normal.

admin.site.register(MainCategory)
admin.site.register(JudgingCriteria)
admin.site.register(Score)
