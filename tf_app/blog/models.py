from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class Author(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(blank=True)


class Post(models.Model):
    author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True)
    created = models.DateTimeField(auto_now_add=True)
    like = models.IntegerField(default=0)
    title = models.CharField(max_length=200)
    copy = models.TextField()
    subcopy = models.TextField(blank=True)
    image = models.ImageField(blank=True)

    def like_post(self):
        """
        Increment the number of likes for the current blog post.
        """
        self.like += 1
        self.save()


class Comment(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100)
    content = models.TextField()
    like = models.IntegerField(default=0)

    def like_comment(self):
        """
        Increment the number of likes for the current blog post.
        """
        self.like += 1
        self.save()