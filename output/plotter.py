import os
import json
import math

import numpy as np
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup


class Plotter:

	METRIC_PT = {'execution': 'Execução',
				  'calls': 'Requisições'}

	METRIC_UNIT = {'execution': 'segundos',
					'calls': 'vezes'}

	CRIME_PT = {'assault': 'Assalto',
				'battery': 'Violência',
				'theft': 'Furto'}

	DAY_PT = {'sunday': 'Domingo',
				'monday': 'Segunda-feira',
				'tuesday': 'Terça-feira',
				'wednesday': 'Quarta-feira',
				'thursday': 'Quinta-feira',
				'friday': 'Sexta-feira',
				'saturday': 'Sábado'}

	def read_xml_file(self, file):

		f = open(file)
		data = f.read()
		soup = BeautifulSoup(data, "xml")
		f.close()

		return soup


	def read_json_file(self, file):

		with open(file, "r") as file:
			return json.load(file)


	def mean_confidence_interval(self, data, confidence=0.95):
		a = 1.0 * np.array(data)
		n = len(a)
		m, se = np.mean(a), np.std(a)
		h = 1.96 * (se/math.sqrt(n))
		return (m, h)


	def get_reroute_metrics(self, ires):

		duration, route_length, time_loss = [], [], []

		tripinfos = ires.find('tripinfos')

		for info in tripinfos.findAll('tripinfo'):

			try:
				dur = float(info['duration'])
				rou = float(info['routeLength'])
				tim = float(info['timeLoss'])

				if dur > 10.00 and rou > 50.00:
					duration.append(dur)
					route_length.append(rou)
					time_loss.append(tim)
			except Exception:
				pass

		return np.mean(duration), np.mean(route_length), np.mean(time_loss)


	def read_reroute_files(self, results, days, cities):

		for city in cities:

			for folder in os.listdir('./output/data/monday/{0}'.format(city)):

				accumulated = {'duration': [],
							'route_length': [],
							'time_loss': []}

				for day in days:

					for iterate in range(20):
						ires = self.read_xml_file('./output/data/{0}/{1}/{2}/{3}_reroute.xml'.format(day, city, folder, iterate))
						dur, rou, tim = self.get_reroute_metrics(ires)
						accumulated['duration'].append(dur)
						accumulated['route_length'].append(rou)
						accumulated['time_loss'].append(tim)

				results['reroute_{0}_{1}'.format(city, folder)] = self.calculate_reroute_metrics(accumulated)

		return results


	def get_contextual_metrics(self, ires):

		execs = ires['execution']
		execs = list(map(float, execs))

		return float(np.mean(execs)), float(ires['calls'])


	def calculate_contextual_metrics(self, accumulated):

		return {'execution': self.mean_confidence_interval(accumulated['execution']),
				'calls': self.mean_confidence_interval(accumulated['calls'])}


	def read_contextual_files(self, results, days, cities):

		for city in cities:

			for folder in os.listdir('./output/data/monday/{0}/assault/'.format(city)):

				accumulated = {'execution': [],
							'calls': []}

				for crime in ['assault', 'battery', 'theft']:

					for day in days:

						for iterate in range(20):
							ires = self.read_json_file('./output/data/{0}/{1}/{2}/{3}/{4}_metrics.json'.format(day, city, crime, folder, iterate))
							execs, calls = self.get_contextual_metrics(ires)
							accumulated['execution'].append(execs)
							accumulated['calls'].append(calls)

					results['context_{0}_{1}_{2}'.format(city, crime, folder)] = self.calculate_contextual_metrics(accumulated)

		return results


	def save_calculation(self, results, file='all'):

		if not os.path.exists('./output/results'):
			os.makedirs('./output/results')

		with open('./output/results/{0}_results.json'.format(file), "w") as write_file:
			json.dump(results, write_file, indent=4)


	def read_calculation(self):

		results = {}

		for file in os.listdir('./output/results/'):

			with open('./output/results/{0}'.format(file), "r") as write_file:
				results[file] = json.load(write_file)

		return results


	def filter_keys(self, results, sfilter='context'):

		filtered_keys = [x for x in results.keys() if sfilter in x]

		filtered_dict = {}
		for f in filtered_keys:
			filtered_dict[f] = results[f]

		metrics = results[filtered_keys[0]].keys()

		return filtered_dict, metrics


	def separate_mean_std(self, just_to_plot, metric, keys_order, cities, crime):

		means, stds = [], []

		for city in cities:
			for key in keys_order:
				k = [x for x in just_to_plot if key in x and city in x and crime in x][0]

				means.append(just_to_plot[k][metric][0])
				stds.append(just_to_plot[k][metric][1])

		return means, stds


	def plot_bars(self, just_to_plot, metric, file, cities, crimes):

		if not os.path.exists('./output/metric_plots'):
			os.makedirs('./output/metric_plots')

		if metric == 'Calls (times)':
			metric = 'Requisições_vezes'

		keys_order = ['baselinea', 'baselinec', 'crimes', 'crashes', 'same']
		xlabels = ['BaselineA', 'BaselineC', 'Crimes', 'Acidentes', 'Ambos']

		means, stds = [], []
		for crime in crimes:
			m, s = self.separate_mean_std(just_to_plot, metric, keys_order, cities, crime)
			means.append(m)
			stds.append(s)

		plt.clf()
		ax = plt.subplot(111)

		#color_list = ['#1d4484', '#7c0404', '#874a97', '#5dddd0', '#86a4ca', '#e6f0fc', '#424564']
		color_list = ['#8AABE0', '#7689A9', '#4D658D', '#2C4770', '#152D54', '#132542', '#010712']

		gap = .5 / len(means)
		for i, row in enumerate(means):
			X = np.arange(len(row))
			plt.bar(X + i * gap, row, yerr=stds[i], width=gap, label=self.CRIME_PT[crimes[i]], color=color_list[i % len(color_list) + i * 2], error_kw=dict(ecolor='#9a9a9c', lw=2, capsize=2, capthick=2), edgecolor='black')

		plt.xlabel('Configuração da Execução', fontweight='bold')
		plt.ylabel('{0} ({1})'.format(self.METRIC_PT[metric.replace('_', ' ')], self.METRIC_UNIT[metric.replace("u'", "'")]), fontweight='bold')
		plt.xticks(np.arange(0, len(xlabels))+0.25, xlabels)

		ax.legend(loc='upper center', ncol=3, fancybox=True, bbox_to_anchor=(0.5, 1.09))

		plt.savefig('./output/metric_plots/bars_{0}_{1}.pdf'.format(file, metric), bbox_inches="tight", format='pdf')


	def plot(self, results, file, cities, crimes):

		contextual, cmetrics = self.filter_keys(results)

		for metric in cmetrics:
			self.plot_bars(contextual, metric, file, cities, crimes)


	def separate_and_filter_crime(self, result, metric, crime, keys_order):

		mean, std = [], []

		for key in keys_order:

			record = result["context_chicago_{0}_{1}".format(crime, key)]

			mean.append(float(record[metric][0]))
			std.append(float(record[metric][1]))

		return mean, std


	def separate_and_multiply(self, result, crime, keys_order):

		time_impact = []

		for key in keys_order:

			record = result["context_chicago_{0}_{1}".format(crime, key)]
			time_impact.append(float(record["execution"][0])*float(record["calls"][0]))

		return time_impact


	def plot_all_days(self, results, days, metric, crime):

		if not os.path.exists('./output/metric_plots'):
			os.makedirs('./output/metric_plots')

		keys_order = ['baselinea', 'baselinec', 'crimes', 'crashes', 'same']
		xlabels = ['BaselineA', 'BaselineC', 'Crimes', 'Acidentes', 'Ambos']

		means, stds = [], []

		for day in results.keys():

			if 'all' not in day:
				m, s = self.separate_and_filter_crime(results[day], metric, crime, keys_order)
				means.append(m)
				stds.append(s)

		plt.clf()
		ax = plt.subplot(111)

		#color_list = ['#1d4484', '#7c0404', '#874a97', '#5dddd0', '#86a4ca', '#627a96', '#424564']
		color_list = ['#8AABE0', '#7689A9', '#4D658D', '#2C4770', '#152D54', '#132542', '#010712']

		gap = .8 / len(means)
		for i, row in enumerate(means):
			X = np.arange(len(row))
			plt.bar(X + i * gap, row, yerr=stds[i], width=gap, label=self.DAY_PT[days[i]], color=color_list[i % len(color_list)], error_kw=dict(ecolor='#9a9a9c', lw=2, capsize=2, capthick=2), edgecolor='black')

		plt.xlabel('Configuração da Execução', fontweight='bold')
		plt.ylabel('{0} ({1})'.format(self.METRIC_PT[metric.replace('_', ' ')], self.METRIC_UNIT[metric.replace("u'", "'")]), fontweight='bold')
		plt.xticks(np.arange(0, len(xlabels))+0.25, xlabels)

		ax.legend(loc='upper center', ncol=3, fancybox=True, bbox_to_anchor=(0.5, 1.2))

		plt.savefig('./output/metric_plots/dall_{0}_{1}.pdf'.format(crime, metric), bbox_inches="tight", format='pdf')


	def plot_overral_time(self, results, days, crime):

		if not os.path.exists('./output/metric_plots'):
			os.makedirs('./output/metric_plots')

		keys_order = ['baselinea', 'baselinec', 'crimes', 'crashes', 'same']
		xlabels = ['BaselineA', 'baselineC', 'Crimes', 'Acidentes', 'Ambos']
		impacts = []

		for day in results.keys():

			if 'all' not in day:
				impact = self.separate_and_multiply(results[day], crime, keys_order)
				impacts.append(impact)

		plt.clf()
		ax = plt.subplot(111)

		color_list = ['#8AABE0', '#7689A9', '#4D658D', '#2C4770', '#152D54', '#132542', '#010712']

		gap = .8 / len(impacts)
		for i, row in enumerate(impacts):
			X = np.arange(len(row))
			plt.bar(X + i * gap, row, width=gap, label=self.DAY_PT[days[i]], color=color_list[i % len(color_list)], error_kw=dict(ecolor='#9a9a9c', lw=2, capsize=2, capthick=2), edgecolor='black')

		plt.xlabel('Configuração da Execução', fontweight='bold')
		plt.ylabel('Requisições x Tempo de Execução (Segundos)', fontweight='bold')
		plt.xticks(np.arange(0, len(xlabels))+0.25, xlabels)

		ax.legend(loc='upper center', ncol=3, fancybox=True, bbox_to_anchor=(0.5, 1.2))

		plt.savefig('./output/metric_plots/impact_{0}.pdf'.format(crime), bbox_inches="tight", format='pdf')


	def main(self, cities=['austin']):

		results = {}
		days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
		crimes = ['assault', 'battery', 'theft']

		self.read_contextual_files(results, days, cities)
		self.save_calculation(results)

		for day in days:

			results = {}
			self.read_contextual_files(results, [day], cities)
			self.save_calculation(results, day)

		results = self.read_calculation()
		for res in results:
			self.plot(results[res], res, cities, crimes)

		for metric in ['execution', 'calls']:
			for crime in crimes:
				self.plot_all_days(results, days, metric, crime)

		for crime in crimes:
			self.plot_overral_time(results, days, crime)
