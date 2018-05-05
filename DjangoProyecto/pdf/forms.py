# -*- coding: utf-8 -*-

from django import forms
from .models import *

class PdfForms (forms.Form):
	pdf = forms.FileField(label="")

class Faltas_Asistencia_Actualizar (forms.Form):

	JustificadasHoras = forms.DateTimeField(label="Hosras Justificadas")
	JustifiacdadPorcentaje = forms.CharField(label="Horas Justificadas Porcentaje")
	InjustificadaHoras = forms.DateTimeField(label="Horas Injustificadas")
	InjustificadasPorcentaje = forms.CharField(label="Horas Injustificadas Porcentaje")
	Retrasos = forms.DateTimeField(label="Retrasos")


	
	