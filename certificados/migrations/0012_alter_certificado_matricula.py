# Generated by Django 5.1.7 on 2025-04-16 10:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('certificados', '0011_disciplina_categoria_alter_curso_tipo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='certificado',
            name='matricula',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='certificado', to='certificados.matricula'),
        ),
    ]
