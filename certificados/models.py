from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
import qrcode
from io import BytesIO
from django.core.files import File
from django.conf import settings
import uuid
from django.utils import timezone
from django.db.models import Avg
from django.utils.text import slugify

class UsuarioManager(BaseUserManager):
    def create_superuser(self, username, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('papel', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)

    def _create_user(self, username, email, password, **extra_fields):
        if not username:
            raise ValueError('The username must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

class Usuario(AbstractUser):
    PAPEIS = (
        ('SECRETARIA', 'Secretaria'),
        ('ADMIN', 'Administrador'),
        ('DIRECAO', 'Direção'),
    )
    
    objects = UsuarioManager()
    papel = models.CharField(max_length=10, choices=PAPEIS)
    telefone = models.CharField(max_length=20, blank=True, null=True)

    def has_module_perms(self, app_label):
        return self.is_staff or self.papel in ['ADMIN', 'SECRETARIA', 'DIRECAO']

    def has_perm(self, perm, obj=None):
        return self.is_staff or self.papel in ['ADMIN', 'SECRETARIA', 'DIRECAO']

class Provincia(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.nome

class Aluno(models.Model):
    SEXO_CHOICES = (
        ('M', 'Masculino'),
        ('F', 'Feminino'),
    )
    
    nome_completo = models.CharField(max_length=200)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)
    data_nascimento = models.DateField()
    local_nascimento = models.CharField(max_length=100)
    provincia = models.ForeignKey(Provincia, on_delete=models.PROTECT)
    nome_pai = models.CharField(max_length=100)
    nome_mae = models.CharField(max_length=100)
    numero_identificacao = models.CharField(max_length=20, unique=True)
    tipo_identificacao = models.CharField(max_length=50, default='Bilhete de Identidade')
    data_emissao_identificacao = models.DateField()
    emissor_identificacao = models.CharField(max_length=100)
    foto = models.ImageField(upload_to='alunos/fotos/', null=True, blank=True)
    
    class Meta:
        verbose_name_plural = 'Alunos'
    
    def __str__(self):
        return self.nome_completo

class AreaFormacao(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    codigo = models.CharField(max_length=20, unique=True)
    
    def __str__(self):
        return self.nome

class Curso(models.Model):
    TIPO_CHOICES = (
        ('MEDIO', 'Curso Médio'),
        ('BASICO', 'Curso Básico'),
    )
    
    nome = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, unique=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    area_formacao = models.ForeignKey(AreaFormacao, on_delete=models.PROTECT)
    duracao_anos = models.PositiveSmallIntegerField()
    
    def __str__(self):
        return f"{self.get_tipo_display()} de {self.nome}"

class Disciplina(models.Model):
    nome = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, unique=True)
    carga_horaria = models.PositiveSmallIntegerField()
    
    def __str__(self):
        return f"{self.codigo} - {self.nome}"

class CursoDisciplina(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE)
    semestre = models.PositiveSmallIntegerField()
    
    class Meta:
        unique_together = ('curso', 'disciplina')
        ordering = ['semestre', 'disciplina__nome']
    
    def __str__(self):
        return f"{self.curso} - {self.disciplina}"

class Matricula(models.Model):
    TURNO_CHOICES = (
        ('DIURNO', 'Diurno'),
        ('NOTURNO', 'Noturno'),
    )
    
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='matriculas')
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT)
    numero_matricula = models.CharField(max_length=20, unique=True)
    data_matricula = models.DateField()
    ano_letivo = models.CharField(max_length=9)  # Formato: 2020/2021
    nivel_classe = models.CharField(max_length=20)  # ex: "13ª classe"
    turno = models.CharField(max_length=10, choices=TURNO_CHOICES)
    ativo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'Matrículas'
    
    def __str__(self):
        return f"{self.aluno} - {self.curso} ({self.ano_letivo})"

class Certificado(models.Model):
    # Identificação
    matricula = models.ForeignKey(Matricula, on_delete=models.PROTECT, related_name='certificados')
    numero_certificado = models.CharField(max_length=20, unique=True, editable=False)
    numero_processo = models.CharField(max_length=20)
    livro_registo = models.CharField(max_length=50, editable=False)
    
    # Datas importantes
    data_emissao = models.DateField(default=timezone.now, editable=True)
    ano_letivo = models.CharField(max_length=9, editable=False)
    
    # Direção responsável
    diretor = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='certificados_emitidos')
    cargo_diretor = models.CharField(max_length=100, default='Directora do Instituto Médio Industrial de Luanda')
    
    # Resultados acadêmicos
    media_curricular = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        default=0.00,
        editable=False
    )
    prova_aptidao_profissional = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        default=0.00
    )
    classificacao_final = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        default=0.00,
        editable=False
    )
    
    # Verificação
    codigo_qr = models.ImageField(upload_to='codigos_qr/', blank=True, editable=False)
    codigo_verificacao = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ativo = models.BooleanField(default=True)
    
    # Metadados
    criado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='certificados_criados')
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True) 
    
    class Meta:
        ordering = ['-data_emissao']
        verbose_name_plural = 'Certificados'
    
    def __str__(self):
        return f"Certificado {self.numero_certificado} - {self.matricula.aluno}"
    
    def save(self, *args, **kwargs):
        # Configura valores iniciais obrigatórios
        if not self.numero_certificado:
            ano_atual = timezone.now().year
            ultimo_certificado = Certificado.objects.filter(
                numero_certificado__startswith=f'IPIC-{ano_atual}'
            ).order_by('-numero_certificado').first()
            
            self.numero_certificado = f"IPIC-{ano_atual}-{ultimo_numero + 1:04d}" if ultimo_certificado else f"IPIC-{ano_atual}-0001"
        
        if not self.ano_letivo and hasattr(self, 'matricula'):
            self.ano_letivo = self.matricula.ano_letivo
        
        if not self.livro_registo:
            self.livro_registo = f"{timezone.now().strftime('%d%m%y')}_{slugify(self.numero_certificado)}"
        
        # Primeiro salvamento para obter ID
        super().save(*args, **kwargs)
        
        # Cálculos que dependem de relacionamentos
        if hasattr(self, 'resultados_disciplinas'):
            self.media_curricular = round(self.resultados_disciplinas.aggregate(
                media=Avg('nota_numerica')
            )['media'] or 0, 2)
        
        # Calcula classificação final
        self.classificacao_final = round(
            (self.media_curricular + self.prova_aptidao_profissional) / 2, 
            2
        )
        
        # Gera QR code se necessário
        if not self.codigo_qr:
            self.gerar_qr_code()
        
        # Salvamento final com todos os dados
        super().save(*args, **kwargs)
    
    def gerar_qr_code(self):
        url_verificacao = f"{settings.BASE_URL}/verificar/{self.codigo_verificacao}/"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url_verificacao)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        nome_arquivo = f'certificado_{self.codigo_verificacao}.png'
        
        self.codigo_qr.save(nome_arquivo, File(buffer), save=False)

class ResultadoDisciplina(models.Model):
    certificado = models.ForeignKey(Certificado, on_delete=models.CASCADE, related_name='resultados_disciplinas')
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)
    nota_numerica = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )
    nota_literal = models.CharField(max_length=20, editable=False)
    
    class Meta:
        unique_together = ('certificado', 'disciplina')
        ordering = ['disciplina__nome']
        verbose_name = 'Resultado de Disciplina'
        verbose_name_plural = 'Resultados de Disciplinas'
    
    def __str__(self):
        return f"{self.disciplina}: {self.nota_numerica}"
    
    def save(self, *args, **kwargs):
        # Converter nota numérica para literal
        self.nota_literal = self.converter_para_literal(self.nota_numerica)
        super().save(*args, **kwargs)
        
        # Atualizar média no certificado
        if self.certificado:
            self.certificado.save()
    
    @staticmethod
    def converter_para_literal(nota_numerica):
        nota = float(nota_numerica)
        if nota >= 17: return "Muito Bom"
        elif nota >= 14: return "Bom"
        elif nota >= 10: return "Suficiente"
        else: return "Insuficiente"

class ConfiguracaoSistema(models.Model):
    nome_instituicao = models.CharField(max_length=200, default="Instituto Médio Industrial de Luanda")
    endereco_instituicao = models.TextField(default="Luanda, Angola")
    ministro_educacao = models.CharField(max_length=100, default="Ministério da Educação")
    texto_certificado = models.TextField(
        default="CERTIFICO em cumprimento do despacho exarado em requerimento que fica arquivado nesta Secretaria..."
    )
    rodape_certificado = models.TextField(
        default="Para efeitos legais é passado o presente CERTIFICADO que consta no livro de registo..."
    )
    
    def __str__(self):
        return "Configurações do Sistema"
    
    class Meta:
        verbose_name_plural = 'Configurações do Sistema'

class PedidoCorrecao(models.Model):
    ESTADOS = (
        ('PENDENTE', 'Pendente'),
        ('APROVADO', 'Aprovado'),
        ('REJEITADO', 'Rejeitado'),
    )
    
    certificado = models.ForeignKey(Certificado, on_delete=models.CASCADE, related_name='pedidos_correcao')
    solicitado_por = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    descricao = models.TextField()
    estado = models.CharField(max_length=10, choices=ESTADOS, default='PENDENTE')
    resolvido_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos_resolvidos')
    data_resolucao = models.DateTimeField(null=True, blank=True)
    notas_resolucao = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-data_solicitacao']
        verbose_name = 'Pedido de Correção'
        verbose_name_plural = 'Pedidos de Correção'
    
    def __str__(self):
        return f"Pedido #{self.id} - {self.certificado}"

class RegistroAuditoria(models.Model):
    ACCOES = (
        ('CRIAR', 'Criar'),
        ('ATUALIZAR', 'Atualizar'),
        ('APAGAR', 'Apagar'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('VERIFICAR', 'Verificar'),
        ('DESCARREGAR', 'Descarregar'),
    )
    
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    accao = models.CharField(max_length=11, choices=ACCOES)
    modelo = models.CharField(max_length=50)
    id_objeto = models.CharField(max_length=50, blank=True, null=True)
    detalhes = models.TextField(blank=True)
    endereco_ip = models.GenericIPAddressField(blank=True, null=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-data_hora']
        verbose_name = 'Registro de Auditoria'
        verbose_name_plural = 'Registros de Auditoria'
    
    def __str__(self):
        return f"{self.usuario} {self.accao} {self.modelo} em {self.data_hora}"
    
class Notificacao(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='notificacoes')
    mensagem = models.TextField()
    lida = models.BooleanField(default=False)
    data_criacao = models.DateTimeField(auto_now_add=True)
    link = models.URLField(blank=True, null=True)
    
    class Meta:
        ordering = ['-data_criacao']
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
    
    def __str__(self):
        return f"Notificação para {self.usuario}: {self.mensagem[:50]}..."