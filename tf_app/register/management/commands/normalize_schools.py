import re
from django.core.management.base import BaseCommand
from django.db import transaction
from difflib import SequenceMatcher
from register.models import School, Participant


class Command(BaseCommand):
    help = (
        "Normalize, unify, dedupe School.name; reassign Participants to a single canonical school; "
        "delete duplicates; and report detailed matches and deletions."
    )

    # threshold for fuzzy matching (0-100)
    SIMILARITY_THRESHOLD = 80
    # how much token-overlap to require (0-100)
    TOKEN_OVERLAP_THRESHOLD = 60
    # words to ignore in token matching
    GENERIC_TOKENS = {"school", "primary", "academy", "college", "nursery", "junior", "senior"}

    def preprocess(self, name):
        # remove punctuation, collapse spaces, lowercase
        clean = re.sub(r"[^a-zA-Z0-9\s]", " ", (name or ""))
        return re.sub(r"\s+", " ", clean).strip().lower()

    def similarity_score(self, a, b):
        return SequenceMatcher(None, a, b).ratio() * 100

    def tokens(self, text):
        # drop generic tokens like "school", "college", etc.
        return [t for t in text.split() if t not in self.GENERIC_TOKENS]

    def handle(self, *args, **options):
        raw_names = list(School.objects.values_list('name', flat=True).distinct())

        canonical_keys = []     # cleaned representative names
        mapping = {}            # raw_name -> canonical key

        for raw in raw_names:
            clean = self.preprocess(raw)
            if not clean:
                continue

            clean_tokens = self.tokens(clean)
            best_key = None
            best_score = 0

            # Token-set matching for ANY length
            for key in canonical_keys:
                key_tokens = self.tokens(key)
                inter = set(clean_tokens).intersection(key_tokens)
                if not inter:
                    continue
                overlap = len(inter) / min(len(clean_tokens), len(key_tokens)) * 100
                if overlap >= self.TOKEN_OVERLAP_THRESHOLD:
                    best_key = key
                    best_score = overlap
                    break

            # If no token-subset match, fall back to fuzzy matching
            if best_key is None:
                for key in canonical_keys:
                    score = self.similarity_score(clean, key)
                    if score > best_score:
                        best_score = score
                        best_key = key

            # Decide cluster assignment
            if best_key and best_score >= self.SIMILARITY_THRESHOLD:
                mapping[raw] = best_key
            else:
                mapping[raw] = clean
                canonical_keys.append(clean)

        # Build clusters
        clusters = {}
        for raw, key in mapping.items():
            clusters.setdefault(key, []).append(raw)

        updated, deleted = 0, 0
        detailed = []

        for key, variants in clusters.items():
            canonical_raw = max(variants, key=lambda s: len(s))
            canonical_name = canonical_raw.strip().upper()

            with transaction.atomic():
                schools = list(School.objects.filter(name__in=variants))
                if not schools:
                    continue

                # pick or default canonical School
                canonical_school = next(
                    (s for s in schools if s.name.strip().upper() == canonical_name),
                    schools[0]
                )

                # update name
                if canonical_school.name.strip().upper() != canonical_name:
                    canonical_school.name = canonical_name
                    canonical_school.save(update_fields=['name'])
                    updated += 1

                deleted_names = []
                for dup in schools:
                    if dup.pk == canonical_school.pk:
                        continue
                    Participant.objects.filter(current_school=dup).update(current_school=canonical_school)
                    deleted_names.append(dup.name)
                    dup.delete()
                    deleted += 1

                detailed.append({
                    'canonical': canonical_school.name,
                    'merged': variants,
                    'deleted': deleted_names,
                })

        # Summary
        self.stdout.write(self.style.SUCCESS(
            f"Processed {len(clusters)} clusters: names updated={updated}, duplicates deleted={deleted}."
        ))
        # Detailed
        for r in detailed:
            self.stdout.write(
                f"- Canonical: {r['canonical']} | Merged: {', '.join(r['merged'])} | Deleted: {', '.join(r['deleted'])}"
            )
