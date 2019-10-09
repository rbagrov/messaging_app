import factory
from faker import Factory
from custom_auth.factories import CustomUserFactory


faker = Factory.create()


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'messenger.Room'


class RoomMemberFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(CustomUserFactory)
    room = factory.SubFactory(RoomFactory)

    class Meta:
        model = 'messenger.RoomMember'
