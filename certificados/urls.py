from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    #path('', views.painel_controle, name='painel_controle'),
    path('login/', views.login, name='login'),
    path('login_aluno/', views.login_aluno, name="login_aluno"),
    path('verificar_certificado/', views.login, name='verificar_certificado'),
    path('certificados/<int:certificado_id>/', views.visualizar_certificado, name='visualizar_certificado'),
    path('certificados/<int:certificado_id>/descarregar/', views.descarregar_certificado, name='descarregar_certificado'),
    path('verificar/<str:identificador>/', views.verificar_certificado, name='verificar_certificado'),
        # Outras URLs...
]