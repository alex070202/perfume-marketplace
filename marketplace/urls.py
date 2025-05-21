from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('perfumes.urls')),
    
    # password reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
    template_name='registration/password_reset_form.html',
    email_template_name='registration/password_reset_email.txt',            
    html_email_template_name='registration/password_reset_email.html',      
    subject_template_name='registration/password_reset_subject.txt',    
    ), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
]

# static/media
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=os.path.join(settings.BASE_DIR, 'static'))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
