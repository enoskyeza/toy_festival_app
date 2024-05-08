from django.contrib import admin
from .models import Post, Author, Comment


# Register your models here.
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created', 'like_count', 'comment_count')
    list_filter = ('author', 'created')
    search_fields = ('title', 'author__user')
    readonly_fields = ('like_count', 'comment_count')
    actions = ['like_post']

    def like_count(self, obj):
        return obj.like

    like_count.short_description = 'Likes'

    def comment_count(self, obj):
        return obj.comment_set.count()

    comment_count.short_description = 'Comments'

    def like_post(self, request, queryset):
        for post in queryset:
            post.like += 1
            post.save()
        self.message_user(request, "Post liked.")

    like_post.short_description = "like selected posts"


admin.site.register(Author)
admin.site.register(Post, PostAdmin)
admin.site.register(Comment)
