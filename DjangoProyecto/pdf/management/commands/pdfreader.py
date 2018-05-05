#! /bin/python
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand, CommandError
from pdf.models import *
import os ,sys
import commands
import re
import datetime
import PyPDF2
import locale
import logging

class Command (BaseCommand):

	help = 'Este comando se encarga de procesar los documentos pdf.'

	def add_arguments(self, parser):
		#parser.add_argument('pdfs', nargs='+', type=str)
#		parser.add_argument('num', nargs='+', type=int)
		pass
	def handle (self, *args, **options):


		class ProcesarPdfs :

			def __init__(self):

				pdf = Pdfs.objects.all().values('pdf')
				for ele in pdf:
					print ele['pdf']
					self.Procesar(ele['pdf'])	
							

			def Procesar (self,pdf) :	

				self.datos = {}
				self.lista_limpia = []
				self.total_dias = []
				self.fechas = []
				self.horas_lectivas = []
				self.insert = {}
				self.ano_academico = 0
				self.unidad = ''
				self.curso = ''
				self.error = False
				self.alumnos = []
				self.APRENDIZAJE = True
				self.error_creainsert = {}

				self.exclusiones = set([

				'',
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
				'I.E.S. Fernando Aguilar Quignon',
				'Año académico:',
				'Curso:',
				'Unidad:',
				'\x0cr',
				'\x0cESTAD\xc3\x8dSTICAS DE ABSENTISMO POR MATERIAS EN UN PERIODO',
				'\x0cCONSEJER\xc3\x8dA DE EDUCACI\xc3\x93N'

				])

				self.dc = pdf
				self.__PdftxtGen()
				self.__read_document()
				self.__clean_list()
				self.__search_Num_Pag()
				self.materias = self.__search_materias()
				self.__search_total_dias()
				self.__search_fechas_ini_fin()
				self.__search_horas_lectivas()
				#self.__pypdf2_horas_lectivas()
				self.__search_curso_unidad_ano()
				self.__print_lista_limpia()

				# Buscando datos por alumnos

				self.__creando_indices_insert()
				self.tablas = self.__tablas()
				self.__limpieza_tablas()
				self.alumnos_por_tabla = self.__alumnos_por_tabla()
				self.tablas_datos_dispersos = self.__tablas_dispersion()
				self.pos_datos_dispersos = self.__pos_de_datos_dispersos()
				self.__procesando_tablas_dispersas()
				self.__sacando_faltas_por_alumnos()

				# Guardando informacion en la base de datos.

				self.__insert_fal_asistencia()
				self.__insert_error_Create_Insert()
				self.__limpieza_temporales()

				if not self.error :
					self.__pdf_marcar_como_procesado()

				else :
					
					self.__error()


			def __insert_error_Create_Insert (self):

				for errores in self.error_creainsert:
					for ele in self.error_creainsert[errores]:
						if not ele == '' :
							__pos_materia = self.materias.index(errores)-1
							__horas_lectivas = str(self.horas_lectivas[__pos_materia])
							#print 'INsert error en database ' + str(ele)
							insert = Faltas_Asistencia.objects.update_or_create(

									Alumno =  ele,
									Curso = self.curso,
									Unidad = self.unidad,
									Materia = str(errores),
									FechaDesde = self.fechas[0],
									FechaHasta = self.fechas[1],
									TotalPeriodo = int(self.total_dias[__pos_materia ]),
									HorasLectivas = int(__horas_lectivas[0:__horas_lectivas.index(':')]),
									Ano = int(self.ano_academico),
									Estado = 'Error',
									pdf = Pdfs.objects.get(pdf=self.dc)							

								)		

			def __pypdf2_horas_lectivas (self):

				__pdf_file = open(self.dc,"rb")
				__readpdf = PyPDF2.PdfFileReader(__pdf_file)
				__numpages = __readpdf.numPages

				for ele in range(0,int(__numpages)):				
					__text = __readpdf.getPage(ele).extractText()
					__expresion = re.compile("Horas lectivas: [0-9][0-9]\:[0-9][0-9]")
				
					for ele in __expresion.findall(__text):
						self.horas_lectivas.append(str(ele))
						self.exclusiones.add(str(ele))
						
				self.__clean_list()


			def __pdf_marcar_como_procesado(self):

				procesado = Pdfs.objects.filter(pdf=self.dc)
				procesado.update(Estado='Procesado',FechaProces=datetime.date.today())

			def __limpieza_temporales(self):

				__directorio = "pdftxt/" + self.dc[7:-3] + "txt"
				os.remove(__directorio)						

			def __error (self) :

				error = Pdfs.objects.filter(pdf=self.dc)
				error.update(Estado="Error")

			def __creando_indices_insert (self):

				for mate in self.materias :
					self.insert[str(mate)] = []

				# Buscando los indices de las materias

			def __tablas (self):

				__mapa_materias = []

				for materia in self.materias :
					try:
						__mapa_materias.append(self.lista_limpia.index(str(materia)))

					except :

						for materia in self.materias:
							cont = 0
							for linea in self.lista_limpia:
								if materia == linea :
									__mapa_materias.append(cont)
								cont = cont + 1

				# Buscando los alumnos con faltas de cada materia
				# Creando grupos por materias

				__tablas = []

				for num in range(0,len(__mapa_materias)) :

					if not num == len(__mapa_materias)-1:
						__tablas.append(self.lista_limpia[__mapa_materias[num]:__mapa_materias[num+1]])

					else:
						__tablas.append(self.lista_limpia[__mapa_materias[-1]:])

				return __tablas

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
							if march and not ele in self.materias :
								self.alumnos.append(ele)
								__cnt = __cnt + 1

					__tabla_cnt.append(__cnt)

				return __tabla_cnt


			# Comprobando la dispersión de los alumnos dentro de las tablas

			def __tablas_dispersion (self):

				__tablas_dispersion = []
				__cont = 0


				for tabla in self.tablas :

					__estado = 0

					for ele in tabla[1:] :

						march = re.search('[a-zA-ZÀ-ÖØ-öø-ÿ]+\.?(( |\-)[a-zA-ZÀ-ÖØ-öø-ÿ]+\.?)*',ele)

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

			# Sacando los elementos de cada tabla, columna por columna

			def __limpieza_tablas (self):

				__cont = 0
				for ele in self.tablas:
					if len(ele) == 0 :
						self.tablas.remove(self.tablas[__cont])
					__cont = __cont + 1


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
							__materia = self.materias[__cont]
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

								#	print self.error_creainsert

							# Metiendo datos en el diccionario insert

							for num in range(0,len(__alumnos)):
								self.insert[str(self.materias[__cont])].append([str(__alumnos[num][2:]),__fjhoras[num],__fjporcen[num],__fihoras[num],__fiporcen[num],__retrasos[num]])

					__cont = __cont + 1

					
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
							self.insert[str(self.materias[datos])].append([str(__alumnos[num][2:]),__fjhoras[num],__fjporcen[num],__fihoras[num],__fiporcen[num],__retrasos[num]])

			def __insert_fal_asistencia (self):

				for materia in self.insert:

					__linea = self.insert[materia]
					__asignatura = materia[9:]

					if not len(__linea) == 0:

						for ele in __linea :

							__pos_materia = self.materias.index(materia)-1
							__horas_lectivas = str(self.horas_lectivas[__pos_materia])

							__dato2 = ele[2].replace(',','.')
							__dato4 = ele[4].replace(',','.')							
							
							try:

								insert = Faltas_Asistencia.objects.update_or_create(

									Alumno =  ele[0],
									Curso = self.curso,
									Unidad = self.unidad,
									Materia = __asignatura,
									FechaDesde = self.fechas[0],
									FechaHasta = self.fechas[1],
									TotalPeriodo = int(self.total_dias[__pos_materia ]),
									HorasLectivas = int(__horas_lectivas[0:__horas_lectivas.index(':')]),
									JustificadasHoras = ele[1][0:ele[1].index(':')],
									JustifiacdadPorcentaje = float(__dato2.replace('%','')),
									InjustificadaHoras = ele[3][0:ele[3].index(':')],
									InjustificadasPorcentaje = float(__dato4.replace('%','')),
									Retrasos = ele[5][0:ele[5].index(':')],
									Ano = int(self.ano_academico),
									Estado = 'Correcto',
									pdf = Pdfs.objects.get(pdf=self.dc)	)

								#print ele

							except : 

								insert = Faltas_Asistencia.objects.update_or_create(

									Alumno =  ele[0],
									Curso = self.curso,
									Unidad = self.unidad,
									Materia = __asignatura,
									FechaDesde = self.fechas[0],
									FechaHasta = self.fechas[1],
									TotalPeriodo = int(self.total_dias[__pos_materia ]),
									HorasLectivas = int(__horas_lectivas[0:__horas_lectivas.index(':')]),
									Ano = int(self.ano_academico),
									Estado = 'Error',
									pdf = Pdfs.objects.get(pdf=self.dc)							

								)		

						#		print 'Error database' + str(ele)				

								
							self.__log('info','Problando Flatas Asistencias ' + str(ele) )

			# Este metodo comprobara si existe una coerencia entre la informacion extraida.
				
			def __log(self,level,texto):

				stdlogger = logging.getLogger('log')
				
				if level == 'error':
					stdlogger.error(texto)
				
				if level == 'info':
					stdlogger.info(texto)

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


			def __search_curso_unidad_ano (self):

				
				self.curso = self.lista_limpia[2]
				self.unidad = self.lista_limpia[1]
				self.ano_academico = self.lista_limpia[0]

				self.exclusiones.add(self.curso)
				self.exclusiones.add(self.unidad)
				self.exclusiones.add(self.ano_academico)

				self.__clean_list()				


			def ___search_ano_academico (self):

				for linea in self.lista_limpia:

					march = re.search('[0-9][0-9][0-9][0-9]',linea)

					if march:

						self.ano_academico(linea)
						self.exclusiones.add(linea)
						self.__clean_list()
						break


			def __search_horas_lectivas (self):

				for linea in self.lista_limpia:
					march = re.search('Horas lectivas: *',linea)
					if march:
						self.horas_lectivas.append(str(linea[-5:]))
						self.exclusiones.add(linea)

				self.__clean_list()


			def __search_total_dias (self):

				for linea in self.lista_limpia:
					march = re.search('Total días *',linea)
					if march:
						self.total_dias.append(linea[-2:])
						self.exclusiones.add(linea)

				self.__clean_list()

			def __search_fechas_ini_fin	(self):

				for linea in self.lista_limpia:
					march = re.search('[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]',linea)
					if march:

						__ano = int(linea[-4:])
						__mes = int(linea[4:5])
						__dia = int(linea[:2])

						self.fechas.append(datetime.date(__ano,__mes,__dia))
						self.exclusiones.add(linea)

					self.__clean_list()
					self.fechas.sort()

			def __search_Num_Pag (self):

				__coincide = []

				for linea in self.lista_limpia:
					march = re.search('Pág.:[1-9] / [1-9]',linea)

					if march :
						__coincide.append(linea)

				for ele in __coincide:
					self.exclusiones.add(str(ele))

				self.__clean_list()


			def __PdftxtGen (self):

				self.temporal = "pdftxt/" + self.dc[7:-3] + "txt" + "\""
				__comando = "/usr/local/bin/pdf2txt.py " +"\"" +self.dc+"\"" + " > " + "\"" + "pdftxt/" + self.dc[7:-3] + "txt" + "\""
				commands.getoutput(__comando)

			def __eliminar_temporales (self):

				commands.getoutput( "rm " +  self.temporal)


			def __read_document(self):

				# Eliminando los retornos de carro

				doc = open(("pdftxt/" + self.dc[7:-3] + "txt"),'r')
				for lineas in doc :
					linea = ''

					for ele in lineas :

						if not ele == '\n' :
							linea = linea + ele

						else:
							self.lista_limpia.append(linea)

				doc.close()

			def __search_materias (self):

				__materias = []

				for linea in self.lista_limpia:
					march = re.search('Materia: *',linea)
					if march:
						__materias.append(str(linea))

				return __materias

			def __clean_list (self):

				# Eliminando elementos de las exclusiones

				for linea in self.lista_limpia:

					if linea in self.exclusiones:
						self.lista_limpia.remove(linea)
					else:
						if len(linea) == 1 :
							self.lista_limpia.remove(linea)



			def __print_lista_limpia (self):

				
				#print self.alumnos
				#print len(self.total_dias)
				#print len(self.horas_lectivas)
				pass				
						
						

						

		a = ProcesarPdfs()