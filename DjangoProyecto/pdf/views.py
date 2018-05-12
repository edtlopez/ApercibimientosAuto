from django.shortcuts import render
from .models import *
from .forms import *
from django.http import HttpResponse 
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .PorcesarPdf import ProcesarPdfs
from .GenInforme import *

from django.conf import settings
#from django.utils.encoding import str
from django.template import Template, Context

#from ProcesarApercibimientos import *
import re
import os
import zipfile
from xhtml2pdf import pisa
import shutil
import datetime


## Vista de modificacion de apercibimientos.

@login_required
def ModAper (request):

	if request.method == 'GET':
		c = set()
		for ele in Faltas_Asistencia.objects.filter(Estado="Apercibimiento").values('Curso'):		
			c.add(ele['Curso'])
		return render(request,"ModAper.html",{'curso':c})


	if request.method == 'POST':
		try:
			Curso = request.POST["Curso"]
			Alumno = request.POST["Alumno"]
			c = set()
			for ele in Faltas_Asistencia.objects.filter(Estado="Apercibimiento").values('Curso'):		
				c.add(ele['Curso'])		
			AlumnoApercibimiento = Faltas_Asistencia.objects.filter(Curso=Curso,Alumno=Alumno,Estado="Apercibimiento").values().order_by("Materia")
			AlumnoIgnorado = Faltas_Asistencia.objects.filter(Curso=Curso,Alumno=Alumno,Estado="Ignorado").values().order_by("Materia")
			return render(request,"ModAper.html",{'AperIgnorado':AlumnoIgnorado,'AperAlumno':AlumnoApercibimiento,'curso':c,'Alumno':Alumno})

		except:
			c = set()
			for ele in Faltas_Asistencia.objects.filter(Estado="Apercibimiento").values('Curso'):		
				c.add(ele['Curso'])	
			for DataPost in request.POST:
				if not "csrfmiddlewaretoken" == DataPost:					
					up = Faltas_Asistencia.objects.filter(id=int(DataPost))					
					if up.values()[0]['Estado'] == "Apercibimiento":
						up.update(Estado='Ignorado')						
					elif  up.values()[0]['Estado'] == "Ignorado":
						up.update(Estado='Apercibimiento')					
					Alumno = up.values()[0]['Alumno']
					Curso = up.values()[0]['Curso']			
			AlumnoApercibimiento = Faltas_Asistencia.objects.filter(Curso=Curso,Alumno=Alumno,Estado="Apercibimiento").values().order_by("Materia")
			AlumnoIgnorado = Faltas_Asistencia.objects.filter(Curso=Curso,Alumno=Alumno,Estado="Ignorado").values().order_by("Materia")
			return render(request,"ModAper.html",{'AperIgnorado':AlumnoIgnorado,'AperAlumno':AlumnoApercibimiento,'curso':c,'Alumno':Alumno})
	
			
## Vista principal de las accioes que se pueden realizar.

@login_required
def pdfprin (request):
	Pdf_error_cnt = Faltas_Asistencia.objects.filter(Estado="Error").values().count()
	Pdf_error_fecha = Pdfs.objects.filter(Estado="FechaError").values().count()	
	return render(request,"pdfges.html",{"pdferrorcont":Pdf_error_cnt,'FechaError':Pdf_error_fecha})

# Sube los pdf o los zip
@login_required
def pdfsubir (request):

	if request.method == 'POST':		
		form = PdfForms(request.POST,request.FILES)		
		
		if form.is_valid():	
			a = Pdfs()
			a.NombrePdf = str(datetime.date.today()) + ' PDF - ' + str(Pdfs.objects.all().count()+1)
			a.Estado = 'SinProcesar'
			a.FechaSubida = datetime.date.today()
			a.pdf = request.FILES['pdf']
			a.save()
			descomprimir_zip()
			ProcesarPdfs().start()	
			return HttpResponseRedirect('/')		
	
	form = PdfForms()
	return render(request,'pdfsubir.html',{'form':form})

# Muestra los rejistros con errores para solucionar de manera manual
@login_required
def error (request):

	if request.method == 'GET':

		Mensaje = ''
		Pdf_error_cnt = Faltas_Asistencia.objects.filter(Estado="Error").values().count()
		pdf_error = Faltas_Asistencia.objects.filter(Estado="Error").values()
		PdfErrorFechaCnt = Pdfs.objects.filter(Estado="FechaError").values().count()
		PdfErrorFecha = Pdfs.objects.filter(Estado="FechaError").values()

		if int(PdfErrorFechaCnt) == 0 and int(Pdf_error_cnt) == 0 :
			Mensaje = "No existe mas problemas por solucionar"

		return render(request,"error.html",{'Mensaje':Mensaje,'PdfErrorFecha':PdfErrorFecha,'PdfErrorFechaCnt':PdfErrorFechaCnt,'PdfErrorCnt':Pdf_error_cnt,'pdfs':pdf_error})

	if request.method == 'POST':

		PdfErrorFecha = Pdfs.objects.filter(Estado="FechaError")		
		for ele in PdfErrorFecha.values("pdf"):
			os.remove(ele['pdf'])
		PdfErrorFecha.delete()
		return HttpResponseRedirect('/error')	



# Busca los fichero zip los descomprime y los anade a la tabla pdf sin procesar, despues elimina el zip

def descomprimir_zip ():

	# Limpiando Directorios

	for folder, subfolders, files in os.walk('tmp/'):
				for file in files:
					if file.endswith('.pdf'):
						os.remove('tmp/'+file)

	# descomprimiendo zip

	for folder, subfolders, files in os.walk('pdfs/'):
		for file in files:
			if file.endswith('.zip'):
				comando = 'unzip ' + 'pdfs/' + str(file) + ' -d ' + 'tmp'
				os.system(comando)
				z = Pdfs.objects.filter(pdf='pdfs/'+file)
				z.delete()
				os.system('rm '+'pdfs/'+'\"'+file+'\"')

	# Anadiendo los pdf comprimidos

	for folder, subfolders, files in os.walk('tmp/'):
		for file in files:
			if file.endswith('.pdf'):
				insert = Pdfs()
				insert.NombrePdf = str(datetime.date.today()) + ' PDF - ' + str(Pdfs.objects.all().count()+1)
				insert.Estado = 'SinProcesar'
				insert.pdf = 'pdfs/'+str(file)
				insert.save()
				os.system('cp '+ '\"' +'tmp/'+str(file)+ '\"' + ' pdfs/')
				os.system('rm '+'tmp/'+'\"'+str(file)+'\"')	

## Actualiza los rejistro erroneos con la informacion proporcionada mediante el formulario
@login_required
def erroract (request,pk):

	if request.method == 'POST':		
		form = PdfForms(request.POST,request.FILES)	
		if form.is_valid:	

			__dato2 = str(request.POST['JustifiacdadPorcentaje']).replace(',','.')
			__dato4 = str(request.POST['InjustificadasPorcentaje']).replace(',','.')

			act = Faltas_Asistencia.objects.filter(id=pk)
			act.update(

				JustificadasHoras = int(request.POST['JustificadasHoras'][0:request.POST['JustificadasHoras'].index(':')]),
				JustificadasPorcentaje = float(__dato2.replace('%','')),
				InjustificadasHoras = int(request.POST['InjustificadaHoras'][0:request.POST['InjustificadaHoras'].index(':')]),
				InjustificadasPorcentaje =float(__dato4.replace('%','')),
				Retrasos = 	int(request.POST['Retrasos'][0:request.POST['Retrasos'].index(':')]),
				Estado = "Correcto" )

			BuscarAper()
			return HttpResponseRedirect('/error')

	alumnos = Faltas_Asistencia.objects.filter(id=pk).values()
	form =  Faltas_Asistencia_Actualizar()
	return render(request,"erroract.html",{'form':form,'alumno':alumnos})


def BuscarAper ():
	rejistros = Faltas_Asistencia.objects.filter(Estado="Correcto").values()
	for ele in rejistros :
		if (float(ele['HorasLectivas'])/float(ele['TotalPeriodo'])) <= float(0.2) :
			if float(ele['InjustificadasPorcentaje']) >= float(settings.APER_PORCENTAJE_1SEM) :
				act = Faltas_Asistencia.objects.filter(id=ele['id'])
				act.update(Estado='Apercibimiento')
			else:
				dell = Faltas_Asistencia.objects.filter(id=ele['id'])
				dell.delete()
			
		else :
			if float(ele['InjustificadasPorcentaje']) >= float(settings.APER_PORCENTAJE_MAS_1SEM) :
				act = Faltas_Asistencia.objects.filter(id=ele['id'])
				act.update(Estado='Apercibimiento')
			else:
				dell = Faltas_Asistencia.objects.filter(id=ele['id'])
				dell.delete()

## Esta vista genera los apercibimientos para los alumnos de un curso
@login_required
def InformePorCursos (request):

	a = set()
	m = set()
	c = set()
	for ele in Faltas_Asistencia.objects.filter(Estado="Apercibimiento").values("FechaDesde","FechaHasta","Curso"):
		a.add(ele['FechaDesde'].year)
		m.add(ele['FechaDesde'].month)
		m.add(ele['FechaHasta'].month)
		c.add(ele['Curso'])

	sorted(c)
	sorted(m)
	sorted(a)

	if request.method == 'POST':	

		try:
			Error = Faltas_Asistencia.objects.filter(Estado="Error",Curso=request.POST["Curso"]).values().count()
		except :
			Error = Faltas_Asistencia.objects.filter(Estado="Error").values().count()

		if not int(Error) > 0 :
			In = GenInformeCurso(request)			
			if not In.Fin :			
				return render(request,"apercibimientosmenu.html",{'anos':a,'mes':m,'curso':c,'AperCreado':False,'Mensaje':'No Existe Apercibimientos'})		
	
		else:
			return render(request,"apercibimientosmenu.html",{'anos':a,'mes':m,'curso':c,'AperCreado':False,'Mensaje':'Existen erroes en el curso a procesar, porfavor solucione antes los problemas'})		

		return render(request,"apercibimientosmenu.html",{'anos':a,'mes':m,'curso':c,'AperCreado':True,'Mensaje':''}) 	
		

	if request.method == 'GET':

		ProcesarPdfs().start()
		return render(request,"apercibimientosmenu.html",{'anos':a,'mes':m,'curso':c,'AperCreado':False})

## Paguina informe para profesores.

@login_required
def InformeTodosCursos (request):

	a = set()
	m = set()
	c = set()		
	for ele in Faltas_Asistencia.objects.filter(Estado="Apercibimiento").values():
		a.add(ele['FechaDesde'].year)
		m.add(ele['FechaDesde'].month)
		m.add(ele['FechaHasta'].month)
		c.add(ele['Curso'])	
	
	sorted(c)
	sorted(m)
	sorted(a)

	if request.method == 'POST':
			
		ano = int(request.POST['Ano'])
		mes = int(request.POST['Mes'])
		In = InformeTodosCursosClas(request)
		if len(In.data) == 0 :
			return render(request,"apercibimientosmenutodos.html",{'anos':a,'mes':m,'curso':c,'AperCreado':False,'Mensaje':"No Existe datos procesables"})
		return render(request,"apercibimientosmenutodos.html",{'anos':a,'mes':m,'curso':c,'AperCreado':True,'Mensaje':""})	

	if request.method == 'GET':	

		ProcesarPdfs().start()	
		return render(request,"apercibimientosmenutodos.html",{'anos':a,'mes':m,'curso':c,'AperCreado':False})

from rest_framework import viewsets
from rest_framework.decorators import action


def AperPorMaterias (request):

	a = set()
	m = set()
	c = set()
	for ele in Faltas_Asistencia.objects.filter(Estado="Apercibimiento").values('FechaDesde','FechaHasta','Curso'):
		a.add(ele['FechaDesde'].year)
		m.add(ele['FechaDesde'].month)
		m.add(ele['FechaHasta'].month)
		c.add(ele['Curso'])

	sorted(m)
	sorted(a)
	sorted(c)
	
	if request.method == 'GET':
		ProcesarPdfs().start()
		return render(request,"MenuAperMes.html", {'anos':a,'mes':m,'curso':c})
	
	if request.method == 'POST':
		Gen = InformePorMaterias(request)	
		try:
			if not Gen.InformeGen:
				return render(request,"MenuAperMes.html", {'curso':c,'anos':a,'mes':m,'AperCreado':False,'Mensaje':"No Existe datos procesables"})
			else:
				return render(request,"MenuAperMes.html", {'curso':c,'anos':a,'mes':m,'AperCreado':True})

		except AttributeError :
			return render(request,"MenuAperMes.html", {'curso':c,'anos':a,'mes':m,'AperCreado':False,'Mensaje':"No Existe datos procesables"})


def AcercaDe (request):
	return render(request,"acercade.html",{'version':str(settings.VERSION)})



# Vista Api
class FlatasApi (viewsets.ModelViewSet):
	queryset = Faltas_Asistencia.objects.filter(Estado='Apercibimiento')
	serializer_class = SerializerFaltasAsistencia


class PdfsApi (viewsets.ModelViewSet):
	queryset = Pdfs.objects.all()
	serializer_class = PdfsSerializer

	


	

