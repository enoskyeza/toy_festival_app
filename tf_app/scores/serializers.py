from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

from rest_framework import serializers
from accounts.models import Judge
from register.models import Contestant, Participant
from .models import MainCategory, JudgingCriteria, Score, JudgeComment

class MainCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MainCategory
        fields = ['id', 'name']


class JudgingCriteriaSerializer(serializers.ModelSerializer):
    category = MainCategorySerializer()

    class Meta:
        model = JudgingCriteria
        fields = ['id', 'name', 'category']


class ScoreSerializer(serializers.ModelSerializer):
    contestant = serializers.PrimaryKeyRelatedField(queryset=Contestant.objects.all())
    judge = serializers.PrimaryKeyRelatedField(queryset=Judge.objects.all())
    criteria = serializers.PrimaryKeyRelatedField(queryset=JudgingCriteria.objects.all())

    class Meta:
        model = Score
        fields = ['id', 'judge', 'contestant', 'criteria', 'score']


class BulkScoreSerializer(serializers.ModelSerializer):
    criteria = serializers.IntegerField(write_only=True)
    judge = serializers.IntegerField(write_only=True)
    contestant = serializers.IntegerField(write_only=True)

    class Meta:
        model = Score
        fields = ['id', 'criteria', 'judge', 'contestant', 'score']

    def validate_criteria(self, value):
        try:
            return JudgingCriteria.objects.get(id=value)
        except JudgingCriteria.DoesNotExist:
            raise serializers.ValidationError(f"Criteria with id '{value}' does not exist.")

    def validate_judge(self, value):
        try:
            return Judge.objects.get(id=value)
        except Judge.DoesNotExist:
            raise serializers.ValidationError(f"Judge with id '{value}' does not exist.")

    def validate_contestant(self, value):
        try:
            return Contestant.objects.get(id=value)
        except Contestant.DoesNotExist:
            raise serializers.ValidationError(f"Contestant with id '{value}' does not exist.")

    def validate(self, data):
        if data['score'] < 0 or data['score'] > 10:
            raise serializers.ValidationError("Score must be between 0 and 10.")
        return data

    def create(self, validated_data):
        return Score.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance



class JudgeCommentSerializer(serializers.ModelSerializer):
    judge_name = serializers.CharField(source='judge.username', read_only=True)
    contestant_full_name = serializers.SerializerMethodField()

    class Meta:
        model = JudgeComment
        fields = ['id', 'judge', 'judge_name', 'contestant', 'contestant_full_name', 'comment']

    def get_contestant_full_name(self, obj):
        return f"{obj.contestant.first_name} {obj.contestant.last_name}"



class ScoreDetailSerializer(serializers.ModelSerializer):
    contestant = serializers.PrimaryKeyRelatedField(queryset=Contestant.objects.all())
    judge = serializers.PrimaryKeyRelatedField(queryset=Judge.objects.all())
    criteria = JudgingCriteriaSerializer(read_only=True)

    class Meta:
        model = Score
        fields = ['id', 'judge', 'contestant', 'criteria', 'score']


class ContestantDetailSerializer(serializers.ModelSerializer):
    scores = ScoreDetailSerializer(many=True, read_only=True)
    comments = JudgeCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Contestant
        fields = ['id', 'first_name', 'last_name', 'identifier', 'age', 'gender', 'scores', 'comments']