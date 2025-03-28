from django.db import models
import uuid
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import HttpResponse

# ==============================
# MODELO DE USUÁRIO
# ==============================
class Usuario(models.Model):
    TIPO_USUARIO_CHOICES = [
        ('Admin', 'Admin'),
        ('Aluno', 'Aluno'),
        ('Professor', 'Professor'),
    ]

    nome = models.CharField(max_length=255)
    sobrenome = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    senha = models.CharField(max_length=100)  # Recomendado usar hash na senha
    telefone = models.CharField(max_length=20, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    tipo = models.CharField(max_length=50, choices=TIPO_USUARIO_CHOICES, default='Aluno')
    data_cadastro = models.DateTimeField(auto_now_add=True)
    imagem = models.ImageField(upload_to='usuarios/', blank=True, null=True)
    codigo = models.CharField(max_length=18, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = str(uuid.uuid4().hex[:18])  # Gera código único
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} {self.sobrenome} - {self.tipo}"

# ==============================
# MODELO DE CURSOS
# ==============================
class Curso(models.Model):
    nome = models.CharField(max_length=255)
    descricao = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome

# ==============================
# MODELO DE CERTIFICADOS
# ==============================
class Certificado(models.Model):
    STATUS_CHOICES = [
        ('Ativo', 'Ativo'),
        ('Revogado', 'Revogado'),
    ]

    aluno = models.ForeignKey("Usuario", on_delete=models.CASCADE, limit_choices_to={'tipo': 'Aluno'})
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    data_emissao = models.DateTimeField(auto_now_add=True)
    codigo_validacao = models.UUIDField(default=uuid.uuid4, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Ativo')

    def __str__(self):
        return f"Certificado de {self.aluno.nome} - {self.curso.nome}"

    def gerar_pdf(self):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="certificado_{self.codigo_validacao}.pdf"'
        
        p = canvas.Canvas(response, pagesize=letter)
        p.setFont("Helvetica-Bold", 20)
        p.drawString(200, 750, "Certificado de Conclusão")
        
        p.setFont("Helvetica", 14)
        p.drawString(100, 700, f"Certificamos que {self.aluno.nome} {self.aluno.sobrenome}")
        p.drawString(100, 680, f"concluiu com êxito o curso: {self.curso.nome}")
        p.drawString(100, 660, f"Data de emissão: {self.data_emissao.strftime('%d/%m/%Y')}")

        if hasattr(self, 'qrcode') and self.qrcode.imagem:
            from PIL import Image
            qr = Image.open(self.qrcode.imagem.path)
            qr = qr.resize((100, 100))
            qr_buffer = BytesIO()
            qr.save(qr_buffer, format="PNG")
            p.drawInlineImage(qr_buffer, 450, 600, 100, 100)
        
        p.showPage()
        p.save()
        return response

# ==============================
# MODELO DE QR CODE
# ==============================
class QRCode(models.Model):
    certificado = models.OneToOneField(Certificado, on_delete=models.CASCADE, related_name='qrcode')
    imagem = models.ImageField(upload_to='qr_codes/', blank=True)

    def save(self, *args, **kwargs):
        if not self.imagem:
            self.gerar_qr_code()
        super().save(*args, **kwargs)

    def gerar_qr_code(self):
        """Gera um QR Code com link para verificação do certificado."""
        url_validacao = f"https://certificados-platform.onrender.com/"
        qr = qrcode.make(url_validacao)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        self.imagem.save(f"qr_{self.certificado.codigo_validacao}.png", ContentFile(buffer.getvalue()), save=False)


    def __str__(self):
        return f"QR Code para {self.certificado}"


# ==============================
# MODELO DE LOGS DE VALIDAÇÃO
# ==============================
class LogValidacao(models.Model):
    certificado = models.ForeignKey(Certificado, on_delete=models.CASCADE, related_name='validacoes')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    data_validacao = models.DateTimeField(auto_now_add=True)
    sucesso = models.BooleanField(default=True)

    def __str__(self):
        return f"Validação em {self.data_validacao} - {'Sucesso' if self.sucesso else 'Falha'}"

# ==============================
# MODELO DE CONFIGURAÇÃO DE SEGURANÇA
# ==============================
class ConfiguracaoSeguranca(models.Model):
    ALGORITHMS = [
        ('SHA-256', 'SHA-256'),
        ('SHA-512', 'SHA-512'),
        ('AES', 'AES'),
    ]

    algoritmo_criptografia = models.CharField(max_length=50, choices=ALGORITHMS, default='SHA-256')
    chave_publica = models.TextField()
    chave_privada = models.TextField()
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Configuração de Segurança - {self.algoritmo_criptografia}"


#New models------------------------------------------------------------

"""
from django.db import models
from django.core.validators import MinLengthValidator
from django.utils import timezone
from django.conf import settings
import qrcode
from io import BytesIO
from django.core.files import File
import hashlib
import uuid
from cryptography.fernet import Fernet
import base64
import os

class ConfiguracaoQRCode(models.Model):
    #Configurações personalizadas para geração de QR Codes
    tamanho = models.PositiveIntegerField(default=10, verbose_name="Tamanho do QR Code (px)")
    cor_frente = models.CharField(max_length=7, default='#000000', verbose_name="Cor da Frente (Hex)")
    cor_fundo = models.CharField(max_length=7, default='#FFFFFF', verbose_name="Cor de Fundo (Hex)")
    logo = models.ImageField(upload_to='qrcode_logos/', blank=True, null=True, verbose_name="Logo no QR Code")
    url_base_validacao = models.URLField(verbose_name="URL Base para Validação")

    def __str__(self):
        return "Configurações do QR Code"

    class Meta:
        verbose_name = "Configuração do QR Code"
        verbose_name_plural = "Configurações do QR Code"

    
    class Instituicao(models.Model):
    #Informações da instituição de ensino (IMIL)
    nome = models.CharField(max_length=200, verbose_name="Nome da Instituição")
    codigo_ministerio = models.CharField(max_length=50, verbose_name="Código no Ministério")
    endereco = models.TextField(verbose_name="Endereço Completo")
    telefone = models.CharField(max_length=20, verbose_name="Telefone")
    email = models.EmailField(verbose_name="E-mail Institucional")
    logotipo = models.ImageField(upload_to='instituicao/logotipos/', verbose_name="Logotipo")
    carimbo_oficial = models.ImageField(upload_to='instituicao/carimbos/', verbose_name="Carimbo Oficial")
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = "Instituição"
        verbose_name_plural = "Instituições"


class CursoTecnico(models.Model):
    #Cursos técnicos oferecidos pelo IMIL
    AREAS_CHOICES = [
        ('ELETRO', 'Electrotecnia'),
        ('MECAN', 'Mecânica'),
        ('INFORM', 'Informática'),
        ('CONSTR', 'Construção Civil'),
        ('QUIM', 'Química Industrial'),
        ('OUTROS', 'Outras Áreas'),
    ]
    
    instituicao = models.ForeignKey(Instituicao, on_delete=models.CASCADE, related_name='cursos')
    nome = models.CharField(max_length=200, verbose_name="Nome do Curso")
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código do Curso")
    area_tecnica = models.CharField(max_length=10, choices=AREAS_CHOICES, verbose_name="Área Técnica")
    duracao_anos = models.PositiveIntegerField(verbose_name="Duração (anos)")
    carga_horaria_total = models.PositiveIntegerField(verbose_name="Carga Horária Total")
    resolucao_legal = models.CharField(max_length=100, verbose_name="Resolução Legal de Criação")
    coordenador = models.CharField(max_length=200, verbose_name="Coordenador do Curso")
    
    def __str__(self):
        return f"{self.nome} ({self.codigo})"
    
    class Meta:
        verbose_name = "Curso Técnico"
        verbose_name_plural = "Cursos Técnicos"

class Disciplina(models.Model):
    #Disciplinas dos cursos técnicos
    curso = models.ForeignKey(CursoTecnico, on_delete=models.CASCADE, related_name='disciplinas')
    nome = models.CharField(max_length=200, verbose_name="Nome da Disciplina")
    codigo = models.CharField(max_length=20, verbose_name="Código da Disciplina")
    carga_horaria = models.PositiveIntegerField(verbose_name="Carga Horária")
    ano_lectivo = models.PositiveIntegerField(verbose_name="Ano Lectivo")
    
    def __str__(self):
        return f"{self.nome} - {self.curso.nome}"
    
    class Meta:
        verbose_name = "Disciplina"
        verbose_name_plural = "Disciplinas"

    class Aluno(models.Model):
    #Dados dos alunos
    GENERO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Feminino'),
    ]
    
    numero_processo = models.CharField(max_length=20, unique=True, verbose_name="Número de Processo")
    nome_completo = models.CharField(max_length=200, verbose_name="Nome Completo")
    genero = models.CharField(max_length=1, choices=GENERO_CHOICES, verbose_name="Género")
    data_nascimento = models.DateField(verbose_name="Data de Nascimento")
    naturalidade = models.CharField(max_length=100, verbose_name="Naturalidade")
    nacionalidade = models.CharField(max_length=100, verbose_name="Nacionalidade")
    bilhete_identidade = models.CharField(max_length=20, unique=True, verbose_name="Bilhete de Identidade")
    emitido_em = models.DateField(verbose_name="Emitido em")
    nome_pai = models.CharField(max_length=200, verbose_name="Nome do Pai")
    nome_mae = models.CharField(max_length=200, verbose_name="Nome da Mãe")
    endereco = models.TextField(verbose_name="Endereço")
    telefone = models.CharField(max_length=20, verbose_name="Telefone")
    email = models.EmailField(verbose_name="E-mail")
    foto = models.ImageField(upload_to='alunos/fotos/', verbose_name="Foto")
    
    def __str__(self):
        return f"{self.nome_completo} (BI: {self.bilhete_identidade})"
    
    class Meta:
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"

class Matricula(models.Model):
    #Registro de matrículas dos alunos
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='matriculas')
    curso = models.ForeignKey(CursoTecnico, on_delete=models.CASCADE, related_name='matriculas')
    numero_matricula = models.CharField(max_length=20, unique=True, verbose_name="Número de Matrícula")
    ano_lectivo = models.CharField(max_length=9, verbose_name="Ano Lectivo (ex: 2022-2023)")
    data_matricula = models.DateField(verbose_name="Data de Matrícula")
    turma = models.CharField(max_length=10, verbose_name="Turma")
    
    def __str__(self):
        return f"Matrícula {self.numero_matricula} - {self.aluno.nome_completo}"
    
    class Meta:
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"

    
    class CertificadoTecnico(models.Model):
    #Model principal para certificados técnicos
    STATUS_CHOICES = [
        ('EMITIDO', 'Emitido'),
        ('VALIDADO', 'Validado'),
        ('INVALIDO', 'Inválido'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    matricula = models.OneToOneField(Matricula, on_delete=models.CASCADE, related_name='certificado')
    codigo_validacao = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    qr_code = models.ImageField(upload_to='certificados/qrcodes/', blank=True, null=True)
    data_emissao = models.DateField(auto_now_add=True, verbose_name="Data de Emissão")
    livro_registro = models.CharField(max_length=20, verbose_name="Livro de Registro")
    folha_registro = models.CharField(max_length=20, verbose_name="Folha de Registro")
    numero_registro = models.CharField(max_length=20, verbose_name="Número de Registro")
    diretor = models.CharField(max_length=200, verbose_name="Nome do Diretor")
    coordenador_curso = models.CharField(max_length=200, verbose_name="Nome do Coordenador")
    secretario = models.CharField(max_length=200, verbose_name="Nome do Secretário")
    carimbo = models.ImageField(upload_to='certificados/carimbos/', verbose_name="Carimbo Oficial")
    assinatura_diretor = models.ImageField(upload_to='certificados/assinaturas/', verbose_name="Assinatura do Diretor")
    assinatura_coordenador = models.ImageField(upload_to='certificados/assinaturas/', verbose_name="Assinatura do Coordenador")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='EMITIDO', verbose_name="Status")
    
    def gerar_qr_code(self):
        #Gera o QR Code com URL de validação
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        url_validacao = f"{settings.SITE_URL}/validar-certificado/{self.codigo_validacao}/"
        qr.add_data(url_validacao)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        nome_arquivo = f'qr_code_{self.codigo_validacao}.png'
        
        self.qr_code.save(nome_arquivo, File(buffer), save=False)
        buffer.close()
    
    def save(self, *args, **kwargs):
        if not self.pk:  # Se for um novo certificado
            self.gerar_qr_code()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Certificado Técnico - {self.matricula.aluno.nome_completo}"
    
    class Meta:
        verbose_name = "Certificado Técnico"
        verbose_name_plural = "Certificados Técnicos"

class ResultadoDisciplinar(models.Model):
    #Notas das disciplinas no certificado
    certificado = models.ForeignKey(CertificadoTecnico, on_delete=models.CASCADE, related_name='resultados')
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE)
    nota_final = models.DecimalField(max_digits=4, decimal_places=2, verbose_name="Nota Final")
    mencao = models.CharField(max_length=50, verbose_name="Menção")
    
    def __str__(self):
        return f"{self.disciplina.nome} - {self.mencao}"
    
    class Meta:
        verbose_name = "Resultado Disciplinar"
        verbose_name_plural = "Resultados Disciplinares"

class ValidacaoCertificado(models.Model):
    #Registro de validações de certificados
    certificado = models.ForeignKey(CertificadoTecnico, on_delete=models.CASCADE, related_name='validacoes')
    data_validacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Validação")
    ip_address = models.GenericIPAddressField(verbose_name="Endereço IP")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    valido = models.BooleanField(verbose_name="Válido?")
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    
    def __str__(self):
        return f"Validação de {self.certificado} em {self.data_validacao}"
    
    class Meta:
        verbose_name = "Validação de Certificado"
        verbose_name_plural = "Validações de Certificados"

    
    class CertificadoDownload(models.Model):
    #Armazena os certificados em PDF para download
    certificado = models.OneToOneField(
        CertificadoTecnico,
        on_delete=models.CASCADE,
        related_name='download'
    )
    arquivo_pdf = models.FileField(
        upload_to='certificados/pdfs/',
        null=True,
        blank=True,
        verbose_name="Arquivo PDF"
    )
    data_geracao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Geração"
    )
    hash_verificacao = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Hash de Verificação"
    )
    tamanho_arquivo = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Tamanho do Arquivo (bytes)"
    )
    template_usado = models.CharField(
        max_length=100,
        default='certificados/modelo_padrao.html',
        verbose_name="Template Utilizado"
    )

    def gerar_pdf(self):
        #Gera o PDF do certificado
        from django.template.loader import render_to_string
        from weasyprint import HTML
        import tempfile

        contexto = {
            'certificado': self.certificado,
            'aluno': self.certificado.matricula.aluno,
            'curso': self.certificado.matricula.curso,
            'instituicao': self.certificado.matricula.curso.instituicao,
            'resultados': self.certificado.resultados.all(),
        }

        html_string = render_to_string(self.template_usado, contexto)
        html = HTML(string=html_string, base_url=settings.BASE_URL)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as output:
            html.write_pdf(target=output)
        
        with open(output.name, 'rb') as f:
            self.arquivo_pdf.save(
                f'certificado_{self.certificado.matricula.aluno.bilhete_identidade}.pdf',
                File(f)
            )
        
        os.unlink(output.name)
        self._calcular_hash()
        self._calcular_tamanho()

    def _calcular_hash(self):
        #Gera um hash SHA-256 do arquivo para verificação de integridade
        if self.arquivo_pdf:
            hash_sha = hashlib.sha256()
            for chunk in self.arquivo_pdf.chunks():
                hash_sha.update(chunk)
            self.hash_verificacao = hash_sha.hexdigest()

    def _calcular_tamanho(self):
        #Calcula o tamanho do arquivo em bytes
        if self.arquivo_pdf:
            self.tamanho_arquivo = self.arquivo_pdf.size

    def save(self, *args, **kwargs):
        if not self.pk or not self.arquivo_pdf:
            self.gerar_pdf()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Download para {self.certificado}"

    class Meta:
        verbose_name = "Download de Certificado"
        verbose_name_plural = "Downloads de Certificados"
"""