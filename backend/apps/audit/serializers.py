from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", default=None)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_username",
            "action",
            "model",
            "object_id",
            "object_repr",
            "changes",
            "ip",
            "user_agent",
            "created_at",
        ]
        read_only_fields = fields
