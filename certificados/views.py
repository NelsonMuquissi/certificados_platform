from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.views import View
from .models import Certificado, ResultadoDisciplina, PedidoCorrecao, Notificacao, RegistroAuditoria
from .forms import FormularioCertificado, FormularioPedidoCorrecao
from django.template.loader import get_template
from xhtml2pdf import pisa
import io

def home(request):
    return render(request, 'index.html')

def login(request):
    pass

@login_required
def painel_controle(request):
    # Painéis diferentes conforme o papel do usuário
    if request.user.papel == 'ESTUDANTE':
        certificados = Certificado.objects.filter(estudante=request.user, ativo=True)
        notificacoes = Notificacao.objects.filter(usuario=request.user, lida=False)
        return render(request, 'painel_estudante.html', {
            'certificados': certificados,
            'notificacoes': notificacoes
        })
    elif request.user.papel == 'SECRETARIA':
        # Painel da secretaria
        pass
    # Outros papéis...

@login_required
def visualizar_certificado(request, certificado_id):
    certificado = get_object_or_404(Certificado, id=certificado_id, ativo=True)
    if request.user.papel == 'ESTUDANTE' and certificado.estudante != request.user:
        return HttpResponse("Não autorizado", status=401)
    
    return render(request, 'detalhes_certificado.html', {'certificado': certificado})

@login_required
def descarregar_certificado(request, certificado_id):
    certificado = get_object_or_404(Certificado, id=certificado_id, ativo=True)
    if request.user.papel == 'ESTUDANTE' and certificado.estudante != request.user:
        return HttpResponse("Não autorizado", status=401)
    
    # Gerar PDF
    template = get_template('certificado_pdf.html')
    html = template.render({'certificado': certificado})
    
    resultado = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), resultado)
    
    if not pdf.err:
        response = HttpResponse(resultado.getvalue(), content_type='application/pdf')
        nome_arquivo = f"certificado_{certificado.numero_certificado}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
        return response
    
    return HttpResponse("Erro ao gerar PDF", status=500)

def verificar_certificado(request, codigo_verificacao):
    certificado = get_object_or_404(Certificado, codigo_verificacao=codigo_verificacao, ativo=True)
    return render(request, 'verificacao_certificado.html', {'certificado': certificado})

# Outras vistas para pedidos de correção, gestão de certificados, etc.