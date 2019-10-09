from django.db import models
from custom_auth.models import CustomUser
from custom_base_model.models import CustomBaseModel
from custom_obscure_id.fields import ObscureIdField


class Room(CustomBaseModel):
    id = ObscureIdField(primary_key=True)
    active = models.BooleanField(default=False)


class RoomMember(CustomBaseModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
