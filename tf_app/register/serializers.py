from django.shortcuts import get_object_or_404

from rest_framework.exceptions import ValidationError
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
    parent = serializers.SerializerMethodField()

    payment_method = PaymentSerializer()

    class Meta:
        model = Contestant
        fields = [
            'id', 'identifier', 'first_name', 'last_name', 'email', 'age', 'gender',
            'school', 'payment_status', 'payment_method', 'parent', 'age_category'
        ]
        extra_kwargs = {
            'age': {
                'min_value': 3,
                'max_value': 17,
                'error_messages': {
                    'min_value': 'Age cannot be less than 3.',
                    'max_value': 'Age cannot be greater than 17.'
                }
            },
        }

    def get_parent(self, obj):
        # Replace this with how you want to represent the parent as a string.
        # For example, you could use the parent's first and last name:
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
