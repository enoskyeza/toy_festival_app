from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class Author(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    pass


class Post(models.Model):
    author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True)
    created = models.DateTimeField(auto_now_add=True)
    like = models.IntegerField(default=0)
    title = models.CharField(max_length=200)
    copy = models.TextField()
    subcopy = models.TextField()
    image = models.ImageField()

    def like_post(self):
        """
        Increment the number of likes for the current blog post.
        """
        self.like += 1
        self.save()

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
