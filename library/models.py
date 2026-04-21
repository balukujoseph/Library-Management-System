from django.db import models
from django.contrib.auth.models import User

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    description = models.TextField()
    stock = models.IntegerField(default=1)
    note_document = models.FileField(upload_to='book_notes/', null=True, blank=True)
    book_file = models.FileField(upload_to='books/', null=True, blank=True)
    

    def __str__(self):
        return self.title

class BorrowRecord(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    borrow_date = models.DateTimeField(auto_now_add=True)
    returned = models.BooleanField(default=False)
    
    
class BookNote(models.Model):
    book = models.ForeignKey('Book', on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=200)
    note_file = models.FileField(upload_to='book_notes/')
    uploaded_at = models.DateTimeField(auto_now_add=True)