from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.pagina_login, name='login'),
    path('login_aluno/', views.login_aluno, name="login_aluno"),
    path('painel_aluno/', views.painel_aluno, name="painel_aluno"),
    path('solicitar_correcao/', views.solicitar_correcao, name="solicitar_correcao"),
    path('logout_aluno/', views.logout_aluno, name="logout_aluno"),
    path('certificados/<int:certificado_id>/', views.visualizar_certificado, name='visualizar_certificado'),
    path('certificados/<int:certificado_id>/descarregar/', views.descarregar_certificado, name='descarregar_certificado'),
    path('verificar/<str:identificador>/', views.verificar_certificado, name='verificar_certificado'),
]