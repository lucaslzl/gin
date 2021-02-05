import os


class Generator:


	def generate_routes(self, times, cities, random_path, scenario_path):

		if not os.path.exists('./scenario/trips'):
			os.makedirs('./scenario/trips')

		command = ("python {0} --validate "
					"-n {1}/{2}.net.xml "
					"-o ./scenario/trips/{2}_{3}.trips.xml "
					"-s {3} "
					"-p 0.6 --fringe-factor 50 --validate")

		for city in cities:
			for i in range(times):
				os.system(command.format(random_path, scenario_path, city, i))


	def generate_cfg(self, times, cities):

		if not os.path.exists('./scenario/cfgs'):
			os.makedirs('./scenario/cfgs')

		for city in cities:
			for i in range(times):
				file = open('./scenario/cfgs/{0}_{1}.sumo.cfg'.format(city, i), 'w')
				file.write(("<configuration>\n"
						    "\t<input>\n"
						    "\t\t<net-file value='../{0}.net.xml'/>\n"
						    "\t\t<route-files value='../trips/{0}_{1}.trips.xml'/>\n"
						    "\t</input>\n"
							"</configuration>").format(city, i))


	def generate_cfg_week(self, times, cities):

		week = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']

		if not os.path.exists('./scenario/cfgs'):
			os.makedirs('./scenario/cfgs')

		for day in week:

			if not os.path.exists('./scenario/cfgs/' + day):
				os.makedirs('./scenario/cfgs/' + day)

			for city in cities:
				for i in range(times):
					file = open('./scenario/cfgs/{0}/{1}_{2}.sumo.cfg'.format(day, city, i), 'w')
					file.write(("<configuration>\n"
							    "\t<input>\n"
							    "\t\t<net-file value='../../{1}.net.xml'/>\n"
							    "\t\t<route-files value='../../trips/{0}/{1}_{2}.trips.xml'/>\n"
							    "\t</input>\n"
								"</configuration>").format(day, city, i))


	def main(self, times=20, cities=['austin']):

		print('!# Begin')

		# random_path = '/home/eros/Documentos/sumo-0.25.0/tools/randomTrips.py'
		random_path = '/usr/share/sumo/tools/randomTrips.py'
		# scenario_path = '/home/eros/Projects/contextsimulation/scenario'
		scenario_path = '/home/lucaszl/Projetos/contextsimulation/scenario'

		# print('! Generate routes')
		# self.generate_routes(times, cities, random_path, scenario_path)

		print('! Generate cfgs')
		# self.generate_cfg(times, cities)
		self.generate_cfg_week(times, cities)

		print('!# End')


def method():

	path = 'python /usr/share/sumo/tools/route2trips.py -n ./chicago.net.xml ' +\
			'-t ./trips/chicago_1.trips.xml -o routes.rou.xml --ignore-errors --begin 0 --end 3600 ' +\
			'--no-step-log --no-warnings'
	os.system(path)

# method()