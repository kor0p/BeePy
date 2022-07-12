from django.urls import path
from . import views

urlpatterns = [
    path('api/groups/', views.GroupList.as_view()),
    path('api/groups/<int:pk>', views.GroupView.as_view()),
    path('api/users/', views.UserList.as_view()),
    path('api/users/<int:pk>', views.UserView.as_view()),
]
