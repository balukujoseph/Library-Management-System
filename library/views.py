from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache
from .models import Book, BorrowRecord, User
from django.contrib import messages
import numpy as np
import json
import os
from groq import Groq
from .forms import BookForm

os.environ['TOKENIZERS_PARALLELISM'] = 'false'

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

PREFERRED_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "allam-2-7b",
]


def get_groq_model():
    """Return an active chat Groq model ID available to this API key, cached for 1 hour."""
    cached_model = cache.get("groq_active_model")
    if cached_model:
        return cached_model

    non_chat_keywords = ("whisper", "guard", "safeguard", "orpheus", "tts")

    try:
        models_page = client.models.list()
        available_ids = [
            m.id for m in getattr(models_page, "data", []) if getattr(m, "id", None)
        ]

        for preferred in PREFERRED_MODELS:
            if preferred in available_ids:
                cache.set("groq_active_model", preferred, timeout=3600)
                return preferred

        for model_id in available_ids:
            lowered = model_id.lower()
            if not any(word in lowered for word in non_chat_keywords):
                cache.set("groq_active_model", model_id, timeout=3600)
                return model_id
    except Exception:
        pass

    return PREFERRED_MODELS[0]


def register(request):
    if request.method == "POST":
        u = request.POST.get('username')
        e = request.POST.get('email')
        p = request.POST.get('password')
        pc = request.POST.get('password_confirm')

        if p != pc:
            messages.error(request, "Passwords do not match! Please try again.")
            return render(request, 'register.html')

        if User.objects.filter(username=u).exists():
            messages.error(request, "That username is already taken.")
            return render(request, 'register.html')

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
                            "content": f"You are the LMS Assistant. Using these books:\n{context}\nExplain how they help the user. Be concise."
                        },
                        {"role": "user", "content": query}
                    ],
                    model=get_groq_model(),
                )
                ai_recommendation = chat_completion.choices[0].message.content
            except Exception:
                cache.delete("groq_active_model")
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
    return render(request, 'admin_dashboard.html', {
        'books': Book.objects.all(),
        'borrows': BorrowRecord.objects.filter(returned=False),
        'pending_users': User.objects.filter(is_active=False)
    })


@user_passes_test(lambda u: u.is_staff)
def return_book(request, record_id):
    record = get_object_or_404(BorrowRecord, id=record_id)

    book = record.book
    book.stock += 1
    book.save()

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
            if user.is_staff:
                return redirect('admin_dashboard')
            return redirect('library_index')
        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'login.html')


@user_passes_test(lambda u: u.is_staff)
def add_book(request):
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES)
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


@login_required
def ai_librarian(request):
    query = request.GET.get('ask')
    ai_response = ""

    if query:
        books = Book.objects.all()[:3]
        top_context = [f"{b.title} by {b.author}: {b.description}" for b in books]
        context_str = "\n".join(top_context) if top_context else "No books currently available in the system."

        try:
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
                model=get_groq_model(),
            )
            ai_response = chat_completion.choices[0].message.content
        except Exception as exc:
            cache.delete("groq_active_model")
            ai_response = f"Sorry, the AI assistant encountered an error: {exc}"

    return render(request, 'ai_librarian.html', {'response': ai_response, 'query': query})


def upload_note(request, book_id):
    if request.method == 'POST':
        note_title = request.POST.get('title')
        uploaded_file = request.FILES.get('note_document')

        if uploaded_file:
            BookNote.objects.create(
                book_id=book_id,
                title=note_title,
                note_file=uploaded_file
            )
            return redirect('book_detail', book_id=book_id)