from django import forms
from django.contrib import admin
from django.db import models
from .models import Certificado, PedidoCorrecao, ResultadoDisciplina, CursoDisciplina, Disciplina

class FormularioCertificado(forms.ModelForm):
    class Meta:
        model = Certificado
        fields = '__all__'
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}),
            'data_emissao': forms.DateInput(attrs={'type': 'date'}),
            'data_emissao_identificacao': forms.DateInput(attrs={'type': 'date'}),
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }

class FormularioPedidoCorrecao(forms.ModelForm):
    class Meta:
        model = PedidoCorrecao
        fields = ['certificado', 'descricao']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Descreva detalhadamente a correção necessária'}),
        }
        
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