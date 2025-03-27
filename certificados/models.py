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
        url_validacao = f"https://certificados-platform.onrender.com/certificados/validar/{self.certificado.codigo_validacao}/"
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
