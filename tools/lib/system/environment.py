
import collections
import re
import numpy
import random

from lib.system.vertices import (ProgramPointVertex, 
                                 SubprogramVertex)
from lib.system import directed_graphs
from lib.utils import dot
from lib.utils import globals


def generate_program():
    program = Program()
    for function_id in range(1, globals.args['subprograms'] + 1):
        function_name = 'f{}'.format(function_id)
        control_flow_graph = directed_graphs.create_control_flow_graph\
                                (function_name)
        program[function_name] = control_flow_graph
        dot.make_file(control_flow_graph)
    
    # For each control flow graph, work out which basic blocks can legitimately 
    # make calls.
    call_site_candidates = {}
    for control_flow_graph in program:
        depth_first_search = directed_graphs.DepthFirstSearch(control_flow_graph, 
                                                              control_flow_graph.entry_vertex,
                                                              False)
        candidates_for_this_function = []
        for vertex in control_flow_graph:
            if vertex.number_of_successors() == 1:
                succ_vertex = control_flow_graph.get_vertex(vertex.
                                                            get_ith_successor_edge(0).
                                                            vertex_id)
                # Check that the sole successor is not a loop header.
                if (vertex, succ_vertex) not in depth_first_search.backedges:
                    candidates_for_this_function.append(vertex)
        call_site_candidates[control_flow_graph.name] = candidates_for_this_function
    
    # Sort the functions by the number of call sites.
    function_ordering = collections.OrderedDict(sorted(call_site_candidates.items(), 
                                                       key=lambda tup: len(tup[1]),
                                                       reverse=True))
    
    # Assign each function a level in the call graph.
    levels_in_call_graph = {}
    level = 0
    for function_name in function_ordering.keys():
        levels_in_call_graph.setdefault(level, []).append(function_name)
        if level == 0:
            level += 1
        elif bool(random.getrandbits(1))\
        and len(call_site_candidates[function_name]) > 0:
            level += 1
    
    # Add acyclic call graph edges by finding a caller that is at a lower level
    # than the callee.       
    for level in sorted(levels_in_call_graph.keys(), reverse=True):
        if level > 0:
            for callee in levels_in_call_graph[level]:
                if random.random() < 0.2:
                    level_lower_than_current = random.randint(0, level-1)
                else:
                    level_lower_than_current = level-1
                    
                candidate_callers = levels_in_call_graph[level_lower_than_current]
                caller = candidate_callers[random.randint(0, len(candidate_callers)-1)]
                call_site_index = random.randint(0, len(call_site_candidates[caller])-1)
                call_site_vertex = call_site_candidates[caller][call_site_index]
                call_site_candidates[caller].remove(call_site_vertex)
                program.call_graph.add_edge(program.call_graph.get_vertex_with_name(caller),
                                            program.call_graph.get_vertex_with_name(callee),
                                            call_site_vertex.vertex_id)
                if len(call_site_candidates[caller]) == 0:
                    candidate_callers.remove(caller)
                    
    # Now that we have tried our best so that there is a path from a designated
    # root vertex to every function, add acyclic edges indiscriminately.
    for level in sorted(levels_in_call_graph.keys(), reverse=True):
        if level > 0:
            for callee in levels_in_call_graph[level]:
                if bool(random.getrandbits(1)):
                    while True:
                        level_lower_than_current = random.randint(0, level-1)
                        candidate_callers = levels_in_call_graph[level_lower_than_current]
                        if candidate_callers:
                            caller = candidate_callers[random.randint(0, len(candidate_callers)-1)]
                            call_site_index = random.randint(0, len(call_site_candidates[caller])-1)
                            call_site_vertex = call_site_candidates[caller][call_site_index]
                            call_site_candidates[caller].remove(call_site_vertex)
                            program.call_graph.add_edge(program.call_graph.get_vertex_with_name(caller),
                                                        program.call_graph.get_vertex_with_name(callee),
                                                        call_site_vertex.vertex_id)
                            if len(call_site_candidates[caller]) == 0:
                                candidate_callers.remove(caller)
                        else:
                            break
    dot.make_file(program.call_graph)
    return program


def write_program_to_file(program):
    with open(globals.args['program_file'], 'w') as the_file:
        for control_flow_graph in program:
            the_file.write('{}\n'.format(control_flow_graph.name))
            for vertex in control_flow_graph:
                if vertex != control_flow_graph.exit_vertex:
                    for succ_edge in vertex.successor_edge_iterator():
                        the_file.write('{}-{}\n'.format(vertex.vertex_id, 
                                                        succ_edge.vertex_id))
            the_file.write('\n')


def create_program_from_input_file():
    program = Program()
    
    def parse_int(value):
        try:
            return int(value)
        except ValueError:
            raise ValueError('Unable to convert {} into an integer'.\
                             format(value))

    
    edges_in_control_flow_graphs = collections.OrderedDict()
    def create_control_flow_graphs(): 
        for function_name, edge_list in edges_in_control_flow_graphs.items():
            control_flow_graph = directed_graphs.ControlFlowGraph(function_name)
            # Add vertices to control flow graph representing basic blocks
            for an_edge in edge_list:
                pred_id = parse_int(an_edge[0])
                succ_id = parse_int(an_edge[1])
                if not control_flow_graph.has_vertex(pred_id):
                    control_flow_graph.add_vertex(ProgramPointVertex
                                                  (pred_id, pred_id))
                if not control_flow_graph.has_vertex(succ_id):
                    control_flow_graph.add_vertex(ProgramPointVertex
                                                  (succ_id, succ_id))
            # Add vertices to control flow graph representing transitions and
            # then link these to basic blocks
            for an_edge in edge_list:
                pred_id = parse_int(an_edge[0])
                succ_id = parse_int(an_edge[1])
                vertex = ProgramPointVertex\
                            (control_flow_graph.get_new_vertex_id(),
                             (pred_id, succ_id))
                control_flow_graph.add_vertex(vertex)
                control_flow_graph.add_edge(control_flow_graph.get_vertex(pred_id),
                                            vertex)
                control_flow_graph.add_edge(vertex,
                                            control_flow_graph.get_vertex(succ_id))
            # Find entry and exit vertex, then add vertex representing an edge 
            # from the exit vertex to the entry vertex 
            control_flow_graph.set_entry_vertex()
            control_flow_graph.set_exit_vertex()
            control_flow_graph.add_exit_to_entry_edge()
            program[function_name] = control_flow_graph
            dot.make_file(control_flow_graph)
    
    
    edges_in_call_graph = set()
    def create_call_graph():
        for call_site_id, caller, callee in edges_in_call_graph:
            if program.call_graph.has_vertex_with_name(caller)\
            and program.call_graph.has_vertex_with_name(callee):
                pred_call_vertex = program.call_graph.get_vertex_with_name(caller)
                succ_call_vertex = program.call_graph.get_vertex_with_name(callee)
                program.call_graph.add_edge(pred_call_vertex, 
                                            succ_call_vertex, 
                                            parse_int(call_site_id))
        dot.make_file(program.call_graph)
    
    
    function_name_regex = re.compile(r'[a-zA-Z]\w+')
    edge_regex = re.compile(r'\d+-\w+$')
    basic_block_id_regex = re.compile(r'\d+')
    program_property_regex = re.compile(r'(\d+|\d+-\d+)\.[a-zA-Z]+')
    delimiter_regex = re.compile(r'(\-|\.|=)')
        
    def first_pass_of_input_file():
        with open(globals.args['program_file']) as the_file:
            for line in the_file:
                if re.match(r'\S', line):
                    line = ''.join(line.lower().split())
                    if function_name_regex.match(line):
                        if globals.args['functions'] is None\
                        or line in globals.args['functions']:
                            current_function = line
                            edges_in_control_flow_graphs[current_function] = set()
                        else:
                            current_function = None
                    elif current_function and edge_regex.match(line): 
                        source, destination = line.split('-')
                        if basic_block_id_regex.match(destination):
                            edges_in_control_flow_graphs[current_function].\
                                add((source, destination))
                        else:
                            edges_in_call_graph.add((source, 
                                                     current_function, 
                                                     destination))
                        
                        
    def second_pass_of_input_file():
        with open(globals.args['program_file']) as the_file:
            for line in the_file:
                if re.match(r'\S', line):
                    line = ''.join(line.lower().split())
                    if function_name_regex.match(line):
                        if globals.args['functions'] is None\
                        or line in globals.args['functions']:
                            current_function = line
                            control_flow_graph = program[current_function]
                        else:
                            current_function = None
                    elif current_function and program_property_regex.match(line):
                        lexemes = delimiter_regex.split(line)
                        if len(lexemes) == 5:
                            # Vertex program point.
                            program_point = parse_int(lexemes[0])
                            property_index = 2
                        else:
                            # Edge program point.
                            program_point = (parse_int(lexemes[0]), 
                                             parse_int(lexemes[2]))
                            property_index = 4
                        
                        if lexemes[property_index] == 'instrument':
                            if lexemes[-1].startswith('t'):
                                control_flow_graph.\
                                program_point_data.\
                                set_instrumented(program_point, True)
                            else:
                                control_flow_graph.\
                                program_point_data.\
                                set_instrumented(program_point, False)
                        elif lexemes[property_index] == 'wcet':
                            control_flow_graph.\
                            program_point_data.\
                            set_wcet(program_point, parse_int(lexemes[-1]))
                        elif lexemes[property_index] == 'loop_bound':
                            assert lexemes[-1][0] == '(' \
                            and lexemes[-1][len(lexemes[-1])-1] == ')'
                            # Strip parentheses from tuple
                            loop_bound_tuple = lexemes[-1][1:len(lexemes[-1])-1]
                            loop_bound_tuple = numpy.array([parse_int(val) for val in 
                                                            loop_bound_tuple.split(',')])
                            control_flow_graph.\
                            program_point_data.\
                            set_loop_bound(program_point, loop_bound_tuple)
                        else:
                            assert False, 'Unknown program point property {}'.\
                            format(lexemes[property_index])   
                                
    
    first_pass_of_input_file()  
    create_control_flow_graphs()
    create_call_graph()
    second_pass_of_input_file()
    return program



class Program:
    
    """
    Models a program as a set of graphs.  These graphs always include the
    control flow graphs of each function and a call graph.  Other graphs,
    like a call-context graph, may be included as well, but it depends on
    the purpose of the analysis.
    """
    
    def __init__(self):
        self._call_graph = directed_graphs.CallGraph()
        self._control_flow_graphs = collections.OrderedDict()
        
    
    @property
    def call_graph(self):
        return self._call_graph
    
    
    @call_graph.setter
    def call_graph(self, value):
        self._call_graph = value
    
    
    def __delitem__(self, function_name):
        try:
            del self._control_flow_graphs[function_name]
            call_vertex = self._call_graph.get_vertex_with_name(function_name)
            self._call_graph.remove_vertex(call_vertex)
        except KeyError:
            raise KeyError('No function called {} to delete'.
                           format(function_name))
    
    
    def __setitem__(self, function_name, control_flow_graph):
        assert function_name not in self._control_flow_graphs,\
            'Duplicate control flow graph with name {}'.\
            format(function_name)
        self._control_flow_graphs[function_name] = control_flow_graph
        self._call_graph.add_vertex(SubprogramVertex
                                    (self._call_graph.get_new_vertex_id(),
                                     control_flow_graph.name))
    
    
    def __getitem__(self, function_name):
        try:
            return self._control_flow_graphs[function_name]
        except KeyError:
            raise KeyError('Unable to find control flow graph for function {}'.\
                           format(function_name))
    
    
    def __contains__(self, function_name):
        return function_name in self._control_flow_graphs
        
    
    def __iter__(self):
        for control_flow_graph in self._control_flow_graphs.values():
            yield control_flow_graph
    
    
    def __len__(self):
        return len(self._control_flow_graphs)

