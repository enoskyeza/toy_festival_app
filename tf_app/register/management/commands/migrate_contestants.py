from django.core.management.base import BaseCommand
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from register.models import (
    Contestant, School, Guardian, Participant, ParticipantGuardian
)
import re, csv, os

def normalize_phone(raw):
    digits = re.sub(r'\D', '', raw or '')
    core9 = digits[-9:]
    return f'256{core9}'

def title_case(name):
    return ' '.join(w.capitalize() for w in name.strip().split())

class Command(BaseCommand):
    help = "Migrate legacy Contestants → Participants/Guardians/Schools"

    def handle(self, *args, **opts):
        school_map = {}
        guardian_map = {}
        participant_map = {}
        failures = []

        for c in Contestant.objects.select_related('parent').all():
            try:
                # --- 1. School dedupe/create ---
                school_key = (c.school or '').strip().lower()
                if school_key and school_key not in school_map:
                    sch = School.objects.create(
                        name=c.school.strip().upper(),
                        address='',
                        email=None,
                        phone_number=None
                    )
                    school_map[school_key] = sch
                school = school_map.get(school_key)

                # --- 2. Guardian dedupe/create ---
                p = c.parent
                phone_norm = normalize_phone(p.phone_number)
                guardian_key = (
                    phone_norm,
                    (p.email or '').strip().lower(),
                    p.first_name.strip().lower(),
                    p.last_name.strip().lower()
                )
                if guardian_key not in guardian_map:
                    g = Guardian.objects.create(
                        first_name=title_case(p.first_name),
                        last_name=title_case(p.last_name),
                        profession=p.profession,
                        address=p.address,
                        email=p.email,
                        phone_number=phone_norm
                    )
                    guardian_map[guardian_key] = g
                guardian = guardian_map[guardian_key]

                # --- 3. Participant dedupe/create with DOB from created_at & age ---
                created_date = c.created_at.date()
                approx_dob = created_date - relativedelta(years=c.age or 0)

                name_match = Participant.objects.filter(
                    first_name__iexact=c.first_name.strip(),
                    last_name__iexact=c.last_name.strip(),
                    age=c.age
                )

                if name_match.exists():
                    participant = name_match.first()
                else:
                    participant = Participant.objects.create(
                        first_name=title_case(c.first_name),
                        last_name=title_case(c.last_name),
                        email=c.email,
                        date_of_birth=approx_dob,
                        age=c.age,
                        gender=c.gender,
                        current_school=school
                    )

                # --- 4. Link Participant ↔ Guardian (skip duplicates) ---
                ParticipantGuardian.objects.get_or_create(
                    participant=participant,
                    guardian=guardian,
                    defaults={'relationship': 'other', 'is_primary': True}
                )

            except Exception as e:
                failures.append({
                    'contestant_id': c.id,
                    'error': str(e),
                })

        # --- 5. Reporting ---
        summary = {
            'schools_created': len(school_map),
            'guardians_created': len(guardian_map),
            'participants_created': len(participant_map),
            'failures': len(failures),
        }
        self.stdout.write(self.style.SUCCESS(f"Migration summary: {summary}"))

        if failures:
            path = os.path.join('tmp', 'migration_failures.csv')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', newline='') as fp:
                writer = csv.DictWriter(fp, fieldnames=['contestant_id', 'error'])
                writer.writeheader()
                writer.writerows(failures)
            self.stdout.write(
                self.style.WARNING(f"Failures logged to {path}")
            )

# from django.core.management.base import BaseCommand
# from dateutil.relativedelta import relativedelta
# from django.utils import timezone
# from register.models import (
#     Contestant, School, Guardian, Participant, ParticipantGuardian
# )
# import re, csv, os
#
# def normalize_phone(raw):
#     digits = re.sub(r'\D', '', raw or '')
#     core9 = digits[-9:]
#     return f'256{core9}'
#
# def title_case(name):
#     return ' '.join(w.capitalize() for w in name.strip().split())
#
# class Command(BaseCommand):
#     help = "Migrate legacy Contestants → Participants/Guardians/Schools"
#
#     def handle(self, *args, **opts):
#         school_map = {}
#         guardian_map = {}
#         participant_map = {}
#         failures = []
#
#         for c in Contestant.objects.select_related('parent').all():
#             try:
#                 # --- 1. School dedupe/create ---
#                 school_key = (c.school or '').strip().lower()
#                 if school_key and school_key not in school_map:
#                     sch = School.objects.create(
#                         name=c.school.strip().upper(),
#                         address='',
#                         email=None,
#                         phone_number=None
#                     )
#                     school_map[school_key] = sch
#                 school = school_map.get(school_key)
#
#                 # --- 2. Guardian dedupe/create ---
#                 p = c.parent
#                 phone_norm = normalize_phone(p.phone_number)
#                 guardian_key = (
#                     phone_norm,
#                     (p.email or '').strip().lower(),
#                     p.first_name.strip().lower(),
#                     p.last_name.strip().lower()
#                 )
#                 if guardian_key not in guardian_map:
#                     g = Guardian.objects.create(
#                         first_name=title_case(p.first_name),
#                         last_name=title_case(p.last_name),
#                         profession=p.profession,
#                         address=p.address,
#                         email=p.email,
#                         phone_number=phone_norm
#                     )
#                     guardian_map[guardian_key] = g
#                 guardian = guardian_map[guardian_key]
#
#                 # --- 3. Participant dedupe/create with DOB from created_at & age ---
#                 created_date = c.created_at.date()
#                 approx_dob = created_date - relativedelta(years=c.age or 0)
#
#                 email_key = (c.email or '').strip().lower()
#                 name_key = (
#                     c.first_name.strip().lower(),
#                     c.last_name.strip().lower(),
#                     approx_dob.isoformat()
#                 )
#                 if email_key and email_key not in participant_map:
#                     participant = Participant.objects.create(
#                         first_name=title_case(c.first_name),
#                         last_name=title_case(c.last_name),
#                         email=c.email,
#                         date_of_birth=approx_dob,
#                         gender=c.gender,
#                         current_school=school
#                     )
#                     participant_map[email_key] = participant
#
#                 elif name_key not in participant_map:
#                     participant = Participant.objects.create(
#                         first_name=title_case(c.first_name),
#                         last_name=title_case(c.last_name),
#                         email=c.email,
#                         date_of_birth=approx_dob,
#                         gender=c.gender,
#                         current_school=school
#                     )
#                     participant_map[name_key] = participant
#
#                 else:
#                     key = email_key if email_key else name_key
#                     participant = participant_map[key]
#
#                 # --- 4. Link Participant ↔ Guardian ---
#                 ParticipantGuardian.objects.get_or_create(
#                     participant=participant,
#                     guardian=guardian,
#                     defaults={'relationship': 'other', 'is_primary': True}
#                 )
#
#             except Exception as e:
#                 failures.append({
#                     'contestant_id': c.id,
#                     'error': str(e),
#                 })
#
#         # --- 5. Reporting ---
#         summary = {
#             'schools_created': len(school_map),
#             'guardians_created': len(guardian_map),
#             'participants_created': len(participant_map),
#             'failures': len(failures),
#         }
#         self.stdout.write(self.style.SUCCESS(f"Migration summary: {summary}"))
#
#         if failures:
#             path = os.path.join('tmp', 'migration_failures.csv')
#             os.makedirs(os.path.dirname(path), exist_ok=True)
#             with open(path, 'w', newline='') as fp:
#                 writer = csv.DictWriter(fp, fieldnames=['contestant_id', 'error'])
#                 writer.writeheader()
#                 writer.writerows(failures)
#             self.stdout.write(
#                 self.style.WARNING(f"Failures logged to {path}")
#             )
#
