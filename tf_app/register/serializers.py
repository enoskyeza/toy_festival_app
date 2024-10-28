from rest_framework import serializers
from .models import Payment, Contestant, Parent


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'payment_method']


class ContestantSerializer(serializers.ModelSerializer):
    # Read-only fields generated based on logic in the model's save method.
    identifier = serializers.CharField(read_only=True)
    age_category = serializers.CharField(read_only=True)

    payment_method = PaymentSerializer()

    class Meta:
        model = Contestant
        fields = [
            'id', 'identifier', 'first_name', 'last_name', 'email', 'age', 'gender',
            'school', 'payment_status', 'payment_method', 'parent', 'age_category'
        ]
        extra_kwargs = {
            'age': {'min_value': 3, 'max_value': 17},
        }

        def validate(self, data):
            # Custom validation, if needed
            age = data.get('age')
            if age and not (3 <= age <= 17):
                raise serializers.ValidationError("Age must be between 3 and 17.")
            return data


class ParentSerializer(serializers.ModelSerializer):
    contestant = ContestantSerializer(many=True, read_only=True)

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
