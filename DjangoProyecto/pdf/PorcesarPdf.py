# -*- coding: utf-8 -*-

import os ,sys
import commands
import re
import datetime
import locale
import logging
from .models import *
from django.utils.encoding import *
import PyPDF2
import threading

#from django.utils.encoding import smal_str 	
class ProcesarPdfs (threading.Thread) :

	def __init__(self): 
		threading.Thread.__init__(self)
	
	def run (self):

		

		pdf = Pdfs.objects.filter(Estado='SinProcesar').values('pdf','id')	
		PdfCount = pdf.count()
		__cont = 0

		for ele in pdf:

		

			# Variables 

			self.datos = {}
			self.lista_pdfto = []
			self.lista_pdf2 = []
			self.total_dias = []
			self.fechas = []
			self.horas_lectivas = []
			self.insert_pdfto = []
			self.insert_pdf2 = []
			self.insert_validado = set()
			self.ano_academico = 0
			self.unidad = ''
			self.curso = ''
			self.error = False
			self.alumnos = []
			self.APRENDIZAJE = True
			self.error_creainsert = {}

			# Lineas a excluir del documento pasado a texto

			self.exclusiones = set([

			'',
			'\n'
			'* El porcentaje se calcula respecto al total de horas lectivas del periodo seleccionado.',
			'Retrasos',
			'Horas',
			'Fecha hasta:',
			'Fecha desde:',
			'Faltas Justificadas',
			'Faltas No Justificadas',
			'Alumno',
			'Retrasos',
			'%*',
			'r',
			'ó',
			'CONSEJERÍA DE EDUCACIÓN',
			'ESTADÍSTICAS DE ABSENTISMO POR MATERIAS EN UN PERIODO',
			'ESTAD\xc3\x8dSTICAS DE ABSENTISMO POR MATERIAS EN UN PERIODO',
			'I.E.S. Fernando Aguilar Quignon',
			'Año académico:',
			'Curso:',
			'Unidad:',
			'\x0cr',
			'\x0cESTAD\xc3\x8dSTICAS DE ABSENTISMO POR MATERIAS EN UN PERIODO',
			'\x0cCONSEJER\xc3\x8dA DE EDUCACI\xc3\x93N',
			'NO HAY FALTAS PARA ESTA MATERIA',
			'Fecha',
			'hasta:',
			'* El porcentaje se calcula respecto al total de horas lectivas del periodo seleccionado.'
			't',
			'O',
			':'

			])

			# Expresiones usadas para eliminar lineas de texto

			self.expresiones = set([

				'Ref.Doc.: *',
				'Cód.Centro: *',
				'Fecha hasta: [0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]',
				'C\xc3\xb3d.Centro: *',
				'A\xc3\xb1o acad\xc3\xa9mico: [0-9][0-9][0-9][0-9]',
				'\* El porcentaje se calcula respecto al total de horas lectivas del periodo seleccionado.'
				

				])			
				
			# Metedos a ejecutar
						
			self.dc =  ele['pdf']
			self.dcid = ele['id']
			self.__PdftxtGen_pdfto()
			self.__PdftxtGen_pdf2()					
			self.__read_document()
			self.__clean_list()
			
			self.__search_Num_Pag()
			self.__search_materias()
			self.__search_materias_pdf2()
			self.__search_total_dias()
			self.__search_fechas_ini_fin()

			if self.__ComprobandoFechasPdf():

				self.__search_horas_lectivas()
				self.__search_curso_unidad_ano()
				self.__buscando_alumnos()
				
				# Script Antiguo

				self.tablas = self.__tablas()
				self.__limpieza_tablas()
				self.alumnos_por_tabla = self.__alumnos_por_tabla()
				self.tablas_datos_dispersos = self.__tablas_dispersion()
				self.pos_datos_dispersos = self.__pos_de_datos_dispersos()
				self.__procesando_tablas_dispersas()
				self.__sacando_faltas_por_alumnos()

				# Sacando informacion con el programa nuevo


				self.__poblando_insert_pdfto()
			#	self.__chequeando_datos_insert()
				self.__insertando_datos_bd()

				# Limpieza
				
				self.__pdf_eliminar_pdf_procesado()
				self.__limpieza_temporales()

				self.__MarcarApercibimientos()

			else:
				self.__MarcarPdfErrorFecha()
			
			__cont += 1

	def __MarcarPdfErrorFecha(self):

		__upda = Pdfs.objects.filter(id=self.dcid)
		__upda.update(Estado="FechaError")
		
	def __ComprobandoFechasPdf (self):

		__salida = False
		if self.fechas[0].year == self.fechas[1].year and self.fechas[0].month == self.fechas[1].month:
			__salida = True
		return __salida


	def __chequeando_datos_insert (self):

		pass


	def __pdf_eliminar_pdf_procesado(self):

		procesado = Pdfs.objects.filter(pdf=str(self.dc))
		procesado.delete()
		os.system('rm '+ '\"'+str(self.dc)+'\"')


	def __limpieza_temporales(self):

		os.remove(self.pdftotext[1:-1])
		os.remove(self.pdf2txt[1:-1])						

	def __error (self) :

		error = Pdfs.objects.filter(pdf=self.dc)
		error.update(Estado="Error")


	def __insertando_datos_bd (self):

		
		for pdf2 in self.insert_pdf2:

			__dato2 = str(pdf2[0]['JustificadasPorcentaje']).replace(',','.')
			__dato4 = str(pdf2[0]['InjustificadasPorcentaje']).replace(',','.')
			
			try:

				insert = Faltas_Asistencia.objects.get(

					Alumno =  pdf2[0]['Alumno'],
					Curso = pdf2[0]['Curso'],
					Unidad = pdf2[0]['Unidad'],
					Materia = pdf2[0]['Materia'][9:],
					FechaDesde = pdf2[0]['FechaDesde'],
					FechaHasta = pdf2[0]['FechaHasta']
					

				)

				
			except:

				try:

					insert = Faltas_Asistencia(

						Alumno =  pdf2[0]['Alumno'],
						Curso = pdf2[0]['Curso'],
						Unidad = pdf2[0]['Unidad'],
						Materia = pdf2[0]['Materia'][9:],
						FechaDesde = pdf2[0]['FechaDesde'],
						FechaHasta = pdf2[0]['FechaHasta'],
						TotalPeriodo = pdf2[0]['TotalPeriodo'],
						HorasLectivas = pdf2[0]['HorasLectivas'][0:pdf2[0]['HorasLectivas'].index(':')],

						JustificadasHoras = pdf2[0]['JustificadasHoras'][0:pdf2[0]['JustificadasHoras'].index(':')],
						JustificadasPorcentaje = float(__dato2.replace('%','')),
						InjustificadasHoras = pdf2[0]['InjustificadasHoras'][0:pdf2[0]['InjustificadasHoras'].index(':')],
						InjustificadasPorcentaje = float(__dato4.replace('%','')),
						Retrasos = pdf2[0]['Retrasos'][0:pdf2[0]['Retrasos'].index(':')]

					)

					insert.Estado = 'Correcto'
					insert.save()

					

				except:

					try:
											

						for pdfto in self.insert_pdfto:
							if pdfto[0]['Alumno'] == pdf2[0]['Alumno'] and pdfto[0]['Materia'] == pdf2[0]['Materia']:

								__dato2 = str(pdfto[0]['JustificadasPorcentaje']).replace(',','.')
								__dato4 = str(pdfto[0]['InjustificadasPorcentaje']).replace(',','.')

								insert = Faltas_Asistencia(

									Alumno =  pdfto[0]['Alumno'],
									Curso = pdfto[0]['Curso'],
									Unidad = pdfto[0]['Unidad'],
									Materia = pdfto[0]['Materia'][9:],
									FechaDesde = pdfto[0]['FechaDesde'],
									FechaHasta = pdfto[0]['FechaHasta'],
									TotalPeriodo = pdfto[0]['TotalPeriodo'],
									HorasLectivas = pdfto[0]['HorasLectivas'][0:pdfto[0]['HorasLectivas'].index(':')],

									JustificadasHoras = pdfto[0]['JustificadasHoras'][0:pdfto[0]['JustificadasHoras'].index(':')],
									JustificadasPorcentaje = float(__dato2.replace('%','')),
									InjustificadasHoras = pdfto[0]['InjustificadasHoras'][0:pdfto[0]['InjustificadasHoras'].index(':')],
									InjustificadasPorcentaje = float(__dato4.replace('%','')),
									Retrasos = pdfto[0]['Retrasos'][0:pdfto[0]['Retrasos'].index(':')]

								)

								insert.Estado = 'Correcto'
								insert.save()


					except:

						insert = Faltas_Asistencia(

									Alumno =  pdfto[0]['Alumno'],
									Curso = pdfto[0]['Curso'],
									Unidad = pdfto[0]['Unidad'],
									Materia = pdfto[0]['Materia'][9:],
									FechaDesde = pdfto[0]['FechaDesde'],
									FechaHasta = pdfto[0]['FechaHasta'],
									TotalPeriodo = pdfto[0]['TotalPeriodo'],
									HorasLectivas = pdfto[0]['HorasLectivas'][0:pdfto[0]['HorasLectivas'].index(':')],								
									Estado = "Error"
								#	pdf = Pdfs.objects.get(pdf=str(self.dc))						

							)		

						insert.save()




	def __poblando_insert_pdfto (self) :

		__pos = 0
		for linea in self.lista_pdfto:			
			
			if linea in self.materias:
				__mate = linea				
			
			if linea in self.alumnos :

				for hl in self.horas_lectivas:
					if hl[0]['Materia'] == __mate :
						__horas_lectivas = hl[0]['Horas']

				for td in self.total_dias:
					if td[0]['Materia'] == __mate :
						__total_dias = td[0]['Dias']
										
				try:
					
					self.insert_pdfto.append([{

						'Alumno': linea,
						'Curso' : self.curso,
						'Unidad' : self.unidad,
						'Materia' : __mate,
						'FechaDesde' : self.fechas[0],
						'FechaHasta' : self.fechas[1],
						'TotalPeriodo' : __total_dias,
						'HorasLectivas' :  __horas_lectivas,
						'JustificadasHoras' : self.lista_pdfto[__pos+1],
						'JustificadasPorcentaje' : self.lista_pdfto[__pos+2],
						'InjustificadasHoras' : self.lista_pdfto[__pos+3],
						'InjustificadasPorcentaje' : self.lista_pdfto[__pos+4],
						'Retrasos' : self.lista_pdfto[__pos+5] 

					}])
				
				except:

					self.insert_pdfto.append([{

						'Alumno': linea,
						'Curso' : self.curso,
						'Unidad' : self.unidad,
						'Materia' : __mate,
						'FechaDesde' : self.fechas[0],
						'FechaHasta' : self.fechas[1],
						'TotalPeriodo' : __total_dias,
						'HorasLectivas' :  __horas_lectivas,
						'JustificadasHoras' : self.lista_pdfto[__pos-5],
						'JustificadasPorcentaje' : self.lista_pdfto[__pos-4],
						'InjustificadasHoras' : self.lista_pdfto[__pos-3],
						'InjustificadasPorcentaje' : self.lista_pdfto[__pos-2],
						'Retrasos' : self.lista_pdfto[__pos-1] 
					}])
					
			
			__pos = __pos + 1	


	def __search_curso_unidad_ano (self):

		
		self.curso = self.lista_pdf2[2]
		self.unidad = self.lista_pdf2[1]
		self.ano_academico = self.lista_pdf2[0]
		self.exclusiones.add(str(self.curso))
		self.exclusiones.add(str(self.unidad))
		self.exclusiones.add(str(self.ano_academico))
		self.__clean_list()

		
	def __search_ano_academico (self):

		for linea in self.lista_pdf2:

			march = re.search('[0-9][0-9][0-9][0-9]',linea)

			if march:
				self.ano_academico = linea
				self.exclusiones.add(linea)
				self.__clean_list()
				break


	def __search_horas_lectivas (self):

		for linea in self.lista_pdf2:
			if linea in self.materias:
				__mate = linea

			march = re.search('Horas lectivas: *',linea)
			if march:
				self.horas_lectivas.append([{'Horas':linea[-5:],'Materia':__mate}])
				self.exclusiones.add(linea)

		self.__clean_list()


	def __search_total_dias (self):

		for linea in self.lista_pdf2:
			if linea in self.materias:
				__mate = linea

			march = re.search('Total días *',linea)
			if march:
				self.total_dias.append([{'Dias':linea[-2:],'Materia':__mate}])
				self.exclusiones.add(linea)

		self.__clean_list()

	def __search_fechas_ini_fin	(self):
		

		for linea in self.lista_pdf2:
			march = re.search('[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]',linea)
			if march:
				__ele = linea[-10:]
				__ano = int(__ele[-4:])
				__mes = int(__ele[3:5])
				__dia = int(__ele[:2])

				self.fechas.append(datetime.date(__ano,__mes,__dia))
				self.exclusiones.add(str(linea))

			self.__clean_list()
		
		for linea in self.lista_pdfto:
			march = re.search('[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]',linea)
			if march:
				__ele = linea[-10:]
				__ano = int(__ele[-4:])
				__mes = int(__ele[3:5])
				__dia = int(__ele[:2])

				self.fechas.append(datetime.date(__ano,__mes,__dia))
				self.exclusiones.add(str(linea))

			self.__clean_list()	
		
		if len(self.fechas) < 2 :
			for fecha1 in self.fechas :
				if fecha1 in self.fechas :
					self.fechas.remove(fecha1)		
		
		self.fechas.sort()

	def __search_Num_Pag (self):

		__coincide = []

		for linea in self.lista_pdf2:
			march = re.search('Pág.:[1-9] / [1-9]',linea)
			if march :
				__coincide.append(linea)
		for ele in __coincide:
			self.exclusiones.add(str(ele))
		self.__clean_list()


	def __PdftxtGen_pdfto (self):

		self.pdftotext = "\"pdftxt/" + self.dc[5:-3] + "pdftotext.txt" + "\""
		__comando = "pdftotext " +"\"" +self.dc+"\"" + "  " + self.pdftotext
		commands.getoutput(str(__comando))

	def __PdftxtGen_pdf2 (self):

		self.pdf2txt = "\"pdftxt/" + self.dc[5:-3] + "pdf2txt.txt" + "\""
		__comando = "/usr/local/bin/pdf2txt.py " +"\"" +self.dc+"\"" + " > " + self.pdf2txt 
		commands.getoutput(str(__comando))


	def __eliminar_temporales (self):

		commands.getoutput( "rm " + self.pdftotext)
		commands.getoutput( "rm " + self.pdf2txt)

	def __read_document(self):

		# Eliminando los retornos de carro
		doc = open(self.pdftotext[1:-1],'rb')
		for lineas in doc :
			linea = ''
			for ele in lineas :
				if not ele == '\n' :
					linea = linea + ele
				else:
					self.lista_pdfto.append(linea)
		doc.close()

		doc = open(self.pdf2txt[1:-1],'rb')
		for lineas in doc :
			linea = ''
			for ele in lineas :
				if not ele == '\n' :
					linea = linea + ele
				else:
					self.lista_pdf2.append(linea)
		doc.close()	

	def __clean_list (self):

		# Eliminando elementos de las exclusiones

		for linea in self.lista_pdf2:

			if linea in self.exclusiones:
				self.lista_pdf2.remove(linea)
			else:
				if len(linea) <= 1 :
					self.lista_pdf2.remove(linea)

		for linea in self.lista_pdf2:
			for ele in self.expresiones:
				march = re.search(ele,linea)
				if march:
					self.lista_pdf2.remove(linea)

		for linea in self.lista_pdfto:

			if linea in self.exclusiones:
				self.lista_pdfto.remove(linea)
			else:
				if len(linea) <= 1 :
					self.lista_pdfto.remove(linea)

		self.expresiones.add('Unidad: *')

		for linea in self.lista_pdfto:
			for ele in self.expresiones:
				march = re.search(ele,linea)
				if march:
					self.lista_pdfto.remove(linea)


	def __search_materias (self):

		__materias = set()
		for linea in self.lista_pdfto:
			march = re.search('Materia: *',linea)
			if march:
				__materias.add(linea)

		for linea in self.lista_pdf2:
			march = re.search('Materia: *',linea)
			if march:
				__materias.add(linea)
		self.materias = __materias

	def __buscando_alumnos (self):

		## No es 100% efectivo, de vez en cuando se cuela un curso 

		__alumnos = set()
		for linea in self.lista_pdfto:
			march = re.search('[a-zA-ZÀ-ÖØ-öø-ÿ]+\.?(( |\-)[a-zA-ZÀ-ÖØ-öø-ÿ]+\.?)*',linea)
			if not (linea in self.materias) and not (linea == self.curso) and not (linea == self.unidad):
				if march:
					__alumnos.add(linea)

		for linea in self.lista_pdf2:
			march = re.search('[a-zA-ZÀ-ÖØ-öø-ÿ]+\.?(( |\-)[a-zA-ZÀ-ÖØ-öø-ÿ]+\.?)*',linea)
			if not (linea in self.materias) and not (linea == self.curso) and not (linea == self.unidad):
				if march:
					__alumnos.add(linea)

		self.alumnos = __alumnos 

		
	def __tablas (self):

		__mapa_materias = []

		for materia in self.materias_pdf2 :
			try:
				__mapa_materias.append(self.lista_pdf2.index(str(materia)))

			except :

				for materia in self.materias_pdf2:
					cont = 0
					for linea in self.lista_pdf2:
						if materia == linea :
							__mapa_materias.append(cont)
						cont = cont + 1

		# Buscando los alumnos con faltas de cada materia
		# Creando grupos por materias

		__tablas = []

		for num in range(0,len(__mapa_materias)) :

			if not num == len(__mapa_materias)-1:
				__tablas.append(self.lista_pdf2[__mapa_materias[num]:__mapa_materias[num+1]])

			else:
				__tablas.append(self.lista_pdf2[__mapa_materias[-1]:])

		return __tablas

	def __limpieza_tablas (self):

		__cont = 0
		for ele in self.tablas:
			if len(ele) == 0 :
				self.tablas.remove(self.tablas[__cont])
			__cont = __cont + 1

	def __alumnos_por_tabla (self):

		# Contando numero de alumnos por tabla

		__tabla_cnt = []

		for con in self.tablas :

			__cnt = 0

			if len(con) == 0 :
				break

			else :

				for ele in con[1:] :
					march = re.search('[a-zA-ZÀ-ÖØ-öø-ÿ]+\.?(( |\-)[a-zA-ZÀ-ÖØ-öø-ÿ]+\.?)*',ele)
					if march and not ele in self.materias_pdf2 :
						self.alumnos.add(ele)
						__cnt = __cnt + 1

			__tabla_cnt.append(__cnt)

		return __tabla_cnt
	

	def __tablas_dispersion (self):

		__tablas_dispersion = []
		__cont = 0


		for tabla in self.tablas :

			__estado = 0

			for ele in tabla[1:] :

				march = re.search('[a-zA-ZÀ-ÖØ-öø-ÿ]+\.?(( |\-)[a-zA-ZÀ-ÖØ-öø-ÿ]+\.?)*',str(ele))

				if march and __estado == 0 :
					__estado = 1

				if not march and __estado == 1:
					__estado = 2

				if march and __estado == 2:
					__tablas_dispersion.append(__cont)
					__estado = 3
					break

			__cont = __cont + 1

		return __tablas_dispersion


	def __pos_de_datos_dispersos (self):

		__pos = {}

		for tabla in self.tablas_datos_dispersos:

			__rangos = []
			__a = []
			__estado = 0

			for pos in range(1,len(self.tablas[tabla])):

				march = re.search('[a-zA-ZÀ-ÖØ-öø-ÿ]+\.?(( |\-)[a-zA-ZÀ-ÖØ-öø-ÿ]+\.?)*',self.tablas[tabla][pos])

				if march and __estado == 0 :
					__a.append(pos)
					__estado = 1

				if not march and __estado == 1:
					__a.append(pos-1)
					__rangos.append(__a)
					__a = []
					__estado = 0

			__pos[tabla] = __rangos

		return __pos


	def __procesando_tablas_dispersas (self):

		for datos in self.pos_datos_dispersos :

			for num in self.pos_datos_dispersos[datos]:

				__numalu = (num[1] - num[0]) + 1
				__conjuntos = self.tablas[datos][num[0]:(num[1]*5)+__numalu*2]


				# Variables

				__alumnos = []
				__fjhoras = []
				__fjporcen = []
				__fihoras = []
				__fiporcen = []
				__retrasos = []

				# Añadiendo datos a la variables


				for ele in range(0,__numalu) :

					__alumnos.append(__conjuntos[ele])
					__fjhoras.append(__conjuntos[ele+(__numalu)])
					__fjporcen.append(__conjuntos[ele+(__numalu*2)])
					__fihoras.append(__conjuntos[ele+(__numalu*3)])
					__fiporcen.append(__conjuntos[ele+(__numalu*4)])
					__retrasos.append(__conjuntos[ele+(__numalu*5)])				


				for num in range(0,__numalu):

					for hl in self.horas_lectivas:
						if hl[0]['Materia'] == self.materias_pdf2[datos] :
							__horas_lectivas = hl[0]['Horas']

					for td in self.total_dias:
						if td[0]['Materia'] == self.materias_pdf2[datos] :
							__total_dias = td[0]['Dias']

					self.insert_pdf2.append([{


							'Alumno': __alumnos[num][2:],
							'Curso' : self.curso,
							'Unidad' : self.unidad,
							'Materia' : self.materias_pdf2[datos],
							'FechaDesde' : self.fechas[0],
							'FechaHasta' : self.fechas[1],
							'TotalPeriodo' : __total_dias,
							'HorasLectivas' :  __horas_lectivas,
							'JustificadasHoras' : __fjhoras[num],
							'JustificadasPorcentaje' : __fjporcen[num],
							'InjustificadasHoras' : __fihoras[num],
							'InjustificadasPorcentaje' : __fiporcen[num],
							'Retrasos' : __retrasos[num] 

						}])


	def __sacando_faltas_por_alumnos (self):

		__cont = 0

		for tabla in self.tablas :				

			__alumnos = []
			__fjhoras = []
			__fjporcen = []
			__fihoras = []
			__fiporcen = []
			__retrasos = []					

			__numalu = self.alumnos_por_tabla[__cont]
			if  not self.alumnos_por_tabla[__cont] == 0 :
				if not (__cont in self.tablas_datos_dispersos):
					__materia = self.materias_pdf2[__cont]
					self.error_creainsert[__materia] = []
					for num in range(1,__numalu+1) :

						try:
						
							__alumnos.append(tabla[num])
							__fjhoras.append(tabla[num+(__numalu)])
							__fjporcen.append(tabla[num+(__numalu*2)])
							__fihoras.append(tabla[num+(__numalu*3)])
							__fiporcen.append(tabla[num+(__numalu*4)])
							__retrasos.append(tabla[num+(__numalu*5)])

						except IndexError :

							self.error_creainsert[tabla[0]].append(tabla[num])
							__alumnos.remove(tabla[num])

					

					# Metiendo datos en el diccionario insert

					for num in range(0,len(__alumnos)):

						for hl in self.horas_lectivas:
							if hl[0]['Materia'] == __materia :
								__horas_lectivas = hl[0]['Horas']

						for td in self.total_dias:
							if td[0]['Materia'] == __materia :
								__total_dias = td[0]['Dias']

						self.insert_pdf2.append([{


							'Alumno': __alumnos[num][2:],
							'Curso' : self.curso,
							'Unidad' : self.unidad,
							'Materia' : __materia,
							'FechaDesde' : self.fechas[0],
							'FechaHasta' : self.fechas[1],
							'TotalPeriodo' : __total_dias,
							'HorasLectivas' :  __horas_lectivas,
							'JustificadasHoras' : __fjhoras[num],
							'JustificadasPorcentaje' : __fjporcen[num],
							'InjustificadasHoras' : __fihoras[num],
							'InjustificadasPorcentaje' : __fiporcen[num],
							'Retrasos' : __retrasos[num] 

						}])


			__cont = __cont + 1

	def __search_materias_pdf2 (self):

		__materias = []

		for linea in self.lista_pdf2:
			march = re.search('Materia: *',linea)
			if march:
				__materias.append(str(linea))

		self.materias_pdf2 = __materias


	def __MarcarApercibimientos (self) :

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
				