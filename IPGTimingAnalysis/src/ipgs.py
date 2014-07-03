import directed_graphs
import trees
import vertices
import edges
import debug

edge_ID = 0

class IPG (directed_graphs.FlowGraph):
    def __init__(self, icfg):
        directed_graphs.FlowGraph.__init__(self)
        self.name = icfg.name
        self.add_vertices(icfg)
        self.add_edges(icfg)
        self.set_entry_and_exit(icfg)
    
    def add_vertices(self, icfg):
        for v in icfg:
            if v.is_ipoint:
                newv = vertices.CFGVertex(v.vertexID, True)
                self.the_vertices[v.vertexID] = newv
                
    def add_edges (self, icfg):
        vertex_to_reachable = {}
        for v in icfg:
            vertex_to_reachable[v.vertexID] = {}
        # Do data-flow analysis
        dfs     = trees.DepthFirstSearch(icfg, icfg.get_entryID())
        changed = True
        while changed:
            changed = False
            for vertexID in reversed(dfs.getPostorder()):
                v = icfg.getVertex(vertexID)
                for predID in v.predecessors.keys():
                    predv = icfg.getVertex(predID)
                    if predv.is_ipoint:
                        if predID not in vertex_to_reachable[vertexID]:
                            changed = True
                            vertex_to_reachable[vertexID][predID] = set()
                            if not v.is_ipoint:
                                vertex_to_reachable[vertexID][predID].add(v)
                    else:
                        for keyID in vertex_to_reachable[predID]:
                            if keyID not in vertex_to_reachable[vertexID]:
                                changed = True
                                vertex_to_reachable[vertexID][keyID] = set()
                                vertex_to_reachable[vertexID][keyID].update(vertex_to_reachable[predID][keyID])
                                if not v.is_ipoint:
                                    vertex_to_reachable[vertexID][keyID].add(v)
                            else:
                                oldSize = len(vertex_to_reachable[vertexID][keyID])
                                vertex_to_reachable[vertexID][keyID].update(vertex_to_reachable[predID][keyID])
                                newSize = len(vertex_to_reachable[vertexID][keyID])
                                if newSize != oldSize:
                                    changed = True
        # Now add the edges 
        for vertexID, ipointToVertexSet in vertex_to_reachable.iteritems():
            v = icfg.getVertex(vertexID)
            if v.is_ipoint:
                for predID, vertex_set in ipointToVertexSet.iteritems():
                    self.add_edge(predID, vertexID, vertex_set)
    
    def add_edge (self, predID, succID, vertex_set):
        global edge_ID
        edge_ID += 1
        predv = self.getVertex(predID)
        succv = self.getVertex(succID)
        prede = edges.IPGEdge(predID, edge_ID)
        succe = edges.IPGEdge(succID, edge_ID)
        prede.edge_label.update(vertex_set)
        succe.edge_label.update(vertex_set)
        predv.add_successor_edge(succe)
        succv.add_predecessor_edge(prede) 
                    
    def set_entry_and_exit(self, icfg):
        entryv = self.the_vertices[icfg.get_entryID()]
        self.entryID = entryv.vertexID
        assert entryv.number_of_predecessors() == 1, "Entry vertex %s of IPG has multiple predecessors" % self._entryID
        for predID in entryv.predecessors.keys():
            self.exitID = predID

class LoopIPG():    
    def __init__ (self, loop_by_loop_info, headerID, icfg, lnt, ipg):
        self.edges_added                 = set()
        self.loop_by_loop_info           = loop_by_loop_info
        self.__icfg                      = icfg
        self.__lnt                       = lnt
        self.__ipg                       = ipg
        self.inner_loop_ipoints          = {}
        self.vertex_to_reachable         = {}
        self.iteration_edge_destinations = set()
        self.iteration_edge_sources      = set()
        self.initialise(headerID)
        self.add_acyclic_edges(headerID)
        self.add_iteration_edges(headerID)
                
    def initialise(self, headerID):
        for v in self.__icfg:
            # No ipoint or header can reach any vertex
            self.vertex_to_reachable[v.vertexID] = set()
            if v.vertexID == self.__icfg.get_entryID() and not self.__ipg.hasVertex(v.vertexID):
                # The vertex is a header and it is not an ipoint.
                # Add the vertex to its reachable set so we can work out
                # which ipoints are reachable from the header
                self.vertex_to_reachable[v.vertexID].add(v.vertexID)
        headerv = self.__lnt.getVertex(self.__lnt.getVertex(headerID).get_parentID())
        for succID in headerv.successors.keys():
            succv = self.__lnt.getVertex(succID)
            if isinstance(succv, vertices.HeaderVertex):
                self.compute_inner_loop_ipoints(succv)
                        
    def compute_inner_loop_ipoints(self, headerv):
        stack = []
        stack.append(headerv)
        while stack:
            poppedv = stack.pop()
            for succID in poppedv.successors.keys():
                succv = self.__lnt.getVertex(succID)
                stack.append(succv)
                if self.__ipg.hasVertex(succID):
                    self.inner_loop_ipoints[succID] = headerv.headerID
                
    def add_acyclic_edges (self, headerID):
        # Compute a topological sort on the ICFG
        dfs = trees.DepthFirstSearch(self.__icfg, self.__icfg.get_entryID())
        if  self.__ipg.hasVertex(self.__icfg.get_entryID()):
            # If the header of the loop is an ipoint then it is the only 
            # destination of an iteration edge
            self.iteration_edge_destinations.add(self.__icfg.get_entryID())
        # Perform data-flow analysis
        changed = True
        while changed:
            changed = False
            for vertexID in reversed(dfs.getPostorder()):
                debug.debug_message("At vertex %d" % vertexID, __name__, 1)
                v = self.__icfg.getVertex(vertexID)
                if self.__lnt.isLoopHeader(vertexID) and vertexID != self.__icfg.get_entryID():
                    # Inner header detected
                    self.add_loop_entry_edges(v)
                    self.add_ipoints_to_abstract_vertex(v)
                else:
                    for predID in v.predecessors.keys():
                        if self.__ipg.hasVertex(predID):
                            if self.__ipg.hasVertex(vertexID):
                                self.add_edge(predID, vertexID)
                            else:
                                self.vertex_to_reachable[vertexID].add(predID)
                        else:
                            for keyID in self.vertex_to_reachable[predID]:
                                if self.__ipg.hasVertex(keyID) and self.__ipg.hasVertex(vertexID):
                                    self.add_edge(keyID, vertexID)
                                elif not self.__ipg.hasVertex(keyID) and self.__ipg.hasVertex(vertexID):
                                    self.iteration_edge_destinations.add(vertexID)
                                else:
                                    self.vertex_to_reachable[vertexID].add(keyID)    
            if vertexID in self.__lnt.getLoopTails(headerID):
                if self.__ipg.hasVertex(vertexID):
                    self.iteration_edge_sources.add(vertexID)
                else:
                    for keyID in self.vertex_to_reachable[vertexID]:
                        if self.__ipg.hasVertex(keyID):
                            self.iteration_edge_sources.add(keyID)
                            
    def add_loop_entry_edges (self, v):
        debug.debug_message("Inner header %d detected" % v.vertexID, __name__, 1)
        inner_loop_info = self.loop_by_loop_info.loop_IPGs[v.vertexID]        
        for predID in v.predecessors.keys():
            if self.__ipg.hasVertex(predID):
                for succID in inner_loop_info.iteration_edge_destinations:
                    self.add_edge(predID, succID)
            else:
                for keyID in self.vertex_to_reachable[predID]:
                    if self.__ipg.hasVertex(keyID):
                        for succID in inner_loop_info.iteration_edge_destinations:
                            self.add_edge(keyID, succID)
                    else:
                        # The key is a header vertex. 
                        # This means that all the destinations of iteration edges of 
                        # the inner loop are also destinations of iterations edges of 
                        # the outer loop 
                        self.iteration_edge_destinations.update(inner_loop_info.iteration_edge_destinations)
        
    def add_ipoints_to_abstract_vertex(self, v):
        headerID        = v.vertexID
        inner_loop_info = self.loop_by_loop_info.loop_IPGs[headerID]
        ipoint_free_path_through_loop = False
        for exitID in self.__lnt.getLoopExits(headerID):
            # Add ipoints which can reach the loop exit
            if self.__ipg.hasVertex(exitID):
                self.vertex_to_reachable[headerID].add(exitID)
            else:
                for keyID in inner_loop_info.vertex_to_reachable[exitID]:
                    if self.__ipg.hasVertex(keyID):
                        self.vertex_to_reachable[headerID].add(keyID)
            if not self.__ipg.hasVertex(exitID) and headerID in inner_loop_info.vertex_to_reachable[exitID]:
                ipoint_free_path_through_loop = True
        
        if not self.__ipg.hasVertex(headerID) and ipoint_free_path_through_loop:
            # Since there is an ipoint-free path through the loop
            # all ipoints which can reach the loop tails can leak in to the outer loop
            for tailID in self.__lnt.getLoopTails(headerID):
                if self.__ipg.hasVertex(tailID):
                    self.vertex_to_reachable[headerID].add(tailID)
                else:
                    for keyID in inner_loop_info.vertex_to_reachable[tailID]:
                        if self.__ipg.hasVertex(keyID):
                            self.vertex_to_reachable[headerID].add(keyID)
            # Similarly for all ipoints which can reach the predecessors
            for predID in v.predecessors.keys():
                if self.__ipg.hasVertex(predID):
                    self.vertex_to_reachable[headerID].add(predID)
                else:
                    for keyID in self.vertex_to_reachable[predID]:
                        self.vertex_to_reachable[headerID].add(keyID)
                        
    def add_iteration_edges (self, headerID):
        for predID in self.iteration_edge_sources:
            for succID in self.iteration_edge_destinations:
                predv = self.__ipg.getVertex(predID)
                succv = self.__ipg.getVertex(succID)
                succe = predv.get_successor_edge(succID)
                prede = succv.get_predecessor_edge(predID)
                succe.iteration_edge = True
                prede.iteration_edge = True
                self.loop_by_loop_info.iteration_edges[headerID].add((predID, succID))
                self.edges_added.add((predID, succID))
                debug.debug_message("(%d, %d) is an iteration edge for loop with header %d" % (predID, succID, headerID), __name__, 1)
                            
    def add_edge(self, predID, succID):
        self.edges_added.add((predID, succID))
        if predID in self.inner_loop_ipoints:
            inner_headerID = self.inner_loop_ipoints[predID]
            debug.debug_message("(%d, %d) is a loop-exit edge for loop with header %d" % (predID, succID, inner_headerID), __name__, 1)
            self.loop_by_loop_info.loop_exit_edges[inner_headerID].add((predID, succID))
        if succID in self.inner_loop_ipoints:
            inner_headerID = self.inner_loop_ipoints[succID]
            debug.debug_message("(%d, %d) is a loop-entry edge for loop with header %d" % (predID, succID, inner_headerID), __name__, 1)
            self.loop_by_loop_info.loop_entry_edges[inner_headerID].add((predID, succID))
    