from django.db import models
from django.conf import settings

from core.models.base_model import TimeStampedUUIDModel


class ClassRoom(TimeStampedUUIDModel):
    teacher_voice_name = models.CharField(max_length=255, null=True, blank=True)
    course_title = models.CharField(max_length=255)
    course_description = models.TextField()
    language = models.CharField(max_length=50, default="en")

    def __str__(self):
        return f"{self.id}"

    class Meta:
        verbose_name_plural = "Class Rooms"
        ordering = ('id',)

class ClassRoomMember(TimeStampedUUIDModel):
    class_room = models.ForeignKey(ClassRoom, related_name="members", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="class_room_members", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.email} in {self.class_room.id}"

    class Meta:
        verbose_name_plural = "Class Room Members"
        ordering = ('id',)

class ClassRoomContent(TimeStampedUUIDModel):
    class_room = models.ForeignKey(ClassRoom, related_name="contents", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    slides = models.JSONField(blank=True, null=True)
    audio_file = models.CharField(max_length=255, null=True, blank=True)
    order = models.PositiveIntegerField()
    content_is_explained = models.BooleanField(default=False)
    ssml = models.TextField(null=True, blank=True)
    audio_length_sec = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.class_room.uuid} - {self.title}"

    class Meta:
        verbose_name_plural = "Class Room Contents"
        ordering = ('id',)