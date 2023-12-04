from django.contrib.auth.models import User
from django.db import models

# Create your models here.

class Judge(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
