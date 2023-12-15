from django.db import models

from register.models import Contestant
from judges.models import Judge

# Create your models here.

class MainCategory(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class JudgingCriteria(models.Model):
    category = models.ForeignKey(MainCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return f'{self.category} - {self.name}'

class Score(models.Model):
    judge = models.ForeignKey(Judge, on_delete=models.CASCADE)
    contestant = models.ForeignKey(Contestant, on_delete=models.CASCADE)
    criteria = models.ForeignKey(JudgingCriteria, on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=5, decimal_places=2)

class JudgeComment(models.Model):
    judge = models.ForeignKey(Judge, on_delete=models.CASCADE)
    contestant = models.ForeignKey(Contestant, on_delete=models.CASCADE)
    comment = models.TextField()