from django.shortcuts import render, get_object_or_404
from .models import Group, User
from .serializers import GroupSerializer, UserSerializer
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView


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
