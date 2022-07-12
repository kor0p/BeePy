from django.db import models
from django.utils.timezone import now


class Group(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=1000)

    def __str__(self):
        return self.name


class User(models.Model):
    username = models.CharField(max_length=100)
    created = models.DateTimeField(default=now)
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name='users')
