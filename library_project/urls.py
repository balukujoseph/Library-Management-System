"""
URL configuration for library_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from library import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls), # Superuser
    path('staff/', views.admin_dashboard, name='admin_dashboard'), # Staff Admin
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', views.library_index, name='library_index'),
    path('staff/return/<int:record_id>/', views.return_book, name='return_book'),
    path('borrow/<int:book_id>/', views.process_borrow, name='borrow'),
    path('staff/add-book/', views.add_book, name='add_book'),
    path('staff/approve/<int:user_id>/', views.approve_user, name='approve_user'),
    path('ai-assistant/', views.ai_librarian, name='ai_librarian'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)