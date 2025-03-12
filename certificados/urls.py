from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('validar/<uuid:codigo>/', views.validar_certificado, name='validar_certificado'),
    path('certificado/<uuid:codigo>/pdf/', views.gerar_pdf_view, name='gerar_pdf'),

]
