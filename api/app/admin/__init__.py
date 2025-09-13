from django.contrib import admin

from app.models import BookForUserModel, BookChunkModel, BookTeachingContentModel, ClassRoomModel, ClassRoomMemberModel, ClassRoomContentModel
from app.admin import book_data
from app.admin import ai_teacher

admin.site.register(BookForUserModel, book_data.BookForUserAdmin)
admin.site.register(BookChunkModel, book_data.BookChunkAdmin)
admin.site.register(BookTeachingContentModel, book_data.BookTeachingContentAdmin)

admin.site.register(ClassRoomModel, ai_teacher.ClassRoomAdmin)
admin.site.register(ClassRoomMemberModel, ai_teacher.ClassRoomMemberAdmin)
admin.site.register(ClassRoomContentModel, ai_teacher.ClassRoomContentAdmin)