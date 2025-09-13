from django.contrib import admin

class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ["uuid", "course_title", "course_description", "language"]
    list_per_page = 10
    search_fields = ["course_title"]

class ClassRoomMemberAdmin(admin.ModelAdmin):
    list_display = ["uuid", "class_room", "user"]
    list_per_page = 10
    search_fields = ["user__email", "class_room__course_title"]

class ClassRoomContentAdmin(admin.ModelAdmin):
    list_display = ["uuid", "class_room", "title", "order", "content_is_explained"]
    list_per_page = 10
    search_fields = ["title", "class_room__course_title"]
