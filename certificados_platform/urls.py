from django.contrib import admin
from django.urls import path, include
from certificados import views
from django.conf.urls.static import static
from django.conf import settings
from certificados.views import Erro

urlpatterns = [
    path('', views.home, name = 'home'),
    path('admin/', admin.site.urls),
    path('certificados/', include('certificados.urls')),
]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = Erro

