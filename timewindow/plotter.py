import os
import json
import math

import numpy as np
import pandas as pd
from matplotlib import colors
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import gmplot
from sklearn.cluster import DBSCAN


class Plotter:


	METRIC_UNIT = {'execution' : 'seconds',
					'calls': 'times',}


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

			for folder in os.listdir('data/monday/{0}'.format(city)):

				accumulated = {'duration': [],
							'route_length': [],
							'time_loss': []}

				for day in days:

					for iterate in range(20):
						ires = self.read_xml_file('./data/{0}/{1}/{2}/{3}_reroute.xml'.format(day, city, folder, iterate))
						dur, rou, tim = self.get_reroute_metrics(ires)
						accumulated['duration'].append(dur)
						accumulated['route_length'].append(rou)
						accumulated['time_loss'].append(tim)

				results['reroute_{0}_{1}'.format(city, folder)] = self.calculate_reroute_metrics(accumulated)

		return results


	def get_contextual_metrics(self, ires):

		execs = ires['execution']
		execs = map(float, execs)

		return float(np.mean(execs)), float(ires['calls'])


	def calculate_contextual_metrics(self, accumulated):

		return {'execution': self.mean_confidence_interval(accumulated['execution']),
				'calls': self.mean_confidence_interval(accumulated['calls'])}


	def read_contextual_files(self, results, days, cities):

		for city in cities:

			for folder in os.listdir('data/monday/{0}/assault/'.format(city)):

				accumulated = {'execution': [],
							'calls': []}

				for crime in ['assault', 'battery', 'theft']:

					for day in days:

						for iterate in range(20):
							ires = self.read_json_file('./data/{0}/{1}/{2}/{3}/{4}_metrics.json'.format(day, city, crime, folder, iterate))
							execs, calls = self.get_contextual_metrics(ires)
							accumulated['execution'].append(execs)
							accumulated['calls'].append(calls)

					results['context_{0}_{1}_{2}'.format(city, crime, folder)] = self.calculate_contextual_metrics(accumulated)

		return results


	def save_calculation(self, results, file='all'):

		if not os.path.exists('results'):
			os.makedirs('results')

		with open('results/{0}_results.json'.format(file), "w") as write_file:
			json.dump(results, write_file, indent=4)


	def read_calculation(self):

		results = {}

		for file in os.listdir('results/'):

			with open('results/{0}'.format(file), "r") as write_file:
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

		if not os.path.exists('metric_plots'):
			os.makedirs('metric_plots')

		keys_order = ['baseline', 'crimes', 'crashes', 'same']
		xlabels = ['Baseline', 'Crimes', 'Crashes', 'Same']

		means, stds = [], []
		for crime in crimes:
			m, s = self.separate_mean_std(just_to_plot, metric, keys_order, cities, crime)
			means.append(m)
			stds.append(s)

		plt.clf()
		ax = plt.subplot(111)

		#color_list = ['#1d4484', '#7c0404', '#874a97', '#5dddd0', '#86a4ca', '#e6f0fc', '#424564']
		color_list = ['#8AABE0', '#7689A9', '#4D658D', '#2C4770', '#152D54', '#132542', '#051938']

		gap = .5 / len(means)
		for i, row in enumerate(means):
			X = np.arange(len(row))
			plt.bar(X + i * gap, row, yerr=stds[i], width=gap, label=crimes[i].capitalize(), color=color_list[i % len(color_list) + i * 2], error_kw=dict(ecolor='#9a9a9c', lw=2, capsize=2, capthick=2))

		plt.xlabel('Execution Configuration')
		plt.ylabel('{0} ({1})'.format(metric.replace('_', ' ').capitalize(), self.METRIC_UNIT[metric.replace("u'", "'")]))
		plt.xticks(np.arange(0, len(xlabels))+0.25, xlabels)

		ax.legend()

		plt.savefig('metric_plots/{0}_{1}.pdf'.format(file, metric), bbox_inches="tight", format='pdf')


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


	def plot_all_days(self, results, days, metric, crime):

		if not os.path.exists('metric_plots'):
			os.makedirs('metric_plots')

		keys_order = ['baseline', 'crimes', 'crashes', 'same']
		xlabels = ['Baseline', 'Crimes', 'Crashes', 'Same']

		means, stds = [], []

		for day in results.keys():

			if 'all' not in day:
				m, s = self.separate_and_filter_crime(results[day], metric, crime, keys_order)
				means.append(m)
				stds.append(s)

		plt.clf()
		ax = plt.subplot(111)

		#color_list = ['#1d4484', '#7c0404', '#874a97', '#5dddd0', '#86a4ca', '#627a96', '#424564']
		color_list = ['#8AABE0', '#7689A9', '#4D658D', '#2C4770', '#152D54', '#132542', '#051938']

		gap = .8 / len(means)
		for i, row in enumerate(means):
			X = np.arange(len(row))
			plt.bar(X + i * gap, row, yerr=stds[i], width=gap, label=days[i].capitalize(), color=color_list[i % len(color_list)], error_kw=dict(ecolor='#9a9a9c', lw=2, capsize=2, capthick=2))

		plt.xlabel('Execution Configuration')
		plt.ylabel('{0} ({1})'.format(metric.replace('_', ' ').capitalize(), self.METRIC_UNIT[metric.replace("u'", "'")]))
		plt.xticks(np.arange(0, len(xlabels))+0.25, xlabels)

		ax.legend(loc='upper center', ncol=3, fancybox=True, bbox_to_anchor=(0.5, 1.2))

		plt.savefig('metric_plots/{0}_{1}.pdf'.format(crime, metric), bbox_inches="tight", format='pdf')


	def put_two_decimals(self, number):

		number = str(number)
		if len(number) == 2:
			return number
		else:
			return '0' + number


	def plot_distribution(self, distribution, month, day):

		plt.clf()
		ax = plt.subplot(111)

		if not os.path.exists('./timewindow/plots/distribution'):
			os.makedirs('./timewindow/plots/distribution')

		dist_contourn = [d + 0.05 for d in distribution]

		plt.bar(range(0, len(dist_contourn)), dist_contourn, width=1.1, color='#343536')
		N = plt.bar(range(0, len(distribution)), distribution)

		hmax = np.amax(distribution)
		hmin = np.amin(distribution)

		norm = colors.Normalize(hmin, hmax)
		for indx, thispatch in enumerate(N.patches):
			color = plt.cm.Reds(norm(distribution[indx]) + 0.2)
			thispatch.set_facecolor(color)

		plt.ylabel('Quantidade de Crimes', fontweight='bold')

		if month == 'year':
			xticks = ['Jan.', 'Fev.', 'Mar.', 'Abr.', 'Maio', 'Jun.', 'Jul.',
					'Ago.', 'Set.', 'Out.', 'Nov.', 'De.']
			plt.xticks(np.arange(0, 576, 48)-0.5, xticks, rotation=30)
			plt.xlabel('Meses', fontweight='bold')
		else:
			xticks = []
			for i in range(0, 24, 2):
				hour = self.put_two_decimals(i)
				xticks.append('{0}:00'.format(hour))
			plt.xticks(np.arange(0, 48, 4)-0.5, xticks, rotation=30)
			plt.xlabel('Horas', fontweight='bold')

		#plt.xticks(np.arange(0, 48), ['' for i in range(0, 48)])

		# plt.show()
		plt.savefig('./timewindow/plots/distribution/distribution_{0}_{1}.pdf'.format(month, day), bbox_inches="tight", format='pdf')



	def main(self, cities=['austin']):

		results = {}
		days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
		crimes = ['assault', 'battery', 'theft']

		# self.read_contextual_files(results, days, cities)
		# self.save_calculation(results)

		# for day in days:

			# results = {}
			# self.read_contextual_files(results, [day], cities)
			# self.save_calculation(results, day)

		results = self.read_calculation()
		for res in results:
			self.plot(results[res], res, cities, crimes)

		for metric in ['execution', 'calls']:
			for crime in crimes:
				self.plot_all_days(results, days, metric, crime)


	def remove_invalid_coord(self, df):
		return df.query('lat != 0 & lon != 0')


	def read_data(self, day='monday', city='chicago', types='crimes'):

		data_file = open('../data/cleaned/{0}_2018_{1}.csv'.format(types, city), 'r')

		crime_list = []

		for line in data_file:
			line = line.strip().split('\t')

			item = {}
			item['datetime'] = pd.to_datetime(str(line[0]))
			item['hour'] = pd.to_datetime(str(line[0])).hour
			item['month'] = pd.to_datetime(str(line[0])).month
			item['lat'] = float(line[1])
			item['lon'] = float(line[2])
			item['type'] = line[3].strip()

			crime_list.append(item)

		df = pd.DataFrame(crime_list)
		df['dayofweek'] = df['datetime'].dt.dayofweek
		df.set_index('datetime', inplace=True)

		return self.remove_invalid_coord(df)


	def plot_heat(self, clusters, hour, lat='41.830785', lon='-87.684644'):

		plt.clf()

		gmap = gmplot.GoogleMapPlotter(lat, lon, 11)

		lats, longs = [], []

		for indx, cluster in clusters.iterrows():
			lats.append(float(cluster['lat']))
			longs.append(float(cluster['lon']))

		gmap.heatmap(lats, longs)

		if not os.path.exists('plots'):
			os.makedirs('plots')

		if not os.path.exists('plots/heat'):
			os.makedirs('plots/heat')

		gmap.draw('plots/heat/{0}.html'.format(hour))


	def heat_call(self):

		df = self.read_data()

		#df = df.query('month == 1').query('dayofweek == 1')

		for hour in range(0, 24):

			df_hour = df.query('hour == {0}'.format(hour))

			df_hour = df_hour.drop(['type', 'hour', 'month', 'dayofweek'], axis=1)

			self.plot_heat(df_hour, hour)


if __name__ == '__main__':

	plotter = Plotter()
	plotter.heat_call()
