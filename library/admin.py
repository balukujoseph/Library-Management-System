from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Book, BorrowRecord

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    # This controls which columns show up in the list view
    list_display = ('title', 'author', 'stock')
    # This allows you to search books by title/author in the admin panel
    search_fields = ('title', 'author')

@admin.register(BorrowRecord)
class BorrowRecordAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'borrow_date', 'returned')
    list_filter = ('returned', 'borrow_date')