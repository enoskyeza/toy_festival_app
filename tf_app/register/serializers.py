from django.shortcuts import get_object_or_404
from django.db import transaction
from datetime import date
from typing import Optional

from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from .models import (
    Payment, Contestant, Parent, Ticket, School, Guardian,
    Participant, ParticipantGuardian ,ProgramType, Program,
    Registration, Receipt, Approval, Coupon, ProgramForm, FormField
)
from scores.serializers import ScoreSerializer
from .forms import RegistrationUtils


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'payment_method']


class ContestantSerializer(serializers.ModelSerializer):
    identifier = serializers.CharField(read_only=True)
    age_category = serializers.CharField(read_only=True)
    parent_name = serializers.SerializerMethodField()
    scores = ScoreSerializer(many=True, read_only=True)

    payment_method = PaymentSerializer()

    class Meta:
        model = Contestant
        fields = [
            'id', 'identifier', 'first_name', 'last_name', 'email', 'age', 'gender',
            'school', 'payment_status', 'payment_method', 'parent', 'parent_name', 'age_category', 'scores'
        ]
        extra_kwargs = {
            'age': {
                'min_value': 3,
                'max_value': 19,
                'error_messages': {
                    'min_value': 'Age cannot be less than 3.',
                    'max_value': 'Age cannot be greater than 19.'
                }
            },
        }

    def get_parent_name(self, obj):
        if obj.parent:
            return f"{obj.parent.first_name} {obj.parent.last_name}"
        return "No parent assigned"


class ParentSerializer(serializers.ModelSerializer):
    contestants = ContestantSerializer(many=True, read_only=True)

    class Meta:
        model = Parent
        fields = ['id', 'first_name', 'last_name', 'profession', 'address', 'email', 'phone_number', 'contestants']


# Create or Update serializer for Parent with nested Contestant creation
class ParentCreateUpdateSerializer(serializers.ModelSerializer):
    contestants = ContestantSerializer(many=True, write_only=True)

    class Meta:
        model = Parent
        fields = [
            'id', 'first_name', 'last_name', 'profession', 'address', 'email', 'phone_number', 'contestants'
        ]

    def create(self, validated_data):
        contestants_data = validated_data.pop('contestants', [])
        parent = Parent.objects.create(**validated_data)

        for contestant_data in contestants_data:
            payment_data = contestant_data.pop('payment_method', None)

            if payment_data:
                try:
                    payment_instance = get_object_or_404(Payment, payment_method=payment_data.get('payment_method'))
                except ValidationError:
                    raise ValidationError({"payment_method": "The specified payment method does not exist."})

                contestant_data['payment_method'] = payment_instance

            Contestant.objects.create(parent=parent, **contestant_data)

        return parent

    def update(self, instance, validated_data):
        contestants_data = validated_data.pop('contestants', [])

        # Update Parent instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update or create Contestants
        for contestant_data in contestants_data:
            payment_data = contestant_data.pop('payment_method', None)

            if payment_data:
                try:
                    payment_instance = get_object_or_404(Payment, payment_method=payment_data.get('payment_method'))
                except ValidationError:
                    raise ValidationError({"payment_method": "The specified payment method does not exist."})

                contestant_data['payment_method'] = payment_instance

            contestant_id = contestant_data.get('id')

            if contestant_id:
                # Update existing Contestant
                contestant = Contestant.objects.get(id=contestant_id, parent=instance)
                for attr, value in contestant_data.items():
                    setattr(contestant, attr, value)
                contestant.save()
            else:
                # Create new Contestant linked to Parent
                Contestant.objects.create(parent=instance, **contestant_data)

        return instance


#Ticket serializer
class TicketSerializer(serializers.ModelSerializer):
    participant = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Ticket
        fields = ['id', 'participant', 'qr_code', 'created_at', 'updated_at']
        read_only_fields = ['id', 'qr_code', 'created_at', 'updated_at']


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
            'capacity', 'requires_ticket', 'active', 'level', 'thumbnail_url', 
            'video_url', 'instructor', 'featured', 'modules', 'learning_outcomes', 
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

    class Meta:
        model = Registration
        fields = [
            'id', 'participant', 'program', 'age_at_registration',
            'school_at_registration', 'guardian_at_registration', 'status', 'amount_due',
            'category_value', 'coupon', 'receipts', 'created_at'
        ]

    def get_coupon(self, obj):
        try:
            coupon = obj.coupon
        except Coupon.DoesNotExist:
            return None
        serializer = CouponSerializer(coupon, context=self.context)
        return serializer.data


class ReceiptSerializer(serializers.ModelSerializer):
    registration = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = ['id', 'registration', 'status', 'issued_by', 'amount', 'created_at']

    def get_registration(self, obj):
        return f"{obj.registration.participant} – {obj.registration.program}"


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
        print('SUBMITTED DATA: ', validated_data)
        user = self.context['request'].user
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

        for pdata in participants_data:
            full_name = f"{pdata['first_name'].strip()} {pdata['last_name'].strip()}"
            school_data = pdata.pop('school_at_registration')
            school = RegistrationUtils.get_or_create_school(school_data)
            participant = RegistrationUtils.get_or_create_participant(pdata, guardian, school)

            category_value = (pdata.get('category_value') or '').strip() or None
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
            'max_value', 'allowed_file_types', 'max_file_size', 'conditional_logic'
        ]
        read_only_fields = ['id']


class ProgramFormSerializer(serializers.ModelSerializer):
    fields = FormFieldSerializer(many=True, read_only=True)

    class Meta:
        model = ProgramForm
        fields = [
            'id', 'program', 'title', 'description', 'slug',
            'is_default', 'age_min', 'age_max', 'fields'
        ]
        read_only_fields = ['id', 'slug']


class FormFieldWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormField
        fields = [
            'id', 'field_name', 'label', 'field_type', 'is_required',
            'help_text', 'order', 'options', 'max_length', 'min_value',
            'max_value', 'allowed_file_types', 'max_file_size', 'conditional_logic'
        ]
        read_only_fields = ['id']


class ProgramFormWriteSerializer(serializers.ModelSerializer):
    fields = FormFieldWriteSerializer(many=True, write_only=True)

    class Meta:
        model = ProgramForm
        fields = [
            'id', 'program', 'title', 'description', 'slug', 'is_default',
            'age_min', 'age_max', 'fields'
        ]
        read_only_fields = ['id', 'slug']

    def create(self, validated_data):
        fields_data = validated_data.pop('fields', [])
        program_form = ProgramForm.objects.create(**validated_data)
        order_counter = 1
        for fdata in fields_data:
            if not fdata.get('order'):
                fdata['order'] = order_counter
            FormField.objects.create(form=program_form, **fdata)
            order_counter += 1
        return program_form


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
