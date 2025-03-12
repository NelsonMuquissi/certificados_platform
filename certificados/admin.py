from django.contrib import admin
from .models import Usuario, Curso, Certificado, LogValidacao, ConfiguracaoSeguranca

admin.site.register(Usuario, icon='fas fa-user')
admin.site.register(Curso, icon='fas fa-graduation-cap')
admin.site.register(Certificado, icon='fas fa-certificate')
admin.site.register(LogValidacao, icon='fas fa-clipboard-check')
admin.site.register(ConfiguracaoSeguranca, icon='fas fa-shield-alt')
