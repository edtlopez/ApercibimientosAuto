# -*- coding: utf-8 -*-
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth.decorators import login_required, permission_required
from .views import *
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.conf.urls.static import static
from django.conf import settings

# Rest Api
from rest_framework import routers, serializers, viewsets
router = routers.DefaultRouter()
router.register(r'FaltasAsistencia', FlatasApi)
router.register(r'Pdfs', PdfsApi)



urlpatterns = [
 
	url(r'^$', pdfprin ,name='inicio'),
	url(r'^subirpdf/$', pdfsubir ,name='subir'),
	#url(r'^porcesarpdf/$', procesar ,name='procesar'),
	url(r'^error/$', error ,name='error'),
	url(r'^error/actualizar/(?P<pk>\d+)/$', erroract ,name='erroract'),
	url(r'^geninformesCurso/$', InformePorCursos ,name='Apercibimientos'),
	url(r'^geninformesTrimestral/$', InformeTodosCursos ,name='ApercibimientosTodos'),
	url(r'^ApercibimientosPorMaterias/$', AperPorMaterias ,name='ApercibimientosPorMaterias'),
	url(r'^ModificarAper/$', ModAper ,name='ModAper'),
	url(r'^apirest/', include(router.urls)),
    url(r'^apirest/', include('rest_framework.urls', namespace='rest_framework'))
]
