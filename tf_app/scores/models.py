from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from core.models import BaseModel
from register.models import Participant
from accounts.models import Judge

# Create your models here.

class MainCategory(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Main Category"
        verbose_name_plural = "Main Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class JudgingCriteria(models.Model):
    category = models.ForeignKey(MainCategory, on_delete=models.CASCADE, related_name='criteria')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ('category', 'name')
        ordering = ['category__name', 'name']

    def __str__(self):
        return f'{self.category} - {self.name}'


class Point(BaseModel):
    judge = models.ForeignKey(Judge, related_name='points', on_delete=models.PROTECT)
    participant = models.ForeignKey(Participant, related_name='points', on_delete=models.PROTECT)
    registration = models.ForeignKey('register.Registration', related_name='points', on_delete=models.CASCADE, null=True, blank=True)
    criteria = models.ForeignKey(JudgingCriteria, on_delete=models.PROTECT)
    score = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)]
    )

    class Meta:
        unique_together = ('judge', 'participant', 'criteria', 'registration')
        indexes = [
            models.Index(fields=['judge', 'participant']),
            models.Index(fields=['criteria']),
            models.Index(fields=['registration']),
        ]

    def __str__(self):
        return f'{self.participant} - {self.criteria} by {self.judge}: {self.score}'


class JudgeComment(BaseModel):
    judge = models.ForeignKey(Judge, related_name='comments', on_delete=models.PROTECT)
    participant = models.ForeignKey(Participant, related_name='comments', on_delete=models.PROTECT)
    comment = models.TextField()

    def __str__(self):
        return f'Comment by {self.judge} on {self.participant}'


# ============================================================================
# PHASE 2: NEW JUDGING SYSTEM MODELS
# ============================================================================


class RubricCategory(BaseModel):
    """
    Categories for organizing judging criteria.
    Example: "Design Quality", "Functionality", "Innovation"
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Category name (e.g., 'Design Quality')"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of what this category evaluates"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower numbers first)"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon name for UI (optional)"
    )
    
    class Meta:
        verbose_name = "Rubric Category"
        verbose_name_plural = "Rubric Categories"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Rubric(BaseModel):
    """
    Complete scoring rubric for a program.
    Contains all criteria and their weights.
    
    Category-aware: If category_value is set, this rubric applies only to 
    registrations with that category. If NULL, it's a general/default rubric.
    """
    program = models.ForeignKey(
        'register.Program',
        on_delete=models.CASCADE,
        related_name='rubrics',
        help_text="Program this rubric is for"
    )
    category_value = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        help_text="If set, this rubric applies only to registrations with this category value "
                  "(e.g., '3-7 years'). If NULL, applies as default/general rubric."
    )
    name = models.CharField(
        max_length=200,
        help_text="Rubric name (e.g., 'Toy Festival 2025 - Ages 3-7')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of scoring approach"
    )
    total_possible_points = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=100.00,
        validators=[MinValueValidator(0)],
        help_text="Total points available across all criteria"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only one rubric can be active per program+category combination"
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_rubrics',
        help_text="User who created this rubric"
    )
    
    class Meta:
        ordering = ['program', 'category_value', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['program', 'category_value'],
                condition=models.Q(is_active=True),
                name='one_active_rubric_per_program_category'
            )
        ]
        indexes = [
            models.Index(fields=['program', 'category_value', 'is_active']),
        ]
    
    def __str__(self):
        if self.category_value:
            return f"{self.name} ({self.program.name} - {self.category_value})"
        return f"{self.name} ({self.program.name})"
    
    @classmethod
    def get_for_registration(cls, registration):
        """
        Get the appropriate active rubric for a registration.
        First tries to find a category-specific rubric, then falls back to general.
        """
        # Try category-specific rubric first
        if registration.category_value:
            rubric = cls.objects.filter(
                program=registration.program,
                category_value=registration.category_value,
                is_active=True
            ).first()
            if rubric:
                return rubric
        
        # Fall back to general rubric (category_value is NULL)
        return cls.objects.filter(
            program=registration.program,
            category_value__isnull=True,
            is_active=True
        ).first()
    
    @property
    def criteria_count(self):
        return self.criteria.count()
    
    def validate_weights_sum_to_one(self):
        """Ensure all criteria weights sum to 1.0 (100%)"""
        total_weight = self.criteria.aggregate(
            total=models.Sum('weight')
        )['total'] or 0
        return abs(total_weight - 1.0) < 0.01  # Allow 1% tolerance


class RubricCriteria(BaseModel):
    """
    Individual criterion in a rubric.
    Example: "Visual Appeal" under "Design Quality" category
    """
    rubric = models.ForeignKey(
        Rubric,
        on_delete=models.CASCADE,
        related_name='criteria',
        help_text="Parent rubric"
    )
    category = models.ForeignKey(
        RubricCategory,
        on_delete=models.PROTECT,
        related_name='rubric_criteria',
        help_text="Category this criterion belongs to"
    )
    name = models.CharField(
        max_length=200,
        help_text="Criterion name (e.g., 'Visual Appeal')"
    )
    description = models.TextField(
        blank=True,
        help_text="What judges should evaluate"
    )
    guidelines = models.TextField(
        blank=True,
        help_text="Scoring guidelines (e.g., '8-10: Excellent, 5-7: Good')"
    )
    max_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        validators=[MinValueValidator(0)],
        help_text="Maximum score for this criterion"
    )
    weight = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        default=0.100,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Weight in final score (0.1 = 10%)"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within category"
    )
    
    class Meta:
        verbose_name = "Rubric Criterion"
        verbose_name_plural = "Rubric Criteria"
        ordering = ['category__order', 'order', 'name']
        unique_together = [('rubric', 'name')]
        indexes = [
            models.Index(fields=['rubric', 'category']),
        ]
    
    def __str__(self):
        return f"{self.category.name}: {self.name}"
    
    @property
    def weight_percentage(self):
        """Return weight as percentage string"""
        return f"{self.weight * 100:.1f}%"


class ScoringConfiguration(BaseModel):
    """
    Configuration for how judging works for a program.
    Controls timing, calculation methods, and rules.
    """
    
    CALCULATION_METHODS = [
        ('AVERAGE_ALL', 'Average All Judges'),
        ('TOP_N', 'Top N Judges (highest scores)'),
        ('MEDIAN', 'Median Score'),
        ('WEIGHTED', 'Weighted Average by Criteria'),
    ]
    
    program = models.OneToOneField(
        'register.Program',
        on_delete=models.CASCADE,
        related_name='scoring_config',
        help_text="Program this configuration applies to"
    )
    
    # Timing
    scoring_start = models.DateTimeField(
        help_text="When judges can start scoring"
    )
    scoring_end = models.DateTimeField(
        help_text="When scoring closes"
    )
    
    # Judge requirements
    min_judges_required = models.PositiveIntegerField(
        default=2,
        validators=[MinValueValidator(1)],
        help_text="Minimum judges that must score each participant"
    )
    max_judges_per_participant = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1)],
        help_text="Maximum judges allowed per participant"
    )
    
    # Calculation
    calculation_method = models.CharField(
        max_length=20,
        choices=CALCULATION_METHODS,
        default='AVERAGE_ALL',
        help_text="How to calculate final scores"
    )
    top_n_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Number of top judges (if method is TOP_N)"
    )
    
    # Revisions
    allow_revisions = models.BooleanField(
        default=True,
        help_text="Can judges edit scores after submission"
    )
    revision_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time judges can revise (blank = same as scoring_end)"
    )
    max_revisions_per_score = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(0)],
        help_text="Maximum times a score can be revised (0 = unlimited)"
    )
    
    # Display
    show_scores_to_participants = models.BooleanField(
        default=False,
        help_text="Can participants see their scores"
    )
    scores_visible_after = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When scores become visible to participants"
    )
    
    class Meta:
        verbose_name = "Scoring Configuration"
    
    def __str__(self):
        return f"Scoring Config: {self.program.name}"
    
    def clean(self):
        """Validation"""
        from django.core.exceptions import ValidationError
        if self.scoring_end <= self.scoring_start:
            raise ValidationError("Scoring end must be after start")
        
        if self.calculation_method == 'TOP_N' and not self.top_n_count:
            raise ValidationError("top_n_count required when method is TOP_N")
        
        if self.revision_deadline and self.revision_deadline > self.scoring_end:
            raise ValidationError("Revision deadline cannot be after scoring end")
    
    @property
    def is_scoring_active(self):
        """Check if scoring is currently active"""
        from django.utils import timezone
        now = timezone.now()
        return self.scoring_start <= now <= self.scoring_end


class JudgeAssignment(BaseModel):
    """
    Assigns a judge to score participants in a specific category.
    Example: Judge John → Toy Festival 2025 → Junior Category
    """
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('PAUSED', 'Paused'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    program = models.ForeignKey(
        'register.Program',
        on_delete=models.CASCADE,
        related_name='judge_assignments',
        help_text="Program to judge"
    )
    judge = models.ForeignKey(
        'accounts.Judge',
        on_delete=models.CASCADE,
        related_name='assignments',
        help_text="Assigned judge"
    )
    category_value = models.CharField(
        max_length=100,
        blank=True,
        help_text="Category value from program.category_options (blank = all categories)"
    )
    assigned_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='judge_assignments_made',
        help_text="Admin who made the assignment"
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True
    )
    max_participants = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Max participants to assign (blank = unlimited)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about this assignment"
    )
    
    class Meta:
        unique_together = [('program', 'judge', 'category_value')]
        indexes = [
            models.Index(fields=['program', 'category_value', 'status']),
            models.Index(fields=['judge', 'status']),
        ]
    
    def __str__(self):
        category_str = f" ({self.category_value})" if self.category_value else " (All Categories)"
        return f"{self.judge.username} → {self.program.name}{category_str}"
    
    @property
    def participants_scored(self):
        """Count how many participants this judge has scored"""
        return JudgingScore.objects.filter(
            judge=self.judge,
            program=self.program,
            registration__category_value=self.category_value or models.F('registration__category_value')
        ).values('registration').distinct().count()
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage"""
        if not self.max_participants:
            return None
        if self.max_participants == 0:
            return 100.0
        return (self.participants_scored / self.max_participants) * 100


class JudgingScore(BaseModel):
    """
    A single score entry: Judge X scored Participant Y 
    on Criterion Z with value W.
    """
    program = models.ForeignKey(
        'register.Program',
        on_delete=models.CASCADE,
        related_name='judging_scores',
        help_text="Program being judged"
    )
    registration = models.ForeignKey(
        'register.Registration',
        on_delete=models.CASCADE,
        related_name='judging_scores',
        help_text="Participant registration"
    )
    judge = models.ForeignKey(
        'accounts.Judge',
        on_delete=models.PROTECT,
        related_name='judging_scores',
        help_text="Judge who gave this score"
    )
    criteria = models.ForeignKey(
        RubricCriteria,
        on_delete=models.PROTECT,
        related_name='judging_scores',
        help_text="Criterion being scored"
    )
    
    # Score values
    raw_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Actual score entered by judge"
    )
    max_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Maximum possible (from criteria at submission time)"
    )
    score_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Normalized to percentage (0-100)"
    )
    weighted_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Score * criteria weight"
    )
    
    # Audit fields
    submitted_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    user_agent = models.TextField(
        blank=True
    )
    
    # Revision tracking
    revision_number = models.PositiveIntegerField(
        default=1,
        help_text="Version number (1 = original)"
    )
    previous_score = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revisions',
        help_text="Previous version if revised"
    )
    revision_reason = models.TextField(
        blank=True,
        help_text="Why was this score revised"
    )
    
    # Optional notes
    notes = models.TextField(
        blank=True,
        help_text="Judge's notes about this score"
    )
    
    class Meta:
        unique_together = [('program', 'registration', 'judge', 'criteria')]
        indexes = [
            models.Index(fields=['program', 'registration']),
            models.Index(fields=['judge', 'submitted_at']),
            models.Index(fields=['registration', 'criteria']),
        ]
    
    def __str__(self):
        return f"{self.judge.username} → {self.registration.participant} ({self.criteria.name}): {self.raw_score}/{self.max_score}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate percentage and weighted score
        if self.max_score > 0:
            self.score_percentage = (self.raw_score / self.max_score) * 100
        else:
            self.score_percentage = 0
        
        self.weighted_score = (self.score_percentage / 100) * self.criteria.weight * self.criteria.rubric.total_possible_points
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validation"""
        from django.core.exceptions import ValidationError
        if self.raw_score > self.max_score:
            raise ValidationError(f"Score ({self.raw_score}) cannot exceed max ({self.max_score})")


class ConflictOfInterest(BaseModel):
    """
    Flags potential conflicts of interest between judges and participants.
    """
    
    RELATIONSHIP_TYPES = [
        ('FAMILY', 'Family Member'),
        ('TEACHER', 'Teacher/Instructor'),
        ('EMPLOYER', 'Employer/Employee'),
        ('SPONSOR', 'Sponsor/Sponsee'),
        ('FRIEND', 'Close Friend'),
        ('OTHER', 'Other Relationship'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved (Can Judge)'),
        ('REJECTED', 'Rejected (Cannot Judge)'),
    ]
    
    judge = models.ForeignKey(
        'accounts.Judge',
        on_delete=models.CASCADE,
        related_name='conflicts'
    )
    participant = models.ForeignKey(
        'register.Participant',
        on_delete=models.CASCADE,
        related_name='judge_conflicts'
    )
    relationship_type = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_TYPES
    )
    description = models.TextField(
        help_text="Details about the relationship"
    )
    flagged_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='conflicts_flagged'
    )
    flagged_at = models.DateTimeField(
        auto_now_add=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conflicts_reviewed'
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )
    review_notes = models.TextField(
        blank=True
    )
    
    class Meta:
        unique_together = [('judge', 'participant')]
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['judge', 'status']),
        ]
    
    def __str__(self):
        return f"{self.judge.username} ↔ {self.participant} ({self.get_relationship_type_display()})"