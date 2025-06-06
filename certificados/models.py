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
from django.core.exceptions import ValidationError
from datetime import date
from django.core.mail import send_mail
from num2words import num2words
from decimal import Decimal, ROUND_HALF_UP
import re



PROVINCIAS_ANGOLA = (
    ('BENGO', 'Bengo'),
    ('BENGUELA', 'Benguela'),
    ('BIE', 'Bié'),
    ('CABINDA', 'Cabinda'),
    ('CUANDO_CUBANGO', 'Cuando Cubango'),
    ('CUANDO', 'Cuando'),
    ('CUANZA_NORTE', 'Cuanza Norte'),
    ('CUANZA_SUL', 'Cuanza Sul'),
    ('CUNENE', 'Cunene'),
    ('HUAMBO', 'Huambo'),
    ('HUILA', 'Huíla'),
    ('LUANDA', 'Luanda'),
    ('ICOLO E BENGO', 'Icolo e Bengo'),
    ('LUNDA_NORTE', 'Lunda Norte'),
    ('LUNDA_SUL', 'Lunda Sul'),
    ('MALANJE', 'Malanje'),
    ('MOXICO', 'Moxico'),
    ('CASSAI ZAMBEZE', 'Cassai Zambeze'),
    ('NAMIBE', 'Namibe'),
    ('UIGE', 'Uíge'),
    ('ZAIRE', 'Zaire'),
    ('OUTRO', 'Outro (Estrangeiro)'),
)

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
        related_name="usuario_groups",
        related_query_name="usuario",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="usuario_permissions",
        related_query_name="usuario",
    )

    def has_module_perms(self, app_label):
        return self.is_staff or self.papel in ['ADMIN', 'SECRETARIA', 'DIRECAO']

    def has_perm(self, perm, obj=None):
        return self.is_staff or self.papel in ['ADMIN', 'SECRETARIA', 'DIRECAO']


class Aluno(models.Model):
    SEXO_CHOICES = (
        ('M', 'Masculino'),
        ('F', 'Feminino'),
    )
    
    TIPO_IDENTIFICACAO_CHOICES = (
        ('BI', 'Bilhete de Identidade'),
        ('PASSAPORTE', 'Passaporte'),
    )
    
    nome_completo = models.CharField(max_length=200)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)
    data_nascimento = models.DateField()
    local_nascimento = models.CharField(max_length=100)
    provincia = models.CharField(max_length=20, choices=PROVINCIAS_ANGOLA)
    nome_pai = models.CharField(max_length=100)
    nome_mae = models.CharField(max_length=100)
    numero_identificacao = models.CharField(max_length=20, unique=True)
    tipo_identificacao = models.CharField(
        max_length=50, 
        choices=TIPO_IDENTIFICACAO_CHOICES, 
        default='BI'
    )
    data_emissao_identificacao = models.DateField()
    emissor_identificacao = models.CharField(max_length=100, default="Direção Nacional de Identificação")
    foto = models.ImageField(upload_to='alunos/fotos/', null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    senha = models.CharField(max_length=128, blank=True)
    conta_habilitada = models.BooleanField(default=False, 
        help_text="Se a conta está habilitada para fazer login")
    ultimo_login = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = 'Alunos'
    
    def __str__(self):
        return self.nome_completo
    
    def clean(self):
        super().clean()
        
        # Validação do número de identificação com regex
        if self.tipo_identificacao == 'BI':
            # Padrão: 9 dígitos + 2 letras + 3 dígitos (ex: 123456789LA123)
            bi_pattern = re.compile(r'^\d{9}[A-Za-z]{2}\d{3}$')
            if not bi_pattern.match(self.numero_identificacao):
                raise ValidationError(
                    {'numero_identificacao': 'Formato inválido de BI.'}
                )
            
            # Validação específica para BI angolano
            letras = self.numero_identificacao[9:11].upper()
            if letras not in ['LA', 'LO', 'BE', 'MO', 'NA', 'NO', 'HA', 'HO', 'ZA', 'ZO','BB', 'CC', 'CN', 'CS', 'CU', 'LU', 'LS', 'MA', 'UE']:
                raise ValidationError(
                    {'numero_identificacao': 'Código de emissor inválido no BI.'}
                )
                
        elif self.tipo_identificacao == 'PASSAPORTE':
            # Padrão: Letra N seguida de 7 dígitos (ex: N1234567)
            passaporte_pattern = re.compile(r'^N\d{7}$')
            if not passaporte_pattern.match(self.numero_identificacao):
                raise ValidationError(
                    {'numero_identificacao': 'Formato inválido de Passaporte. Use o padrão'}
                )
        
        # Validação de idade mínima (15 anos)
        if self.data_nascimento:
            hoje = date.today()
            idade = hoje.year - self.data_nascimento.year - ((hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day))
            
            if idade < 15:
                raise ValidationError(
                    {'data_nascimento': 'O aluno deve ter pelo menos 15 anos completos.'}
                )
            if self.data_nascimento > hoje:
                raise ValidationError(
                    {'data_nascimento': 'A data de nascimento não pode ser no futuro.'}
                )
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        # Define a senha como o número de identificação (hasheado) se estiver vazia
        if not self.senha:
            self.senha = make_password(self.numero_identificacao)
        elif not self.senha.startswith('pbkdf2_'):
            # Garante que senhas fornecidas manualmente sejam hasheadas
            self.senha = make_password(self.senha)

        if self.email:
            self.email = self.email.lower()
        
        # Força a validação antes de salvar
        self.full_clean()
        super().save(*args, **kwargs)
        
        if is_new and self.email:
            try:
                self.enviar_email_boas_vindas()
            except Exception as e:
                # Captura qualquer erro no envio de email e registra, mas não interrompe
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Falha ao enviar email de boas-vindas: {str(e)}", exc_info=True)

    def enviar_email_boas_vindas(self):
        try:
            assunto = "🎉 Bem-vindo ao IPIZ - Sua Jornada Começa Aqui!"
            
            # Mensagem HTML formatada
            mensagem_html = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background-color: #0056b3;
                        color: white;
                        padding: 20px;
                        text-align: center;
                        border-radius: 5px 5px 0 0;
                    }}
                    .welcome-icon {{
                        font-size: 48px;
                        margin-bottom: 15px;
                    }}
                    .content {{
                        padding: 20px;
                        background-color: #f9f9f9;
                        border-radius: 0 0 5px 5px;
                    }}
                    .credentials {{
                        background-color: white;
                        border: 1px solid #e0e0e0;
                        border-left: 4px solid #0056b3;
                        padding: 15px;
                        margin: 20px 0;
                    }}
                    .credential-item {{
                        margin-bottom: 10px;
                        display: flex;
                        align-items: center;
                    }}
                    .icon {{
                        margin-right: 10px;
                        color: #0056b3;
                        width: 20px;
                        text-align: center;
                    }}
                    .steps {{
                        margin: 20px 0;
                        padding-left: 20px;
                    }}
                    .step {{
                        margin-bottom: 10px;
                        position: relative;
                        padding-left: 30px;
                    }}
                    .step-number {{
                        position: absolute;
                        left: 0;
                        background-color: #0056b3;
                        color: white;
                        width: 20px;
                        height: 20px;
                        border-radius: 50%;
                        text-align: center;
                        line-height: 20px;
                        font-size: 12px;
                    }}
                    .button {{
                        display: inline-block;
                        background-color: #0056b3;
                        color: white;
                        padding: 12px 25px;
                        text-decoration: none;
                        border-radius: 5px;
                        margin: 15px 0;
                        font-weight: bold;
                    }}
                    .contact {{
                        margin-top: 25px;
                        padding-top: 15px;
                        border-top: 1px solid #e0e0e0;
                    }}
                    .footer {{
                        margin-top: 20px;
                        font-size: 0.9em;
                        color: #666;
                        text-align: center;
                    }}
                    .highlight {{
                        background-color: #fff8e1;
                        padding: 2px 5px;
                        border-radius: 3px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <div class="welcome-icon">🎓</div>
                    <h2 style="margin:0;">Bem-vindo ao IPIZ!</h2>
                    <p style="margin:5px 0 0;font-size:0.9em;">Instituto Politécnico Industrial do Zango</p>
                </div>
                
                <div class="content">
                    <p>Olá <strong>{self.nome_completo}</strong>,</p>
                    
                    <p>É com grande alegria que damos as boas-vindas ao <strong>Instituto Politécnico Industrial do Zango</strong>!</p>
                    
                    <p>Estamos entusiasmados por você fazer parte da nossa comunidade acadêmica e comprometidos com o seu sucesso.</p>
                    
                    <div class="credentials">
                        <h3 style="margin-top:0;color:#0056b3;">📋 Suas Credenciais de Acesso</h3>
                        
                        <div class="credential-item">
                            <span class="icon">📧</span>
                            <span><strong>Email:</strong> {self.email}</span>
                        </div>
                        <div class="credential-item">
                            <span class="icon">🔑</span>
                            <span><strong>Senha inicial:</strong> <span class="highlight">Seu número de documento ({self.numero_identificacao})</span></span>
                        </div>
                    </div>
                    
                    <h3 style="color:#0056b3;">📝 Primeiros Passos Recomendados</h3>
                    
                    <div class="steps">
                        <div class="step">
                            <div class="step-number">1</div>
                            <strong>Acesse o sistema</strong> o quanto antes para conhecer a plataforma
                        </div>
                        <div class="step">
                            <div class="step-number">2</div>
                            <strong>Altere sua senha</strong> para uma combinação mais segura
                        </div>
                        <div class="step">
                            <div class="step-number">3</div>
                            <strong>Complete seu perfil acadêmico</strong> com suas informações atualizadas
                        </div>
                    </div>
                    
                    <p style="text-align:center;">
                        <a style="color:#fff" href="{settings.BASE_URL}" class="button">Acessar a Plataforma</a>
                    </p>
                    
                    <div class="contact">
                        <h3 style="color:#0056b3;margin-top:0;">📞 Precisa de Ajuda?</h3>
                        <p>Nossa equipe de suporte está pronta para auxiliá-lo:</p>
                        <div class="credential-item">
                            <span class="icon">✉️</span>
                            <span><strong>Email:</strong> suporte@ipiz.ed.ao</span>
                        </div>
                        <div class="credential-item">
                            <span class="icon">📱</span>
                            <span><strong>Telefone:</strong> +244 936 327 119</span>
                        </div>
                    </div>
                    
                    <p>Estamos à disposição para apoiar sua jornada acadêmica!</p>
                </div>
                
                <div class="footer">
                    <p>© {timezone.now().year} IPIZ - Instituto Politécnico Industrial do Zango</p>
                    <p>Este é um email automático, por favor não responda.</p>
                </div>
            </body>
            </html>
            """
            
            # Versão alternativa em texto simples
            mensagem_texto = f"""
            Olá {self.nome_completo}!

            Seja muito bem-vindo(a) ao Instituto Politécnico Industrial do Zango!

            ========== SUAS CREDENCIAIS ==========
            Email: {self.email}
            Senha inicial: Seu número de documento ({self.numero_identificacao})
            ======================================

            RECOMENDAÇÕES IMPORTANTES:
            1. Acesse o sistema o quanto antes
            2. Altere sua senha para uma mais segura
            3. Complete seu perfil acadêmico

            ACESSO À PLATAFORMA:
            {settings.BASE_URL}

            SUPORTE TÉCNICO:
            Email: suporte@ipiz.ed.ao
            Telefone: +244 936 327 119

            Estamos à disposição para apoiar seu sucesso acadêmico!

            Atenciosamente,
            Direção Acadêmica
            IPIZ - Instituto Politécnico Industrial do Zango
            """
            
            send_mail(
                assunto,
                mensagem_texto,
                settings.EMAIL_HOST_USER,
                [self.email],
                html_message=mensagem_html,
                fail_silently=False,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Falha ao enviar email de boas-vindas: {str(e)}", exc_info=True)
            raise

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
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='Curso Médio')
    area_formacao = models.ForeignKey(AreaFormacao, on_delete=models.PROTECT)
    duracao_anos = models.PositiveSmallIntegerField(default=4)
    identificador_matricula = models.CharField(
        max_length=10,
        unique=True,
        help_text="Identificador único para geração do número de matrícula (ex: I para Informática, M para Mecânica)"
    )
    
    def __str__(self):
        return f"{self.get_tipo_display()} de {self.nome}"

class Disciplina(models.Model):
    
    CATEGORIA_CHOICES = (
        ('COMPONENTE SOCIO-CULTURAL', 'Componente Socio-cultural'),
        ('COMPONENTE CIENTIFICA', 'Componente Cientifica'),
        ('COMPONENTE TECNOLOGICA E PRATICA', 'Componente Tecnologica e Pratica'),
    )
    nome = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, unique=True)
    categoria = models.CharField(max_length=100, choices=CATEGORIA_CHOICES)
    
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
    numero_matricula = models.CharField(max_length=20, unique=True, editable=False)
    data_matricula = models.DateField()
    ano_letivo = models.CharField(max_length=9, default='2024-2025')
    nivel_classe = models.CharField(max_length=20, default='13')
    turno = models.CharField(max_length=10, choices=TURNO_CHOICES)
    ativo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'Matrículas'
    
    def __str__(self):
        return f"{self.aluno} - {self.curso} ({self.ano_letivo})"
    
    def save(self, *args, **kwargs):
        if not self.numero_matricula:
            identificador = self.curso.identificador_matricula.upper()
            
            ultima_matricula = Matricula.objects.all().order_by('-id').first()
            
            if ultima_matricula:
                try:
                    ultimo_numero = int(ultima_matricula.numero_matricula[1:])
                    novo_numero = ultimo_numero + 1
                except (ValueError, IndexError):
                    novo_numero = 1
            else:
                novo_numero = 1
            
            self.numero_matricula = f"{identificador}{novo_numero}"
        
        super().save(*args, **kwargs)

class Certificado(models.Model):
    matricula = models.OneToOneField('Matricula', on_delete=models.PROTECT, related_name='certificado')
    numero_certificado = models.CharField(max_length=20, unique=True, editable=False)
    numero_processo = models.CharField(max_length=20, unique=True, editable=False)
    livro_registo = models.CharField(max_length=50, editable=False)
    
    data_emissao = models.DateField(default=timezone.now, editable=True)
    ano_letivo = models.CharField(max_length=9, editable=False)
    
    diretor = models.ForeignKey('Usuario', on_delete=models.PROTECT, related_name='certificados_emitidos')
    cargo_de_direção = models.CharField(max_length=100, default='Directora do Instituto Politécnico Industrial do Zango')
    
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
    
    codigo_qr = models.ImageField(upload_to='codigos_qr/', blank=True, editable=False)
    codigo_verificacao = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ativo = models.BooleanField(default=True)
    
    criado_por = models.ForeignKey('Usuario', on_delete=models.SET_NULL, null=True, related_name='certificados_criados')
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True) 
    
    class Meta:
        ordering = ['-data_emissao']
        verbose_name_plural = 'Certificados'
        
    def __str__(self):
        return f"Certificado {self.numero_certificado} - {self.matricula.aluno}"
        
    def gerar_numero_certificado(self):
        ano_atual = timezone.now().year
        ultimo_certificado = Certificado.objects.filter(
            numero_certificado__startswith=f'IPIZ-{ano_atual}'
        ).order_by('-numero_certificado').first()
            
        if ultimo_certificado:
            try:
                ultimo_numero = int(ultimo_certificado.numero_certificado.split('-')[-1])
                self.numero_certificado = f"IPIZ-{ano_atual}-{ultimo_numero + 1:04d}"
            except (IndexError, ValueError):
                self.numero_certificado = f"IPIZ-{ano_atual}-0001"
        else:
            self.numero_certificado = f"IPIZ-{ano_atual}-0001"
        
    def atualizar_medias(self):
        if hasattr(self, 'resultados_disciplinas'):
            media = self.resultados_disciplinas.aggregate(
                media=Avg('nota_numerica')
            )['media'] or 0
            self.media_curricular = round(media, 2)
            
        self.classificacao_final = round(
            ((self.media_curricular * 2) + self.prova_aptidao_profissional) / 3, 
            2
        )
        
    def gerar_qr_code(self):
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
        super().clean()
        
        # Verificação única e clara da matrícula
        if not hasattr(self, 'matricula') or not self.matricula:
            raise ValidationError({'matricula': 'Este campo é obrigatório'})
        
        # Atualiza número do processo se necessário
        if self.matricula.numero_matricula != self.numero_processo:
            self.numero_processo = self.matricula.numero_matricula

        # Verifica se matrícula está ativa
        if not self.matricula.ativo:
            raise ValidationError({
                'matricula': 'Não é possível emitir certificado para matrícula inativa. '
                           'Ative a matrícula primeiro.'
            })
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
    
        if not self.numero_certificado:
            self.gerar_numero_certificado()
                
        if hasattr(self, 'matricula') and self.matricula:
            if not self.numero_processo:
                self.numero_processo = self.matricula.numero_matricula
            
            if not self.ano_letivo:
                self.ano_letivo = self.matricula.ano_letivo
                
            if not self.matricula.ativo:
                raise ValidationError("Não é possível emitir certificado para matrícula inativa")

        if not self.livro_registo:
            self.livro_registo = f"{timezone.now().strftime('%d%m%y')}_{slugify(self.numero_certificado)}"
            
        super().save(*args, **kwargs)
            
        if hasattr(self, 'matricula') and self.matricula:
            self.atualizar_medias()
                
        if not self.codigo_qr:
            self.gerar_qr_code()
                
        super().save(*args, **kwargs)

        if is_new and hasattr(self, 'matricula') and hasattr(self.matricula, 'aluno'):
            try:
                self.enviar_email_certificado()
            except Exception as e:
                # Captura qualquer erro no envio de email e registra, mas não interrompe
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Falha ao enviar email de certificado: {str(e)}", exc_info=True)

    def enviar_email_certificado(self):
        try:
            aluno = self.matricula.aluno
            assunto = "🎓 Seu Certificado foi Emitido - IPIZ"
            
            # Mensagem HTML formatada
            mensagem_html = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background-color: #28a745;
                        color: white;
                        padding: 15px;
                        text-align: center;
                        border-radius: 5px 5px 0 0;
                    }}
                    .content {{
                        padding: 20px;
                        background-color: #f9f9f9;
                        border-radius: 0 0 5px 5px;
                    }}
                    .details {{
                        background-color: white;
                        border-left: 4px solid #28a745;
                        padding: 15px;
                        margin: 15px 0;
                    }}
                    .detail-item {{
                        margin-bottom: 10px;
                        display: flex;
                        align-items: center;
                    }}
                    .icon {{
                        margin-right: 10px;
                        color: #28a745;
                        width: 20px;
                        text-align: center;
                    }}
                    .footer {{
                        margin-top: 20px;
                        font-size: 0.9em;
                        color: #666;
                        text-align: center;
                    }}
                    .verification-code {{
                        background-color: #e6ffed;
                        padding: 10px;
                        border-radius: 5px;
                        font-family: monospace;
                        text-align: center;
                        margin: 15px 0;
                        font-weight: bold;
                    }}
                    .button {{
                        display: inline-block;
                        background-color: #28a745;
                        color: white;
                        padding: 10px 20px;
                        text-decoration: none;
                        border-radius: 5px;
                        margin: 10px 0;
                    }}
                    .congrats {{
                        font-size: 1.2em;
                        color: #28a745;
                        font-weight: bold;
                        text-align: center;
                        margin: 15px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2 style="margin:0;">IPIZ - Instituto Politécnico Industrial do Zango</h2>
                </div>
                
                <div class="content">
                    <p>Prezado(a) <strong>{aluno.nome_completo}</strong>,</p>
                    
                    <div class="congrats">
                        🎉 Parabéns! Seu certificado foi emitido com sucesso! 🎉
                    </div>
                    
                    <div class="details">
                        <div class="detail-item">
                            <span class="icon">📜</span>
                            <span><strong>Número do Certificado:</strong> {self.numero_certificado}</span>
                        </div>
                        <div class="detail-item">
                            <span class="icon">📚</span>
                            <span><strong>Curso:</strong> {self.matricula.curso.nome}</span>
                        </div>
                        <div class="detail-item">
                            <span class="icon">📅</span>
                            <span><strong>Data de Emissão:</strong> {self.data_emissao.strftime('%d/%m/%Y')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="icon">🏆</span>
                            <span><strong>Classificação Final:</strong> {self.classificacao_final}</span>
                        </div>
                    </div>
                    
                    <p>Este certificado representa a conclusão bem-sucedida de seu curso no IPIZ. Você pode verificar sua autenticidade a qualquer momento usando:</p>
                    
                    <div class="verification-code">
                        <div style="margin-bottom:5px;">🔒 Código de Verificação:</div>
                        {self.codigo_verificacao}
                    </div>
                    
                    <p style="text-align:center;">
                        <a style="color:#fff;" href="{settings.BASE_URL}/certificados/painel-aluno/" class="button">Acessar Área do Aluno</a>
                    </p>
                    
                    <p>Seu certificado está disponível para download em sua área do aluno, juntamente com o QR Code para verificação.</p>
                    
                    <p style="font-style:italic; text-align:center;">
                        "O conhecimento é a chave para abrir as portas do futuro."
                    </p>
                </div>
                
                <div class="footer">
                    <p>© {timezone.now().year} IPIZ - Instituto Politécnico Industrial do Zango</p>
                    <p>Este é um email automático, por favor não responda.</p>
                </div>
            </body>
            </html>
            """
            
            # Versão alternativa em texto simples
            mensagem_texto = f"""
            Prezado(a) {aluno.nome_completo},

            🎉 Parabéns! Seu certificado foi emitido com sucesso! 🎉

            Detalhes do Certificado:
            - Número: {self.numero_certificado}
            - Curso: {self.matricula.curso.nome}
            - Data de Emissão: {self.data_emissao.strftime('%d/%m/%Y')}
            - Classificação Final: {self.classificacao_final}

            Código de Verificação: {self.codigo_verificacao}

            Este certificado representa a conclusão bem-sucedida de seu curso no IPIZ.

            Acesse sua área do aluno em: {settings.BASE_URL}/certificados/painel-aluno/

            "O conhecimento é a chave para abrir as portas do futuro."

            Atenciosamente,
            Direção Acadêmica
            IPIZ - Instituto Politécnico Industrial do Zango
            """
            
            send_mail(
                assunto,
                mensagem_texto,
                settings.EMAIL_HOST_USER,
                [aluno.email],
                html_message=mensagem_html,
                fail_silently=False,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Falha ao enviar email de certificado: {str(e)}", exc_info=True)
            raise
    # Métodos para notas por extenso
    def get_nota_formatada(self, valor):
        """Formata a nota como inteiro, arredondando corretamente"""
        try:
            valor = Decimal(str(valor)).quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )
            return str(int(valor))
        except:
            return "0"

    def get_nota_extenso(self, valor):
        """Converte a nota arredondada para extenso (apenas inteiros)"""
        try:
            valor = Decimal(str(valor)).quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )
            return num2words(int(valor), lang='pt').upper()
        except:
            return "ZERO"

    # Mantenha os outros métodos como estão, mas agora usarão a versão inteira
    def get_media_formatada(self):
        return self.get_nota_formatada(self.media_curricular)
    
    def get_pap_formatada(self):
        return self.get_nota_formatada(self.prova_aptidao_profissional)
    
    def get_classificacao_formatada(self):
        return self.get_nota_formatada(self.classificacao_final)
    
    def get_media_extenso(self):
        return self.get_nota_extenso(self.media_curricular)
    
    def get_pap_extenso(self):
        return self.get_nota_extenso(self.prova_aptidao_profissional)
    
    def get_classificacao_extenso(self):
        return self.get_nota_extenso(self.classificacao_final)

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
        self.nota_literal = self.converter_para_literal(self.nota_numerica)
        super().save(*args, **kwargs)
        
        if self.certificado:
            self.certificado.save()
    
    @staticmethod
    def converter_para_literal(nota_numerica):
        nota = float(nota_numerica)
        if nota >= 17: return "Muito Bom"
        elif nota >= 14: return "Bom"
        elif nota >= 10: return "Suficiente"
        else: return "Insuficiente"
    
    # Métodos para formatação de notas
    def get_nota_formatada(self):
        """Formata a nota como inteiro"""
        try:
            nota = Decimal(str(self.nota_numerica)).quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )
            return str(int(nota))
        except:
            return "0"

    def get_nota_extenso(self):
        """Converte a nota arredondada para extenso (apenas inteiros)"""
        try:
            nota = Decimal(str(self.nota_numerica)).quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )
            return num2words(int(nota), lang='pt').upper()
        except:
            return "ZERO"

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


class DeclaracaoNotas(models.Model):
    matricula = models.ForeignKey(Matricula, on_delete=models.PROTECT, related_name='declaracoes')
    numero_processo = models.CharField(max_length=20)
    ano_letivo = models.CharField(max_length=9)
    turma = models.CharField(max_length=20, default="TI12AD")
    codigo_verificacao = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    qr_code = models.ImageField(upload_to='qrcodes_declaracoes/', blank=True)
    data_emissao = models.DateField(default=timezone.now)
    emitido_por = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Declaração de Notas'
        verbose_name_plural = 'Declarações de Notas'
        ordering = ['-data_emissao']
    
    def __str__(self):
        return f"Declaração de Notas - {self.matricula.aluno} ({self.ano_letivo})"
    
    def gerar_qr_code(self):
        url = f"{settings.BASE_URL}/certificados/verificar-declaracao/{self.codigo_verificacao}/"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        nome_arquivo = f'declaracao_{self.codigo_verificacao}.png'
        
        self.qr_code.save(nome_arquivo, File(buffer), save=False)
    
    def enviar_email_declaracao(self):
            try:
                aluno = self.matricula.aluno
                assunto = "📄 Sua Declaração de Notas foi Emitida - IPIZ"
                
                # Mensagem HTML formatada
                mensagem_html = f"""
                <html>
                <head>
                    <style>
                        body {{
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            line-height: 1.6;
                            color: #333;
                            max-width: 600px;
                            margin: 0 auto;
                            padding: 20px;
                        }}
                        .header {{
                            background-color: #0056b3;
                            color: white;
                            padding: 15px;
                            text-align: center;
                            border-radius: 5px 5px 0 0;
                        }}
                        .content {{
                            padding: 20px;
                            background-color: #f9f9f9;
                            border-radius: 0 0 5px 5px;
                        }}
                        .details {{
                            background-color: white;
                            border-left: 4px solid #0056b3;
                            padding: 15px;
                            margin: 15px 0;
                        }}
                        .detail-item {{
                            margin-bottom: 10px;
                            display: flex;
                            align-items: center;
                        }}
                        .icon {{
                            margin-right: 10px;
                            color: #0056b3;
                            width: 20px;
                            text-align: center;
                        }}
                        .footer {{
                            margin-top: 20px;
                            font-size: 0.9em;
                            color: #666;
                            text-align: center;
                        }}
                        .verification-code {{
                            background-color: #f0f7ff;
                            padding: 10px;
                            border-radius: 5px;
                            font-family: monospace;
                            text-align: center;
                            margin: 15px 0;
                            font-weight: bold;
                        }}
                        .button {{
                            display: inline-block;
                            background-color: #0056b3;
                            color: white;
                            padding: 10px 20px;
                            text-decoration: none;
                            border-radius: 5px;
                            margin: 10px 0;
                        }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h2 style="margin:0;">IPIZ - Instituto Politécnico Industrial do Zango</h2>
                    </div>
                    
                    <div class="content">
                        <p>Prezado(a) <strong>{aluno.nome_completo}</strong>,</p>
                        
                        <p style="font-size:1.1em;">Sua declaração de notas foi emitida com sucesso! 🎓</p>
                        
                        <div class="details">
                            <div class="detail-item">
                                <span class="icon">📋</span>
                                <span><strong>Número do Processo:</strong> {self.numero_processo}</span>
                            </div>
                            <div class="detail-item">
                                <span class="icon">📅</span>
                                <span><strong>Ano Letivo:</strong> {self.ano_letivo}</span>
                            </div>
                            <div class="detail-item">
                                <span class="icon">👥</span>
                                <span><strong>Turma:</strong> {self.turma}</span>
                            </div>
                            <div class="detail-item">
                                <span class="icon">📆</span>
                                <span><strong>Data de Emissão:</strong> {self.data_emissao.strftime('%d/%m/%Y')}</span>
                            </div>
                        </div>
                        
                        <p>Você pode verificar a autenticidade desta declaração a qualquer momento usando:</p>
                        
                        <div class="verification-code">
                            <div style="margin-bottom:5px;">🔒 Código de Verificação:</div>
                            {self.codigo_verificacao}
                        </div>
                        
                        <p style="text-align:center;">
                            <a style="color:#fff;" href="{settings.BASE_URL}/painel-aluno/" class="button">Acessar Área do Aluno</a>
                        </p>
                        
                        <p>Esta declaração também está disponível para download em sua área do aluno, juntamente com o QR Code para verificação.</p>
                    </div>
                    
                    <div class="footer">
                        <p>© {timezone.now().year} IPIZ - Instituto Politécnico Industrial do Zango</p>
                        <p>Este é um email automático, por favor não responda.</p>
                    </div>
                </body>
                </html>
                """
                
                # Versão alternativa em texto simples
                mensagem_texto = f"""
                Prezado(a) {aluno.nome_completo},

                Sua declaração de notas foi emitida com sucesso!

                Detalhes da Declaração:
                - Número do Processo: {self.numero_processo}
                - Ano Letivo: {self.ano_letivo}
                - Turma: {self.turma}
                - Data de Emissão: {self.data_emissao.strftime('%d/%m/%Y')}
                
                Código de Verificação: {self.codigo_verificacao}

                Acesse sua área do aluno em: {settings.BASE_URL}/certificados/painel-aluno/

                Atenciosamente,
                Secretaria Acadêmica
                IPIZ - Instituto Politécnico Industrial do Zango
                """
                
                send_mail(
                    assunto,
                    mensagem_texto,
                    settings.EMAIL_HOST_USER,
                    [aluno.email],
                    html_message=mensagem_html,
                    fail_silently=False,
                )
            
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Falha ao enviar email de declaração: {str(e)}", exc_info=True)
                raise
    def clean(self):
        super().clean()
        if hasattr(self, 'resultados') and self.resultados.count() > 12:
            raise ValidationError("Uma declaração de notas não pode ter mais de 12 disciplinas.")
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        if not self.numero_processo and hasattr(self, 'matricula'):
            self.numero_processo = self.matricula.numero_matricula
        
        if not self.ano_letivo and hasattr(self, 'matricula'):
            self.ano_letivo = self.matricula.ano_letivo
        
        if not self.qr_code:
            self.gerar_qr_code()
            
        super().save(*args, **kwargs)
            
        # Envia email apenas para novas declarações
        if is_new and hasattr(self, 'matricula') and hasattr(self.matricula, 'aluno'):
            try:
                self.enviar_email_declaracao()
            except Exception as e:
                # Captura qualquer erro no envio de email e registra, mas não interrompe
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Falha ao enviar email de declaração: {str(e)}", exc_info=True)


class ResultadoDeclaracao(models.Model):
    declaracao = models.ForeignKey(DeclaracaoNotas, on_delete=models.CASCADE, related_name='resultados')
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)
    nota_numerica = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )
    
    class Meta:
        unique_together = ('declaracao', 'disciplina')
        ordering = ['disciplina__nome']
        verbose_name = 'Resultado na Declaração'
        verbose_name_plural = 'Resultados na Declaração'
    
    def __str__(self):
        return f"{self.disciplina}: {self.nota_numerica}"
    
    def get_nota_formatada(self):
        """Formata a nota como inteiro (14 valores) como no exemplo"""
        try:
            nota = Decimal(str(self.nota_numerica)).quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )
            return f"({int(nota)})valores"
        except:
            return "(0)valores"
        
        
class PedidoCorrecao(models.Model):
    ESTADOS = (
        ('PENDENTE', 'Pendente'),
        ('APROVADO', 'Aprovado'),
        ('REJEITADO', 'Rejeitado'),
    )
    
    TIPO_DOCUMENTO = (
        ('CERTIFICADO', 'Certificado'),
        ('DECLARACAO', 'Declaração de Notas'),
    )
    
    tipo_documento = models.CharField(max_length=12, choices=TIPO_DOCUMENTO, default='CERTIFICADO')
    certificado = models.ForeignKey(Certificado, on_delete=models.CASCADE, null=True, blank=True, related_name='pedidos_correcao')
    declaracao = models.ForeignKey(DeclaracaoNotas, on_delete=models.CASCADE, null=True, blank=True, related_name='pedidos_correcao')
    solicitado_por = models.ForeignKey(Aluno, on_delete=models.CASCADE)
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
        doc = self.certificado or self.declaracao
        return f"Pedido #{self.id} - {doc} ({self.get_tipo_documento_display()})"
