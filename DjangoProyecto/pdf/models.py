# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from rest_framework import serializers


class Pdfs (models.Model):

	NombrePdf = models.CharField(max_length=50)
	Estado = models.CharField(max_length=50)
	FechaSubida = models.DateField(auto_now_add=True,blank=True)
	FechaProces = models.DateField(auto_now_add=False,null=True,blank=True)
	pdf =  models.FileField(upload_to='pdfs')

	def __str__ (self):
		return  self.NombrePdf 

	class Meta:
		ordering = ["NombrePdf"]
		verbose_name_plural = "Pdfs"

class Faltas_Asistencia (models.Model):

	Alumno = models.CharField(max_length=50)  
	Curso = models.CharField(max_length=50)
	Unidad = models.CharField(max_length=100)
	Materia = models.CharField(max_length=100)
	FechaDesde = models.DateField(auto_now_add=False,blank=True)
	FechaHasta = models.DateField(auto_now_add=False,blank=True)
	TotalPeriodo = models.IntegerField(blank=True,null=True)
	HorasLectivas = models.IntegerField(blank=True,null=True)
	JustificadasHoras = models.IntegerField(blank=True,null=True)
	JustificadasPorcentaje = models.FloatField(blank=True,null=True)
	InjustificadasHoras = models.IntegerField(blank=True,null=True)
	InjustificadasPorcentaje = models.FloatField(blank=True,null=True)
	Retrasos = models.IntegerField(blank=True,null=True)
	Estado = models.CharField(max_length=50)

	def __str__ (self):
		return  self.Alumno + ' , ' + self.Curso + ' , ' + self.Materia + ' , ' + str(self.InjustificadasPorcentaje)

	def __unicode__(self):
		return u'Proposal for: %s' % self.id
	
	class Meta:
		ordering = ["Alumno"]
		verbose_name_plural = "Falta_Asistencia"

# Modelo Api para Faltas de Asistencia
class SerializerFaltasAsistencia (serializers.ModelSerializer):
	class Meta:
		model = Faltas_Asistencia
		fields = "__all__"


class PdfsSerializer (serializers.ModelSerializer):
	class Meta:
		model = Pdfs
		fields = "__all__"
