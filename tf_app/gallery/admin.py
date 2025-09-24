# gallery/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.contrib.contenttypes.admin import GenericTabularInline

from .models import Media


class MediaInline(GenericTabularInline):
    model = Media
    extra = 1
    readonly_fields = ('preview',)
    fields = ('file', 'preview', 'caption', 'description', 'media_type', 'app_label', 'context')

    def preview(self, obj):
        if obj.is_image():
            url = obj.thumb_small.url
            return format_html('<img src="{}" style="max-height: 100px;"/>', url)
        if obj.poster:
            url = obj.poster.url
            return format_html('<img src="{}" style="max-height: 100px;"/>', url)
        return ''
    preview.short_description = 'Preview'


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('id', 'file_link', 'content_obj', 'app_label', 'context', 'media_type', 'duration', 'created_at')
    list_filter = ('content_type', 'app_label', 'media_type')
    search_fields = ('caption', 'description', 'file')
    readonly_fields = ('preview', 'thumb_small', 'thumb_medium', 'poster', 'duration')
    fields = (
        'file', 'preview', 'caption', 'description',
        'media_type', 'app_label', 'context',
        'content_type', 'object_id',
        'thumb_small', 'thumb_medium', 'poster', 'duration',
    )

    def preview(self, obj):
        if obj.is_image():
            return format_html('<img src="{}" style="max-height: 100px;"/>', obj.thumb_small.url)
        if obj.poster:
            return format_html('<img src="{}" style="max-height: 100px;"/>', obj.poster.url)
        return ''
    preview.short_description = 'Preview'

    def file_link(self, obj):
        return format_html('<a href="{}" target="_blank">{}</a>', obj.file.url, obj.file.name)
    file_link.short_description = 'File'
