from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from core.models import BaseModel
from register.models import Contestant
from accounts.models import Judge

# Create your models here.

class MainCategory(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Main Category"
        verbose_name_plural = "Main Categories"

    def __str__(self):
        return self.name


class JudgingCriteria(models.Model):
    category = models.ForeignKey(MainCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ('category', 'name')

    def __str__(self):
        return f'{self.category} - {self.name}'


class Score(BaseModel):
    judge = models.ForeignKey(Judge, related_name='scores', on_delete=models.CASCADE)
    contestant = models.ForeignKey(Contestant, related_name='scores', on_delete=models.CASCADE)
    criteria = models.ForeignKey(JudgingCriteria, on_delete=models.CASCADE)
    score = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)]
    )

    class Meta:
        unique_together = ('judge', 'contestant', 'criteria')


class JudgeComment(BaseModel):
    judge = models.ForeignKey(Judge, related_name='comments', on_delete=models.CASCADE)
    contestant = models.ForeignKey(Contestant, related_name='comments', on_delete=models.CASCADE)
    comment = models.TextField()