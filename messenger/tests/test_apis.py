from django.test import override_settings
from messenger.helpers import get_protocol_contents
from comms.tests.factories import MessageFactory
from comms.models import Message
from custom_auth.factories import CustomUserFactory
from custom_unittests import CustomTestCase


class TestInitialInfo(CustomTestCase):

    def setUp(self):
        super().setUp()
        self.user = CustomUserFactory()
        self.message = MessageFactory()
        self.message.protocol = Message.WS
        self.message.direction = Message.INCOMING
        self.message.status = Message.SENT
        self.message.context = {"room": "123"}
        self.message.sender = self.user
        self.message.save()

    @override_settings(RPC_PROTO_SPECS=get_protocol_contents('proto1', path='src/messenger/'))
    def test_initial_info_ok(self):
        print(get_protocol_contents('proto1'))
        with self.client.authenticated_as(self.user):
            response = self.client.get('/messenger/init_info/')

        self.assertEqual(200, response.status_code, response.content)
