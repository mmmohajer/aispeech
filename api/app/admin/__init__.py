from django.contrib import admin

from app.models import BookForUserModel, BookChunkModel, BookTeachingContentModel
from app.admin import book_data

admin.site.register(BookForUserModel, book_data.BookForUserAdmin)
admin.site.register(BookChunkModel, book_data.BookChunkAdmin)
admin.site.register(BookTeachingContentModel, book_data.BookTeachingContentAdmin)