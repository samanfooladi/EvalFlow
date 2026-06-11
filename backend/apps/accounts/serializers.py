from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Role, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "assessor_code",
            "is_active",
            "must_change_password",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["date_joined", "last_login", "must_change_password"]


class UserCreateSerializer(UserSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["password"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_role(self, value):
        if value not in Role.values:
            raise serializers.ValidationError("نقش نامعتبر است.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        # Admin-created accounts must rotate their initial password.
        user.must_change_password = True
        user.save()
        return user


class UserUpdateSerializer(UserSerializer):
    """Admin update — never the password (separate endpoint handles that)."""


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("کلمه عبور فعلی صحیح نیست.")
        return value

    def validate_new_password(self, value):
        validate_password(value, user=self.context["request"].user)
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        return user
