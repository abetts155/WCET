from Edges import Edge
from DirectedGraphs import dummyVertexID

class UndirectedVertex ():
    def __init__ (self, vertexID):
        self._vertexID = vertexID
        self._edges = []
    
    def getVertexID (self):
        return self._vertexID
    
    def addEdge (self, vertexID, edgeID=None):
        self._edges.append(vertexID)
        
    def getVertexIDs (self):
        return self._edges
    
    def degree (self):
        return len(self._edges)
    
    def __str__ (self):
        string = "Vertex ID = " + str(self._vertexID) + "\n"
        string += "pred = {"
        count = 1
        for vertexID in sorted(self._edges):
            string += str(vertexID)
            if count < len(self._edges):
                string += ","
                count = count + 1
        string += "}\n"
        return string

class Vertex ():
    def __init__ (self, vertexID):
        self._vertexID = vertexID
        self._predecessors = {}
        self._successors = {}
        
    def getVertexID (self):
        return self._vertexID
    
    def addPredecessor (self, predID, edgeID=None):
        assert predID not in self._predecessors, "Vertex %d already has predecessor %d" % (self._vertexID, predID)
        e = Edge(predID, edgeID)
        self._predecessors[predID] = e
        
    def addPredecessorEdge (self, prede):
        predID = prede.getVertexID()
        assert predID not in self._predecessors, "Vertex %d already has predecessor %d" % (self._vertexID, predID)
        self._predecessors[predID] = prede
            
    def removePredecessor (self, predID):
        assert predID in self._predecessors, "Cannot remove %d as it is not in predecessor of %d" % (predID, self._vertexID)
        del self._predecessors[predID]
    
    def getPredecessorIDs (self):
        return self._predecessors.keys()
    
    def getPredecessorEdges (self):
        return self._predecessors.values()
    
    def numberOfPredecessors (self):
        return len(self._predecessors)
    
    def hasPredecessor (self, predID):
        return predID in self._predecessors.keys()
    
    def getPredecessorEdge (self, predID):
        assert predID in self._predecessors, "Vertex %d is not a predecessor of %d" % (predID, self._vertexID)
        return self._predecessors[predID]
    
    def addSuccessor (self, succID,edgeID=None):
        assert succID not in self._successors, "Vertex %d already has successor %d" % (self._vertexID, succID)
        e = Edge(succID, edgeID)
        self._successors[succID] = e
        
    def addSuccessorEdge (self, succe):
        succID = succe.getVertexID()
        assert succID not in self._successors, "Vertex %d already has successor %d" % (self._vertexID, succID)
        self._successors[succID] = succe
        
    def removeSuccessor (self, succID):
        assert succID in self._successors, "Cannot remove %d as it is not in _successors of %d" % (succID, self._vertexID)
        del self._successors[succID]
        
    def getSuccessorIDs (self):
        return self._successors.keys()
    
    def getSuccessorEdges (self):
        return self._successors.values()
    
    def numberOfSuccessors (self):
        return len(self._successors)
    
    def hasSuccessor (self, succID):
        return succID in self._successors.keys()
    
    def getSuccessorEdge (self, succID):
        assert succID in self._successors, "Vertex %d is not a successor of %d" % (succID, self._vertexID)
        return self._successors[succID]
    
    def predecessorStr (self):
        string = "pred = {"
        count = 1
        for predID in sorted(self._predecessors.keys()):
            string += str(predID)
            if count < len(self._predecessors):
                string += ","
                count = count + 1
        string += "}\n"
        return string
    
    def successorStr (self):        
        string = "succ = {"
        count = 1
        for succID in sorted(self._successors.keys()):
            string += str(succID)
            if count < len(self._successors):
                string += ","
                count = count + 1
        string += "}\n"
        return string
    
class TreeVertex (Vertex):
    def __init__ (self, vertexID):
        Vertex.__init__(self, vertexID)
        self._parentID = dummyVertexID
        self._level    = -1
        
    def setParentID (self, parentID):
        self._parentID = parentID
        
    def getParentID (self):
        assert self._parentID != dummyVertexID, "Parent ID of %d has not been set" % self._parentID
        return self._parentID
    
    def setLevel (self, level):
        assert level >= 0, "The level of a vertex cannot be less than 0. You gave %d" % level
        self._level = level
    
    def getLevel (self):
        return self._level     
    
    def __str__ (self):
        if self._parentID == dummyVertexID:
            return "parent(%d) = <>\n" % self._vertexID
        else:
            return "parent(%d) = %d\n" % (self._vertexID, self._parentID)
    
class HeaderVertex (TreeVertex):
    def __init__ (self, vertexID, headerID):
        TreeVertex.__init__(self, vertexID)
        self.headerID = headerID
        
    def getHeaderID (self):
        return self.headerID
    
    def __str__ (self):
        return TreeVertex.__str__(self)[:-1] + " (" + "*" * 3 + " HEADER " + "*" * 3 + ")\n" 
    
class Ipoint (Vertex):
    def __init__ (self, vertexID, IpointID, realID=None):
        Vertex.__init__(self, vertexID)
        self.__IpointID = IpointID
        self.__succIpointIDToVertexID = {}
        self.__isGhost = False
        if realID:
            self.__realID = realID
        else:
            self.__realID = vertexID
    
    def setGhost (self):
        self.__isGhost = True
        
    def isGhost (self):
        return self.__isGhost
        
    def getIpointID (self):
        return self.__IpointID
    
    def getRealID (self):
        return self.__realID
    
    def addIpointSuccessor (self, succIpointID, succID):
        self.__succIpointIDToVertexID[succIpointID] = succID
    
    def getIpointSuccessor (self, succIpointID):
        assert succIpointID in self.__succIpointIDToVertexID, \
        "Unable to find successor of %s with Ipoint ID 0x%04X" % (self._vertexID, succIpointID)
        return self.__succIpointIDToVertexID[succIpointID]
    
    def __str__ (self):
        string = "Vertex ID = " + str(self._vertexID) + "\n"
        string += "\tIpoint ID = " + str(self.__IpointID) + "\n"
        string += "\t" + Vertex.predecessorStr(self)
        string += "\t" + Vertex.successorStr(self)    
        return string
    