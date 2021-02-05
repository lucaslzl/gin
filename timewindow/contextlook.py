import json
import os, sys
from os import listdir
import time

import pandas as pd
import numpy as np
from scipy.signal import find_peaks, wiener, correlate

from .plotter import Plotter


class ContextLook:


	crimes_chicago = ['ASSAULT', 'BATTERY', 'BURGLARY', 'CRIMINAL DAMAGE',
					 'DECEPTIVE PRACTICE', 'MOTOR VEHICLE THEFT', 'ROBBERY',
					 'THEFT']

	crimes_austin = ['ASSAULT', 'AUTO', 'BURGLARY', 'CRIMINAL', 'FAMILY',
					'POSS', 'THEFT']

	def __init__(self):
		self.MONTHS = {
					1  : 'January',
					2  : 'February',
					3  : 'March',
					4  : 'April',
					5  : 'May',
					6  : 'June',
					7  : 'July',
					8  : 'August',
					9  : 'September',
					10 : 'October',
					11 : 'November',
					12 : 'December',
		}

		self.plotter = Plotter()

	def remove_invalid_coord(self, df):
		return df.query('lat != 0 & lon != 0')


	def read_data(self, folder, file):

		data_file = open(folder + file, 'r')

		context_list = []

		for line in data_file:
			line = line.strip().split('\t')

			item = {}
			item['datetime'] = pd.to_datetime(str(line[0]))
			item['hour'] = pd.to_datetime(str(line[0])).hour
			item['minute'] = pd.to_datetime(str(line[0])).minute
			item['lat'] = float(line[1])
			item['lon'] = float(line[2])
			item['type'] = line[3].strip().split()[0]

			context_list.append(item)

		data_file.close()

		df = pd.DataFrame(context_list)
		df['dayofweek'] = df['datetime'].dt.dayofweek
		df.set_index('datetime', inplace=True)

		return self.remove_invalid_coord(df)


	def read_data_folder(self):

		dfs = {}

		folder = './data/cleaned/'
		for file in listdir(folder):

			if 'chicago' in file and 'crime' in file:
				print('! File: {0}'.format(file))
				dfs[file] = self.read_data(folder, file)

		return dfs


	def filter_daily(self, df, dayofweek):

		df_filtered = df.query('dayofweek ==' + str(dayofweek))
		return df_filtered


	def make_gauss(self, N=1, sig=1, mu=0):
		return lambda x: N/(sig * (2*np.pi)**.5) * np.e ** (-(x-mu)**2/(410 * sig**2))
		# return lambda x: N/(sig * (2*np.pi)**.5) * np.e ** (-(x-mu)**2/(105 * sig**2))


	def calculate_difference(self, hour, minute, ref_hour, ref_minute):

		time = hour*60 + minute
		ref_time = ref_hour*60 + ref_minute

		xt = time - ref_time

		score = self.make_gauss()(xt)

		return float('%.5f' % (score))


	def normalize(self, window_scores):

		maxi = np.amax(window_scores)
		mini = np.amin(window_scores)

		for indx, w in enumerate(window_scores):
			window_scores[indx] = (w - mini) / (maxi - mini)

		return window_scores


	def calculate_score(self, crimes_filtered):

		window_scores = []

		for hour in range(0, 24):

			for minute in range(0, 60, 10):

				state_score = []
				for index, row in crimes_filtered.iterrows():
					state_score.append(self.calculate_difference(row['hour'], row['minute'], hour, minute))

				window_scores.append(np.sum(state_score))

		return self.normalize(window_scores)


	def identify_window(self, window_scores, peaks):

		last_peak = 0
		apeaks = []

		peaks.append(len(window_scores)-1)

		for peak in peaks:

			mini = last_peak + np.argmin(window_scores[last_peak:peak])

			if window_scores[mini] == 0.0:
				apeaks.append(mini)

				zero_indx = mini
				while zero_indx < len(window_scores) and window_scores[zero_indx] == 0.0:
					zero_indx += 1

				apeaks.append(zero_indx-1)

			else:
				apeaks.append(mini)

			last_peak = peak

		if apeaks[0] < 3:
			apeaks[0] = 0
		if apeaks[0] != 0:
			apeaks.insert(0, 0)

		if apeaks[-1] > len(window_scores) - 3:
			apeaks[-1] = len(window_scores) - 1
		elif apeaks[-1] != len(window_scores)-1:
			apeaks.append(len(window_scores)-1)

		return apeaks


	def get_window(self, start, end, crimes_filtered):

		start_hour = start * 10 // 60
		start_minute = start * 10 % 60

		end_hour = end * 10 // 60
		end_minute = end * 10 % 60

		# Filter the closed interval
		crimes_opened = crimes_filtered.query('hour > {0} & hour < {1}'.format(start_hour, end_hour))

		# Filter the opened interval
		crimes_closed_low = crimes_filtered.query('hour == {0} & minute >= {1}'.format(start_hour, start_minute))
		crimes_closed_high = crimes_filtered.query('hour == {0} & minute < {1}'.format(end_hour, end_minute))

		return pd.concat([crimes_opened, crimes_closed_low, crimes_closed_high])


	def format_data(self, data):

		if data is None:
			return []

		formatted_data = []

		for indx, row in data.iterrows():
			formatted_data.append((row['lat'], row['lon']))

		return formatted_data


	def smooth_scores(self, window_scores):
		return wiener(window_scores)


	def find_window(self, data, day='monday', month=1, ep=0.01):

		dict_data = {}

		window_scores = self.calculate_score(data)
		window_scores = list(self.smooth_scores(window_scores))
		#self.plotter.plot_window_comparison(window_scores, window_scores2)

		if self.do_i_diff:
			self.weekly_out.append(window_scores)
			self.monthly_out.append(window_scores)

		if self.do_i_window:
			self.plotter.add_one_more(window_scores)

		return 0


	def process(self, month_data, key, day, month):

		windows = {}

		if 'crimes' in key:

			crimes = month_data.groupby('type').all().index

			for crime in crimes:
				if (crime in self.crimes_chicago or crime in self.crimes_austin) and crime == 'ASSAULT':
					crimes_filtered = month_data.query("type == '%s'" % crime)
					dict_data = self.find_window(crimes_filtered, day, month)
					windows[crime] = dict_data
		else:
			dict_data = self.find_window(month_data, ep=0.02)
			windows['unkown'] = dict_data

		if self.do_i_window:
			self.plotter.plot_many_windows(key)

		return windows


	def get_distribution(self, day_data):

		distribution = []

		for hour in range(0, 24):

			for minute in range(0, 60, 30):

				data_ranged = day_data.query('hour == {0} & minute >= {1} & minute < {2}'.format(hour, minute, minute + 30))
				distribution.append(data_ranged.shape[0])

		return distribution


	def call_plot_all(self, out, file_name='w'):

		self.plotter.initialize_window()

		for o in out:
			self.plotter.add_one_more(o)

		if self.week:
			self.plotter.plot_many_windows(file_name)
		else:
			self.plotter.plot_many_windows(file_name)


	def my_correlate(self, out1, out2):

		diff = []
		for i in range(len(out1)):

			res = 0
			if out1[i] > out2[i]:
				res = out1[i]-out2[i]
			else:
				res = out2[i]-out1[i]

			diff.append(res)

		return diff


	def my_buffer_correlate(self, out1, out2):

		diff = []
		for i in range(len(out1)):

			res = 0
			if out1[i] > out2[i]:
				res = out1[i]-out2[i]
			else:
				res = out2[i]-out1[i]

			diff.append(res)

		close_data = [d for d in diff if d < 0.1]

		return float('{0:.2f}'.format((len(close_data)*100) / len(out1)))


	# (SUM x_n + y_N) / sqrt( SUM x_n^2 * y_n^2)
	def find_correlate(self):

		out = []

		if self.week:
			out = self.weekly_out
		else:
			out = self.monthly_out

		self.call_plot_all(out, file_name='win')

		comparisons = []

		for i in range(len(out)):

			x, y = i, i+1
			if i == len(out) - 1:
				y = 0

			corr = self.my_buffer_correlate(out[x], out[y])
			# corr = correlate(out[0], out[0], mode='valid', method='fft')
			comparisons.append(corr)

		# self.call_plot_all(comparisons, file_name='comp')

		ds = [np.amax(c) for c in comparisons]
		print(ds)


	def find_correlate_all(self):

		out = self.monthly_out

		compare_months = []

		for i in range(0, len(out), 7):

			compare_days = []

			for j in range(i, i+7):

				x, y = j, j+1

				if y == i + 7:
					y = i

				corr = self.my_buffer_correlate(out[x], out[y])
				compare_days.append(corr)

			compare_months.append(compare_days)

		print(compare_months)

		self.plotter.plot_all_correlations(compare_months)


	def main_window(self):

		print('!# Begin')

		self.do_i_kde = False
		self.do_i_window = True
		self.do_i_diff = False

		print('! Read all files')
		dfs = self.read_data_folder()

		print('! Process files')

		for indx_day, day in enumerate(['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']):

			print('! Day: {0}'.format(day))
			output_data = {}

			for key in dfs:

				self.plotter.initialize_window()

				print('! File: {0}'.format(key))

				day_data = self.filter_daily(dfs[key], indx_day)

				for month in range(1, 13):

					print('! Month: {0}'.format(self.MONTHS[month]))

					month_data = day_data['2018-' + str(month)]

					windows = self.process(month_data, key)

					break

		print('!# End')


	def main_kde(self):

		print('!# Begin')

		self.do_i_kde = True
		self.do_i_window = False
		self.do_i_diff = False

		print('! Read all files')
		dfs = self.read_data_folder()

		print('! Process files')

		for indx_day, day in enumerate(['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']):

			print('! Day: {0}'.format(day))

			for key in dfs:

				print('! File: {0}'.format(key))
				key_output = {}

				if self.do_i_kde:
					self.plotter.plot_kde(dfs[key], key)

			if self.do_i_kde:
				exit()


	def main_see_diff(self):

		print('!# Begin')

		self.do_i_kde = False
		self.do_i_window = False
		self.do_i_diff = True

		self.week = True

		print('! Read all files')
		dfs = self.read_data_folder()

		print('! Process files')

		self.weekly_out = []
		self.monthly_out = []

		for indx_day, day in enumerate(['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']):

			print('! Day: {0}'.format(day))

			for key in dfs:

				print('! File: {0}'.format(key))

				day_data = self.filter_daily(dfs[key], indx_day)

				for month in range(1, 13):

					print('! Month: {0}'.format(self.MONTHS[month]))

					month_data = day_data['2018-' + str(month)]

					self.process(month_data, key, day, month)

					if self.week:
						break

				if not self.week:
					break

			if not self.week:
				break

		self.find_correlate()

	def see_diff_all(self):

		self.do_i_kde = False
		self.do_i_window = False
		self.do_i_diff = True

		print('! Read all files')
		dfs = self.read_data_folder()

		print('! Process files')

		self.weekly_out = []
		self.monthly_out = []

		for key in dfs:

			print('! File: {0}'.format(key))

			df_key = dfs[key]

			for month in range(1, 13):

				print('! Month: {0}'.format(self.MONTHS[month]))

				month_data = df_key['2018-' + str(month)]

				for indx_day, day in enumerate(['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']):

					print('! Day: {0}'.format(day))

					day_data = self.filter_daily(month_data, indx_day)
					self.process(day_data, key, day, month)

			break

		self.find_correlate_all()

		# self.plotter.plot_all_correlations([[46.53, 43.06, 49.31, 39.58, 45.83, 33.33, 38.19], [46.53, 36.11, 43.06, 40.28, 29.17, 26.39, 38.89], [38.19, 35.42, 33.33, 41.67, 34.72, 38.89, 37.5], [49.31, 51.39, 53.47, 41.67, 47.92, 38.19, 35.42], [49.31, 43.06, 45.83, 49.31, 43.06, 23.61, 27.08], [38.89, 45.83, 34.03, 25.0, 35.42, 52.08, 36.81], [50.69, 34.03, 46.53, 34.03, 40.28, 30.56, 27.08], [40.97, 44.44, 38.89, 39.58, 45.83, 29.86, 44.44], [37.5, 59.03, 47.92, 31.94, 41.67, 39.58, 37.5], [46.53, 44.44, 39.58, 40.28, 34.03, 45.83, 36.11], [31.94, 40.28, 54.17, 43.75, 39.58, 27.78, 30.56], [36.11, 48.61, 50.0, 42.36, 31.25, 38.19, 27.08]])


	def main_pure_data(self):

		print('! Read all files')
		dfs = self.read_data_folder()

		print('! Process files')

		self.monthly_out = []

		for key in dfs:

			print('! File: {0}'.format(key))

			df_key = dfs[key]

			for month in range(1, 13):
			# month = 1

				print('! Month: {0}'.format(self.MONTHS[month]))
				month_data = df_key['2018-' + str(month)]

				for indx_day, day in enumerate(['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']):

					print('! Day: {0}'.format(day))

					day_data = self.filter_daily(month_data, indx_day)
					day_data = day_data.query("type == 'ASSAULT'")

					distribution = self.get_distribution(day_data)

					self.monthly_out.append(distribution)

					self.plotter.plot_distribution(distribution, self.MONTHS[month], day)

		for indx_day, day in enumerate(['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']):

			dayly = []

			for i in range(indx_day, len(self.monthly_out), 7):

				dayly.extend(self.monthly_out[i])

			self.plotter.plot_distribution(dayly, 'year', day)

		# self.find_correlate_all()


	def main(self):

		self.main_pure_data()
