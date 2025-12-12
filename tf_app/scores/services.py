"""
Business Logic Services for Judging System

This module contains all business logic separated from views and models.
Following proper separation of concerns and single responsibility principle.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.db.models import Avg, Sum, Count, Q, F
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.cache import cache

from .models import (
    JudgingScore, ConflictOfInterest, Rubric, RubricCriteria,
    ScoringConfiguration, JudgeAssignment
)
from register.models import Registration, Program
from accounts.models import Judge


class ScoringService:
    """
    Handles all scoring business logic.
    Centralizes score submission, validation, and conflict checking.
    """
    
    @staticmethod
    def submit_scores(judge: Judge, registration: Registration, scores_dict: Dict[int, Decimal]) -> List[JudgingScore]:
        """
        Submit multiple scores for a registration.
        
        Args:
            judge: Judge submitting scores
            registration: Registration being scored
            scores_dict: Dict of {criteria_id: score_value}
        
        Returns:
            List of created JudgingScore objects
        
        Raises:
            ValidationError: If validation fails
        """
        program = registration.program
        
        # Validate scoring window
        ScoringService.validate_scoring_window(program)
        
        # Validate judge permission
        ScoringService.validate_judge_permission(judge, registration)
        
        # Check for conflicts
        ScoringService.check_conflicts(judge, registration)
        
        # Get active rubric for this registration's category
        rubric = Rubric.get_for_registration(registration)
        if not rubric:
            category_msg = f" (category: {registration.category_value})" if registration.category_value else ""
            raise ValidationError(f"No active rubric found for program {program.name}{category_msg}")
        
        created_scores = []
        
        with transaction.atomic():
            for criteria_id, raw_score in scores_dict.items():
                try:
                    criteria = RubricCriteria.objects.get(id=criteria_id, rubric=rubric)
                except RubricCriteria.DoesNotExist:
                    raise ValidationError(f"Criteria {criteria_id} not found in active rubric")
                
                # Validate score range
                if raw_score > criteria.max_score:
                    raise ValidationError(
                        f"Score {raw_score} exceeds maximum {criteria.max_score} for {criteria.name}"
                    )
                
                # Check if score already exists
                existing_score = JudgingScore.objects.filter(
                    program=program,
                    registration=registration,
                    judge=judge,
                    criteria=criteria
                ).first()
                
                if existing_score:
                    # This is a revision
                    new_score = ScoringService.track_revision(
                        old_score=existing_score,
                        new_score=raw_score,
                        criteria=criteria,
                        judge=judge,
                        registration=registration,
                        program=program
                    )
                    created_scores.append(new_score)
                else:
                    # Create new score
                    score = JudgingScore.objects.create(
                        program=program,
                        registration=registration,
                        judge=judge,
                        criteria=criteria,
                        raw_score=raw_score,
                        max_score=criteria.max_score
                        # score_percentage and weighted_score are auto-calculated in save()
                    )
                    created_scores.append(score)
        
        return created_scores
    
    @staticmethod
    def validate_scoring_window(program: Program) -> None:
        """
        Validate that scoring is currently allowed for the program.
        
        Raises:
            ValidationError: If scoring window is closed
        """
        try:
            config = ScoringConfiguration.objects.get(program=program)
        except ScoringConfiguration.DoesNotExist:
            raise ValidationError(f"No scoring configuration found for program {program.name}")
        
        now = timezone.now()
        
        if now < config.scoring_start:
            raise ValidationError(
                f"Scoring has not started yet. Opens at {config.scoring_start}"
            )
        
        if now > config.scoring_end:
            raise ValidationError(
                f"Scoring window has closed. Ended at {config.scoring_end}"
            )
    
    @staticmethod
    def validate_judge_permission(judge: Judge, registration: Registration) -> None:
        """
        Validate that judge is assigned to score this registration.
        
        Raises:
            ValidationError: If judge is not assigned
        """
        program = registration.program
        category_value = registration.category_value
        
        # Check if judge has an active assignment for this program/category
        assignment = JudgeAssignment.objects.filter(
            judge=judge,
            program=program,
            status='ACTIVE'
        ).filter(
            Q(category_value='') | Q(category_value=category_value)
        ).first()
        
        if not assignment:
            raise ValidationError(
                f"Judge {judge.username} is not assigned to score {registration.participant} in {program.name}"
            )
    
    @staticmethod
    def check_conflicts(judge: Judge, registration: Registration) -> None:
        """
        Check for conflicts of interest.
        
        Raises:
            ValidationError: If rejected conflict exists
        """
        participant = registration.participant
        
        conflict = ConflictOfInterest.objects.filter(
            judge=judge,
            participant=participant
        ).first()
        
        if conflict and conflict.status == 'REJECTED':
            raise ValidationError(
                f"Conflict of interest: {judge.username} cannot score {participant} "
                f"({conflict.get_relationship_type_display()})"
            )
    
    @staticmethod
    def track_revision(old_score: JudgingScore, new_score: Decimal, **kwargs) -> JudgingScore:
        """
        Create a new score entry as a revision of an existing score.
        
        Args:
            old_score: Original score being revised
            new_score: New score value
            **kwargs: Additional fields (criteria, judge, registration, program)
        
        Returns:
            New JudgingScore object
        """
        # Check revision limits
        config = ScoringConfiguration.objects.get(program=old_score.program)
        
        if not config.allow_revisions:
            raise ValidationError("Score revisions are not allowed for this program")
        
        if config.revision_deadline and timezone.now() > config.revision_deadline:
            raise ValidationError("Revision deadline has passed")
        
        if config.max_revisions_per_score > 0:
            revision_count = JudgingScore.objects.filter(
                program=old_score.program,
                registration=old_score.registration,
                judge=old_score.judge,
                criteria=old_score.criteria
            ).count()
            
            if revision_count >= config.max_revisions_per_score:
                raise ValidationError(f"Maximum {config.max_revisions_per_score} revisions exceeded")
        
        # Create revision
        revised_score = JudgingScore.objects.create(
            program=kwargs['program'],
            registration=kwargs['registration'],
            judge=kwargs['judge'],
            criteria=kwargs['criteria'],
            raw_score=new_score,
            max_score=kwargs['criteria'].max_score,
            revision_number=old_score.revision_number + 1,
            previous_score=old_score,
            revision_reason=kwargs.get('revision_reason', 'Score updated')
        )
        
        return revised_score


class RubricService:
    """
    Handles rubric management business logic.
    """
    
    @staticmethod
    def create_rubric(program: Program, name: str, criteria_list: List[Dict], 
                     created_by=None, total_points: Decimal = Decimal('100.00'),
                     category_value: str = None) -> Rubric:
        """
        Create a rubric with criteria in one transaction.
        
        Args:
            program: Program for the rubric
            name: Rubric name
            criteria_list: List of dicts with criteria data
            created_by: User creating the rubric
            total_points: Total possible points
            category_value: Optional category this rubric applies to (e.g., '3-7 years')
        
        Returns:
            Created Rubric object
        
        Raises:
            ValidationError: If validation fails
        """
        # Validate weights sum to 1.0
        RubricService.validate_rubric_weights(criteria_list)
        
        with transaction.atomic():
            # Deactivate any existing active rubrics for this program+category
            Rubric.objects.filter(
                program=program, 
                category_value=category_value,
                is_active=True
            ).update(is_active=False)
            
            # Create rubric
            rubric = Rubric.objects.create(
                program=program,
                category_value=category_value,
                name=name,
                total_possible_points=total_points,
                is_active=True,
                created_by=created_by
            )
            
            # Create criteria
            for criterion_data in criteria_list:
                RubricCriteria.objects.create(
                    rubric=rubric,
                    **criterion_data
                )
        
        return rubric
    
    @staticmethod
    def clone_rubric(source_rubric: Rubric, target_program: Program, new_name: str = None) -> Rubric:
        """
        Clone an existing rubric to a new program.
        
        Args:
            source_rubric: Rubric to clone
            target_program: Target program
            new_name: Optional new name (defaults to source name + " (Copy)")
        
        Returns:
            New Rubric object
        """
        if new_name is None:
            new_name = f"{source_rubric.name} (Copy)"
        
        with transaction.atomic():
            # Deactivate existing rubrics for target program
            Rubric.objects.filter(program=target_program, is_active=True).update(is_active=False)
            
            # Clone rubric
            new_rubric = Rubric.objects.create(
                program=target_program,
                name=new_name,
                description=source_rubric.description,
                total_possible_points=source_rubric.total_possible_points,
                is_active=True
            )
            
            # Clone criteria
            for criteria in source_rubric.criteria.all():
                RubricCriteria.objects.create(
                    rubric=new_rubric,
                    category=criteria.category,
                    name=criteria.name,
                    description=criteria.description,
                    guidelines=criteria.guidelines,
                    max_score=criteria.max_score,
                    weight=criteria.weight,
                    order=criteria.order
                )
        
        return new_rubric
    
    @staticmethod
    def validate_rubric_weights(criteria_list: List[Dict]) -> None:
        """
        Validate that criteria weights sum to 1.0 (100%).
        
        Raises:
            ValidationError: If weights don't sum to 1.0
        """
        total_weight = sum(Decimal(str(c.get('weight', 0))) for c in criteria_list)
        
        # Allow 1% tolerance
        if abs(total_weight - Decimal('1.0')) > Decimal('0.01'):
            raise ValidationError(
                f"Criteria weights must sum to 1.0 (100%). Current total: {total_weight} ({total_weight * 100}%)"
            )


class ResultsService:
    """
    Handles results calculation and leaderboard generation.
    """
    
    @staticmethod
    def calculate_leaderboard(program: Program, category_value: str = None, 
                            use_cache: bool = True) -> List[Dict]:
        """
        Calculate leaderboard for a program.
        
        Args:
            program: Program to calculate for
            category_value: Optional category filter
            use_cache: Whether to use cached results
        
        Returns:
            List of dicts with participant results
        """
        cache_key = f"leaderboard_{program.id}_{category_value or 'all'}"
        
        if use_cache:
            cached_results = cache.get(cache_key)
            if cached_results:
                return cached_results
        
        # Get all registrations for program
        registrations = Registration.objects.filter(
            program=program,
            status='PAID'
        )
        
        if category_value:
            registrations = registrations.filter(category_value=category_value)
        
        results = []
        
        for registration in registrations:
            result = ResultsService.aggregate_scores(registration)
            results.append(result)
        
        # Sort by final score descending
        results.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Add rankings
        for rank, result in enumerate(results, 1):
            result['rank'] = rank
        
        # Cache results for 5 minutes
        if use_cache:
            cache.set(cache_key, results, 300)
        
        return results
    
    @staticmethod
    def aggregate_scores(registration: Registration) -> Dict:
        """
        Aggregate all scores for a registration.
        
        Args:
            registration: Registration to aggregate
        
        Returns:
            Dict with aggregated scores
        """
        program = registration.program
        
        # Get scoring configuration
        try:
            config = ScoringConfiguration.objects.get(program=program)
        except ScoringConfiguration.DoesNotExist:
            config = None
        
        # Get all latest scores for this registration
        scores = JudgingScore.objects.filter(
            program=program,
            registration=registration
        ).select_related('judge', 'criteria')
        
        # Group by judge and criteria to get latest revisions
        latest_scores = {}
        for score in scores:
            key = (score.judge_id, score.criteria_id)
            if key not in latest_scores or score.revision_number > latest_scores[key].revision_number:
                latest_scores[key] = score
        
        scores_list = list(latest_scores.values())
        
        # Apply calculation method
        if config:
            final_score = ResultsService.apply_calculation_method(scores_list, config.calculation_method, config.top_n_count)
        else:
            final_score = ResultsService.apply_calculation_method(scores_list, 'AVERAGE_ALL')
        
        # Count judges
        judges_count = len(set(score.judge_id for score in scores_list))
        
        return {
            'registration_id': registration.id,
            'participant_id': registration.participant.id,
            'participant_name': f"{registration.participant.first_name} {registration.participant.last_name}",
            'category_value': registration.category_value,
            'final_score': float(final_score),
            'judges_count': judges_count,
            'scores_count': len(scores_list)
        }
    
    @staticmethod
    def apply_calculation_method(scores: List[JudgingScore], method: str, top_n: int = None) -> Decimal:
        """
        Apply calculation method to scores.
        
        Args:
            scores: List of JudgingScore objects
            method: Calculation method (AVERAGE_ALL, TOP_N, MEDIAN, WEIGHTED)
            top_n: Number of top scores to use (for TOP_N method)
        
        Returns:
            Calculated final score
        """
        if not scores:
            return Decimal('0.00')
        
        if method == 'AVERAGE_ALL':
            # Average of all weighted scores
            total = sum(score.weighted_score for score in scores)
            return total / len(scores)
        
        elif method == 'TOP_N':
            # Average of top N judges' scores
            if not top_n:
                top_n = 3  # Default
            
            # Group by judge, sum their weighted scores
            judge_totals = {}
            for score in scores:
                if score.judge_id not in judge_totals:
                    judge_totals[score.judge_id] = Decimal('0.00')
                judge_totals[score.judge_id] += score.weighted_score
            
            # Get top N
            top_scores = sorted(judge_totals.values(), reverse=True)[:top_n]
            return sum(top_scores) / len(top_scores) if top_scores else Decimal('0.00')
        
        elif method == 'MEDIAN':
            # Median of weighted scores
            sorted_scores = sorted(score.weighted_score for score in scores)
            n = len(sorted_scores)
            if n % 2 == 0:
                return (sorted_scores[n//2 - 1] + sorted_scores[n//2]) / 2
            else:
                return sorted_scores[n//2]
        
        elif method == 'WEIGHTED':
            # Already weighted in JudgingScore model
            return sum(score.weighted_score for score in scores)
        
        else:
            # Default to average
            total = sum(score.weighted_score for score in scores)
            return total / len(scores)
    
    @staticmethod
    def cache_results(program_id: int, results: List[Dict]) -> None:
        """
        Cache results for a program.
        
        Args:
            program_id: Program ID
            results: Results to cache
        """
        cache_key = f"leaderboard_{program_id}_all"
        cache.set(cache_key, results, 300)  # Cache for 5 minutes


class JudgeAssignmentService:
    """
    Handles judge assignment logic and workload distribution.
    """
    
    @staticmethod
    def assign_judge(program: Program, judge: Judge, category_value: str = '', 
                    max_participants: int = None, assigned_by=None) -> JudgeAssignment:
        """
        Assign a judge to a program/category.
        
        Args:
            program: Program to assign to
            judge: Judge to assign
            category_value: Optional category (blank = all categories)
            max_participants: Maximum participants to assign
            assigned_by: User making the assignment
        
        Returns:
            Created JudgeAssignment
        
        Raises:
            ValidationError: If assignment already exists
        """
        # Check for existing assignment
        existing = JudgeAssignment.objects.filter(
            program=program,
            judge=judge,
            category_value=category_value
        ).first()
        
        if existing:
            if existing.status == 'CANCELLED':
                # Reactivate
                existing.status = 'ACTIVE'
                existing.save()
                return existing
            else:
                raise ValidationError(
                    f"Judge {judge.username} is already assigned to {program.name} "
                    f"({category_value or 'all categories'})"
                )
        
        # Create assignment
        assignment = JudgeAssignment.objects.create(
            program=program,
            judge=judge,
            category_value=category_value,
            max_participants=max_participants,
            assigned_by=assigned_by,
            status='ACTIVE'
        )
        
        return assignment
    
    @staticmethod
    def distribute_workload(program: Program, category_value: str = None) -> Dict[int, int]:
        """
        Distribute participants evenly among judges.
        
        Args:
            program: Program to distribute for
            category_value: Optional category filter
        
        Returns:
            Dict of {judge_id: participant_count}
        """
        # Get active judge assignments
        assignments = JudgeAssignment.objects.filter(
            program=program,
            status='ACTIVE'
        )
        
        if category_value:
            assignments = assignments.filter(
                Q(category_value='') | Q(category_value=category_value)
            )
        
        if not assignments.exists():
            return {}
        
        # Get participants needing scoring
        registrations = Registration.objects.filter(
            program=program,
            status='PAID'
        )
        
        if category_value:
            registrations = registrations.filter(category_value=category_value)
        
        total_participants = registrations.count()
        total_judges = assignments.count()
        
        if total_judges == 0:
            return {}
        
        # Calculate distribution
        participants_per_judge = total_participants // total_judges
        remainder = total_participants % total_judges
        
        distribution = {}
        for idx, assignment in enumerate(assignments):
            count = participants_per_judge + (1 if idx < remainder else 0)
            distribution[assignment.judge_id] = count
        
        return distribution
    
    @staticmethod
    def check_assignment_status(assignment: JudgeAssignment) -> Dict:
        """
        Check status of a judge assignment.
        
        Args:
            assignment: JudgeAssignment to check
        
        Returns:
            Dict with status information
        """
        # Count participants scored
        scored_count = assignment.participants_scored
        
        # Calculate completion
        completion = assignment.completion_percentage
        
        # Check if overloaded
        is_overloaded = False
        if assignment.max_participants and scored_count > assignment.max_participants:
            is_overloaded = True
        
        return {
            'assignment_id': assignment.id,
            'judge': assignment.judge.username,
            'program': assignment.program.name,
            'category': assignment.category_value or 'All',
            'status': assignment.status,
            'scored_count': scored_count,
            'max_participants': assignment.max_participants,
            'completion_percentage': completion,
            'is_overloaded': is_overloaded,
            'is_complete': completion == 100.0 if completion else False
        }
