from rest_framework import serializers
from .models import Media

class MediaSerializer(serializers.ModelSerializer):
    thumb_small = serializers.ImageField(read_only=True)
    thumb_medium = serializers.ImageField(read_only=True)
    poster = serializers.ImageField(read_only=True)
    duration = serializers.FloatField(read_only=True)

    class Meta:
        model = Media
        fields = [
            'uuid', 'file', 'thumb_small', 'thumb_medium',
            'poster', 'duration', 'caption', 'created_at'
        ]