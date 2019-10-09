from django.conf import settings
from django.db.models import Q
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync

from custom_auth.models import CustomUser
from comms.models import Message
from comms.serializers import MessageSerializer

from .models import Room, RoomMember
from .presence import Presence


class MessageValidator(object):
    _DATA_TYPES = {"string": str, "array": list, "integer": int, "null": None}

    def __init__(self, text):
        self.text = text
        self.commands = settings.RPC_PROTO_SPECS.get("commands")

    @property
    def is_valid(self):
        if not self._command_exists():
            return False
        return all(
            [
                self._command_contents(),
                self._command_param_types(),
                self._params_not_empty(),
            ]
        )

    def _command_exists(self):
        return self.text.get("command", False)

    def _command_contents(self):
        command_id = self.text["command"] in [
            command["id"] for command in self.commands
        ]

        if not command_id:
            return False

        for command in self.commands:
            if command["id"] == self.text["command"]:
                self.command = command
                self.message_params = self.text.copy()
                self.message_params.pop("command")
                self.params = command["params"]
        return self._params_exists()

    def _params_exists(self):
        self.param_ids = [param["id"] for param in self.params]
        return all([self.text.get(pid, False) for pid in self.param_ids])

    def _command_param_types(self):
        self.param_types = {
            p["id"]: self._DATA_TYPES[p["type"]] for p in self.params
        }  # noqa
        return all(
            isinstance(self.text.get(pid), self.param_types[pid])
            for pid in self.param_ids
        )

    def _params_not_empty(self):
        for value in self.message_params.values():
            if isinstance(value, (str, list)) and len(value) == 0:
                return False
        return True


class MessageResponse(object):
    def __init__(self):
        for ntf in settings.RPC_PROTO_SPECS.get("notifications"):
            setattr(self, "_" + ntf["id"], ntf)
        self._BASE_RESPONSE = {"type": "chat_message"}

        self._ERRORS = {
            "not_valid": "Message could not pass validation",
            "user_not_found": "User not found",
            "not_allowed": "Action not allowed",
        }

    def N4(self, room_id, participants):
        out = self._BASE_RESPONSE.copy()
        out["id"] = self._N4["id"]
        out["name"] = self._N4["name"]
        out["room_id"] = room_id
        out["participants"] = participants
        return out

    def N1(self, room_id, room_member_id, message_id):
        out = self._BASE_RESPONSE.copy()
        out["id"] = self._N1["id"]
        out["name"] = self._N1["name"]
        out["room_id"] = room_id
        out["room_member_id"] = room_member_id
        out["message_id"] = message_id
        return out

    def N2(self, room_id, room_member_id, message_id):
        out = self._BASE_RESPONSE.copy()
        out["id"] = self._N2["id"]
        out["name"] = self._N2["name"]
        out["room_id"] = room_id
        out["room_member_id"] = room_member_id
        out["message_id"] = message_id
        return out

    def N0(self, message_data):
        out = self._BASE_RESPONSE.copy()
        out["id"] = self._N0["id"]
        out["name"] = self._N0["name"]
        out["room_id"] = message_data["context"]["room"]
        out["message_data"] = message_data
        out["message_id"] = message_data["id"]
        out["message_status"] = message_data["status"]["display"]
        return out

    def N3(self, error):
        out = self._BASE_RESPONSE.copy()
        out["error"] = self._ERRORS[error]
        return out

    def N5(self, messages):
        out = self._BASE_RESPONSE.copy()
        out["id"] = self._N5["id"]
        out["name"] = self._N5["name"]
        out["rooms"] = messages
        return out


class ProtocolHandlerMixin(object):
    def message_is_valid(self, text_data):
        _validator = MessageValidator(text_data)
        self.response = MessageResponse()
        return _validator.is_valid

    def process(self):
        dispatch_map = {
            "C0": self.command0,
            "C1": self.command1,
            "C2": self.command2,
            "C3": self.command3,
        }
        bound = dispatch_map[self._message["command"]].__get__(self, type(self))
        bound()

    @database_sync_to_async
    def _get_users_from_message(self):
        return CustomUser.objects.filter(id__in=self._message["uids"])

    @database_sync_to_async
    def _get_related_rooms(self, all_room_members):
        all_rooms = []
        uids = []

        for member in all_room_members:
            room_member_objects = RoomMember.objects.filter(user=member)
            if not room_member_objects.exists():
                return None
            all_rooms.append({member_object.room.id for member_object in room_member_objects})
            uids.append(member.id)

        intersection_rooms = set.intersection(*all_rooms) or None
        should_create = True

        if intersection_rooms:
            for intersection_room in intersection_rooms:
                if RoomMember.objects.filter(room_id=intersection_room).exclude(user__in=uids).exists():
                    should_create = True
                else:
                    should_create = False
                    valid_room = intersection_room

        if should_create:
            return None
        return valid_room

    @database_sync_to_async
    def _create_room(self):
        return Room.objects.create(active=True)

    @database_sync_to_async
    def _get_room(self, rid):
        return Room.objects.get(id=rid)

    @database_sync_to_async
    def _add_roommembers(self, users, room):
        for user in users:
            RoomMember.objects.create(room=room, user=user)

    def command0(self):
        users = self._get_users_from_message()
        if users.count() == 0:
            self.send_json(self.response.N3("user_not_found"))

        all_room_members = [user for user in users]
        all_room_members.append(self.me)
        room = self._get_related_rooms(set(all_room_members))

        if not room:
            room = self._create_room()
            self._add_roommembers(set(all_room_members), room)
        else:
            room = self._get_room(room)

        participants = [
            {
                "user_id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
            for user in all_room_members
        ]

        for user in users:
            if Presence.is_online(user.id):
                async_to_sync(self.channel_layer.group_send)(
                    user.id, self.response.N4(room.id, participants)
                )
        self.send_json(self.response.N4(room.id, participants))

    @database_sync_to_async
    def _get_members(self, room_id):
        return RoomMember.objects.filter(room__id=room_id).exclude(user=self.me)

    @database_sync_to_async
    def _can_communicate_in_room(self, room_id):
        return RoomMember.objects.filter(room__id=room_id, user=self.me).exists()

    @database_sync_to_async
    def _get_last_message(self, room_id):
        try:
            return Message.objects.filter(context__contains={"room": room_id}).latest(
                "created_on"
            )
        except Message.DoesNotExist:
            return None

    @database_sync_to_async
    def _persist_message(self, member):
        message = Message(
            protocol=Message.WS,
            direction=Message.INCOMING,
            status=Message.SENT,
            content=self._message["message_data"],
            recipient=member,
            sender=self.me,
            context={"room": self._message["room_id"]},
            previous=self._get_last_message(self._message["room_id"]),
        )
        message.save()
        return message

    def command1(self):
        try:
            if not self._can_communicate_in_room(self._message["room_id"]):
                return self.send_json(self.response.N3("not_allowed"))
            members = self._get_members(self._message["room_id"])
            for member in members:
                stored_message = self._persist_message(member.user)
                serialized = MessageSerializer(stored_message)
                if Presence.is_online(member.user.id):
                    async_to_sync(self.channel_layer.group_send)(
                        member.user.id, self.response.N0(serialized.data)
                    )
            async_to_sync(self.channel_layer.group_send)(
                self.me.id, self.response.N0(serialized.data)
            )
        except Exception as e:
            print(e)

    @database_sync_to_async
    def _get_message(self, message_id):
        return Message.objects.get(id=message_id)

    @database_sync_to_async
    def _get_room_members(self, users):
        return RoomMember.objects.filter(user__in=users).latest("id")

    @database_sync_to_async
    def _update_message_status(self, message, status):
        message.status = status
        message.save()

    def command2(self):
        try:
            _msg = self._get_message(self._message["message_id"])
            if self.me.id not in [_msg.sender.id, _msg.recipient.id]:
                return self.send_json(self.response.N3("not_allowed"))
            room_member_obj = self._get_room_members(
                [_msg.sender.id, _msg.recipient.id]
            )
            async_to_sync(self.channel_layer.group_send)(
                _msg.sender.id,
                self.response.N1(room_member_obj.room_id, _msg.recipient.id, _msg.id),
            )
            self._update_message_status(_msg, Message.RECEIVED)
        except Exception:
            self.send_json(self.response.N3("not_valid"))

    def command3(self):
        try:
            _msg = self._get_message(self._message["message_id"])
            if self.me.id not in [_msg.sender.id, _msg.recipient.id]:
                return self.send_json(self.response.N3("not_allowed"))
            room_member_obj = self._get_room_members(
                [_msg.sender.id, _msg.recipient.id]
            )
            async_to_sync(self.channel_layer.group_send)(
                _msg.sender.id,
                self.response.N2(room_member_obj.room_id, _msg.recipient.id, _msg.id),
            )
            self._update_message_status(_msg, Message.READ)
        except Exception:
            self.send_json(self.response.N3("not_valid"))


class Starter(object):
    @staticmethod
    def get_initial_info(me):
        out = []
        response = MessageResponse()
        try:
            for message in Message.objects.filter(
                Q(sender=me) | Q(recipient=me), context__has_key="room"
            ).distinct("context"):
                room = {}
                room.update({"room_id": message.context.get("room")})
                room.update({"last_message": MessageSerializer(message).data})
                room.update(
                    {
                        "participants": [
                            {
                                "user_id": member.user.id,
                                "first_name": member.user.first_name,
                                "last_name": member.user.last_name,
                            }
                            for member in RoomMember.objects.filter(
                                room_id=message.context.get("room")
                            )
                        ]
                    }
                )
                out.append(room)
            return response.N5(out)
        except Exception:
            pass
