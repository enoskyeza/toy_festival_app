from rest_framework import serializers
from django.contrib.auth import authenticate

from .models import User, Judge


class JudgeSerializer(serializers.ModelSerializer):
    """Serializer for Judge CRUD operations."""
    full_name = serializers.SerializerMethodField()
    assignments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'full_name', 'is_active', 'assignments_count'
        ]
        read_only_fields = ['id', 'full_name', 'assignments_count']
    
    def get_full_name(self, obj):
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        return obj.username
    
    def get_assignments_count(self, obj):
        return obj.assignments.filter(status='ACTIVE').count() if hasattr(obj, 'assignments') else 0
    
    def create(self, validated_data):
        # Set role to JUDGE and create with a default password
        validated_data['role'] = User.Role.JUDGE
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
        else:
            # Set a default password (username + "123")
            user.set_password(f"{validated_data['username']}123")
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class JudgeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new judge with password."""
    password = serializers.CharField(write_only=True, required=False, min_length=6)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password']
        read_only_fields = ['id']
    
    def create(self, validated_data):
        validated_data['role'] = User.Role.JUDGE
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_password(f"{validated_data['username']}123")
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user is None:
                raise serializers.ValidationError("Invalid username or password.")
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
            data['user'] = user
        else:
            raise serializers.ValidationError("Both username and password are required.")

        return data
