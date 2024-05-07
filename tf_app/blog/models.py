from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Post(models.Model):
    created = models.DateTimeField(auto_now_add=True)
# class Comments(models.Model):
#     created = models.DateTimeField(auto_now_add=True)
#     comment = models.CharField()
#     user = models.CharField()
#
# class Likes(models.Model):
#     number = models.IntegerField()
#
# class Author(models.Model):
#     user = models.OneToOneField(User)
#     name = models.CharField()
#     image = models.ImageField()
# class Post(models.Model):
#     created = models.DateTimeField(auto_now_add=True)
#     author = models.ForeignKey(Author)
#     tag = models.CharField()
#     title = models.TextField()
#     copy = models.TextField()
#     subcopy = models.TextField()
#     comments = models.ManyToOneRel(Comments)
#     image = models.ImageField()
#
