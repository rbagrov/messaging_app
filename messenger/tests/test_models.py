from .factories import RoomFactory
from custom_unittests import CustomTestCase


class TestRoomModel(CustomTestCase):

    def setUp(self):
        super().setUp()

    def test_make_room_active(self):
        room = RoomFactory()
        room.active = True
        room.save()
        self.assertEqual(True, room.active)
