from django import forms
from django.contrib import admin
from django.db import IntegrityError
from django.utils import timezone
from django.contrib.auth.admin import UserAdmin
from .models import (
    Usuario, Aluno, AreaFormacao, Curso, Disciplina, 
    CursoDisciplina, Matricula, Certificado, ResultadoDisciplina,
    PedidoCorrecao, RegistroAuditoria, ConfiguracaoSistema,ResultadoDeclaracao, DeclaracaoNotas
)

# Formulários devem vir primeiro
class ResultadoDisciplinaForm(forms.ModelForm):
    class Meta:
        model = ResultadoDisciplina
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtra as disciplinas com base no curso do certificado, se existir
        if self.instance and self.instance.certificado_id:
            try:
                certificado = Certificado.objects.get(pk=self.instance.certificado_id)
                if certificado.matricula and certificado.matricula.curso:
                    curso = certificado.matricula.curso
                    # Obtém as disciplinas do curso através do modelo CursoDisciplina
                    disciplinas_ids = CursoDisciplina.objects.filter(
                        curso=curso
                    ).values_list('disciplina_id', flat=True)
                    
                    self.fields['disciplina'].queryset = Disciplina.objects.filter(
                        id__in=disciplinas_ids
                    ).order_by('nome')
            except Certificado.DoesNotExist:
                pass
            
            
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'papel', 'is_staff', 'is_superuser')
    list_filter = ('papel', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informações Pessoais', {'fields': ('first_name', 'last_name', 'email', 'telefone')}),
        ('Permissões', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Papel', {'fields': ('papel',)}),
        ('Datas Importantes', {'fields': ('last_login', 'date_joined')}),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(is_superuser=False)
        return qs

class AlunoAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'numero_identificacao', 'data_nascimento', 'provincia')
    list_filter = ('provincia', 'sexo')
    search_fields = ('nome_completo', 'numero_identificacao')
    readonly_fields = ('foto_preview',)
    
    def foto_preview(self, obj):
        return obj.foto and f'<img src="{obj.foto.url}" style="max-height: 200px;" />'
    foto_preview.allow_tags = True
    foto_preview.short_description = 'Pré-visualização'

class AreaFormacaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo')
    search_fields = ('nome', 'codigo')

class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo', 'categoria')
    search_fields = ('nome', 'codigo', 'categoria')
    list_filter = ('codigo',)

class CursoDisciplinaInline(admin.TabularInline):
    model = CursoDisciplina
    extra = 1
    autocomplete_fields = ['disciplina']

class CursoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo', 'tipo', 'area_formacao', 'duracao_anos')
    list_filter = ('tipo', 'area_formacao')
    search_fields = ('nome', 'codigo')
    inlines = [CursoDisciplinaInline]

class MatriculaAdmin(admin.ModelAdmin):
    list_display = ('numero_matricula', 'aluno', 'curso', 'ano_letivo', 'turno', 'ativo')
    list_filter = ('curso', 'ano_letivo', 'turno', 'ativo')
    search_fields = ('numero_matricula', 'aluno__nome_completo')
    autocomplete_fields = ['aluno', 'curso']

class ResultadoDisciplinaInline(admin.TabularInline):
    model = ResultadoDisciplina
    form = ResultadoDisciplinaForm
    extra = 0  # Não mostrar linhas extras
    readonly_fields = ('nota_literal',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('disciplina')
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        
        # Se estiver criando um novo certificado ou editando um existente
        if obj is not None:
            # Verifica se já existem resultados para este certificado
            existing_disciplinas = obj.resultados_disciplinas.values_list(
                'disciplina_id', flat=True
            )
            
            # Obtém todas as disciplinas do curso que ainda não foram adicionadas
            curso_disciplinas = CursoDisciplina.objects.filter(
                curso=obj.matricula.curso
            ).exclude(
                disciplina_id__in=existing_disciplinas
            ).select_related('disciplina')
            
            # Adiciona automaticamente as disciplinas faltantes
            for curso_disciplina in curso_disciplinas:
                ResultadoDisciplina.objects.create(
                    certificado=obj,
                    disciplina=curso_disciplina.disciplina,
                    nota_numerica=0.00  # Valor padrão
                )
        
        return formset

class CertificadoAdmin(admin.ModelAdmin):
    list_display = ('numero_certificado', 'numero_processo', 'matricula', 'data_emissao', 'classificacao_final', 'ativo')
    list_filter = ('data_emissao', 'ativo', 'matricula__curso')
    search_fields = ('numero_certificado', 'matricula__aluno__nome_completo', 'numero_processo')
    
    readonly_fields = (
        'numero_certificado', 'numero_processo', 'ano_letivo', 
        'media_curricular', 'classificacao_final', 'codigo_verificacao', 
        'livro_registo', 'codigo_qr_preview', 'data_criacao', 'data_atualizacao', 'data_emissao'
    )
    
    autocomplete_fields = ['matricula', 'diretor', 'criado_por']
    inlines = [ResultadoDisciplinaInline]
    
    fieldsets = (
        ('Identificação', {
            'fields': ('numero_certificado', 'matricula', 'numero_processo', 'livro_registo')
        }),
        ('Datas', {
            'fields': ('data_emissao', 'ano_letivo')
        }),
        ('Direção', {
            'fields': ('diretor', 'cargo_de_direção')
        }),
        ('Resultados', {
            'fields': ('media_curricular', 'prova_aptidao_profissional', 'classificacao_final')
        }),
        ('Verificação', {
            'fields': ('codigo_verificacao', 'codigo_qr_preview', 'ativo')
        }),
        ('Metadados', {
            'fields': ('criado_por', 'data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )
    
    def codigo_qr_preview(self, obj):
        if obj.codigo_qr:
            return f'<img src="{obj.codigo_qr.url}" style="max-height: 150px;" />'
        return "Nenhum QR Code gerado"
    codigo_qr_preview.allow_tags = True
    codigo_qr_preview.short_description = 'QR Code'
    
    def get_exclude(self, request, obj=None):
        """Garante que numero_processo não aparece no formulário de adição"""
        excluded = super().get_exclude(request, obj) or []
        if obj is None:  # Durante a criação
            return list(excluded) + ['numero_processo']
        return excluded
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Novo certificado
            obj.criado_por = request.user
            if not obj.prova_aptidao_profissional:
                obj.prova_aptidao_profissional = 0.00
            
            # Garante que o numero_processo é definido antes do primeiro save
            if hasattr(obj, 'matricula'):
                obj.numero_processo = obj.matricula.numero_matricula
        
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            # Fallback para garantir que os campos obrigatórios tenham valores
            if not hasattr(obj, 'media_curricular'):
                obj.media_curricular = 0.00
            if not hasattr(obj, 'classificacao_final'):
                obj.classificacao_final = 0.00
            if not hasattr(obj, 'numero_processo') and hasattr(obj, 'matricula'):
                obj.numero_processo = obj.matricula.numero_matricula
            super().save_model(request, obj, form, change)       
        
class PedidoCorrecaoAdmin(admin.ModelAdmin):
    list_display = ('certificado', 'solicitado_por', 'data_solicitacao', 'estado')
    list_filter = ('estado', 'data_solicitacao')
    search_fields = ('certificado__numero_certificado', 'solicitado_por__username')
    readonly_fields = ('data_solicitacao',)
    autocomplete_fields = ['certificado', 'solicitado_por', 'resolvido_por']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('certificado', 'solicitado_por', 'resolvido_por')
    
    def has_change_permission(self, request, obj=None):
        return request.user.papel in ['ADMIN', 'SECRETARIA']
    
    def save_model(self, request, obj, form, change):
        if obj.estado in ['APROVADO', 'REJEITADO'] and not obj.resolvido_por:
            obj.resolvido_por = request.user
            obj.data_resolucao = timezone.now()
        super().save_model(request, obj, form, change)

class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'accao', 'modelo', 'data_hora')
    list_filter = ('accao', 'modelo', 'data_hora')
    search_fields = ('usuario__username', 'modelo', 'detalhes')
    readonly_fields = ('usuario', 'accao', 'modelo', 'id_objeto', 'detalhes', 'endereco_ip', 'data_hora')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

class ConfiguracaoSistemaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not ConfiguracaoSistema.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False

class ResultadoDeclaracaoInline(admin.TabularInline):
    model = ResultadoDeclaracao
    extra = 0
    autocomplete_fields = ['disciplina']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('disciplina')
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        
        # Se estiver criando uma nova declaração ou editando uma existente
        if obj is not None:
            # Verifica se já existem resultados para esta declaração
            existing_disciplinas = obj.resultados.values_list(
                'disciplina_id', flat=True
            )
            
            # Obtém todas as disciplinas do curso que ainda não foram adicionadas
            curso_disciplinas = CursoDisciplina.objects.filter(
                curso=obj.matricula.curso
            ).exclude(
                disciplina_id__in=existing_disciplinas
            ).select_related('disciplina')
            
            # Adiciona automaticamente as disciplinas faltantes
            for curso_disciplina in curso_disciplinas:
                ResultadoDeclaracao.objects.create(
                    declaracao=obj,
                    disciplina=curso_disciplina.disciplina,
                    nota_numerica=0.00  # Valor padrão
                )
        
        return formset

class DeclaracaoNotasAdmin(admin.ModelAdmin):
    list_display = ('numero_processo', 'matricula', 'ano_letivo', 'turma', 'data_emissao', 'carimbo_oleo')
    list_filter = ('ano_letivo', 'turma', 'carimbo_oleo')
    search_fields = ('numero_processo', 'matricula__aluno__nome_completo')
    
    readonly_fields = (
        'numero_processo', 'ano_letivo', 'codigo_verificacao', 
        'qr_code_preview', 'data_criacao', 'atualizado_em'
    )
    
    autocomplete_fields = ['matricula', 'emitido_por']
    inlines = [ResultadoDeclaracaoInline]
    
    fieldsets = (
        ('Identificação', {
            'fields': ('matricula', 'numero_processo', 'ano_letivo', 'turma')
        }),
        ('Emissão', {
            'fields': ('data_emissao', 'emitido_por', 'carimbo_oleo')
        }),
        ('Verificação', {
            'fields': ('codigo_verificacao', 'qr_code_preview')
        }),
        ('Metadados', {
            'fields': ('data_criacao', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )
    
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return f'<img src="{obj.qr_code.url}" style="max-height: 150px;" />'
        return "Nenhum QR Code gerado"
    qr_code_preview.allow_tags = True
    qr_code_preview.short_description = 'QR Code'
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Nova declaração
            if not obj.numero_processo and hasattr(obj, 'matricula'):
                obj.numero_processo = obj.matricula.numero_matricula
            if not obj.ano_letivo and hasattr(obj, 'matricula'):
                obj.ano_letivo = obj.matricula.ano_letivo
        
        super().save_model(request, obj, form, change)
        
        # Garante que o QR code seja gerado
        if not obj.qr_code:
            obj.gerar_qr_code()
            obj.save()

class ResultadoDeclaracaoAdmin(admin.ModelAdmin):
    list_display = ('declaracao', 'disciplina', 'nota_numerica')
    list_filter = ('disciplina',)
    search_fields = ('declaracao__numero_processo', 'disciplina__nome')
    autocomplete_fields = ['declaracao', 'disciplina']

# Registro dos modelos
admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(Aluno, AlunoAdmin)
admin.site.register(AreaFormacao, AreaFormacaoAdmin)
admin.site.register(Curso, CursoAdmin)
admin.site.register(Disciplina, DisciplinaAdmin)
admin.site.register(Matricula, MatriculaAdmin)
admin.site.register(Certificado, CertificadoAdmin)
admin.site.register(PedidoCorrecao, PedidoCorrecaoAdmin)
admin.site.register(RegistroAuditoria, RegistroAuditoriaAdmin)
admin.site.register(ConfiguracaoSistema, ConfiguracaoSistemaAdmin)
admin.site.register(DeclaracaoNotas, DeclaracaoNotasAdmin)
admin.site.register(ResultadoDeclaracao, ResultadoDeclaracaoAdmin)