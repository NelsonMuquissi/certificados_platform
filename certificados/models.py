from django.db import models
import uuid
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

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

    aluno = models.ForeignKey(Usuario, on_delete=models.CASCADE, limit_choices_to={'tipo': 'Aluno'})
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    data_emissao = models.DateTimeField(auto_now_add=True)
    codigo_validacao = models.CharField(max_length=64, unique=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Ativo')

    def save(self, *args, **kwargs):
        if not self.codigo_validacao:
            self.codigo_validacao = uuid.uuid4().hex  # Gera código único
        if not self.qr_code:
            self.gerar_qr_code()  # Gera QR Code apenas se não existir
        super().save(*args, **kwargs)

    def gerar_qr_code(self):
        """Gera um QR Code com link para verificação do certificado."""
        url_validacao = f"https://ipiz.com/validar/{self.codigo_validacao}"
        qr = qrcode.make(url_validacao)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        self.qr_code.save(f"qr_{self.codigo_validacao}.png", ContentFile(buffer.getvalue()), save=False)

    def __str__(self):
        return f"Certificado de {self.aluno.nome} - {self.curso.nome}"

# ==============================
# MODELO DE LOGS DE VALIDAÇÃO
# ==============================
class LogValidacao(models.Model):
    certificado = models.ForeignKey(Certificado, on_delete=models.CASCADE, related_name='validacoes')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)  # Registra o navegador do usuário
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
