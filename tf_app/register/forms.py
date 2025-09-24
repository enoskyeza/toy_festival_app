from django.core.exceptions import ValidationError
# from django.utils.text import slugify
# from django.core.files.storage import default_storage
from typing import Optional



from .models import (
    School,
    Guardian,
    Participant,
    Program,
    ProgramForm,
    FormResponse,
    FormResponseEntry,
    ParticipantGuardian
)


class RegistrationUtils:
    @staticmethod
    def normalize_phone(phone: Optional[str]) -> Optional[str]:
        digits = ''.join(filter(str.isdigit, phone or ''))
        return '256' + digits[-9:] if len(digits) >= 9 else None

    @staticmethod
    def estimate_dob(age: int) -> 'date':
        from datetime import date
        today = date.today()
        try:
            return today.replace(year=today.year - age)
        except ValueError:
            return today.replace(year=today.year - age, day=28)

    @staticmethod
    def get_or_create_school(data: dict) -> School:
        id_ = data.get('id')
        if id_:
            try:
                return School.objects.get(id=id_)
            except School.DoesNotExist:
                raise ValidationError(f"School with id {id_} does not exist.")
        raw_name = (data.get('name') or '').strip()
        if not raw_name:
            raise ValidationError("Each participant must include a school (or school id).")
        name = raw_name.upper()
        phone = RegistrationUtils.normalize_phone(data.get('phone_number'))
        school, created = School.objects.get_or_create(
            name__iexact=raw_name,
            defaults={
                'name': name,
                'address': data.get('address'),
                'email': data.get('email'),
                'phone_number': phone,
            }
        )
        if not created and school.name != name:
            school.name = name
            school.save(update_fields=['name'])
        return school

    @staticmethod
    def get_or_create_guardian(data: dict) -> Guardian:
        phone = RegistrationUtils.normalize_phone(data.get('phone_number'))
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

    @staticmethod
    def get_or_create_participant(data: dict, guardian: Guardian, school: School) -> Participant:
        qs = Participant.objects.filter(
            first_name__iexact=data['first_name'].strip(),
            last_name__iexact=data['last_name'].strip(),
            guardians=guardian,
        )
        if participant := qs.first():
            return participant
        dob = data.get('date_of_birth') or RegistrationUtils.estimate_dob(data['age_at_registration'])
        participant = Participant.objects.create(
            first_name=data['first_name'].strip(),
            last_name=data['last_name'].strip(),
            email=data.get('email'),
            date_of_birth=dob,
            age=data['age_at_registration'],
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

    @staticmethod
    def handle_dynamic_form_submission(form_slug: str, form_data: dict, program: Program, participant: Participant, request=None) -> FormResponse:

        from .serializers import DynamicFormSubmissionSerializer

        form = ProgramForm.objects.get(slug=form_slug, program=program)
        serializer = DynamicFormSubmissionSerializer(data=form_data, form=form)
        serializer.is_valid(raise_exception=True)
        response = FormResponse.objects.create(
            form=form,
            submitted_by=request.user if request and request.user.is_authenticated else None,
            ip_address=request.META.get("REMOTE_ADDR") if request else None,
            user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
            participant=participant
        )
        for field in form.fields.all():
            val = serializer.validated_data.get(field.field_name)
            entry = FormResponseEntry(response=response, field=field)
            if field.field_type == 'file' and val:
                entry.file_upload = val
                entry.value = val.name
            else:
                entry.value = str(val or '')
            entry.save()
        return response


