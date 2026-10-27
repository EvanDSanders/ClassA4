"""URL routes for the PRS."""
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", auth_views.LoginView.as_view(template_name="prs/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("patients/", views.patient_search, name="patient_search"),
    path("patients/new/", views.patient_register, name="patient_register"),
    path("patients/<str:patient_id>/", views.patient_detail, name="patient_detail"),
    path("patients/<str:patient_id>/edit/", views.patient_edit, name="patient_edit"),
    path("patients/<str:patient_id>/notes/add/", views.note_add, name="note_add"),
    path("notes/<int:note_id>/resolve/", views.note_resolve, name="note_resolve"),
    path("requests/", views.request_queue, name="request_queue"),
    path("requests/<int:request_id>/review/", views.request_review, name="request_review"),
    path("logs/", views.audit_log, name="audit_log"),
    path("portal/", views.portal, name="portal"),
]
