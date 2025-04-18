from django.shortcuts import get_object_or_404
from django.db import transaction

from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from .models import (
    Payment, Contestant, Parent, Ticket, School, Guardian,
    Participant, ProgramType, Program, Registration

)
from scores.serializers import ScoreSerializer


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
    class Meta:
        model = Program
        fields = ['id','type', 'year', 'name', 'description', 'start_date', 'end_date',
                  'registration_fee', 'age_min', 'age_max', 'capacity', 'requires_ticket']


class RegistrationSerializer(serializers.ModelSerializer):
    participant = serializers.PrimaryKeyRelatedField(
        queryset=Participant.objects.all()
    )
    program = serializers.PrimaryKeyRelatedField(
        queryset=Program.objects.all()
    )
    school_at_registration = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.all(),
        allow_null=True,
        required=False
    )
    guardian_at_registration = serializers.PrimaryKeyRelatedField(
        queryset=Guardian.objects.all(),
        allow_null=True,
        required=False
    )

    class Meta:
        model = Registration
        fields = [
            'id', 'participant', 'program', 'age_at_registration',
            'school_at_registration', 'guardian_at_registration', 'status'
        ]


# SELF REGISTRATION
class SchoolInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)
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
    date_of_birth = serializers.DateField()
    gender = serializers.ChoiceField(choices=Participant.Gender.choices)
    age_at_registration = serializers.IntegerField()


class SelfRegistrationSerializer(serializers.Serializer):
    program = serializers.PrimaryKeyRelatedField(queryset=Program.objects.all())
    school = SchoolInputSerializer()
    guardian = GuardianInputSerializer()
    participants = ParticipantInputSerializer(many=True)

    def normalize_phone(self, phone):
        digits = ''.join(filter(str.isdigit, phone or ''))
        if len(digits) >= 9:
            return '256' + digits[-9:]
        return None

    def get_or_create_school(self, data):
        if data.get('id'):
            try:
                return School.objects.get(id=data['id'])
            except School.DoesNotExist:
                raise ValidationError(f"School with id {data['id']} does not exist.")

        name = data.get('name', '').strip()
        if not name:
            raise ValidationError("School name is required if not providing an id.")
        school, _ = School.objects.get_or_create(
            name__iexact=name,
            defaults={
                'name': name,
                'address': data.get('address'),
                'email': data.get('email'),
                'phone_number': self.normalize_phone(data.get('phone_number'))
            }
        )
        return school

    def get_or_create_guardian(self, data):
        phone = self.normalize_phone(data.get('phone_number'))
        qs = Guardian.objects.all()
        if phone:
            guardian = qs.filter(phone_number=phone).first()
        elif data.get('email'):
            guardian = qs.filter(email__iexact=data['email']).first()
        else:
            guardian = qs.filter(
                first_name__iexact=data['first_name'].strip(),
                last_name__iexact=data['last_name'].strip()
            ).first()

        if guardian:
            return guardian
        return Guardian.objects.create(
            first_name=data['first_name'].strip(),
            last_name=data['last_name'].strip(),
            profession=data.get('profession'),
            address=data.get('address'),
            email=data.get('email'),
            phone_number=phone
        )

    def get_or_create_participant(self, data, guardian, school):
        # try to find existing participant for this guardian by name
        qs = Participant.objects.filter(
            first_name__iexact=data['first_name'].strip(),
            last_name__iexact=data['last_name'].strip(),
            guardians=guardian
        )
        participant = qs.first()
        if participant:
            return participant

        participant = Participant.objects.create(
            first_name=data['first_name'].strip(),
            last_name=data['last_name'].strip(),
            email=data.get('email'),
            date_of_birth=data['date_of_birth'],
            gender=data['gender'],
            current_school=school
        )
        ParticipantGuardian.objects.create(
            participant=participant,
            guardian=guardian,
            relationship='other',
            is_primary=True
        )
        return participant

    @transaction.atomic
    def create(self, validated_data):
        program = validated_data['program']
        school_data = validated_data['school']
        guardian_data = validated_data['guardian']
        participants_data = validated_data['participants']

        school = self.get_or_create_school(school_data)
        guardian = self.get_or_create_guardian(guardian_data)

        registrations = []
        for pdata in participants_data:
            participant = self.get_or_create_participant(pdata, guardian, school)

            reg, created = Registration.objects.get_or_create(
                participant=participant,
                program=program,
                defaults={
                    'age_at_registration': pdata['age_at_registration'],
                    'school_at_registration': school,
                    'guardian_at_registration': guardian,
                    'status': Registration.Status.PENDING
                }
            )
            registrations.append(reg)

        return registrations