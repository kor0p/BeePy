from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from .models import Group, User
from .serializers import GroupSerializer, UserSerializer


class GroupView(RetrieveUpdateDestroyAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class GroupList(ListCreateAPIView, GroupView):
    pass


class UserView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserList(ListCreateAPIView, UserView):
    pass
