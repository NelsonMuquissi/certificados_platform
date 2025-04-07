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
from django.contrib.auth.hashers import make_password

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
    
    # Adicione estes campos para resolver os conflitos
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="usuario_groups",  # Nome único para o relacionamento reverso
        related_query_name="usuario",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="usuario_permissions",  # Nome único para o relacionamento reverso
        related_query_name="usuario",
    )

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
    
    # Campos para autenticação
    email = models.EmailField(unique=True, null=True, blank=True)
    password = models.CharField(max_length=128)  # Senha armazenada como hash
    conta_habilitada = models.BooleanField(default=False, 
        help_text="Se a conta está habilitada para fazer login")
    ultimo_login = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = 'Alunos'
    
    def __str__(self):
        return self.nome_completo
    
    def set_password(self, raw_password):
        """Define a senha do aluno (armazenada como hash)"""
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Verifica se a senha fornecida está correta"""
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)
    
    def save(self, *args, **kwargs):
        # Se é um novo aluno e não tem senha definida, usa o número de identificação como senha
        if not self.pk and not self.password:
            self.set_password(self.numero_identificacao)
        
        # Garante que o email está em lowercase
        if self.email:
            self.email = self.email.lower()
            
        super().save(*args, **kwargs)

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
    identificador_matricula = models.CharField(
        max_length=10,
        unique=True,
        help_text="Identificador único para geração do número de matrícula (ex: I para Informática, M para Mecânica)"
    )
    
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
        ('MANHA', 'Manha'),
        ('TARDE', 'Tarde'),
        ('NOTURNO', 'Noturno'),
    )
    
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='matriculas')
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT)
    numero_matricula = models.CharField(max_length=20, unique=True, editable=False)  # Removido o editable=True
    data_matricula = models.DateField()
    ano_letivo = models.CharField(max_length=9)  # Formato: 2020/2021
    nivel_classe = models.CharField(max_length=20, default='13')  # ex: "13ª classe"
    turno = models.CharField(max_length=10, choices=TURNO_CHOICES)
    ativo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'Matrículas'
    
    def __str__(self):
        return f"{self.aluno} - {self.curso} ({self.ano_letivo})"
    
    def save(self, *args, **kwargs):
        if not self.numero_matricula:
            # Usa o identificador_matricula do curso
            identificador = self.curso.identificador_matricula.upper()
            
            # Encontrar o último número de matrícula no sistema (independente do curso)
            ultima_matricula = Matricula.objects.all().order_by('-id').first()
            
            if ultima_matricula:
                try:
                    # Extrai o número da última matrícula
                    ultimo_numero = int(ultima_matricula.numero_matricula[1:])
                    novo_numero = ultimo_numero + 1
                except (ValueError, IndexError):
                    # Se houver erro na conversão, começa do 1
                    novo_numero = 1
            else:
                # Primeira matrícula do sistema
                novo_numero = 1
            
            self.numero_matricula = f"{identificador}{novo_numero}"
        
        super().save(*args, **kwargs)

class Certificado(models.Model):
    # Identificação
    matricula = models.ForeignKey('Matricula', on_delete=models.PROTECT, related_name='certificados')
    numero_certificado = models.CharField(max_length=20, unique=True, editable=False)
    numero_processo = models.CharField(max_length=20, editable=False)
    livro_registo = models.CharField(max_length=50, editable=False)
    
    # Datas importantes
    data_emissao = models.DateField(default=timezone.now, editable=True)
    ano_letivo = models.CharField(max_length=9, editable=False)
    
    # Direção responsável
    diretor = models.ForeignKey('Usuario', on_delete=models.PROTECT, related_name='certificados_emitidos')
    cargo_diretor = models.CharField(max_length=100, default='Directora do Instituto Politécnico Industrial do Calumbo')
    
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
    criado_por = models.ForeignKey('Usuario', on_delete=models.SET_NULL, null=True, related_name='certificados_criados')
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True) 
    
    class Meta:
        ordering = ['-data_emissao']
        verbose_name_plural = 'Certificados'
        
    def __str__(self):
        return f"Certificado {self.numero_certificado} - {self.matricula.aluno}"
        
    def gerar_numero_certificado(self):
        """Gera um número de certificado único no formato IPIC-YYYY-NNNN"""
        ano_atual = timezone.now().year
        ultimo_certificado = Certificado.objects.filter(
            numero_certificado__startswith=f'IPIC-{ano_atual}'
        ).order_by('-numero_certificado').first()
            
        if ultimo_certificado:
            try:
                ultimo_numero = int(ultimo_certificado.numero_certificado.split('-')[-1])
                self.numero_certificado = f"IPIC-{ano_atual}-{ultimo_numero + 1:04d}"
            except (IndexError, ValueError):
                self.numero_certificado = f"IPIC-{ano_atual}-0001"
        else:
            self.numero_certificado = f"IPIC-{ano_atual}-0001"
        
    def atualizar_medias(self):
        """Atualiza as médias e classificação final com a nova fórmula"""
        if hasattr(self, 'resultados_disciplinas'):
            media = self.resultados_disciplinas.aggregate(
                media=Avg('nota_numerica')
            )['media'] or 0
            self.media_curricular = round(media, 2)
            
        self.classificacao_final = round(
            (self.media_curricular * 2 + self.prova_aptidao_profissional) / 3, 
            2
        )
        
    def gerar_qr_code(self):
        """Gera o código QR para verificação do certificado"""
        url_verificacao = f"{settings.BASE_URL}/certificados/verificar/{self.codigo_verificacao}/"
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
        
    def clean(self):
        """Garante que o numero_processo sempre corresponde à matrícula"""
        super().clean()
        if hasattr(self, 'matricula') and self.matricula.numero_matricula != self.numero_processo:
            self.numero_processo = self.matricula.numero_matricula
        
    def save(self, *args, **kwargs):
        # Configura valores iniciais obrigatórios
        if not self.numero_certificado:
            self.gerar_numero_certificado()
                
        # Garante que temos uma matrícula associada
        if not hasattr(self, 'matricula'):
            raise ValueError("Certificado deve estar associado a uma matrícula")
                
        # Define o número de processo como o número de matrícula
        if not self.numero_processo:
            self.numero_processo = self.matricula.numero_matricula
                
        # Define o ano letivo
        if not self.ano_letivo:
            self.ano_letivo = self.matricula.ano_letivo
                
        # Gera o livro de registro
        if not self.livro_registo:
            self.livro_registo = f"{timezone.now().strftime('%d%m%y')}_{slugify(self.numero_certificado)}"
                
        # Primeiro salvamento para obter ID
        super().save(*args, **kwargs)
                
        # Atualiza cálculos que dependem de relacionamentos
        self.atualizar_medias()
                
        # Gera QR code se necessário
        if not self.codigo_qr:
            self.gerar_qr_code()
                
        # Salvamento final com todos os dados
        super().save(*args, **kwargs)

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
    nome_instituicao = models.CharField(max_length=200, default="Instituto Politecnico Industrial do Icolo e Bengo")
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