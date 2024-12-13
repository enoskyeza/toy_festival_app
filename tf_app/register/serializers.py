from django.shortcuts import get_object_or_404

from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from .models import Payment, Contestant, Parent, Ticket


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'payment_method']


class ContestantSerializer(serializers.ModelSerializer):
    identifier = serializers.CharField(read_only=True)
    age_category = serializers.CharField(read_only=True)
    parent_name = serializers.SerializerMethodField()

    payment_method = PaymentSerializer()

    class Meta:
        model = Contestant
        fields = [
            'id', 'identifier', 'first_name', 'last_name', 'email', 'age', 'gender',
            'school', 'payment_status', 'payment_method', 'parent', 'parent_name', 'age_category', 'has_scores'
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
