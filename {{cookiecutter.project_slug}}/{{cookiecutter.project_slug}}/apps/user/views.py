from django.contrib.auth import get_user_model, password_validation
from django.conf import settings
from django.contrib.auth.models import Permission
from django.utils import timezone
from django.http import Http404
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from rest_framework import status, viewsets, mixins
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import JSONParser

from {{cookiecutter.project_slug}} import permissions

from .models import (
    TemporaryToken,
    ActionToken, )

from . import serializers

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return the given user.

    list:
    Return a list of all existing users.

    create:
    Create a new user instance.

    update:
    Update fields of a user instance.

    delete:
    Sets the user inactive.
    """
    queryset = User.objects.all()
    filter_fields = '__all__'

    def get_serializer_class(self):
        if (self.action == 'update') | (self.action == 'partial_update'):
            return serializers.UserUpdateSerializer
        return serializers.UserSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = User.objects.all()
        if self.kwargs.get("pk", "") == "me":
            self.kwargs['pk'] = user.id
        return queryset

    def get_permissions(self):
        """
        Returns the list of permissions that this view requires.
        """
        if self.action == 'create':
            permission_classes = []
        elif self.action == 'list':
            permission_classes = [IsAdminUser, ]
        else:
            permission_classes = [
                IsAuthenticated,
                permissions.IsOwner
            ]
        return [permission() for permission in permission_classes]

    def retrieve(self, request, *args, **kwargs):
        if request.user.is_staff:
            return super().retrieve(request, *args, **kwargs)
        try:
            return super().retrieve(request, *args, **kwargs)
        except Http404:
            raise PermissionDenied

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.is_active = False
            instance.save()
        except Http404:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        """ Fully update a User instance """
        if request.user.is_staff:
            return super().update(request, *args, **kwargs)
        try:
            return super().update(request, *args, **kwargs)
        except Http404:
            raise PermissionDenied

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        user = User.objects.get(email=request.data["email"])
        if response.status_code == status.HTTP_201_CREATED:
            if settings.LOCAL_SETTINGS['AUTO_ACTIVATE_USER'] is True:
                user.is_active = True
                user.save()

            user.send_confirm_signup_email()

        return response


class UsersActivation(APIView):
    """
    post:
    Activate the User that possesses the provided activation token.
    """
    authentication_classes = ()
    permission_classes = ()

    def get_serializer(self):
        return serializers.UsersActivationSerializer()

    def post(self, request):
        activation_token = request.data.get('activation_token')

        token = ActionToken.objects.filter(
            key=activation_token,
            type='account_activation',
        )

        # There is only one reference, we will set the user active
        if len(token) == 1:
            # We activate the user
            user = token[0].user
            user.is_active = True
            user.save()

            # We delete the token used
            token[0].delete()

            # We return the user
            serializer = serializers.UserSerializer(
                user,
                context={'request': request},
            )

            return Response(serializer.data)

        # There is no reference to this token or multiple identical token
        # exists.
        else:
            error = '"{0}" is not a valid activation_token.'. \
                format(activation_token)

            return Response(
                {'activation_token': error},
                status=status.HTTP_400_BAD_REQUEST
            )


class ResetPassword(APIView):
    """
    post:
    Create a new token allowing user to change his password.
    """
    permission_classes = ()
    authentication_classes = ()

    def get_serializer(self):
        return serializers.ResetPasswordSerializer()

    def post(self, request, *args, **kwargs):
        if settings.LOCAL_SETTINGS['EMAIL_SERVICE'] is not True:
            # Without email this functionality is not provided
            return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

        # Valid params
        serializer = serializers.ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        user.send_reset_password()

        return Response(status=status.HTTP_201_CREATED)


class ChangePassword(APIView):
    """
    post:
    Get a token and a new password and change the password of
    the token's owner.
    """
    authentication_classes = ()
    permission_classes = ()

    def get_serializer(self):
        return serializers.ChangePasswordSerializer()

    def post(self, request):
        # Valid params
        serializer = serializers.ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_key = request.data.get('token')
        new_password = request.data.get('new_password')

        token = ActionToken.get_password_change_token(token_key)

        user = token.user

        user.set_password(new_password)
        user.save()

        # We expire the token used
        token.expire()

        # We return the user
        serializer = serializers.UserSerializer(
            user,
            context={'request': request}
        )

        return Response(serializer.data)


class ObtainTemporaryAuthToken(ObtainAuthToken):
    """
    post:
    Create a temporary token used to connect to the API.
    """
    model = TemporaryToken
    parser_classes = (JSONParser,)

    def get_serializer(self):
        return AuthTokenSerializer()

    def post(self, request):
        serializer = serializers.CustomAuthTokenSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        token = user.get_temporary_token()

        data = {'token': token.key}
        return Response(data)


class TemporaryTokenDestroy(viewsets.GenericViewSet, mixins.DestroyModelMixin):
    """
    destroy:
    Delete a TemporaryToken object. Used to logout.
    """
    queryset = TemporaryToken.objects.none()

    def get_queryset(self):
        key = self.kwargs.get('pk')
        tokens = TemporaryToken.objects.filter(
            key=key,
            user=self.request.user,
        )
        return tokens


class PermissionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows permissions to be viewed or edited.
    """
    queryset = Permission.objects.all()
    serializer_class = serializers.PermissionSerializer
