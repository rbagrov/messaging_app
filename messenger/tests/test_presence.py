from unittest.mock import patch
from django.test import override_settings
from messenger.helpers import get_protocol_contents
from custom_unittests import CustomTestCase
from fakeredis import FakeStrictRedis
from messenger.presence import Presence


@override_settings(RPC_PROTO_SPECS=get_protocol_contents('proto1', path='src/messenger/'))
class TestPresence(CustomTestCase):

    def setUp(self):
        super().setUp()

    def test_is_online(self):
        with patch.object(Presence, '_connect', return_value=FakeStrictRedis()) as mock_method:
            self.assertFalse(Presence.is_online("test_user0"))

    def test_increment_no_user(self):
        with patch.object(Presence, '_connect', return_value=FakeStrictRedis()) as mock_method:
            self.assertEqual(1, Presence.increment_active_connections("test_user1"))

    def test_decrement_no_user(self):
        with patch.object(Presence, '_connect', return_value=FakeStrictRedis()) as mock_method:
            self.assertEqual(0, Presence.decrement_active_connections("test_user2"))

    def tearDown(self):
        super().tearDown()
        redis = FakeStrictRedis()
        redis.flushdb()
