from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Book, BorrowRecord, User
from sentence_transformers import SentenceTransformer
from django.contrib import messages
import numpy as np
import json
import os
from groq import Groq
from .forms import BookForm
os.environ['TOKENIZERS_PARALLELISM'] = 'false'


def register(request):
    if request.method == "POST":
        u = request.POST.get('username')
        e = request.POST.get('email')
        p = request.POST.get('password')
        pc = request.POST.get('password_confirm')

        # Check for mismatch
        if p != pc:
            messages.error(request, "Passwords do not match! Please try again.")
            return render(request, 'register.html') # Stop here and show the error

        # Check if username exists (to avoid server errors)
        if User.objects.filter(username=u).exists():
            messages.error(request, "That username is already taken.")
            return render(request, 'register.html')

        # If we reach here, passwords matched!
        user = User.objects.create_user(username=u, email=e, password=p)
        user.is_active = False 
        user.save()
        
        messages.info(request, "Registration successful! Please wait for a librarian to approve your account.")
        return redirect('login')
    return render(request, 'register.html')

@login_required
def library_index(request):
    query = request.GET.get('search')
    ai_recommendation = ""
    
    if query:
        books = Book.objects.filter(title__icontains=query) | Book.objects.filter(description__icontains=query)
        
        if books.exists():
            context = "\n".join([f"- {b.title} by {b.author}: {b.description}" for b in books[:3]])
            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are the LMS Assistant. Using these books:\n{context}\nExplain how they help the user. Be consise."
                        },
                        {"role": "user", "content": query}
                    ],
                    model="llama-3.3-70b-versatile",
                )
                
                ai_recommendation = chat_completion.choices[0].message.content
            except Exception:
                # Fallback if the internet or API fails
                ai_recommendation = "AI Assistant is currently offline, but here are your matches."

    else:
        books = Book.objects.all()
    return render(request, 'index.html', {
        'books': books, 
        'ai_recommendation': ai_recommendation,
        'query': query
    })

@login_required
def process_borrow(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if book.stock > 0:
        book.stock -= 1
        book.save()
        BorrowRecord.objects.create(book=book, user=request.user)
    return redirect('library_index')

@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    # This function ONLY displays the dashboard
    return render(request, 'admin_dashboard.html', {
        'books': Book.objects.all(),
        'borrows': BorrowRecord.objects.filter(returned=False),
        'pending_users': User.objects.filter(is_active=False)
    })
    
@user_passes_test(lambda u: u.is_staff)
def return_book(request, record_id):
    record = get_object_or_404(BorrowRecord, id=record_id)
    
    # 1. Update the book stock
    book = record.book
    book.stock += 1
    book.save()
    
    # 2. Mark record as returned
    record.returned = True
    record.save()
    
    messages.success(request, f"'{book.title}' has been returned to the shelves.")
    return redirect('admin_dashboard')

def login_view(request):
    if request.method == "POST":
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(username=u, password=p)
        
        if user is not None:
            auth_login(request, user)
            # This is the "Staff Check"
            if user.is_staff:
                return redirect('admin_dashboard') # Send to staff area
            return redirect('library_index')       # Send to student area
        else:
            messages.error(request, "Invalid username or password")
            
    return render(request, 'login.html')


@user_passes_test(lambda u: u.is_staff)
def add_book(request):
    if request.method == "POST":
        form = BookForm(request.POST)
        if form.is_valid():
            form.save()
           
            messages.success(request, "Book added successfully")
            return redirect('admin_dashboard')
    else:
        form = BookForm()
    
    return render(request, 'add_book.html', {'form': form})

@user_passes_test(lambda u: u.is_staff)
def approve_user(request, user_id):
    user_to_approve = get_object_or_404(User, id=user_id)
    user_to_approve.is_active = True
    user_to_approve.save()
    messages.success(request, f"User {user_to_approve.username} has been approved!")
    return redirect('admin_dashboard')


client = Groq(api_key="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")
@login_required
def ai_librarian(request):
    query = request.GET.get('ask')
    ai_response = ""
    
    if query:
        # 1. RETRIEVAL: Use your existing vector search to find relevant context
        books = Book.objects.all()
        scored_books = []
        
        
        # Take the top 3 most relevant books as context
        top_context = [f"{item[1].title} by {item[1].author}: {item[1].description}" for item in scored_books[:3]]
        context_str = "\n".join(top_context)

        # 2. GENERATION: Send the context to Groq
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": f"You are the Kyezabu Cyber Hut Assistant. Use this library data to help users: {context_str}. If a book isn't in this list, politely explain you don't have it."
                },
                {
                    "role": "user",
                    "content": query,
                }
            ],
            model="llama-3.3-70b-versatile", # Groq's high-speed model
        )
        ai_response = chat_completion.choices[0].message.content

    return render(request, 'ai_librarian.html', {'response': ai_response, 'query': query})