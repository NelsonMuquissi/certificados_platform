from django.shortcuts import render

def home(request):
    return render(request, 'index.html')

def validar_certificado(request):
    return render(request, 'certificados/validacao.html')
