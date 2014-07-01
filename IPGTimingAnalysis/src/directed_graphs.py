import vertices

class DirectedGraph ():        
    def __init__ (self):
        self.the_vertices = {}
        self.name = None
    
    def getVertex (self, vertexID):
        assert vertexID in self.the_vertices, "Vertex " + str(vertexID) + " is not in the graph"
        return self.the_vertices[vertexID]
    
    def removeVertex (self, vertexID):
        assert vertexID in self.the_vertices, "Vertex " + str(vertexID) + " is not in the graph"
        del self.the_vertices[vertexID]
    
    def hasVertex (self, vertexID):
        return vertexID in self.the_vertices
    
    def addEdge (self, predID, succID):
        predv = self.getVertex(predID)
        succv = self.getVertex(succID)
        predv.add_successor(succID)
        succv.add_predecessor(predID)
    
    def removeEdge (self, predID, succID):
        predv = self.getVertex(predID)
        succv = self.getVertex(succID)
        predv.remove_successor(succID)
        succv.remove_predecessor(predID)
        
    def add_predecessor_edges (self):
        for v in self:
            for succID in v.successors.keys():
                succv = self.getVertex(succID)
                if not succv.has_predecessor(v.vertexID):
                    succv.add_predecessor(v.vertexID)
    
    def getNextVertexID (self):
        nextID = 1
        while nextID in self.the_vertices.keys():
            nextID = nextID + 1 
        return nextID
    
    def number_of_vertices(self):
        return len(self.the_vertices)
    
    def number_of_edges(self):
        total = 0
        for v in self.the_vertices.values():
            total += v.number_of_successors()
        return total
    
    def __iter__ (self):
        return self.the_vertices.values().__iter__()

class FlowGraph (DirectedGraph):
    def __init__ (self):
        DirectedGraph.__init__(self)
        self._entryID = vertices.dummyID
        self._exitID = vertices.dummyID
        
    def get_entryID (self):
        assert self._entryID != vertices.dummyID, "Entry to flow graph not found"
        return self._entryID
    
    def get_exitID (self):
        assert self._exitID != vertices.dummyID, "Exit to flow graph not found"
        return self._exitID
    
    def __str__ (self):
        the_string = "*" * 40 + "\n" + \
        "Entry ID = %s\n" % str(self._entryID) + \
        "Exit ID  = %s\n" % str(self._exitID) + "\n"
        for v in self.the_vertices.values():
            the_string += v.__str__()
        the_string += "*" * 40 + "\n"
        return the_string
