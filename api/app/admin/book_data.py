from django.contrib import admin

class BookForUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'summary')
    search_fields = ('title', 'summary', 'user__email')
    list_filter = ('user',)
    list_per_page = 10

class BookChunkAdmin(admin.ModelAdmin):
    list_display = ('id', 'book_for_user', 'chunk_index')
    search_fields = ('chunk_text', 'chunk_html', 'book_for_user__title')
    list_filter = ('book_for_user',)
    list_per_page = 10

class BookTeachingContentAdmin(admin.ModelAdmin):
    list_display = ('id', 'book_for_user', 'chunk_index', 'user_has_learned')
    search_fields = ('content', 'book_for_user__title')
    list_filter = ('book_for_user', 'user_has_learned')
    list_per_page = 10
