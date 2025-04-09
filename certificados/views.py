from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.views import View
from .models import Certificado, ResultadoDisciplina, PedidoCorrecao, Notificacao, RegistroAuditoria
from .forms import FormularioCertificado, FormularioPedidoCorrecao
from django.template.loader import get_template
from xhtml2pdf import pisa
import io
from django.core.exceptions import ValidationError
import uuid
from django.http import Http404
from django.contrib.auth import authenticate, login
from django.contrib import messages

def home(request):
    return render(request, 'index.html')

def login(request):
    return render(request, 'login.html')

def login_aluno(request):
    if request.method == 'POST':
        email = request.POST['email']
        senha = request.POST['senha']
        user = authenticate(request, email=email, password=senha)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard_aluno')
        else:
            messages.error(request, 'Email, senha inválidos ou conta desabilitada.')
    
    return render(request, 'login.html')

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

"""def verificar_certificado(request, codigo_verificacao):
    certificado = get_object_or_404(Certificado, codigo_verificacao=codigo_verificacao, ativo=True)
    return render(request, 'verificacao_certificado.html', {'certificado': certificado})"""

def verificar_certificado(request, identificador):
    """
    Verifica certificado tanto por código de verificação (UUID) quanto por número de matrícula
    """
    try:
        # Tenta primeiro como UUID (código de verificação)
        try:
            # Verifica se é um UUID válido
            uuid_obj = uuid.UUID(identificador)
            certificado = get_object_or_404(
                Certificado, 
                codigo_verificacao=uuid_obj,
                ativo=True
            )
            metodo_verificacao = 'código de verificação'
        except (ValueError, AttributeError):
            # Se não for UUID válido, tenta como número de matrícula
            certificado = get_object_or_404(
                Certificado, 
                matricula__numero_matricula=identificador.upper(),
                ativo=True
            )
            metodo_verificacao = 'número de matrícula'
            
    except Http404:
        # Se ambos falharem, mostra página de erro
        return render(request, 'verificacao_certificado.html', {
            'invalido': True,
            'identificador': identificador
        })
    
    return render(request, 'verificacao_certificado.html', {
        'certificado': certificado,
        'metodo_verificacao': metodo_verificacao,
        'valido': True
    })