from rest_framework import serializers

from .models import Company, ProductSystem


class CompanySerializer(serializers.ModelSerializer):
    systems_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Company
        fields = ["id", "name", "name_en", "systems_count", "created_at"]
        read_only_fields = ["created_at"]


class ProductSystemSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = ProductSystem
        fields = [
            "id",
            "company",
            "company_name",
            "name",
            "name_en",
            "version",
            "description",
            "created_at",
        ]
        read_only_fields = ["created_at"]
