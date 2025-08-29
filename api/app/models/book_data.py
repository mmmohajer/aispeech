from django.conf import settings
from django.db import models
from pgvector.django import VectorField

from core.models.base_model import TimeStampedUUIDModel, TimeStampedModel


class BookForUser(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='books')
    title = models.CharField(max_length=255)
    summary = models.TextField(max_length=2048)

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name_plural = "Book For Users"
        ordering = ('id',)


class BookChunk(TimeStampedModel):
    book_for_user = models.ForeignKey(BookForUser, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.PositiveIntegerField()
    chunk_text = models.TextField()
    chunk_html = models.TextField(blank=True, null=True)
    embedding = VectorField(dimensions=3072)

    def __str__(self):
        return f"BookChunk {self.id}"

    class Meta:
        verbose_name_plural = "Book Chunks"
        ordering = ('id',)

class BookTeachingContent(TimeStampedModel):
    book_for_user = models.ForeignKey(BookForUser, on_delete=models.CASCADE, related_name='teaching_contents')
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    q_and_a = models.JSONField()
    user_has_learned = models.BooleanField(default=False)

    def __str__(self):
        return f"BookTeachingContent {self.id}"

    class Meta:
        verbose_name_plural = "Book Teaching Contents"
        ordering = ('id',)

SENDER_OPTIONS = (
    ("user", "user"),
    ("system", "system"),
)

class BookChatMessage(TimeStampedModel):
    book_for_user = models.ForeignKey(BookForUser, on_delete=models.CASCADE, related_name='chat_messages')
    speech_message = models.TextField(blank=True, null=True)
    slide_message = models.TextField(blank=True, null=True)
    simple_message = models.TextField(blank=True, null=True)
    message_embedding = VectorField(dimensions=3072)
    sender = models.CharField(max_length=10, choices=SENDER_OPTIONS)

    def __str__(self):
        return f"BookChatMessage {self.id}"

    class Meta:
        verbose_name_plural = "Book Chat Messages"
        ordering = ('id',)