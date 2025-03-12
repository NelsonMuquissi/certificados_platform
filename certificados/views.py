from django.shortcuts import render
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import Certificado, LogValidacao
import socket
from django.http import FileResponse

def gerar_pdf_view(request, codigo):
    certificado = get_object_or_404(Certificado, codigo_validacao=codigo)
    return certificado.gerar_pdf()

def validar_certificado(request, codigo):
    certificado = get_object_or_404(Certificado, codigo_validacao=codigo)

    # Obtendo informações do usuário
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    # Registrando validação
    LogValidacao.objects.create(
        certificado=certificado,
        ip_address=ip_address,
        user_agent=user_agent,
        sucesso=True
    )

    return render(request, 'validacao.html', {'certificado': certificado})

def get_client_ip(request):
    """ Obtém o IP do usuário. """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def home(request):
    return render(request, 'index.html')

