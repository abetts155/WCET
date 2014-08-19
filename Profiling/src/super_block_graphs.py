import directed_graphs
import vertices
import debug
import utils
import udraw

class SuperBlockSubgraph(directed_graphs.DirectedGraph):
    def __init__(self):
        directed_graphs.DirectedGraph.__init__(self)
        self.program_point_to_superv = {}
        self.rootv                   = None

class SuperBlockCFG(directed_graphs.DirectedGraph):    
    def __init__(self, cfg):
        directed_graphs.DirectedGraph.__init__(self)    
        self.name              = cfg.name
        self.forward_subgraphs = {}
        self.reverse_subgraphs = {}
        self.super_block_pairs = {}
        lnt                    = cfg.get_loop_nesting_tree()
        for headerv in lnt.get_header_vertices():
            debug.debug_message("Analysing header %d" % headerv.headerID, __name__, 1)
            enhanced_CFG         = lnt.induce_subgraph_with_tails_and_exits(headerv)
            enhanced_CFG_reverse = enhanced_CFG.get_reverse_graph()
            dominator_graph      = DominatorGraph(enhanced_CFG.get_dominator_tree(), enhanced_CFG_reverse.get_dominator_tree())
            udraw.make_file(enhanced_CFG, "%s.header_%d.whole.enhanced_CFG" % (cfg.name, headerv.headerID)) 
            udraw.make_file(enhanced_CFG_reverse, "%s.header_%d.whole.enhanced_CFG_reverse" % (cfg.name, headerv.headerID))                                                                               
            forward_subgraph, reverse_subgraph = self.construct_super_block_cfg(cfg, 
                                                                                lnt, 
                                                                                headerv,
                                                                                enhanced_CFG,
                                                                                enhanced_CFG_reverse,
                                                                                dominator_graph)
            self.forward_subgraphs[headerv.headerID] = forward_subgraph
            self.reverse_subgraphs[headerv.headerID] = reverse_subgraph

    def construct_super_block_cfg(self, cfg, lnt, headerv, enhanced_CFG, enhanced_CFG_reverse, dominator_graph):
        forward_subgraph = SuperBlockSubgraph()
        self.add_super_blocks(lnt, 
                              enhanced_CFG, 
                              enhanced_CFG.get_depth_first_search_tree(), 
                              StrongComponents(dominator_graph), 
                              headerv, 
                              forward_subgraph)     
        self.add_edges(lnt, 
                       enhanced_CFG, 
                       enhanced_CFG.get_depth_first_search_tree(), 
                       headerv, 
                       forward_subgraph)
        
        reverse_subgraph = SuperBlockSubgraph()
        self.add_super_blocks(lnt, 
                              enhanced_CFG_reverse, 
                              enhanced_CFG_reverse.get_depth_first_search_tree(), 
                              StrongComponents(dominator_graph), 
                              headerv, 
                              reverse_subgraph)
        self.add_edges(lnt, 
                       enhanced_CFG_reverse, 
                       enhanced_CFG_reverse.get_depth_first_search_tree(), 
                       headerv, 
                       reverse_subgraph)
        
        for superv in reverse_subgraph:
            if isinstance(superv.representative, vertices.CFGEdge):
                the_edge = superv.representative.edge
                self.super_block_pairs[superv] = forward_subgraph.program_point_to_superv[(the_edge[1], the_edge[0])]
            else:
                self.super_block_pairs[superv] = forward_subgraph.program_point_to_superv[superv.representative.vertexID]
        
        return forward_subgraph, reverse_subgraph
                        
    def add_super_blocks(self, lnt, enhanced_CFG, dfs, sccs, headerv, subgraph):
        for sccID in sccs.scc_vertices.keys():
            superv                                 = vertices.SuperBlock(sccID, headerv.headerID, headerv.headerID != enhanced_CFG.get_entryID())
            subgraph.the_vertices[superv.vertexID] = superv
        for vertexID in reversed(dfs.post_order):
            program_point = enhanced_CFG.getVertex(vertexID)
            if not program_point.dummy: 
                sccID  = sccs.vertex_SCC[vertexID]
                superv = subgraph.getVertex(sccID)
                if isinstance(program_point, vertices.CFGEdge):
                    subgraph.program_point_to_superv[program_point.edge] = superv
                    superv.program_points.append(program_point)
                    if lnt.is_loop_exit_edge_for_header(headerv.headerID, program_point.edge[0], program_point.edge[1]):
                        superv.exit_edge = (program_point.edge[0], program_point.edge[1])
                else:
                    program_point_headerv = lnt.getVertex(lnt.getVertex(program_point.vertexID).parentID)
                    if program_point_headerv.headerID == headerv.headerID:
                        superv.program_points.append(program_point)
                        superv.representative = program_point
                        subgraph.program_point_to_superv[program_point.vertexID] = superv
                    else:
                        superv.program_points.append(program_point_headerv)      
                        subgraph.program_point_to_superv[program_point_headerv.vertexID] = superv
        for superv in subgraph:
            if superv.representative is None:
                # Representative basic block not yet set.
                # Just choose the first program point instead
                superv.representative = superv.program_points[0]
        subgraph.rootv = subgraph.program_point_to_superv[headerv.headerID] 
                
    def add_edges(self, lnt, enhanced_CFG, dfs, headerv, subgraph):
        first_program_point_to_super_block = {}
        for superv in subgraph:
            first_program_point_to_super_block[superv.program_points[0]] = superv
        for vertexID in reversed(dfs.post_order):
            program_point = enhanced_CFG.getVertex(vertexID)
            if program_point in first_program_point_to_super_block:
                superv = first_program_point_to_super_block[program_point]
                if isinstance(program_point, vertices.CFGEdge):
                    if not (lnt.is_loop_back_edge(program_point.edge[0], program_point.edge[1]) 
                            or lnt.is_loop_back_edge(program_point.edge[1], program_point.edge[0])):
                        # The program point represents a CFG edge.
                        # Find the super block which contains the source of the CFG edge 
                        # and link the super blocks
                        basic_block_predID = program_point.edge[0]
                        if lnt.getVertex(lnt.getVertex(basic_block_predID).parentID) == headerv:
                            pred_superv = subgraph.program_point_to_superv[basic_block_predID] 
                            subgraph.addEdge(pred_superv.vertexID, superv.vertexID)
                            assert enhanced_CFG.getVertex(basic_block_predID).number_of_successors() > 1
                            if basic_block_predID not in pred_superv.successor_partitions:
                                pred_superv.successor_partitions[basic_block_predID] = set()
                            pred_superv.successor_partitions[basic_block_predID].add(superv.vertexID)
                        else:
                            inner_headerv = lnt.getVertex(lnt.getVertex(basic_block_predID).parentID)
                            pred_superv   = subgraph.program_point_to_superv[inner_headerv.vertexID] 
                            subgraph.addEdge(pred_superv.vertexID, superv.vertexID)
                            if inner_headerv.headerID not in pred_superv.successor_partitions:
                                pred_superv.successor_partitions[inner_headerv.headerID] = set()
                            pred_superv.successor_partitions[inner_headerv.headerID].add(superv.vertexID)
                            if superv.exit_edge:
                                pred_superv.exit_edge_partitions.add(inner_headerv.headerID)

class DominatorGraph (directed_graphs.DirectedGraph):
    def __init__ (self, predom_tree, postdom_tree):
        directed_graphs.DirectedGraph.__init__(self)
        self.add_vertices(predom_tree, postdom_tree)
        self.add_edges(predom_tree, postdom_tree)
        
    def add_vertices(self, predom_tree, postdom_tree):
        for v in predom_tree:
            assert postdom_tree.hasVertex(v.vertexID), "Vertex %d in pre-dominator tree but not in post-dominator tree" % v.vertexID
            self.the_vertices[v.vertexID] = vertices.Vertex(v.vertexID)        

    def add_edges(self, predom_tree, postdom_tree):
        for v in predom_tree:
            if v.vertexID != predom_tree.getRootID():
                self.addEdge(v.parentID, v.vertexID)
        for v in postdom_tree:
            if v.vertexID != postdom_tree.getRootID(): 
                if not self.getVertex(v.vertexID).has_predecessor(v.parentID):
                    self.addEdge(v.parentID, v.vertexID)

class StrongComponents:
    COLORS = utils.enum('WHITE', 'BLACK', 'GRAY', 'BLUE', 'RED')
    SCCID  = 0
    
    def __init__(self, directedg):
        self.directedg     = directedg
        self.reverseg      = directedg.get_reverse_graph()
        self.vertex_colour = {}
        self.vertex_SCC    = {}
        self.scc_vertices  = {}
        self.initialise()
        self.do_forward_visit()
        self.do_reverse_visit()
        
    def initialise(self):
        for v in self.directedg:
            self.vertex_colour[v.vertexID] = StrongComponents.COLORS.WHITE
            
    def do_forward_visit(self):
        self.vertex_list = []
        for v in self.directedg:
            if self.vertex_colour[v.vertexID] == StrongComponents.COLORS.WHITE:
                self.visit1(v)

    def do_reverse_visit(self):
        for vertexID in reversed(self.vertex_list):
            if self.vertex_colour[vertexID] == StrongComponents.COLORS.BLACK:
                StrongComponents.SCCID += 1
                self.scc_vertices[StrongComponents.SCCID] = set()
                # The vertex v is from the forward directed graph.
                # Need to get the vertex from the reverse graph instead
                self.visit2(self.reverseg.getVertex(vertexID))
    
    def visit1(self, v):
        stack = []
        stack.append(v)
        while stack:
            poppedv = stack.pop()
            if self.vertex_colour[poppedv.vertexID] == StrongComponents.COLORS.WHITE:
                self.vertex_colour[poppedv.vertexID] = StrongComponents.COLORS.GRAY
                stack.append(poppedv)
                for succID in poppedv.successors.keys():
                    if self.vertex_colour[succID] == StrongComponents.COLORS.WHITE:
                        stack.append(self.directedg.getVertex(succID))
            elif self.vertex_colour[poppedv.vertexID] == StrongComponents.COLORS.GRAY:  
                self.vertex_colour[poppedv.vertexID] = StrongComponents.COLORS.BLACK
                self.vertex_list.append(poppedv.vertexID)
                
    def visit2(self, v):
        stack = []
        stack.append(v)
        while stack:
            poppedv = stack.pop()
            self.vertex_SCC[poppedv.vertexID] = StrongComponents.SCCID
            self.scc_vertices[StrongComponents.SCCID].add(poppedv.vertexID)
            if self.vertex_colour[poppedv.vertexID] == StrongComponents.COLORS.BLACK:
                self.vertex_colour[poppedv.vertexID] = StrongComponents.COLORS.BLUE
                stack.append(poppedv)
                for succID in poppedv.successors.keys():
                    if self.vertex_colour[succID] == StrongComponents.COLORS.BLACK:
                        stack.append(self.reverseg.getVertex(succID))
            elif self.vertex_colour[poppedv.vertexID] == StrongComponents.COLORS.BLUE:
                self.vertex_colour[poppedv.vertexID] = StrongComponents.COLORS.RED  
    