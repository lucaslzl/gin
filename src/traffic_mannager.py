import traci
import logging
import networkx as nx
import random
import json


CONTEXT_CONFIG = {'0' : {'traffic': 1, 'crimes': 1, 'crashes': 0},
                  '1' : {'traffic': 1, 'crimes': 0, 'crashes': 1},
                  '2' : {'traffic': 0, 'crimes': 1, 'crashes': 0},
                  '3' : {'traffic': 0, 'crimes': 0, 'crashes': 1},
                  '4' : {'traffic': 0, 'crimes': 1, 'crashes': 1}}


def invert_coords(coord):
    return (coord[1], coord[0])


def update_road_map(road_map, road, metrics):

    for key in metrics:
        road_map[road][key] = metrics[key]


def output_ids_coords(graph):

    just_to_save = {}

    for road in graph.nodes():

        road_coords = []
        lane_coords = traci.lane.getShape(str(road) + "_0")

        for lc in lane_coords:
            coord = traci.simulation.convertGeo(*lc)
            road_coords.append((coord[1], coord[0]))

        just_to_save[road] = road_coords

    with open('./routing/mapping/ids_and_coords.json', "w") as write_file:
        json.dump(just_to_save, write_file, indent=4)


def update_context_on_roads(graph, contextual, step_time, indx_config, road_map, next_windows, crime_type):

    #output_ids_coords(graph)
    
    for road in graph.nodes():

        if road not in road_map.keys():
            road_map[str(road)] = {'traffic': 0, 'crimes': 0, 'crashes': 0, 'popularity': {'weight': {}, 'count': {}}}

        # Traffic
        average_speed = traci.edge.getLastStepMeanSpeed(road)
        max_speed = traci.lane.getMaxSpeed(str(road) + "_0")
        traffic = float(max_speed - average_speed) / float(max_speed)

        # Geo coordinates
        lane_coords = traci.lane.getShape(str(road) + "_0")
        start = traci.simulation.convertGeo(*lane_coords[0])
        end = traci.simulation.convertGeo(*lane_coords[1])

        start = invert_coords(start)
        end = invert_coords(end)

        weight, metrics, next_windows = contextual.trade_off(traffic, start, end, step_time, crime_type, context_weight=CONTEXT_CONFIG[str(indx_config)])
        update_road_map(road_map, str(road), metrics)

        for successor_road in graph.successors(road):
            graph.adj[road][successor_road]["weight"] = weight

            if successor_road in road_map[str(road)]['popularity']['weight']:

                if successor_road not in road_map[str(road)]['popularity']['weight'][successor_road]:
                    road_map[str(road)]['popularity']['weight'][successor_road] = 0
                    road_map[str(road)]['popularity']['count'][successor_road] = 0

                road_map[str(road)]['popularity']['weight'][successor_road] = weight

    return graph, next_windows


def update_weight_by_popularity(graph, road, road_map):

    for successor_road in graph.successors(road):

        if successor_road in road_map[str(road)]['popularity']['count']:

            road_map[str(road)]['popularity']['count'][successor_road] += 1
            
            length = traci.lane.getLength(str(road) + "_0")
            lines = traci.edge.getLaneNumber(road)
            laststep_vehicles = traci.edge.getLastStepVehicleNumber(road)

            road_capacity = (length * lines) / 5
            vehicle_load = laststep_vehicles + road_map[str(road)]['popularity']['count'][successor_road]
            load_percentage = vehicle_load / road_capacity

            graph.adj[road][successor_road]["weight"] = road_map[str(road)]['popularity']['weight'][successor_road] + road_map[str(road)]['popularity']['weight'][successor_road] * load_percentage


def reroute_vehicles(graph, p, indx_config, road_map):

    vehicles = list(set(traci.vehicle.getIDList()))
    vehicles.sort()

    for vehicle in vehicles:

        source = traci.vehicle.getRoadID(vehicle)
        if source.startswith(":"): continue
        route = traci.vehicle.getRoute(vehicle)
        destination = route[-1]

        if source != destination:

            logging.debug("Calculating optimal path for pair (%s, %s)" % (source, destination))

            shortest_path = None

            if indx_config == 0:
                indx_source = route.index(source)
                shortest_path = [1, route[indx_source:]]
            else:
                shortest_path = nx.algorithms.shortest_paths.weighted.bidirectional_dijkstra(graph, source, destination, "weight")

            traci.vehicle.setRoute(vehicle, shortest_path[1])

            for vertex in list(shortest_path[1]):

                update_weight_by_popularity(graph, vertex, road_map)

