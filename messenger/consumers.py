import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from messenger.presence import Presence
from messenger.protocol import ProtocolHandlerMixin, Starter


class RPCConsumer(ProtocolHandlerMixin, JsonWebsocketConsumer):
    def connect(self):
        if not self.scope.get("user"):
            self.close()
            self.me = None
            return

        self.me = self.scope.get("user")
        Presence.increment_active_connections(self.me.id)

        async_to_sync(self.channel_layer.group_add)(self.me.id, self.channel_name)

        self.accept(self.scope.get("subprotocols")[0])

    def disconnect(self, close_code):

        if not self.me:
            return

        Presence.decrement_active_connections(self.me.id)

        async_to_sync(self.channel_layer.group_discard)(self.me.id, self.channel_name)

    def receive_json(self, text_data):
        if not self.message_is_valid(text_data):
            return self.send_json(self.response.N3("not_valid"))
        self._message = text_data
        self.process()

    def chat_message(self, event):
        self.send_json(event)
