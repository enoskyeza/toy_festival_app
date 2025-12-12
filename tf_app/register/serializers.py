import json
from collections import defaultdict
from copy import deepcopy

from django.shortcuts import get_object_or_404
from django.db import models
from django.db import transaction
from datetime import date
from typing import Optional

from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from .models import (
    School, Guardian, Participant, ParticipantGuardian, ProgramType, Program,
    Registration, Receipt, Approval, Coupon, ProgramForm, FormField,
    FormResponse, FormResponseEntry
)
from .forms import RegistrationUtils


# NEW ARCHITECTURE


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ['id', 'name', 'address', 'email', 'phone_number']


class GuardianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardian
        fields = ['id', 'first_name', 'last_name', 'profession', 'address', 'email', 'phone_number']


class ParticipantSerializer(serializers.ModelSerializer):
    # represent current_school by its ID
    current_school = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.all(),
        allow_null=True,
        required=False
    )

    class Meta:
        model = Participant
        fields = [
            'id', 'first_name', 'last_name', 'email', 'date_of_birth',
            'gender', 'current_school'
        ]


class ProgramTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgramType
        fields = ['id', 'name', 'description', 'form_key']


class ProgramSerializer(serializers.ModelSerializer):
    type = ProgramTypeSerializer(read_only=True)
    type_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Program
        fields = [
            'id', 'type', 'type_id', 'year', 'name', 'description', 'long_description',
            'start_date', 'end_date', 'registration_fee', 'age_min', 'age_max', 
            'capacity', 'requires_ticket', 'active', 'is_judgable', 'level', 'thumbnail_url', 
            'logo', 'video_url', 'instructor', 'featured', 'modules', 'learning_outcomes', 
            'requirements', 'category_label', 'category_options'
        ]

    def validate_category_options(self, value):
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('category_options must be a list of strings.')
        cleaned = []
        for option in value:
            if not isinstance(option, str):
                raise serializers.ValidationError('Each category option must be a string.')
            stripped = option.strip()
            if stripped:
                cleaned.append(stripped)
        return cleaned
    
    def create(self, validated_data):
        # Handle type_id separately
        type_id = validated_data.pop('type_id', None)
        
        # Create the program instance
        program = Program(**validated_data)
        
        # Set the type if type_id is provided
        if type_id:
            try:
                program_type = ProgramType.objects.get(id=type_id)
                program.type = program_type
            except ProgramType.DoesNotExist:
                raise serializers.ValidationError({'type_id': 'Invalid program type ID'})
        
        program.save()
        return program


class MiniParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participant
        fields = [
            'id', 'first_name', 'last_name', 'gender'
        ]


class MiniGuardianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardian
        fields = [
            'id', 'first_name', 'last_name', 'phone_number', 'address', 'email', 'profession'
        ]


class CouponSerializer(serializers.ModelSerializer):
    qr_code = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = ['id', 'status', 'qr_code', 'created_at']

    def get_qr_code(self, obj):
        if not obj.qr_code:
            return None
        request = self.context.get('request')
        url = obj.qr_code.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class ReceiptSummarySerializer(serializers.ModelSerializer):
    issued_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = ['id', 'status', 'amount', 'issued_by', 'issued_by_name', 'created_at']

    def get_issued_by_name(self, obj):
        user = getattr(obj, 'issued_by', None)
        if not user:
            return None
        # Safely build a name without assuming get_full_name exists
        first = getattr(user, 'first_name', '') or ''
        last = getattr(user, 'last_name', '') or ''
        full = f"{first} {last}".strip()
        if full:
            return full
        username = getattr(user, 'username', None)
        return username or str(user)


class RegistrationSerializer(serializers.ModelSerializer):
    participant = MiniParticipantSerializer(read_only=True)
    program = serializers.StringRelatedField(read_only=True)
    school_at_registration = serializers.StringRelatedField(read_only=True)
    guardian_at_registration = MiniGuardianSerializer(read_only=True)
    amount_due = serializers.DecimalField(
        max_digits=8, decimal_places=2,
        read_only=True
    )
    category_value = serializers.CharField(read_only=True)
    coupon = serializers.SerializerMethodField()
    receipts = ReceiptSummarySerializer(many=True, read_only=True)
    
    # Scoring metadata for judge panel
    has_scores = serializers.SerializerMethodField()
    scored_by = serializers.SerializerMethodField()
    judge_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    program_logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Registration
        fields = [
            'id', 'participant', 'program', 'age_at_registration',
            'school_at_registration', 'guardian_at_registration', 'status', 'amount_due',
            'category_value', 'coupon', 'receipts', 'created_at',
            'has_scores', 'scored_by', 'judge_count', 'comment_count', 'program_logo_url'
        ]

    def get_coupon(self, obj):
        try:
            coupon = obj.coupon
        except Coupon.DoesNotExist:
            return None
        serializer = CouponSerializer(coupon, context=self.context)
        return serializer.data
    
    def get_has_scores(self, obj):
        """Check if this registration has any judging scores"""
        return obj.judging_scores.exists()
    
    def get_scored_by(self, obj):
        """Get list of judge usernames who have scored this registration"""
        # Get distinct judges who have scored this registration
        judges = obj.judging_scores.values_list(
            'judge__username', flat=True
        ).distinct()
        return list(judges)
    
    def get_judge_count(self, obj):
        """Count how many judges have scored this registration"""
        return obj.judging_scores.values('judge').distinct().count()
    
    def get_comment_count(self, obj):
        """Count how many comments this participant has"""
        from scores.models import JudgeComment
        return JudgeComment.objects.filter(participant=obj.participant).count()

    def get_program_logo_url(self, obj):
        request = self.context.get('request')
        logo = getattr(obj.program, 'logo', None)
        if not logo:
            return None
        try:
            url = logo.url
        except Exception:
            return None
        return request.build_absolute_uri(url) if request else url


class ReceiptSerializer(serializers.ModelSerializer):
    registration = serializers.SerializerMethodField()
    registration_id = serializers.IntegerField(source='registration.id', read_only=True)
    issued_by_name = serializers.CharField(source='issued_by.get_full_name', read_only=True)
    program_name = serializers.CharField(source='registration.program.name', read_only=True)
    participant_name = serializers.SerializerMethodField()
    registration_details = serializers.SerializerMethodField()
    program_logo_url = serializers.SerializerMethodField()
    program_fee = serializers.SerializerMethodField()
    amount_paid_total = serializers.SerializerMethodField()
    outstanding_balance = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = [
            'id', 'registration', 'registration_id', 'registration_details',
            'status', 'issued_by', 'issued_by_name', 'amount', 
            'program_name', 'participant_name', 'program_logo_url',
            'program_fee', 'amount_paid_total', 'outstanding_balance',
            'created_at', 'updated_at'
        ]

    def get_registration(self, obj):
        return f"{obj.registration.participant} – {obj.registration.program}"
    
    def get_participant_name(self, obj):
        participant = obj.registration.participant
        return f"{participant.first_name} {participant.last_name}"
    
    def get_registration_details(self, obj):
        """Return detailed registration info for receipt display"""
        reg = obj.registration
        participant = reg.participant
        guardian = reg.guardian_at_registration
        
        data = {
            'id': reg.id,
            'participant': {
                'id': participant.id,
                'first_name': participant.first_name,
                'last_name': participant.last_name,
                'gender': participant.gender,
            },
            'program': reg.program.name,
            'age_at_registration': reg.age_at_registration,
            'status': reg.status,
            'amount_due': str(reg.amount_due),
        }
        
        if guardian:
            data['guardian_at_registration'] = {
                'id': guardian.id,
                'first_name': guardian.first_name,
                'last_name': guardian.last_name,
                'phone_number': guardian.phone_number,
                'email': guardian.email or '',
                'address': guardian.address or '',
                'profession': guardian.profession or '',
            }
        
        return data

    def get_program_logo_url(self, obj):
        request = self.context.get('request')
        logo = getattr(obj.registration.program, 'logo', None)
        if not logo:
            return None
        try:
            url = logo.url
        except Exception:
            return None
        return request.build_absolute_uri(url) if request else url

    def get_program_fee(self, obj):
        fee = obj.registration.program.registration_fee
        return str(fee or 0)

    def get_amount_paid_total(self, obj):
        # Total paid across all approvals (more reliable than a single receipt.amount)
        total = obj.registration.approvals.aggregate(total=models.Sum('amount'))['total']
        return str(total or 0)

    def get_outstanding_balance(self, obj):
        return str(obj.registration.amount_due)


class ApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Approval
        fields = ['id', 'registration', 'status', 'amount']
        read_only_fields = ['id']

    def validate_amount(self, amt):
        reg = Registration.objects.get(pk=self.initial_data['registration'])
        if amt is not None and amt > reg.amount_due:
            raise serializers.ValidationError("Cannot pay more than the amount due.")
        return amt

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            raise serializers.ValidationError({'detail': 'Authentication is required to perform approvals.'})
        if not getattr(user, 'is_staff', False):
            raise serializers.ValidationError({'detail': 'Only staff members can record approvals.'})
        validated_data['created_by'] = user
        approval = super().create(validated_data)
        approval.post_process()
        return approval



# SELF REGISTRATION
class SchoolInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_null=True)
    phone_number = serializers.CharField(required=False, allow_null=True)


class GuardianInputSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    profession = serializers.CharField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_null=True)
    email = serializers.EmailField(required=False, allow_null=True)
    phone_number = serializers.CharField(required=False, allow_null=True)


class ParticipantInputSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField(required=False, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=Participant.Gender.choices)
    age_at_registration = serializers.IntegerField()
    school_at_registration = SchoolInputSerializer()

    form_slug = serializers.CharField(required=False)
    extra_data = serializers.DictField(required=False)
    category_value = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class SelfRegistrationSerializer(serializers.Serializer):
    program = serializers.PrimaryKeyRelatedField(queryset=Program.objects.all())
    guardian = GuardianInputSerializer()
    participants = ParticipantInputSerializer(many=True)

    @transaction.atomic
    def create(self, validated_data: dict) -> dict:
        program = validated_data['program']
        guardian_data = validated_data['guardian']
        participants_data = validated_data['participants']

        guardian = RegistrationUtils.get_or_create_guardian(guardian_data)
        successes = []
        failures = []
        registration_records = []

        for index, pdata in enumerate(participants_data):
            full_name = f"{pdata['first_name'].strip()} {pdata['last_name'].strip()}"
            school_data = pdata.pop('school_at_registration')
            school = RegistrationUtils.get_or_create_school(school_data)
            participant = RegistrationUtils.get_or_create_participant(pdata, guardian, school)

            category_value = (pdata.get('category_value') or '').strip() or None
            if getattr(program, 'category_label', None) and not category_value:
                raise serializers.ValidationError({
                    'participants': [{
                        'full_name': full_name,
                        'category_value': f"{program.category_label} is required."
                    }]
                })
            if program.category_options and category_value and category_value not in program.category_options:
                raise serializers.ValidationError({
                    'participants': [{
                        'full_name': full_name,
                        'category_value': f"'{category_value}' is not a valid option for this program."
                    }]
                })

            try:
                reg, created = Registration.objects.get_or_create(
                    participant=participant,
                    program=program,
                    defaults={
                        'age_at_registration': pdata['age_at_registration'],
                        'school_at_registration': school,
                        'guardian_at_registration': guardian,
                        'status': Registration.Status.PENDING,
                        'category_value': category_value,
                    }
                )
                if not created and category_value and reg.category_value != category_value:
                    reg.category_value = category_value
                    reg.save(update_fields=['category_value'])
                # Handle dynamic form if provided
                form_slug = pdata.get("form_slug")
                extra_data = pdata.get("extra_data")
                if form_slug and extra_data:
                    RegistrationUtils.handle_dynamic_form_submission(
                        form_slug=form_slug,
                        form_data=extra_data,
                        program=program,
                        participant=participant,
                        request=self.context.get('request')
                    )
                if created:
                    successes.append({
                        'reg_no': reg.id,
                        'first_name': participant.first_name,
                        'last_name': participant.last_name
                    })
                else:
                    failures.append({
                        'name': full_name,
                        'reason': 'Already registered for this program'
                    })
            except Exception as exc:
                failures.append({
                    'name': full_name,
                    'reason': str(exc)
                })

        return {
            'guardian': f"{guardian.first_name} {guardian.last_name}",
            'participants': successes,
            'report': failures
        }


class FormFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormField
        fields = [
            'id', 'form', 'field_name', 'label', 'field_type', 'is_required',
            'help_text', 'order', 'options', 'max_length', 'min_value',
            'max_value', 'allowed_file_types', 'max_file_size', 'conditional_logic',
            'step_key', 'column_span'
        ]
        read_only_fields = ['id']


class HybridParticipantInputSerializer(serializers.Serializer):
    """
    Enhanced participant input for hybrid registration.
    """
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField(required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=Participant.Gender.choices)
    age_at_registration = serializers.IntegerField()
    school_at_registration = SchoolInputSerializer()
    category_value = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class HybridRegistrationSerializer(serializers.Serializer):
    """
    Handles hybrid registration with static guardian/participant data + dynamic form fields.
    """
    program = serializers.PrimaryKeyRelatedField(queryset=Program.objects.all())
    guardian = GuardianInputSerializer()
    participants = HybridParticipantInputSerializer(many=True)
    custom_fields = serializers.DictField(required=False, default=dict)

    @transaction.atomic
    def create(self, validated_data: dict) -> dict:
        program = validated_data['program']
        guardian_data = validated_data['guardian']
        participants_data = validated_data['participants']
        custom_fields_data = validated_data.get('custom_fields', {})

        # Create/get guardian using existing utility
        guardian = RegistrationUtils.get_or_create_guardian(guardian_data)
        successes = []
        failures = []
        registration_records = []

        for index, pdata in enumerate(participants_data):
            full_name = f"{pdata['first_name'].strip()} {pdata['last_name'].strip()}"
            school_data = pdata.pop('school_at_registration')
            school = RegistrationUtils.get_or_create_school(school_data)
            participant = RegistrationUtils.get_or_create_participant(pdata, guardian, school)

            category_value = (pdata.get('category_value') or '').strip() or None
            if getattr(program, 'category_label', None) and not category_value:
                raise serializers.ValidationError({
                    'participants': [{
                        'full_name': full_name,
                        'category_value': f"{program.category_label} is required."
                    }]
                })
            if program.category_options and category_value and category_value not in program.category_options:
                raise serializers.ValidationError({
                    'participants': [{
                        'full_name': full_name,
                        'category_value': f"'{category_value}' is not a valid option for this program."
                    }]
                })

            try:
                # Create registration
                reg, created = Registration.objects.get_or_create(
                    participant=participant,
                    program=program,
                    defaults={
                        'age_at_registration': pdata['age_at_registration'],
                        'school_at_registration': school,
                        'guardian_at_registration': guardian,
                        'status': Registration.Status.PENDING,
                        'category_value': category_value,
                    }
                )

                if not created and category_value and reg.category_value != category_value:
                    reg.category_value = category_value
                    reg.save(update_fields=['category_value'])

                registration_records.append({
                    'index': index,
                    'registration': reg,
                    'created': created,
                    'participant': participant,
                })

                if created:
                    successes.append({
                        'reg_no': reg.id,
                        'first_name': participant.first_name,
                        'last_name': participant.last_name
                    })
                else:
                    failures.append({
                        'name': full_name,
                        'reason': 'Already registered for this program'
                    })
            except Exception as exc:
                failures.append({
                    'name': full_name,
                    'reason': str(exc)
                })

        if custom_fields_data:
            self._handle_custom_fields(program, registration_records, custom_fields_data)

        return {
            'guardian': f"{guardian.first_name} {guardian.last_name}",
            'participants': successes,
            'report': failures
        }

    def _handle_custom_fields(self, program: Program, registrations: list, custom_fields: dict):
        """
        Handle custom form field submissions.
        """
        # Prefer active form, fall back to default if none active
        custom_form = program.forms.filter(is_active=True).first()
        if not custom_form:
            custom_form = program.forms.filter(is_default=True).first()
        if not custom_form:
            return

        field_map = {field.field_name: field for field in custom_form.fields.all()}

        if isinstance(custom_fields, dict):
            if 'per_participant' in custom_fields or 'participants' in custom_fields:
                per_participant_data = custom_fields.get('per_participant') or custom_fields.get('participants') or []
                per_participant = {}
                for entry in per_participant_data:
                    if not isinstance(entry, dict):
                        continue
                    idx = entry.get('participant_index')
                    values = entry.get('values') or entry.get('data') or {}
                    if idx is None:
                        continue
                    try:
                        per_participant[int(idx)] = values or {}
                    except (TypeError, ValueError):
                        continue
                global_values = custom_fields.get('global') or custom_fields.get('shared') or {}
            else:
                global_values = custom_fields
                per_participant = {}
        else:
            global_values = {}
            per_participant = {}

        request = self.context.get('request')
        submitted_by = None
        ip_address = None
        user_agent = ''
        if request:
            submitted_by = request.user if request.user.is_authenticated else None
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')

        for record in registrations:
            registration = record.get('registration')
            index = record.get('index')
            if registration is None or index is None:
                continue

            values = {}
            if isinstance(global_values, dict):
                values.update(global_values)
            participant_values = per_participant.get(index)
            if isinstance(participant_values, dict):
                values.update(participant_values)

            filtered_values = {k: v for k, v in values.items() if k in field_map}
            if not filtered_values:
                continue

            # Remove previous responses for this registration/form combination to avoid duplicates
            registration.form_responses.filter(form=custom_form).delete()

            response = FormResponse.objects.create(
                form=custom_form,
                registration=registration,
                submitted_by=submitted_by,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            for field_name, raw_value in filtered_values.items():
                field = field_map[field_name]
                entry_kwargs = {
                    'response': response,
                    'field': field,
                }

                if field.field_type == 'file' and raw_value is not None and hasattr(raw_value, 'read'):
                    entry_kwargs['file_upload'] = raw_value
                    entry_kwargs['value'] = raw_value.name
                else:
                    if isinstance(raw_value, (dict, list)):
                        entry_kwargs['value'] = json.dumps(raw_value)
                    elif raw_value is None:
                        entry_kwargs['value'] = ''
                    else:
                        entry_kwargs['value'] = str(raw_value)

                FormResponseEntry.objects.create(**entry_kwargs)


class ProgramFormSerializer(serializers.ModelSerializer):
    fields = FormFieldSerializer(many=True, read_only=True)

    class Meta:
        model = ProgramForm
        fields = [
            'id', 'program', 'title', 'description', 'slug',
            'is_default', 'is_active', 'age_min', 'age_max', 'fields'
        ]
        read_only_fields = ['id', 'slug']


class ProgramFormStructureSerializer(serializers.ModelSerializer):
    """Return a unified structure combining static and dynamic fields."""

    fields = serializers.SerializerMethodField(method_name='get_combined_fields')
    steps = serializers.SerializerMethodField()
    layout_config = serializers.SerializerMethodField()

    STATIC_GUARDIAN_TEMPLATE = [
        {
            'id': 'guardian-first-name',
            'field_name': 'guardian_first_name',
            'label': 'First Name',
            'field_type': 'text',
            'is_required': True,
            'help_text': '',
            'order': 1,
            'options': None,
            'column_span': 2,
            'step_key': 'static-guardian',
        },
        {
            'id': 'guardian-last-name',
            'field_name': 'guardian_last_name',
            'label': 'Last Name',
            'field_type': 'text',
            'is_required': True,
            'help_text': '',
            'order': 2,
            'options': None,
            'column_span': 2,
            'step_key': 'static-guardian',
        },
        {
            'id': 'guardian-email',
            'field_name': 'guardian_email',
            'label': 'Email Address',
            'field_type': 'email',
            'is_required': False,
            'help_text': '',
            'order': 3,
            'options': None,
            'column_span': 2,
            'step_key': 'static-guardian',
        },
        {
            'id': 'guardian-phone',
            'field_name': 'guardian_phone',
            'label': 'Phone Number',
            'field_type': 'phone',
            'is_required': True,
            'help_text': '',
            'order': 4,
            'options': None,
            'column_span': 2,
            'step_key': 'static-guardian',
        },
        {
            'id': 'guardian-profession',
            'field_name': 'guardian_profession',
            'label': 'Profession',
            'field_type': 'text',
            'is_required': False,
            'help_text': '',
            'order': 5,
            'options': None,
            'column_span': 2,
            'step_key': 'static-guardian',
        },
        {
            'id': 'guardian-address',
            'field_name': 'guardian_address',
            'label': 'Address',
            'field_type': 'text',
            'is_required': False,
            'help_text': '',
            'order': 6,
            'options': None,
            'column_span': 4,
            'step_key': 'static-guardian',
        },
    ]

    STATIC_PARTICIPANT_TEMPLATE = [
        {
            'id': 'participants-list',
            'field_name': 'participants_list',
            'label': 'Participants (Multiple participants can be added)',
            'field_type': 'text',
            'is_required': True,
            'help_text': '',
            'order': 101,
            'options': None,
            'column_span': 4,
            'step_key': 'static-participants',
        },
        {
            'id': 'participant-school',
            'field_name': 'participant_school',
            'label': 'School (Search and select or add new)',
            'field_type': 'text',
            'is_required': True,
            'help_text': '',
            'order': 102,
            'options': None,
            'column_span': 4,
            'step_key': 'static-participants',
        },
    ]

    class Meta:
        model = ProgramForm
        fields = [
            'id', 'program', 'title', 'description', 'slug', 'is_default', 'is_active',
            'age_min', 'age_max', 'fields', 'steps', 'layout_config'
        ]
        read_only_fields = ['id', 'slug']

    def get_combined_fields(self, obj):
        static_fields = self._build_static_field_entries(obj)
        dynamic_fields = self._build_dynamic_field_entries(obj)
        all_fields = static_fields + dynamic_fields
        return sorted(all_fields, key=lambda item: item.get('order', 0))

    def get_steps(self, obj):
        static_steps = self._build_static_steps(obj)
        dynamic_fields = self._build_dynamic_field_entries(obj)
        dynamic_steps = self._build_dynamic_steps(obj, dynamic_fields)
        steps = static_steps + dynamic_steps
        return sorted(steps, key=lambda step: step.get('order', 0))

    def get_layout_config(self, obj):
        layout = obj.layout_config or {}
        if not layout.get('columns'):
            layout['columns'] = 4
        return layout

    def _build_static_field_entries(self, obj):
        guardian_fields = deepcopy(self.STATIC_GUARDIAN_TEMPLATE)
        participant_fields = deepcopy(self.STATIC_PARTICIPANT_TEMPLATE)

        static_fields = []
        for field in guardian_fields + participant_fields:
            field_entry = {
                **field,
                'options': field.get('options') or None,
                'is_static': True,
            }
            static_fields.append(field_entry)

        program = obj.program
        if getattr(program, 'category_label', None):
            category_field = {
                'id': 'participant-category',
                'field_name': 'participant_category',
                'label': program.category_label,
                'field_type': 'dropdown',
                'is_required': True,
                'help_text': f"Select {program.category_label.lower()}",
                'order': 103,
                'options': program.category_options or [],
                'is_static': True,
                'column_span': 4,
                'step_key': 'static-participants',
            }
            static_fields.append(category_field)

        return static_fields

    def _build_dynamic_field_entries(self, obj):
        fields = []
        default_step_key = self._default_dynamic_step_key(obj)
        for field in obj.fields.all().order_by('order', 'id'):
            order_value = field.order or 0
            if order_value < 200:
                order_value = order_value + 200
            field_entry = {
                'id': field.id,
                'field_name': field.field_name,
                'label': field.label,
                'field_type': field.field_type,
                'is_required': field.is_required,
                'help_text': field.help_text,
                'order': order_value,
                'options': field.options,
                'max_length': field.max_length,
                'min_value': field.min_value,
                'max_value': field.max_value,
                'allowed_file_types': field.allowed_file_types,
                'max_file_size': field.max_file_size,
                'conditional_logic': field.conditional_logic,
                'is_static': False,
                'step_key': field.step_key or default_step_key,
                'column_span': field.column_span or 4,
            }
            fields.append(field_entry)
        return fields

    def _build_static_steps(self, obj):
        guardian_fields = [
            {**field, 'is_static': True}
            for field in deepcopy(self.STATIC_GUARDIAN_TEMPLATE)
        ]
        participant_fields = [
            {**field, 'is_static': True}
            for field in deepcopy(self.STATIC_PARTICIPANT_TEMPLATE)
        ]

        program = obj.program
        if getattr(program, 'category_label', None):
            participant_fields.append({
                'id': 'participant-category',
                'field_name': 'participant_category',
                'label': program.category_label,
                'field_type': 'dropdown',
                'is_required': True,
                'help_text': f"Select {program.category_label.lower()}",
                'order': 103,
                'options': program.category_options or [],
                'is_static': True,
                'column_span': 4,
                'step_key': 'static-participants',
            })

        return [
            {
                'key': 'static-guardian',
                'title': 'Guardian Information',
                'description': 'Parent or guardian details',
                'order': 1,
                'is_static': True,
                'per_participant': False,
                'layout': {'columns': 4},
                'fields': guardian_fields,
                'conditional_logic': None,
            },
            {
                'key': 'static-participants',
                'title': 'Participant Information',
                'description': 'Details of participants to register',
                'order': 2,
                'is_static': True,
                'per_participant': True,
                'layout': {'columns': 4},
                'fields': participant_fields,
                'conditional_logic': None,
            },
        ]

    def _build_dynamic_steps(self, obj, dynamic_fields):
        if not dynamic_fields:
            return []

        steps_metadata = obj.step_metadata or []
        fields_by_step = defaultdict(list)
        for field in dynamic_fields:
            step_key = field.get('step_key') or self._default_dynamic_step_key(obj)
            fields_by_step[step_key].append(deepcopy(field))

        dynamic_steps = []
        if steps_metadata:
            sorted_metadata = sorted(
                [meta for meta in steps_metadata if isinstance(meta, dict)],
                key=lambda m: m.get('order', 0)
            )
            offset = 2  # static steps occupy first positions
            for index, meta in enumerate(sorted_metadata, start=1):
                key = meta.get('key') or f'step-{index}'
                step_fields = fields_by_step.get(key, [])
                dynamic_steps.append({
                    'key': key,
                    'title': meta.get('title') or f'Additional Information {index}',
                    'description': meta.get('description', ''),
                    'order': offset + meta.get('order', index),
                    'is_static': False,
                    'per_participant': meta.get('per_participant', True),
                    'layout': meta.get('layout') or {'columns': 4},
                    'fields': step_fields,
                    'conditional_logic': meta.get('conditional_logic') or None,
                })
                fields_by_step.pop(key, None)

        # Handle any fields without matching metadata by grouping on order buckets
        if fields_by_step:
            fallback_steps = self._fallback_steps_from_fields(fields_by_step)
            dynamic_steps.extend(fallback_steps)

        return dynamic_steps

    def _fallback_steps_from_fields(self, fields_by_step):
        fallback_steps = []
        for index, (step_key, fields) in enumerate(sorted(fields_by_step.items()), start=1):
            fallback_steps.append({
                'key': step_key or f'step-{index}',
                'title': f'Additional Information {index}',
                'description': '',
                'order': 2 + index,
                'is_static': False,
                'per_participant': True,
                'layout': {'columns': 4},
                'fields': fields,
                'conditional_logic': None,
            })
        return fallback_steps

    def _default_dynamic_step_key(self, obj):
        steps_metadata = obj.step_metadata or []
        for meta in steps_metadata:
            if isinstance(meta, dict) and not meta.get('is_static'):
                return meta.get('key')
        return 'dynamic-step-1'


class FormFieldWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormField
        fields = [
            'id', 'field_name', 'label', 'field_type', 'is_required',
            'help_text', 'order', 'options', 'max_length', 'min_value',
            'max_value', 'allowed_file_types', 'max_file_size', 'conditional_logic',
            'step_key', 'column_span'
        ]
        read_only_fields = ['id']


class ProgramFormWriteSerializer(serializers.ModelSerializer):
    fields = FormFieldWriteSerializer(many=True, write_only=True)
    steps = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)
    layout_config = serializers.JSONField(required=False)

    class Meta:
        model = ProgramForm
        fields = [
            'id', 'program', 'title', 'description', 'slug', 'is_default', 'is_active',
            'age_min', 'age_max', 'layout_config', 'fields', 'steps'
        ]
        read_only_fields = ['id', 'slug']

    def create(self, validated_data):
        steps_data = validated_data.pop('steps', [])
        fields_data = validated_data.pop('fields', [])
        layout_config = validated_data.pop('layout_config', None)

        field_layout_map = self._build_field_layout_map(steps_data)
        normalized_steps = self._normalize_steps(steps_data)

        program_form = ProgramForm.objects.create(**validated_data)

        updates = []
        if layout_config is not None:
            program_form.layout_config = layout_config or {}
            updates.append('layout_config')
        if normalized_steps is not None:
            program_form.step_metadata = normalized_steps
            updates.append('step_metadata')
        if updates:
            program_form.save(update_fields=updates)

        order_counter = 1
        default_step_key = self._default_step_key(program_form.step_metadata)

        for fdata in fields_data:
            payload = fdata.copy()
            if not payload.get('order'):
                payload['order'] = order_counter
            order_counter += 1

            layout_info = field_layout_map.get(payload.get('field_name'))
            if layout_info:
                payload['step_key'] = layout_info.get('step_key', payload.get('step_key') or default_step_key)
                payload['column_span'] = layout_info.get('column_span') or payload.get('column_span') or 4
            else:
                payload.setdefault('column_span', 4)
                if not payload.get('step_key'):
                    payload['step_key'] = default_step_key

            FormField.objects.create(form=program_form, **payload)

        return program_form

    def update(self, instance, validated_data):
        steps_data = validated_data.pop('steps', None)
        fields_data = validated_data.pop('fields', None)
        layout_config = validated_data.pop('layout_config', None)

        normalized_steps = None
        if steps_data is not None:
            normalized_steps = self._normalize_steps(steps_data)

        field_layout_map = self._build_field_layout_map(steps_data)

        with transaction.atomic():
            if layout_config is not None:
                instance.layout_config = layout_config or {}
            if normalized_steps is not None:
                instance.step_metadata = normalized_steps

            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if fields_data is not None:
                existing_fields = {field.field_name: field for field in instance.fields.all()}
                existing_layout = {
                    field.field_name: {'step_key': field.step_key, 'column_span': field.column_span}
                    for field in existing_fields.values()
                }
                seen_field_names = set()
                order_counter = 1
                default_step_key = self._default_step_key(instance.step_metadata)

                for field_payload in fields_data:
                    payload = field_payload.copy()
                    field_name = payload.get('field_name')
                    if not field_name:
                        continue

                    incoming_order = payload.get('order') or order_counter
                    payload['order'] = incoming_order
                    order_counter += 1

                    layout_info = field_layout_map.get(field_name) or existing_layout.get(field_name)
                    if layout_info:
                        payload['step_key'] = layout_info.get('step_key', payload.get('step_key') or default_step_key)
                        payload['column_span'] = layout_info.get('column_span') or payload.get('column_span') or 4
                    else:
                        payload.setdefault('column_span', 4)
                        if not payload.get('step_key'):
                            payload['step_key'] = default_step_key

                    field_instance = existing_fields.get(field_name)
                    if field_instance:
                        for key, value in payload.items():
                            if key in {'id', 'form'}:
                                continue
                            setattr(field_instance, key, value)
                        field_instance.save()
                    else:
                        payload.pop('id', None)
                        payload.pop('form', None)
                        FormField.objects.create(form=instance, **payload)

                    seen_field_names.add(field_name)

                for field_name, field_instance in existing_fields.items():
                    if field_name not in seen_field_names:
                        field_instance.delete()

        return instance

    def _normalize_steps(self, steps_data):
        if steps_data is None:
            return None
        normalized = []
        for index, step in enumerate(steps_data, start=1):
            if not isinstance(step, dict):
                continue
            key = step.get('key') or step.get('id') or f'step-{index}'
            normalized.append({
                'key': key,
                'title': step.get('title') or f'Step {index}',
                'description': step.get('description', ''),
                'order': step.get('order', index),
                'per_participant': step.get('per_participant', True),
                'layout': step.get('layout') or {},
                'conditional_logic': step.get('conditional_logic') or None,
            })
        return normalized

    def _build_field_layout_map(self, steps_data):
        mapping = {}
        if not steps_data:
            return mapping
        for step in steps_data:
            if not isinstance(step, dict):
                continue
            step_key = step.get('key') or step.get('id')
            if not step_key:
                continue
            for field in step.get('fields', []) or []:
                if not isinstance(field, dict):
                    continue
                field_name = field.get('field_name') or field.get('name')
                if not field_name:
                    continue
                mapping[field_name] = {
                    'step_key': step_key,
                    'column_span': field.get('column_span') or field.get('columnSpan'),
                }
        return mapping

    def _default_step_key(self, step_metadata):
        if not step_metadata:
            return ''
        for step in step_metadata:
            if isinstance(step, dict) and not step.get('is_static'):
                return step.get('key', '')
        first = step_metadata[0]
        return first.get('key', '') if isinstance(first, dict) else ''


class DynamicFormSubmissionSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        self.form = kwargs.pop('form', None)
        super().__init__(*args, **kwargs)
        self._build_fields()

    def _build_fields(self):
        for field in self.form.fields.order_by('order'):
            kwargs = {
                'required': field.is_required,
                'help_text': field.help_text,
                'allow_blank': not field.is_required,
            }
            if field.field_type == 'text':
                self.fields[field.field_name] = serializers.CharField(max_length=field.max_length or 255, **kwargs)
            elif field.field_type == 'textarea':
                self.fields[field.field_name] = serializers.CharField(style={'base_template': 'textarea.html'}, **kwargs)
            elif field.field_type == 'email':
                self.fields[field.field_name] = serializers.EmailField(**kwargs)
            elif field.field_type == 'number':
                self.fields[field.field_name] = serializers.FloatField(min_value=field.min_value, max_value=field.max_value, **kwargs)
            elif field.field_type == 'date':
                self.fields[field.field_name] = serializers.DateField(**kwargs)
            elif field.field_type == 'url':
                self.fields[field.field_name] = serializers.URLField(**kwargs)
            elif field.field_type == 'phone':
                self.fields[field.field_name] = serializers.RegexField(regex=r'^\+?1?\d{9,15}$', **kwargs)
            elif field.field_type == 'file':
                self.fields[field.field_name] = serializers.FileField(**kwargs)
            elif field.field_type in ['dropdown', 'radio']:
                choices = [(opt['value'], opt['label']) if isinstance(opt, dict) else (opt, opt) for opt in field.options or []]
                self.fields[field.field_name] = serializers.ChoiceField(choices=choices, **kwargs)
            elif field.field_type == 'checkbox':
                self.fields[field.field_name] = serializers.BooleanField(**kwargs)
            else:
                self.fields[field.field_name] = serializers.CharField(**kwargs)

    def validate(self, data):
        for field in self.form.fields.filter(field_type='file'):
            val = data.get(field.field_name)
            if val and isinstance(val, UploadedFile):
                if field.max_file_size and val.size > field.max_file_size:
                    raise serializers.ValidationError({field.field_name: f"Max size is {field.max_file_size / 1024:.1f}KB"})
                if field.allowed_file_types:
                    ext = val.name.split('.')[-1].lower()
                    if ext not in field.allowed_file_types:
                        raise serializers.ValidationError({field.field_name: f"Invalid file type '.{ext}'"})
        return data


# JUDGING SYSTEM SERIALIZERS
class RegistrationWithParticipantSerializer(serializers.ModelSerializer):
    """Serializer for judge panel to display paid registrations."""
    participant = ParticipantSerializer(read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    program_id = serializers.IntegerField(source='program.id', read_only=True)
    category_value = serializers.CharField(read_only=True)
    school_name = serializers.CharField(source='school_at_registration.name', read_only=True, allow_null=True)
    has_judge_scores = serializers.SerializerMethodField()
    points = serializers.SerializerMethodField()
    
    class Meta:
        model = Registration
        fields = [
            'id', 'participant', 'program_name', 'program_id', 'age_at_registration',
            'category_value', 'school_name', 'status', 'has_judge_scores', 'points'
        ]
    
    def get_has_judge_scores(self, obj):
        """Check if current judge has scored this participant."""
        judge_id = self.context.get('judge_id')
        if not judge_id:
            return False
        return obj.points.filter(judge_id=judge_id).exists()
    
    def get_points(self, obj):
        """Get all points/scores for this registration."""
        from scores.serializers import PointSerializer
        return PointSerializer(obj.points.all(), many=True).data
