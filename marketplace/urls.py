from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
import os
from perfumes import views as perfume_views

urlpatterns = [
    # 👉 custom admin dashboard (преди Django admin)
    path('admin/dashboard/', perfume_views.admin_dashboard, name='admin_dashboard'),

    # Django Admin panel
    path('admin/', admin.site.urls),

    # Приложението ти
    path('', include('perfumes.urls')),

    # Password reset
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

    path('dashboard/ban/<int:user_id>/', perfume_views.ban_user, name='ban_user'),
    path('dashboard/unban/<int:user_id>/', perfume_views.unban_user, name='unban_user'),

]

# static/media
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=os.path.join(settings.BASE_DIR, 'static'))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
