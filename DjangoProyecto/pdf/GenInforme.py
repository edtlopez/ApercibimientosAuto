# -*- coding: utf-8 -*-
import re
import commands
import os
from .models import *
from django.shortcuts import render
from xhtml2pdf import pisa
import zipfile



class GenInformeCurso :
		
	def __init__ (self,ano,mes,curso,request):

		self.ano = ano
		self.mes = mes
		self.curso = curso
		self.request = request
		self.AperCurso = Faltas_Asistencia.objects.filter(Curso=self.curso,Estado="Apercibimiento").values()
		self.__GenCursoEscolar()
		self.__AperMesCurso()
		self.__ApercebimientosCursoEscolar()
		self.__AlumnosMesCurso()
		
		if not len(self.Alumnos) == 0 :
			
			self.__CreandoDatosInformePorCurso()
			self.__EliminandoInformesAntguos()
			self.__RenderizandoHtml()
			self.__CreandoPDFAgrupado()
			self.__ComprimiendoInformes()

	def __CreandoPDFAgrupado(self):

		os.system( "pdftk tmp/*.pdf cat output tmp/PdfAgrupado.pdf" )

	def __GenCursoEscolar (self):	
		self.CursoEscolar = []
		if self.mes <= 9 :
			for r in range(1,self.mes+1):
				self.CursoEscolar.append([r,self.ano])
			for r in range(9,13):
				self.CursoEscolar.append([r,self.ano-1])
		else:
			for r in range(9,self.mes+1):
				self.CursoEscolar.append([r,self.ano])
	

	def __AperMesCurso (self):

		self.AperMesCurso = []
		for aper in self.AperCurso:
			if aper['FechaDesde'].year == self.ano and aper['FechaDesde'].month == self.mes :
				self.AperMesCurso.append([aper])
		

	def __AlumnosMesCurso (self):
		self.Alumnos= set()
		for aper in self.AperMesCurso:
			self.Alumnos.add(aper[0]['Alumno'])

		

	def __ApercebimientosCursoEscolar(self):

		self.AperCursoEscolar = []
		for aper in self.AperCurso:
			for cur in self.CursoEscolar:
				if aper['FechaDesde'].year == cur[1] and aper['FechaDesde'].month == cur[0] :
					self.AperCursoEscolar.append(aper)

	def __ContandoAper (self,alumno,materia):
		__cont = 0
		for aper in self.AperCursoEscolar:
			if aper['Alumno'] == alumno and aper['Materia'] == materia :
				__cont += 1
		return __cont 


	def __CreandoDatosInformePorCurso (self):

		datos = []
		self.aper = []
		for alu in self.Alumnos:
			datos = []
			for aper in self.AperMesCurso:
				if aper[0]['Alumno'] == alu :
					datos.append({'Materia':aper[0]['Materia'],'NumAper':self.__ContandoAper(aper[0]['Alumno'],aper[0]['Materia']),'InjuHoras':aper[0]['InjustificadasHoras'],'InjuPorcen':aper[0]['InjustificadasPorcentaje']})
			self.aper.append({'Alumno':alu,'anos':self.ano,'mes':self.mes,'curso':self.curso,'aper': datos})


	def __EliminandoInformesAntguos (self):

		for folder, subfolders, files in os.walk('tmp/'):
				for file in files:
					if file.endswith('.pdf'):
						os.remove('tmp/'+file)

	def __CrearPDF(self,ren,alumno):
	
		# Generando documentos html por Alumno	
		html = ''
		cont = 0
		for linea in str(ren):
			if not cont < 38:
				html = html + linea
			cont = cont + 1

		# Generando PDF
		salida = open('tmp/'+ alumno +'.pdf','w+b')
		pisa_status = pisa.CreatePDF(str(html),dest=salida)
		salida.close()		

	def __RenderizandoHtml(self):

		meses = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',
		6:'Junio',7:'Julio',8:'Agosto',9:'Septiembre',
		10:'Octubre',11:'Noviembre',12:'Diciembre'}

		for infor in self.aper:
			ren = render(self.request,'informe.html',{'aper':infor['aper'],'Alumno':infor['Alumno'],'anos':self.ano,'mes':meses[self.mes],'curso':self.curso})
			self.__CrearPDF(ren,infor["Alumno"])


	def __ComprimiendoInformes (self):

		fantasy_zip = zipfile.ZipFile('pdf/static/report.zip', 'w') 
		for folder, subfolders, files in os.walk('tmp/'): 
			for file in files:
				if file.endswith('.pdf'):
					fantasy_zip.write(os.path.join(folder, file), file, compress_type = zipfile.ZIP_DEFLATED)
		fantasy_zip.close()
	
	

class InformeTodosCursosClas :
	def __init__ (self,request):

		self.ano =  int(request.POST['Ano'])
		self.mes =  int(request.POST['Mes'])

		try:
			self.curso =  request.POST['Curso']
		except:
			self.curso = ""
		try:
			self.NumAper = int(request.POST['NumAper'])
		except:
			self.NumAper = 2

		self.TipoInforme = request.POST['TipoInforme']
		self.Aper = []
		self.request = request
		self.__GenCursoEscolar()

		for fecha in self.CursoEscolar:

			if self.TipoInforme == "Completo":
				__datos = Faltas_Asistencia.objects.filter(FechaDesde__year = fecha[1],FechaDesde__month = fecha[0],Estado="Apercibimiento",).order_by('Curso').values()
				self.Aper.append(__datos)
				
			elif self.TipoInforme == "Individual":
				__datos = Faltas_Asistencia.objects.filter(Curso=self.curso,FechaDesde__year = fecha[1],FechaDesde__month = fecha[0],Estado="Apercibimiento",).order_by('Curso').values()
				self.Aper.append(__datos)

		if not len(self.Aper) == 0:
			__select = []
			for ele in self.Aper:
				for ala in ele :
					__select.append(ala)
						
			self.Aper = __select
			self.__Cursos()
			self.__GenDataPdf()
			self.__RenderizandoHtml()
	
	def __CrearPDF(self,ren):
	
		# Generando documentos html por Alumno	
		html = ''
		cont = 0
		for linea in str(ren):
			if not cont < 38:
				html = html + linea
			cont = cont + 1

		# Generando PDF
		salida = open('pdf/static/'+ 'InformeTodosLosCursos' +'.pdf','w+b')
		pisa_status = pisa.CreatePDF(str(html),dest=salida)
		salida.close()		

	def __RenderizandoHtml(self):

		meses = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',
		6:'Junio',7:'Julio',8:'Agosto',9:'Septiembre',
		10:'Octubre',11:'Noviembre',12:'Diciembre'}

		ren = render(self.request,'InformeTodosLosCursos.html',{'NumAper':self.NumAper,'Data':self.data,'Ano':self.ano,'Mes':meses[self.mes]})
		self.__CrearPDF(ren)


	def __BuscandoMateriasApercebidas(self,alumno,curso):

		__salida = set()
		for aper in self.Aper:
			if aper['Curso'] == curso and aper['Alumno'] == alumno:
				__salida.add(aper['Materia'])
		return __salida

	def __ContandoAper (self,alumno,materia,curso):

		__cont = 0
		for aper in self.Aper:
			if aper['Alumno'] == alumno and aper['Materia'] == materia and aper['Curso'] == curso :
				__cont += 1
		
		return __cont

	def __GenDataPdf (self):
		
		self.data = []
		for curso in self.AperCursos:
			for alumno in self.__AlumnosDelCurso(curso):
				for materia in self.__BuscandoMateriasApercebidas(alumno,curso):
					__numaper = self.__ContandoAper(alumno,materia,curso)
					if int(__numaper) >= self.NumAper :
						self.data.append({'Alumno':alumno,'Curso':curso,'Materia':materia,'numaper': str(__numaper) })		

	def __AlumnosDelCurso (self,curso):

		__salida = set()
		for aper in self.Aper:
			if aper['Curso'] == curso :
				__salida.add(aper['Alumno'])
		return __salida

	def __Cursos (self):

		self.AperCursos = set()
		for ele in self.Aper:
			self.AperCursos.add(ele['Curso'])

	def __GenCursoEscolar (self):

		self.CursoEscolar = []
		if self.mes <= 9 :
			for r in range(1,self.mes+1):
				self.CursoEscolar.append([r,self.ano])
			for r in range(9,13):
				self.CursoEscolar.append([r,self.ano-1])
		else:
			for r in range(9,self.mes+1):
				self.CursoEscolar.append([r,self.ano])
		sorted(self.CursoEscolar)
		

class InformePorMaterias :

	def __init__ (self,request):
	
		self.mes = int(request.POST["Mes"])
		self.ano = int(request.POST["Ano"])
		self.Cursos = set()
		self.request = request		

		# Metodos a Ejecutar.

		self.__GenCursoEscolar()
		self.__CursosSearch()
		self.__EliminandoInformesAntguos()
		
		# Separando Por cursos


		for Cur in self.Cursos:
			self.Materia = set()
			self.__MateriasSearch(Cur)
			self.DatosMaterias = {}

			## Creando los datos para cada materia

			for Mate in self.Materia:
				self.__SelectDatabaseMateria(Mate,Cur)
				self.__AlumnosSearch()
				self.__CreateDataHtmlMateria()
		
		# Generando las tablas con los apercibimirntos de los alumnos por materia.

			self.__RenderizandoHtmlMarerias()	
			self.__RenderCabecera(Cur)
			self.__JuntarCabeceraTrablas()
			self.__CrearPDF(Cur)

		# Agrupando y comprimiendo los pdf

		self.__CreandoPDFAgrupado()
		self.__ComprimiendoInformes()

		
	def __JuntarCabeceraTrablas (self):

		for tabla in self.HtmlTablas:

			html = ''
			cont = 0
			for linea in str(tabla):
				if not cont < 38:
					html = html + linea
				cont = cont + 1

			self.HtmlCabezera += str(html)
		self.HtmlCabezera += "</body></html>" 

	def __RenderCabecera (self,Cur):	

		meses = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',
		6:'Junio',7:'Julio',8:'Agosto',9:'Septiembre',
		10:'Octubre',11:'Noviembre',12:'Diciembre'}
		
		self.HtmlCabezera = str(render(self.request,'InformePorMaterias.html',{'Curso':Cur,'Mes':meses[self.mes],'Ano':self.ano}))

	def __RenderizandoHtmlMarerias (self):
		
		self.HtmlTablas = []
		for DatosMate in self.DatosMaterias:
			ren = render(self.request,'materias.html',{'data':self.DatosMaterias[DatosMate],'Materia':DatosMate})
			self.HtmlTablas.append(ren)

	def __CursosSearch (self):
	
		for fecha in self.CursoEscolar:
			__select = Faltas_Asistencia.objects.filter(FechaDesde__year = fecha[1],FechaDesde__month = fecha[0],Estado="Apercibimiento").values('Curso')
			for ele in __select :
				self.Cursos.add(ele['Curso'])
	
	
	def __MateriasSearch (self,Curso):

		for fecha in self.CursoEscolar:
			__select = Faltas_Asistencia.objects.filter(Curso=Curso,FechaDesde__year = fecha[1],FechaDesde__month = fecha[0],Estado="Apercibimiento").values('Materia')
			for ele in __select :
				self.Materia.add(ele['Materia'])
		
	def __CrearPDF(self,Curso):
		
		# Generando documentos html por Alumno	
		html = ''
		cont = 0
		for linea in self.HtmlCabezera:
			if not cont < 38:
				html = html + linea
			cont = cont + 1

		# Generando PDF
		salida = open('tmp/'+ Curso +'.pdf','w+b')
		pisa_status = pisa.CreatePDF(str(html),dest=salida)
		salida.close()		
	
	def __CreateDataHtmlMateria (self):
		
		for MA in self.Materia:
			self.DatosMaterias[MA] = []
			for AL in self.Alumnos: 
				self.DatosMaterias[MA].append({'Alumnos':AL,'NumAper':self.__ContarAper(AL,MA)})


	def __ContarAper (self,Alumno,Materia):
		
		__cont = 0
		for ele in self.DataBase:
			if ele['Alumno'] == Alumno : 
				__cont += 1
		return int(__cont)

	def __SelectDatabaseMateria(self,Materia,Curso):

		self.DataBase = []
		for fecha in self.CursoEscolar:
			__select = Faltas_Asistencia.objects.filter(Curso=Curso,Materia=Materia,FechaDesde__year = fecha[1],FechaDesde__month = fecha[0],Estado="Apercibimiento").values()
			try:
				self.DataBase.append(__select[0])
			except IndexError :
				pass	
	
	def __AlumnosSearch (self):

		self.Alumnos = set()
		for ele in self.DataBase :
			self.Alumnos.add(ele["Alumno"])
	
	def __GenCursoEscolar (self):

		self.CursoEscolar = []
		if self.mes <= 9 :
			for r in range(1,self.mes+1):
				self.CursoEscolar.append([r,self.ano])
			for r in range(9,13):
				self.CursoEscolar.append([r,self.ano-1])
		else:
			for r in range(9,self.mes+1):
				self.CursoEscolar.append([r,self.ano])
		sorted(self.CursoEscolar)
						

	def __EliminandoInformesAntguos (self):

		for folder, subfolders, files in os.walk('tmp/'):
				for file in files:
					if file.endswith('.pdf'):
						os.remove('tmp/'+file)

		try:
			os.remove('pdf/static/report.zip')
		except OSError :
			pass
		
	def __ComprimiendoInformes (self):

		fantasy_zip = zipfile.ZipFile('pdf/static/report.zip', 'w') 
		for folder, subfolders, files in os.walk('tmp/'): 
			for file in files:
				if file.endswith('.pdf'):
					fantasy_zip.write(os.path.join(folder, file), file, compress_type = zipfile.ZIP_DEFLATED)
		fantasy_zip.close()	

	def __CreandoPDFAgrupado(self):

		os.system( "pdftk tmp/*.pdf cat output tmp/InformeMateriasAgrupado.pdf" )

	
