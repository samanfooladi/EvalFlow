from rest_framework import serializers

from .models import Clause, DefaultTextTemplate, Framework, Requirement


class ClauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clause
        fields = ["id", "requirement", "code", "title", "description",
                  "objective", "order"]


class RequirementSerializer(serializers.ModelSerializer):
    clauses = ClauseSerializer(many=True, read_only=True)

    class Meta:
        model = Requirement
        fields = ["id", "framework", "klass_title", "code", "title",
                  "guidance", "order", "clauses"]


class RequirementWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requirement
        fields = ["id", "framework", "klass_title", "code", "title",
                  "guidance", "order"]


class DefaultTextTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefaultTextTemplate
        fields = ["id", "framework", "status", "template"]


class FrameworkSerializer(serializers.ModelSerializer):
    requirements_count = serializers.IntegerField(read_only=True, default=0)
    clauses_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Framework
        fields = ["id", "code", "title", "kind", "is_active",
                  "requirements_count", "clauses_count"]


class FrameworkDetailSerializer(FrameworkSerializer):
    requirements = RequirementSerializer(many=True, read_only=True)
    default_texts = DefaultTextTemplateSerializer(many=True, read_only=True)

    class Meta(FrameworkSerializer.Meta):
        fields = FrameworkSerializer.Meta.fields + ["requirements", "default_texts"]
