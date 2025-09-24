from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Tag, Post, PostLike, Comment, CommentLike
from gallery.admin import MediaInline


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    ordering = ('name',)


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1
    readonly_fields = ('created_at', 'updated_at', 'likes_count')
    fields = ('author', 'email', 'content', 'active', 'likes_count', 'created_at')


class PostLikeInline(admin.TabularInline):
    model = PostLike
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'published_at', 'likes_count', 'created_at')
    list_filter = ('status', 'author', 'categories', 'tags', 'created_at')
    search_fields = ('title', 'excerpt', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('likes_count', 'preview_featured')

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author', 'status', 'published_at')
        }),
        ('Content', {
            'fields': ('excerpt', 'content', 'featured_img', 'preview_featured')
        }),
        ('Relations', {
            'fields': ('categories', 'tags', 'likes_count')
        }),
    )

    inlines = [MediaInline, CommentInline, PostLikeInline]

    def preview_featured(self, obj):
        if obj.featured_img:
            return format_html('<img src="{}" style="max-height: 150px;" />', obj.featured_img.url)
        return "-"
    preview_featured.short_description = "Featured Image"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'email', 'post', 'active', 'likes_count', 'created_at')
    list_filter = ('active', 'created_at')
    search_fields = ('author', 'email', 'content')


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'post__title')


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'comment', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'comment__content')
