from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

from rest_framework import serializers
from accounts.models import Judge
from register.models import Participant
from .models import MainCategory, JudgingCriteria, JudgeComment

class MainCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MainCategory
        fields = ['id', 'name']


class JudgingCriteriaSerializer(serializers.ModelSerializer):
    category = MainCategorySerializer()

    class Meta:
        model = JudgingCriteria
        fields = ['id', 'name', 'category']


# NEW JUDGING SYSTEM SERIALIZERS (for Participant/Registration architecture)
from register.models import Registration
from .models import Point, JudgeComment as ParticipantComment

class PointSerializer(serializers.ModelSerializer):
    """Serializer for Point model (new architecture)."""
    participant = serializers.PrimaryKeyRelatedField(queryset=Participant.objects.all())
    registration = serializers.PrimaryKeyRelatedField(queryset=Registration.objects.all(), required=False, allow_null=True)
    judge = serializers.PrimaryKeyRelatedField(queryset=Judge.objects.all())
    criteria = JudgingCriteriaSerializer(read_only=True)
    criteria_id = serializers.PrimaryKeyRelatedField(
        queryset=JudgingCriteria.objects.all(),
        source='criteria',
        write_only=True
    )

    class Meta:
        model = Point
        fields = ['id', 'judge', 'participant', 'registration', 'criteria', 'criteria_id', 'score', 'created_at']
        read_only_fields = ['created_at']


class BulkPointSerializer(serializers.Serializer):
    """Serializer for bulk creating/updating points."""
    criteria = serializers.IntegerField(write_only=True)
    judge = serializers.IntegerField(write_only=True)
    participant = serializers.IntegerField(write_only=True)
    registration = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    score = serializers.DecimalField(max_digits=5, decimal_places=2)

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

    def validate_participant(self, value):
        try:
            return Participant.objects.get(id=value)
        except Participant.DoesNotExist:
            raise serializers.ValidationError(f"Participant with id '{value}' does not exist.")
            
    def validate_registration(self, value):
        if value is None:
            return None
        try:
            from register.models import Registration
            return Registration.objects.get(id=value)
        except Registration.DoesNotExist:
            raise serializers.ValidationError(f"Registration with id '{value}' does not exist.")

    def validate(self, data):
        if data['score'] < 0 or data['score'] > 10:
            raise serializers.ValidationError("Score must be between 0 and 10.")
        return data

    def create(self, validated_data):
        return Point.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ParticipantCommentSerializer(serializers.ModelSerializer):
    """Serializer for comments on participants (new architecture)."""
    judge_name = serializers.CharField(source='judge.username', read_only=True)
    participant_full_name = serializers.SerializerMethodField()

    class Meta:
        model = ParticipantComment
        fields = ['id', 'judge', 'judge_name', 'participant', 'participant_full_name', 'comment', 'created_at']

    def get_participant_full_name(self, obj):
        return f"{obj.participant.first_name} {obj.participant.last_name}"


# ============================================================================
# PHASE 3: API SERIALIZERS FOR PHASE 2 MODELS
# ============================================================================

from .models import (
    RubricCategory, Rubric, RubricCriteria, ScoringConfiguration,
    JudgeAssignment, JudgingScore, ConflictOfInterest
)


class RubricCategorySerializer(serializers.ModelSerializer):
    """Serializer for RubricCategory."""
    class Meta:
        model = RubricCategory
        fields = ['id', 'name', 'description', 'order', 'icon', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class RubricCriteriaSerializer(serializers.ModelSerializer):
    """Serializer for RubricCriteria with category details."""
    category = RubricCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=RubricCategory.objects.all(),
        source='category',
        write_only=True
    )
    weight_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = RubricCriteria
        fields = [
            'id', 'rubric', 'category', 'category_id', 'name', 'description',
            'guidelines', 'max_score', 'weight', 'weight_percentage', 'order',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'weight_percentage']


class RubricSerializer(serializers.ModelSerializer):
    """Serializer for Rubric with nested criteria."""
    criteria = RubricCriteriaSerializer(many=True, read_only=True)
    criteria_count = serializers.ReadOnlyField()
    program_name = serializers.CharField(source='program.name', read_only=True)
    
    class Meta:
        model = Rubric
        fields = [
            'id', 'program', 'program_name', 'category_value', 'name', 'description',
            'total_possible_points', 'is_active', 'criteria_count', 'criteria',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'criteria_count']


class RubricForRegistrationSerializer(serializers.ModelSerializer):
    """
    Lightweight rubric serializer for judge scoring interface.
    Returns rubric with criteria for a specific registration's category.
    """
    criteria = RubricCriteriaSerializer(many=True, read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    
    class Meta:
        model = Rubric
        fields = [
            'id', 'program', 'program_name', 'category_value', 'name',
            'description', 'total_possible_points', 'criteria'
        ]


class ScoringConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for ScoringConfiguration."""
    program_name = serializers.CharField(source='program.name', read_only=True)
    is_scoring_active = serializers.ReadOnlyField()
    
    class Meta:
        model = ScoringConfiguration
        fields = [
            'id', 'program', 'program_name', 'scoring_start', 'scoring_end',
            'min_judges_required', 'max_judges_per_participant',
            'calculation_method', 'top_n_count', 'allow_revisions',
            'revision_deadline', 'max_revisions_per_score',
            'show_scores_to_participants', 'scores_visible_after',
            'is_scoring_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_scoring_active']


class JudgeAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for JudgeAssignment."""
    program_name = serializers.CharField(source='program.name', read_only=True)
    judge_username = serializers.CharField(source='judge.username', read_only=True)
    participants_scored = serializers.ReadOnlyField()
    completion_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = JudgeAssignment
        fields = [
            'id', 'program', 'program_name', 'judge', 'judge_username',
            'category_value', 'assigned_by', 'assigned_at', 'max_participants',
            'status', 'notes', 'participants_scored', 'completion_percentage',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['assigned_at', 'created_at', 'updated_at']


class JudgingScoreSerializer(serializers.ModelSerializer):
    """Serializer for JudgingScore."""
    judge_username = serializers.CharField(source='judge.username', read_only=True)
    participant_name = serializers.SerializerMethodField()
    criteria_name = serializers.CharField(source='criteria.name', read_only=True)
    
    class Meta:
        model = JudgingScore
        fields = [
            'id', 'program', 'registration', 'judge', 'judge_username',
            'participant_name', 'criteria', 'criteria_name', 'raw_score',
            'max_score', 'score_percentage', 'weighted_score', 'notes',
            'revision_number', 'previous_score', 'revision_reason',
            'submitted_at', 'updated_at', 'created_at'
        ]
        read_only_fields = ['score_percentage', 'weighted_score', 'submitted_at', 'updated_at', 'created_at']
    
    def get_participant_name(self, obj):
        participant = obj.registration.participant
        return f"{participant.first_name} {participant.last_name}"


class ConflictOfInterestSerializer(serializers.ModelSerializer):
    """Serializer for ConflictOfInterest."""
    judge_username = serializers.CharField(source='judge.username', read_only=True)
    participant_name = serializers.SerializerMethodField()
    relationship_type_display = serializers.CharField(source='get_relationship_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ConflictOfInterest
        fields = [
            'id', 'judge', 'judge_username', 'participant', 'participant_name',
            'relationship_type', 'relationship_type_display', 'description',
            'flagged_by', 'flagged_at', 'status', 'status_display',
            'reviewed_by', 'reviewed_at', 'review_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['flagged_at', 'reviewed_at', 'created_at', 'updated_at']
    
    def get_participant_name(self, obj):
        return f"{obj.participant.first_name} {obj.participant.last_name}"