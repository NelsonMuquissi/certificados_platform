from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.views import View
from .models import Certificado, ResultadoDisciplina, PedidoCorrecao, Notificacao, RegistroAuditoria, Aluno, Matricula, DeclaracaoNotas
from .forms import FormularioCertificado, FormularioPedidoCorrecao
from django.template.loader import get_template
from xhtml2pdf import pisa
import io
from django.core.exceptions import ValidationError
import uuid
from django.http import Http404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.utils.timezone import now
from django.contrib.auth.hashers import check_password
from io import BytesIO
from django.db.models import Q

def home(request):
    return render(request, 'index.html')


def pagina_login(request):
    return render(request, 'login.html')

def login_aluno(request):
    if request.method == "POST":
        email = request.POST.get('email')
        senha = request.POST.get('senha')

        aluno = Aluno.objects.filter(email=email).first()

        if not aluno or not aluno.conta_habilitada:
            messages.error(request, "Credenciais inválidas ou conta desativada.")
            return redirect('login')

        if not check_password(senha, aluno.senha):
            messages.error(request, "Credenciais inválidas.")
            return redirect('login')

        request.session['aluno_id'] = aluno.id
        request.session['aluno_nome'] = aluno.nome_completo  # Adicionando nome do aluno na sessão
        return redirect('painel_aluno')  # Note que agora usa underscore

def painel_aluno(request):
    if 'aluno_id' not in request.session:
        messages.error(request, "Por favor, faça login para acessar esta página.")
        return redirect('login')
    
    try:
        aluno = Aluno.objects.get(id=request.session['aluno_id'])
        
        # Obtém a matrícula ativa mais recente do aluno
        matricula = Matricula.objects.filter(aluno=aluno, ativo=True).order_by('-data_matricula').first()
        
        # Obtém o certificado do aluno
        certificado = Certificado.objects.filter(matricula__aluno=aluno).first()
        
        # Obtém as declarações do aluno
        declaracoes = DeclaracaoNotas.objects.filter(matricula__aluno=aluno).order_by('-data_emissao')
        
        # Obtém TODOS os pedidos de correção do aluno (certificados e declarações)
        pedidos_correcao = PedidoCorrecao.objects.filter(
            Q(certificado__matricula__aluno=aluno) | 
            Q(declaracao__matricula__aluno=aluno),
            solicitado_por=aluno  # Garante que foi o aluno quem solicitou
        ).order_by('-data_solicitacao')
        
        context = {
            'aluno': aluno,
            'matricula': matricula,
            'certificado': certificado,
            'declaracoes': declaracoes,
            'pedidos_correcao': pedidos_correcao,
        }
        
        return render(request, 'dashboard_aluno.html', context)
        
    except Aluno.DoesNotExist:
        messages.error(request, "Aluno não encontrado.")
        return redirect('login')

def solicitar_correcao(request):
    if 'aluno_id' not in request.session:
        messages.error(request, "Por favor, faça login para acessar esta página.")
        return redirect('login_aluno')
    
    if request.method == 'POST':
        tipo_documento = request.POST.get('tipo_documento')
        documento_id = request.POST.get('documento_id')
        descricao = request.POST.get('descricao')
        
        try:
            aluno = Aluno.objects.get(id=request.session['aluno_id'])
            
            if tipo_documento == 'CERTIFICADO':
                documento = Certificado.objects.get(
                    id=documento_id, 
                    matricula__aluno=aluno
                )
                PedidoCorrecao.objects.create(
                    tipo_documento='CERTIFICADO',
                    certificado=documento,
                    descricao=descricao,
                    estado='PENDENTE',
                    solicitado_por=aluno
                )
            else:
                documento = DeclaracaoNotas.objects.get(
                    id=documento_id,
                    matricula__aluno=aluno
                )
                PedidoCorrecao.objects.create(
                    tipo_documento='DECLARACAO',
                    declaracao=documento,
                    descricao=descricao,
                    estado='PENDENTE',
                    solicitado_por=aluno
                )
            
            messages.success(request, "Solicitação de correção enviada com sucesso!")
            return redirect('painel_aluno')
            
        except (Certificado.DoesNotExist, DeclaracaoNotas.DoesNotExist):
            messages.error(request, "Documento não encontrado ou não pertence a você.")
        except Aluno.DoesNotExist:
            messages.error(request, "Aluno não encontrado.")
            return redirect('login_aluno')
        except Exception as e:
            messages.error(request, f"Ocorreu um erro: {str(e)}")
        
        return redirect('painel_aluno')
    
    return redirect('painel_aluno')

def logout_aluno(request):
    request.session.flush()
    return redirect('home')



 
def visualizar_certificado(request, certificado_id):
    # Verifica se o aluno está logado na sessão
    if 'aluno_id' not in request.session:
        messages.error(request, "Por favor, faça login para acessar esta página.")
        return redirect('login_aluno')
    
    try:
        aluno = Aluno.objects.get(id=request.session['aluno_id'])
        certificado = get_object_or_404(Certificado, id=certificado_id, ativo=True)
        
        # Verifica se o certificado pertence ao aluno logado
        if certificado.matricula.aluno != aluno:
            messages.error(request, "Você não tem permissão para acessar este certificado.")
            return redirect('painel_aluno')
        
        # Organiza as disciplinas por componentes usando a categoria do modelo
        resultados = certificado.resultados_disciplinas.all().select_related('disciplina')
        
        # Filtra as disciplinas por categoria
        socio_cultural = resultados.filter(
            disciplina__categoria='COMPONENTE SOCIO-CULTURAL'
        ).order_by('disciplina__nome')
        
        cientifica = resultados.filter(
            disciplina__categoria='COMPONENTE CIENTIFICA'
        ).order_by('disciplina__nome')
        
        tecnica = resultados.filter(
            disciplina__categoria='COMPONENTE TECNOLOGICA E PRATICA'
        ).order_by('disciplina__nome')
        
        context = {
            'certificado': certificado,
            'aluno': aluno,
            'socio_cultural': socio_cultural,
            'cientifica': cientifica,
            'tecnica': tecnica,
        }
        
        return render(request, 'detalhes_certificado.html', context)
        
    except Aluno.DoesNotExist:
        messages.error(request, "Aluno não encontrado.")
        return redirect('login_aluno')
    except Certificado.DoesNotExist:
        messages.error(request, "Certificado não encontrado.")
        return redirect('painel_aluno')


def descarregar_certificado(request, certificado_id):
    # Verifica se o aluno está logado na sessão
    if 'aluno_id' not in request.session:
        messages.error(request, "Por favor, faça login para acessar esta página.")
        return redirect('login_aluno')
    
    try:
        aluno = Aluno.objects.get(id=request.session['aluno_id'])
        certificado = get_object_or_404(Certificado, id=certificado_id, ativo=True)
        
        # Verifica se o certificado pertence ao aluno logado
        if certificado.matricula.aluno != aluno:
            messages.error(request, "Você não tem permissão para baixar este certificado.")
            return redirect('painel_aluno')
        
        # Organiza as disciplinas por componentes
        resultados = certificado.resultados_disciplinas.all().select_related('disciplina')
        
        # Filtra as disciplinas por categoria
        socio_cultural = resultados.filter(
            disciplina__categoria='COMPONENTE SOCIO-CULTURAL'
        ).order_by('disciplina__nome')
        
        cientifica = resultados.filter(
            disciplina__categoria='COMPONENTE CIENTIFICA'
        ).order_by('disciplina__nome')
        
        tecnica = resultados.filter(
            disciplina__categoria='COMPONENTE TECNOLOGICA E PRATICA'
        ).order_by('disciplina__nome')
        
        context = {
            'certificado': certificado,
            'aluno': aluno,
            'socio_cultural': socio_cultural,
            'cientifica': cientifica,
            'tecnica': tecnica,
        }
        
        # Renderiza o template para PDF
        template = get_template('detalhes_certificado.html')
        html = template.render(context)
        
        # Cria o PDF
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"certificado_{certificado.numero_certificado}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        
        return HttpResponse("Erro ao gerar PDF", status=500)
        
    except Aluno.DoesNotExist:
        messages.error(request, "Aluno não encontrado.")
        return redirect('login_aluno')
    except Certificado.DoesNotExist:
        messages.error(request, "Certificado não encontrado.")
        return redirect('painel_aluno')

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


def visualizar_declaracao(request, declaracao_id):
    # Verifica se o aluno está logado na sessão
    if 'aluno_id' not in request.session:
        messages.error(request, "Por favor, faça login para acessar esta página.")
        return redirect('login_aluno')
    
    try:
        aluno = Aluno.objects.get(id=request.session['aluno_id'])
        declaracao = get_object_or_404(DeclaracaoNotas, id=declaracao_id)
        
        # Verifica se a declaração pertence ao aluno logado
        if declaracao.matricula.aluno != aluno:
            messages.error(request, "Você não tem permissão para acessar esta declaração.")
            return redirect('painel_aluno')
        
        # Organiza os resultados
        resultados = declaracao.resultados.all().select_related('disciplina')
        
        context = {
            'declaracao': declaracao,
            'aluno': aluno,
            'resultados': resultados,
        }
        
        return render(request, 'detalhes_declaracao.html', context)
        
    except Aluno.DoesNotExist:
        messages.error(request, "Aluno não encontrado.")
        return redirect('login_aluno')
    except DeclaracaoNotas.DoesNotExist:
        messages.error(request, "Declaração não encontrada.")
        return redirect('painel_aluno')

def descarregar_declaracao(request, declaracao_id):
    # Verifica se o aluno está logado na sessão
    if 'aluno_id' not in request.session:
        messages.error(request, "Por favor, faça login para acessar esta página.")
        return redirect('login_aluno')
    
    try:
        aluno = Aluno.objects.get(id=request.session['aluno_id'])
        declaracao = get_object_or_404(DeclaracaoNotas, id=declaracao_id)
        
        # Verifica se a declaração pertence ao aluno logado
        if declaracao.matricula.aluno != aluno:
            messages.error(request, "Você não tem permissão para baixar esta declaração.")
            return redirect('painel_aluno')
        
        # Obtém os resultados
        resultados = declaracao.resultados.all().select_related('disciplina')
        
        context = {
            'declaracao': declaracao,
            'aluno': aluno,
            'resultados': resultados,
        }
        
        # Renderiza o template para PDF
        template = get_template('detalhes_declaracao.html')
        html = template.render(context)
        
        # Cria o PDF
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"declaracao_{declaracao.numero_processo}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        
        return HttpResponse("Erro ao gerar PDF", status=500)
        
    except Aluno.DoesNotExist:
        messages.error(request, "Aluno não encontrado.")
        return redirect('login_aluno')
    except DeclaracaoNotas.DoesNotExist:
        messages.error(request, "Declaração não encontrada.")
        return redirect('painel_aluno')

def verificar_declaracao(request, identificador):
    """
    Verifica declaração por número de processo ou código de verificação
    """
    try:
        # Tenta primeiro como número de processo (mais comum)
        declaracao = get_object_or_404(
            DeclaracaoNotas, 
            numero_processo=identificador.upper(),
        )
        metodo_verificacao = 'número de processo'
            
    except Http404:
        # Se falhar, tenta como código de verificação (UUID)
        try:
            declaracao = get_object_or_404(
                DeclaracaoNotas, 
                codigo_verificacao=identificador,
            )
            metodo_verificacao = 'código de verificação'
        except (Http404, ValidationError):
            # Se ambos falharem, mostra página de erro
            return render(request, 'verificacao_declaracao.html', {
                'invalido': True,
                'identificador': identificador
            })
    
    return render(request, 'verificacao_declaracao.html', {
        'declaracao': declaracao,
        'metodo_verificacao': metodo_verificacao,
        'valido': True
    })
    
    
def Erro(request, exception):
    return render(request, 'error.html', status=404)