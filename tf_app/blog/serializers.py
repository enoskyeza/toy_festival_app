from rest_framework import serializers
from .models import Author, Post, Comment


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = '__all__'


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'


class PostSerializer(serializers.ModelSerializer):
    # Serializer fields for nested representation of author and comments
    author = AuthorSerializer()
    comments = CommentSerializer(many=True)

    class Meta:
        model = Post
        fields = '__all__'