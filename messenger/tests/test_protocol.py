from django.test import override_settings
from messenger.helpers import get_protocol_contents
from custom_unittests import CustomTestCase
from messenger.protocol import ProtocolHandlerMixin, MessageResponse
from messenger.models import RoomMember, Room
from messenger.tests.factories import RoomFactory, RoomMemberFactory
from custom_auth.factories import CustomUserFactory
from comms.tests.factories import MessageFactory
from comms.models import Message


@override_settings(RPC_PROTO_SPECS=get_protocol_contents('proto1', path='src/messenger/'))
class TestProtocol(CustomTestCase):

    def setUp(self):
        super().setUp()
        self.protocol = ProtocolHandlerMixin()
        self.response = MessageResponse()
        self.room = RoomFactory()
        self.user = CustomUserFactory()
        self.user1 = CustomUserFactory()
        self.message = MessageFactory()
        self.message.protocol = Message.WS
        self.message.direction = Message.INCOMING
        self.message.status = Message.SENT
        self.message.context = {"room": self.room.id}
        self.message.sender = self.user
        self.message.save()

        self.rmb = RoomMemberFactory(user=self.user, room=self.room)
        self.rmb1 = RoomMemberFactory(user=self.user1, room=self.room)

        self.C0_valid = {"command": "C0", "uids": [self.user.id]}
        self.C0_valid_with_invalid_user = {"command": "C0", "uids": ["invalid_user"]}
        self.C0_invalid = {"command": "C0", "uids": "pe-ak9"}
        self.C0_invalid1 = {"command": "C0", "uids": []}

        self.C1_valid = {"command": "C1", "room_id": "lqlqlq", "message_data": "test"}
        self.C1_invalid = {"command": "C1", "non": "valid"}

        self.C2_valid = {"command": "C2", "message_id": "123"}
        self.C2_invalid = {"command": "C2", "non": "valid"}

        self.C3_valid = {"command": "C3", "message_id": "123"}
        self.C3_invalid = {"command": "C3", "non": "valid"}

        self.invalid_message = {"non": "valid"}

    def test_get_users_from_message(self):
        self.protocol._message = self.C0_valid
        users = self.protocol._get_users_from_message()
        self.assertTrue(1 == users.count())

    def test_get_users_from_message_with_invalid_user(self):
        self.protocol._message = self.C0_valid_with_invalid_user
        users = self.protocol._get_users_from_message()
        self.assertTrue(0 == users.count())

    def test_get_related_rooms(self):
        room = self.protocol._get_related_rooms([self.user, self.user1])
        self.assertEqual(room, self.room.id)

    def test_get_rid(self):
        self.assertEqual(self.room.id, self.protocol._get_room(self.room.id).id)

    def test_add_roommembers(self):
        room1 = RoomFactory()
        self.protocol._add_roommembers([self.user, self.user1], room1)
        room_member = RoomMember.objects.filter(room=room1)
        self.assertTrue(room_member.exists())

    def test_get_members(self):
        self.protocol.me = self.user
        members = self.protocol._get_members(self.room.id)
        self.assertEqual(int(members[0].user.id), self.user1.id)

    def test_get_last_message(self):
        self.assertEqual(self.protocol._get_last_message(self.room.id).id, self.message.id)

    def test_get_message(self):
        self.assertEqual(self.protocol._get_message(self.message.id).id, self.message.id)

    def test_get_room_members(self):
        self.assertEqual(self.protocol._get_room_members([self.user]).id, self.rmb.id)

    def test_create_room(self):
        room = self.protocol._create_room()
        self.assertTrue(Room.objects.filter(id=room.id).exists())

    def test_update_message_status(self):
        status = 0
        self.protocol._update_message_status(self.message, status)
        self.assertEqual(self.message.status, status)

    def test_persist_message(self):
        self.protocol.me = self.user
        self.protocol._message = self.C1_valid
        message = self.protocol._persist_message(self.user1)
        msg_obj = Message.objects.filter(id=message.id)
        self.assertTrue(msg_obj.exists())

    def test_can_communicate_in_room(self):
        self.protocol.me = self.user
        self.assertTrue(self.protocol._can_communicate_in_room(self.room.id))

    def test_C0_valid(self):
        self.assertTrue(self.protocol.message_is_valid(self.C0_valid))

    def test_C0_invalid(self):
        self.assertFalse(self.protocol.message_is_valid(self.C0_invalid))

    def test_C0_invalid_empty_list(self):
        self.assertFalse(self.protocol.message_is_valid(self.C0_invalid1))

    def test_C1_valid(self):
        self.assertTrue(self.protocol.message_is_valid(self.C1_valid))

    def test_C1_invalid(self):
        self.assertFalse(self.protocol.message_is_valid(self.C1_invalid))

    def test_C2_valid(self):
        self.assertTrue(self.protocol.message_is_valid(self.C2_valid))

    def test_C2_invalid(self):
        self.assertFalse(self.protocol.message_is_valid(self.C2_invalid))

    def test_C3_valid(self):
        self.assertTrue(self.protocol.message_is_valid(self.C3_valid))

    def test_C3_invalid(self):
        self.assertFalse(self.protocol.message_is_valid(self.C3_invalid))

    def test_invalid_message(self):
        self.assertFalse(self.protocol.message_is_valid(self.invalid_message))

    def test_N0(self):
        r = self.response.N0({"context": {"room": "123"}, "id": "321", "status": {"display": "OK"}})
        self.assertTrue(isinstance(r, dict))

    def test_N1(self):
        r = self.response.N1("123", "456", "789")
        self.assertTrue(isinstance(r, dict))

    def test_N2(self):
        r = self.response.N2("123", "456", "789")
        self.assertTrue(isinstance(r, dict))

    def test_N3_not_valid(self):
        r = self.response.N3("not_valid")
        self.assertTrue(isinstance(r, dict))

    def test_N3_user_not_found(self):
        r = self.response.N3("user_not_found")
        self.assertTrue(isinstance(r, dict))

    def test_N3_not_allwoed(self):
        r = self.response.N3("not_allowed")
        self.assertTrue(isinstance(r, dict))

    def test_N4(self):
        r = self.response.N4("123", ["user_a", "user_b"])
        self.assertTrue(isinstance(r, dict))

    def test_N5(self):
        r = self.response.N5("messages")
        self.assertTrue(isinstance(r, dict))
