from django import forms
from .models import Book

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'description', 'stock', 'note_document', 'book_file']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Enter book summary for AI indexing...'}),
        }