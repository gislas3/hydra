import uuid

from .models import (
    Batch,
    Job_Definition,
    Job_Spec,
    Region,
    Batch_Job
)
from rest_framework import serializers


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job_Definition
        fields = '__all__'


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = '__all__'


def validate_batch_id(value):
    if type(value) != uuid.UUID:
        try:
            value = uuid.UUID(value)
        except Exception as e:
            raise serializers.ValidationError('Badly formatted batch_id')
    batch_exists = Batch.objects.filter(batch_id=value).count()
    if batch_exists:
        raise serializers.ValidationError('Batch_id already exists!')


class BatchSerializer(serializers.ModelSerializer):
    batch_id = serializers.UUIDField(validators=[validate_batch_id])
    region = serializers.SlugRelatedField(
        many=False,
        # read_only=True,
        queryset=Region.objects.all(),
        slug_field='code'
    )

    class Meta:
        model = Batch
        fields = '__all__'


class JobSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job_Spec
        fields = '__all__'


class BatchJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch_Job
        fields = '__all__'
