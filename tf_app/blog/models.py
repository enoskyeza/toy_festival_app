import os

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.contenttypes.fields import GenericRelation

from accounts.models import Author
from core.models import BaseModel
from gallery.models import Media


class Category(BaseModel):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(BaseModel):
    name = models.CharField(max_length=30, unique=True)
    slug = models.SlugField(max_length=40, unique=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Post(BaseModel):
    STATUS_CHOICES = [('draft', 'Draft'), ('published', 'Published')]

    author        = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True)
    title         = models.CharField(max_length=200)
    slug          = models.SlugField(max_length=220, unique=True, blank=True)
    excerpt       = models.CharField(max_length=255, blank=True)
    content       = models.TextField()
    featured_img  = models.ImageField(upload_to='posts/%Y/%m/%d/', blank=True)
    categories    = models.ManyToManyField(Category, blank=True)
    tags          = models.ManyToManyField(Tag, blank=True)
    media         = GenericRelation(Media)  # ⬅ attach gallery media here
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    published_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-published_at', '-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def likes_count(self):
        return self.post_likes.count()

    def __str__(self):
        return self.title


class PostLike(BaseModel):
    """Tracks per-user likes on posts."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='post_likes', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'post')


class Comment(BaseModel):
    post    = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    author  = models.CharField(max_length=100)
    email   = models.EmailField()
    content = models.TextField()
    active  = models.BooleanField(default=True)

    class Meta:
        ordering = ['created_at']

    @property
    def likes_count(self):
        return self.comment_likes.count()

    def __str__(self):
        return f"Comment by {self.author} on {self.post}"


class CommentLike(BaseModel):
    """Tracks per-user likes on comments."""
    user    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, related_name='comment_likes', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'comment')

#
#
# # Create your models here.
# def user_directory_path(instance, filename):
#     # Get the model name (Author or Post)
#     model_name = instance.__class__.__name__.lower()
#     # Generate a slug from the filename
#     extension = os.path.splitext(filename)[1]
#     slug = slugify(os.path.splitext(filename)[0])
#
#     # Check if the instance is Author or Post and set the user_id accordingly
#     if model_name == 'author':
#         user_id = instance.user.id
#     elif model_name == 'post':
#         user_id = instance.author.user.id
#     else:
#         # Handle unexpected model types if necessary
#         user_id = 'default'
#
#     # Upload to MEDIA_ROOT/user_<id>/model_name/<slug>
#     return f'user_{user_id}/{model_name}/{slug}{extension}'
#
#
# class Author(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     image = models.ImageField(upload_to=user_directory_path, blank=True)
#
#     def __str__(self):
#         return f'{self.user.first_name} {self.user.last_name}'
#
#
# class Post(models.Model):
#     author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True)
#     created = models.DateTimeField(auto_now_add=True)
#     like = models.IntegerField(default=0)
#     title = models.CharField(max_length=200)
#     copy = models.TextField()
#     subcopy = models.TextField(blank=True)
#     image = models.ImageField(upload_to=user_directory_path, blank=True)
#
#     def like_post(self):
#         """
#         Increment the number of likes for the current blog post.
#         """
#         self.like += 1
#         self.save()
#
#
# class Comment(models.Model):
#     post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
#     created = models.DateTimeField(auto_now_add=True)
#     name = models.CharField(max_length=100)
#     content = models.TextField()
#     like = models.IntegerField(default=0)
#
#     def like_comment(self):
#         """
#         Increment the number of likes for the comment.
#         """
#         self.like += 1
#         self.save()