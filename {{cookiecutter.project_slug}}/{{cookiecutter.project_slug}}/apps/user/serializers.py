import re

from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.contrib.auth import authenticate
from django.utils.translation import ugettext_lazy as _

from rest_framework.settings import api_settings

from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework.authtoken.serializers import AuthTokenSerializer

from {{cookiecutter.project_slug}}.apps.user.models import ActionToken

User = get_user_model()


# Validator for phone numbers
def phone_number_validator(phone):
    reg = re.compile('^([+][0-9]{1,2})?[0-9]{9,10}$')
    char_list = " -.()"
    for i in char_list:
        phone = phone.replace(i, '')
    if not reg.match(phone):
        raise serializers.ValidationError(_("Invalid format."))
    return phone


class UserUpdateSerializer(serializers.HyperlinkedModelSerializer):
    """
    Set  certain fields such as university, academic_level and email to read
    only.
    """
    id = serializers.ReadOnlyField()

    new_password = serializers.CharField(
        max_length=128,
        required=False,
        help_text=_("A valid password."),
    )
    phone = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        label=_('Phone number'),
        max_length=17,
        required=False,
        help_text=_("A valid phone number."),
    )
    other_phone = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        label=_('Other number'),
        max_length=17,
        required=False,
        help_text=_("A valid phone number."),
    )

    def validate_phone(self, value):
        return phone_number_validator(value)

    def validate_other_phone(self, value):
        return phone_number_validator(value)

    def update(self, instance, validated_data):
        if 'new_password' in validated_data.keys():
            try:
                old_pw = validated_data.pop('password')
            except KeyError:
                raise serializers.ValidationError({
                    'password': _("This field is required.")
                })

            new_pw = validated_data.pop('new_password')

            try:
                password_validation.validate_password(password=new_pw)
            except ValidationError as err:
                raise serializers.ValidationError({
                    'new_password': err.messages
                })

            if instance.check_password(old_pw):
                instance.set_password(new_pw)
                instance.save()
            else:
                msg = {'password': _("Bad password")}
                raise serializers.ValidationError(msg)

        return super().update(instance, validated_data)

    class Meta:
        model = User
        fields = '__all__'
        extra_kwargs = {
            'password': {
                'write_only': True,
                'help_text': _("A valid password."),
            },
            'new_password': {'write_only': True},
            'first_name': {
                'allow_blank': False,
                'help_text': _("A valid first name."),
            },
            'last_name': {
                'allow_blank': False,
                'help_text': _("A valid last name."),
            },
        }
        read_only_fields = (
            'id',
            'url',
            'is_staff',
            'is_superuser',
            'is_active',
            'date_joined',
            'last_login',
            'groups',
            'user_permissions',
            'email',
        )


class UserSerializer(UserUpdateSerializer):
    """
    Complete serializer for user creation
    """
    # Remove the new_password field.
    new_password = None

    email = serializers.EmailField(
        label=_('Email address'),
        max_length=254,
        required=True,

        help_text=_("A valid email address."),
    )

    def validate_password(self, value):
        try:
            password_validation.validate_password(password=value)
        except ValidationError as err:
            raise serializers.ValidationError(err.messages)
        return value

    def create(self, validated_data):
        """
        Validate choosen password and create User object.
        """
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        try:
            user = User.objects.get(email=email)

            if user.has_usable_password() and user.is_active:
                raise serializers.ValidationError({
                    "email": [
                        _(
                            "An account for the specified email "
                            "address already exists."
                        )
                    ]
                })

        except ObjectDoesNotExist:
            pass

        user, created = User.objects.get_or_create(
            email=email, defaults=validated_data)

        # Hash the user's password
        user.set_password(password)
        # Put user inactive by default
        user.is_active = False
        user.save()

        # Create an ActivationToken to activate user in the future
        ActionToken.objects.create(
            user=user,
            type='account_activation',
        )

        return user

    class Meta:
        model = User
        fields = '__all__'
        extra_kwargs = {
            'password': {
                'style': {'input_type': 'password'},
                'write_only': True,
                'help_text': _("A valid password."),
            },
            'first_name': {
                'allow_blank': False,
                'help_text': _("A valid first name."),
            },
            'last_name': {
                'allow_blank': False,
                'help_text': _("A valid last name."),
            },
        }
        read_only_fields = (
            'id',
            'url',
            'is_staff',
            'is_superuser',
            'is_active',
            'date_joined',
            'last_login',
            'groups',
            'user_permissions',
        )


class CustomAuthTokenSerializer(AuthTokenSerializer):
    """
    Subclass of default AuthTokenSerializer to enable email authentication
    """
    email = serializers.CharField(
        label=_("Email"),
        required=True,
        help_text=_("A valid email."),
    )

    username = serializers.CharField(
        label=_("Username"),
        required=False,
        help_text=_("A valid username."),
    )

    password = serializers.CharField(
        label=_("Password"),
        style={'input_type': 'password'},
        trim_whitespace=False,
        required=True,
        help_text=_("A valid password."),
    )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        try:
            user_obj = User.objects.get(email=email)
            email = user_obj.email
        except User.DoesNotExist:
            pass

        user = authenticate(request=self.context.get('request'),
                            email=email, password=password)

        if not user:
            msg = _('Unable to log in with provided credentials.')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user

        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(
        label=_('Email address'),
        max_length=254,
        required=True,
        help_text=_("A valid email address."),
    )

    def validate_email(self, value):
        if User.objects.filter(email=value):
            return value
        raise serializers.ValidationError(
            _("No account associated to this email address.")
        )

    def validate(self, attrs):
        return User.objects.get(email=attrs['email'])


class ChangePasswordSerializer(serializers.Serializer):
    token = serializers.CharField(
        required=True,
        help_text=_("Action token authorizing password change."),
    )
    new_password = serializers.CharField(
        required=True,
        help_text=_("Desired password"),
    )


class UsersActivationSerializer(serializers.Serializer):
    activation_token = serializers.CharField(
        required=True,
        help_text=_("Action token authorizing user activation."),
    )


class PermissionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Permission
        fields = '__all__'
