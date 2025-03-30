from django import forms
from .models import Certificado, PedidoCorrecao

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