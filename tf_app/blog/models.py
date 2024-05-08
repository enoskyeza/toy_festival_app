import os

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


# Create your models here.
def user_directory_path(instance, filename):
    # Get the model name (Author or Post)
    model_name = instance.__class__.__name__.lower()
    # Generate a slug from the filename
    slug = slugify(filename)
    # Upload to MEDIA_ROOT/user_<id>/model_name/<slug>
    return f'user_{instance.author.user.id}/{model_name}/{slug}'


class Author(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to=user_directory_path, blank=True)

    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name}'


class Post(models.Model):
    author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True)
    created = models.DateTimeField(auto_now_add=True)
    like = models.IntegerField(default=0)
    title = models.CharField(max_length=200)
    copy = models.TextField()
    subcopy = models.TextField(blank=True)
    image = models.ImageField(upload_to=user_directory_path, blank=True)

    def like_post(self):
        """
        Increment the number of likes for the current blog post.
        """
        self.like += 1
        self.save()


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100)
    content = models.TextField()
    like = models.IntegerField(default=0)

    def like_comment(self):
        """
        Increment the number of likes for the comment.
        """
        self.like += 1
        self.save()