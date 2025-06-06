# Generated by Django 5.1.7 on 2025-03-30 22:48

import django.core.validators
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('certificados', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='certificado',
            name='classificacao_final',
            field=models.DecimalField(decimal_places=2, default=0.0, editable=False, max_digits=4, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(20)]),
        ),
        migrations.AlterField(
            model_name='certificado',
            name='data_emissao',
            field=models.DateField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='certificado',
            name='media_curricular',
            field=models.DecimalField(decimal_places=2, default=0.0, editable=False, max_digits=4, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(20)]),
        ),
        migrations.AlterField(
            model_name='certificado',
            name='prova_aptidao_profissional',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=4, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(20)]),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='groups',
            field=models.ManyToManyField(blank=True, help_text='The groups this user belongs to.', related_name='usuario_groups', related_query_name='usuario', to='auth.group', verbose_name='groups'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='user_permissions',
            field=models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='usuario_permissions', related_query_name='usuario', to='auth.permission', verbose_name='user permissions'),
        ),
    ]
