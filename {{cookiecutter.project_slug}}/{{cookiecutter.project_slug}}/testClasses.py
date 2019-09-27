from rest_framework.test import APITestCase


class SerializerTestCase(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(SerializerTestCase, cls).setUpClass()
        cls.serializer_attrs = [
            'id',
            'url',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'phone',
            'other_phone',
            'is_superuser',
            'is_staff',
            'last_login',
            'date_joined',
            'groups',
            'user_permissions',
            'picture'
        ]

    def validate_attrs(self, content):
        # Check the system doesn't return attributes not expected
        attributes = self.serializer_attrs.copy()
        for key in content.keys():
            self.assertTrue(
                key in attributes,
                'Attribute "{0}" is not expected but is '
                'returned by the system.'.format(key)
            )
            attributes.remove(key)

        # Ensure the system returns all expected attributes
        self.assertTrue(
            len(attributes) == 0,
            'The system failed to return some '
            'attributes : {0}'.format(attributes)
        )
