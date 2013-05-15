import Debug, ARM, Vertices
import random, os, hashlib, shlex, sys

newTrace = "=>"
endTrace = "<="

class GenerateTraces:
    maxNumberOfCalls  = 20
    maxLoopIterations = 10
    
    def __init__ (self, basepath, basename, program, numberOfTraces=1):
        self.__program = program
        filename       = basepath + os.sep + basename + ".traces"
        with open(filename, 'w') as self.__outfile:
            self.__outfile.write("%s\n" % hashlib.sha1(basename).hexdigest())
            for trace in xrange(1, numberOfTraces+1):
                Debug.debugMessage("Generating trace #%d" % trace, 1)
                self.__outfile.write("%s\n" % newTrace)
                self.__generateTrace() 
                self.__outfile.write("\n%s\n" % endTrace)
    
    def __generateTrace (self):
        # To keep track of loop tail iteration count
        self.__functionToTailCount = {}
        # To keep trace of the number of function calls
        self.__numberOfCalls = 0
        callg = self.__program.getCallGraph()
        rootv = callg.getVertex(callg.getRootID())
        self.__currentCallv = rootv
        self.__currentICFG  = self.__program.getICFG(rootv.getName())
        self.__currentLNT   = self.__program.getLNT(rootv.getName())
        self.__currentv     = self.__currentICFG.getVertex(self.__currentICFG.getEntryID())
        self.__vertexID     = self.__currentv.getVertexID()
        self.__callStack    = []
        while True: 
            self.__outfile.write("%d " % self.__vertexID)
            if self.__vertexID == self.__currentICFG.getExitID():
                if callg.getVertexWithName(self.__currentICFG.getName()) == rootv:
                    # End of the program reached
                    break
                else:
                    # End of function call
                    Debug.debugMessage("Returning from %s" % self.__currentCallv.getName(), 5)
                    self.__currentCallv, self.__currentICFG, self.__currentLNT, self.__currentv = self.__callStack.pop()
                    self.__vertexID  = self.__currentv.getVertexID()
                    # Go past the call site
                    self.__chooseSuccessorInICFG()
            elif self.__currentLNT.isLoopTail(self.__vertexID):
                tupleIndex = self.__currentICFG.getName(), self.__vertexID
                if tupleIndex not in self.__functionToTailCount:
                    self.__functionToTailCount[tupleIndex] = 1
                    self.__chooseSuccessorInICFG()
                elif self.__functionToTailCount[tupleIndex] < GenerateTraces.maxLoopIterations:
                    self.__functionToTailCount[tupleIndex] += 1
                    self.__chooseSuccessorInICFG()
                else:
                    self.__chooseNonLoopBackEdgeSuccessorInICFG()
            elif self.__currentICFG.isCallSite(self.__vertexID):
                # If the number of calls have been exceeded or we non-deterministically choose not to make the call here
                # then select a successor in the current ICFG 
                if self.__numberOfCalls > GenerateTraces.maxNumberOfCalls or not bool(random.getrandbits(1)):
                    self.__chooseSuccessorInICFG()
                else:
                    # Make the call. First save state then move to the callee ICFG
                    self.__callStack.append((self.__currentCallv, self.__currentICFG, self.__currentLNT, self.__currentv))
                    succID              = self.__currentCallv.getSuccessorWithCallSite(self.__vertexID)
                    self.__currentCallv = callg.getVertex(succID)
                    calleeName          = self.__currentCallv.getName()
                    Debug.debugMessage("Calling %s" % self.__currentCallv.getName(), 5)
                    self.__currentICFG  = self.__program.getICFG(calleeName)
                    self.__currentLNT   = self.__program.getLNT(calleeName)
                    self.__currentv     = self.__currentICFG.getVertex(self.__currentICFG.getEntryID())
                    self.__vertexID     = self.__currentv.getVertexID()
            else:
                self.__chooseSuccessorInICFG()
    
    def __chooseSuccessorInICFG (self):
        succIndex = random.randint(0, self.__currentv.numberOfSuccessors() - 1)
        succID    = self.__currentv.getSuccessorIDs()[succIndex]
        self.__currentv = self.__currentICFG.getVertex(succID)
        self.__vertexID = self.__currentv.getVertexID()
        
    def __chooseNonLoopBackEdgeSuccessorInICFG (self):
        succIDs = [succID for succID in self.__currentv.getSuccessorIDs() if not self.__currentLNT.isLoopBackEdge(self.__vertexID, succID)]
        succIndex = random.randint(0, len(succIDs) - 1)
        succID    = succIDs[succIndex]
        self.__currentv = self.__currentICFG.getVertex(succID)
        self.__vertexID = self.__currentv.getVertexID()
        
class TraceInformation:
    def __init__ (self, program):
        self._program    = program
        self._allruns    = set([])
        self._partitions = {}
        self._initialiseSuperBlockInformation()
        self._initialiseRequiredWCETInformation()
        
    def _outputConjectures (self):
        for pathg, supervs in self._executesKTimes.iteritems():
            for supervID in supervs:
                conjecture = self._executesKTimes[pathg][supervID]
                if conjecture > 0:
                    Debug.verboseMessage("Conjecture that %d executes %d times holds" % (supervID, conjecture)) 
                else:
                    Debug.verboseMessage("Found an execution where %d NEVER executes" % supervID) 
            
    def _endOfFunction (self, pathg):
        Debug.debugMessage("Falsifying conjectures in %s" % pathg.getName(), 1)
        newConjectures = {}
        for supervID, conjecture in self._executesKTimes[pathg].iteritems():
            executionCount = self._superBlockExecutionCounts[pathg][supervID]
            if executionCount < conjecture:
                Debug.debugMessage("Falsifying conjecture that %d executes %d times. Found %d instead"  % (supervID, conjecture, executionCount), 1)
                newConjectures[supervID] = executionCount
            self._superBlockExecutionCounts[pathg][supervID] = 0 
        for supervID, conjecture in newConjectures.iteritems():
            self._executesKTimes[pathg][supervID] = conjecture
        # Now falsify mutual exclusion edges
        for partitionID1 in self._partitions[pathg].keys():
            for partitionID2 in self._partitions[pathg].keys():
                if partitionID1 != partitionID2:
                    for superv1 in self._partitions[pathg][partitionID1]:
                        for superv2 in self._partitions[pathg][partitionID2]:
                            if pathg.hasEdge(superv1.getVertexID(), superv2.getVertexID()):
                                Debug.debugMessage("Falsifying conjecture that (%d, %d) is mutually exclusive"  % (superv1.getVertexID(), superv2.getVertexID()), 1)
                                pathg.removeEdge(superv1.getVertexID(), superv2.getVertexID())
                                pathg.removeEdge(superv2.getVertexID(), superv1.getVertexID())
    
    def _endRun (self):
        for cfg in self._program.getICFGs():
            superg = self._program.getSuperBlockCFG(cfg.getName())
            pathg  = superg.getSuperBlockPathInformationGraph()
            for partitionID in self._partitions[pathg].keys():
                self._partitions[pathg][partitionID].clear()
                
    def _end (self):
        for pathg, supervs in self._executesKTimes.iteritems():
            for supervID in supervs:
                if supervID not in self._observedSuperBlocks:
                    Debug.verboseMessage("NEVER saw %d executing" % supervID)
                    self._executesKTimes[pathg][supervID] = 0
    
    def _initialiseSuperBlockInformation (self):
        self._superBlockExecutionCounts = {}
        self._executesKTimes            = {}
        self._observedSuperBlocks       = set([])
        for cfg in self._program.getICFGs():
            superg = self._program.getSuperBlockCFG(cfg.getName())
            pathg  = superg.getSuperBlockPathInformationGraph()
            self._partitions[pathg]                = {}
            self._superBlockExecutionCounts[pathg] = {}
            self._executesKTimes[pathg]            = {}
            for superv in pathg:
                self._superBlockExecutionCounts[pathg][superv.getVertexID()] = 0
                if superv.acyclicPartition:
                    self._executesKTimes[pathg][superv.getVertexID()] = 1
                else:
                    self._executesKTimes[pathg][superv.getVertexID()] = sys.maxint
                partitionID = superv.partitionID
                if partitionID not in self._partitions[pathg]:
                    self._partitions[pathg][partitionID] = set([])
    
    def _initialiseRequiredWCETInformation (self):
        self._longestTime = 0
        self._executionTimes = {}
        self._loopBounds = {}
        self._loopBoundsInCurrentRun = {}
        for cfg in self._program.getICFGs():
            functionName = cfg.getName()
            for v in cfg:
                self._executionTimes[(functionName, v.getOriginalVertexID())] = 0
            lnt = self._program.getLNT(functionName)
            for v in lnt:
                if isinstance(v, Vertices.HeaderVertex):
                    self._loopBounds[(functionName, v.getHeaderID())] = 0
                    self._loopBoundsInCurrentRun[(functionName, v.getHeaderID())] = 0
    
    def _normaliseData (self):
        for tupleKey in self._executionTimes.keys():
            self._executionTimes[tupleKey] *= pow(10,-3)
        self._longestTime *= pow(10,-3)
        
    def _analyseCFGVertex (self, pathg, bbID):
        if pathg.isMonitoredBasicBlock(bbID):
            superv = pathg.getMonitoredBasicBlockSuperBlock(bbID)
            self._superBlockExecutionCounts[pathg][superv.getVertexID()] += 1
            self._partitions[pathg][superv.partitionID].add(superv)
            self._observedSuperBlocks.add(superv.getVertexID())
            
    def _analyseCFGEdge (self, pathg, predID, succID):
        if pathg.isMonitoredEdge(predID, succID):
            superv = pathg.getMonitoredEdgeSuperBlock(predID, succID)
            self._superBlockExecutionCounts[pathg][superv.getVertexID()] += 1
            self._partitions[pathg][superv.partitionID].add(superv)
            self._observedSuperBlocks.add(superv.getVertexID())
            
    def getLoopBound (self, functionName, headerID):
        tupleKey = (functionName, headerID)
        assert tupleKey in self._loopBounds
        return self._loopBounds[tupleKey]

    def getExecutionTime (self, functionName, vertexID):
        tupleKey = (functionName, vertexID)
        assert tupleKey in self._executionTimes
        return self._executionTimes[tupleKey]
    
    def getLongestTime (self):
        return self._longestTime
    
    def getMinimumExecutionCount (self, pathg, superv):
        return self._executesKTimes[pathg][superv.getVertexID()]
    
    def alwaysExecutes (self, pathg, superv):
        return self._executesKTimes[pathg][superv.getVertexID()] > 0
    
    def neverExecutes (self, pathg, superv):
        return self._executesKTimes[pathg][superv.getVertexID()] == 0
        
    def getNumberOfAlwaysExecute (self, pathg):
        num = 0
        for superv in pathg:
            if self._executesKTimes[pathg][superv.getVertexID()] > 0:
                num += 1
        return num
    
    def getNumberOfNeverExecute (self, pathg):
        num = 0
        for superv in pathg:
            if self._executesKTimes[pathg][superv.getVertexID()] == 0:
                num += 1
        return num
    
class ParseTraces (TraceInformation):
    def __init__ (self, basename, tracefile, program):
        TraceInformation.__init__(self, program)
        self.__contextg = self._program.getContextGraph()
        self.__rootv    = self.__contextg.getVertex(self.__contextg.getRootID())
        self.__bbToCFG  = {}
        self.__verifyMagicNumber(basename, tracefile)
        self.__initialise()
        self.__parse(tracefile)
        self._computePathInformation()          
                    
    def __verifyMagicNumber (self, basename, tracefile):
        magicNumber = hashlib.sha1(basename).hexdigest()
        # First assert that the magic numbers match
        with open(tracefile, 'r') as f:
            line = f.readline()
            fileMagicNumber = line.strip()
            assert fileMagicNumber == magicNumber, "The magic number of the trace file does not compute"
    
    def __initialise (self):
        for icfg in self._program.getICFGs():
            for v in icfg:
                self.__bbToCFG[v.getVertexID()] = icfg
    
    def __parse (self, tracefile):
        runID = 0
        with open(tracefile, 'r') as f:
        # Move past the magic number line
            next(f)
            for line in f:
                if line.startswith(newTrace):
                    runID += 1
                    self._allruns.add(runID)
                    self.__reset()
                elif line.startswith(endTrace):
                    pass
                else:
                    lexemes = shlex.split(line)
                    lastID = None
                    for lex in lexemes:
                        nextID = int(lex)
                        if self.__currentCFG.hasVertex(nextID):
                            self._analyseSuperBlock(self.__currentContextv, self.__currentSuperg, lastID, nextID, runID)
                        else:
                            self.__handleCallAndReturn(lastID, nextID)
                        lastID = nextID
    
    def __reset (self):
        self.__callStack       = []
        self.__currentContextv = self.__rootv
        self.__currentCFG      = self._program.getICFG(self.__rootv.getName())
        self.__currentSuperg   = self._program.getSuperBlockCFG(self.__rootv.getName())
        
    def __handleCallAndReturn (self, lastID, nextID):
        assert lastID, "The last ID was not set"
        if self.__currentCFG.getExitID() == lastID:
            Debug.debugMessage("Returning because of basic block %d" % lastID, 1)
            self.__currentContextv, self.__currentCFG, self.__currentSuperg = self.__callStack.pop()
        else:
            callerFrame = (self.__currentContextv, self.__currentCFG, self.__currentSuperg)
            self.__callStack.append(callerFrame) 
            self.__currentCFG      = self.__bbToCFG[nextID]
            newContextID           = self.__currentContextv.getSuccessorWithCallSite(lastID)
            self.__currentContextv = self.__contextg.getVertex(newContextID)
            self.__currentSuperg   = self._program.getSuperBlockCFG(self.__currentCFG.getName())

class Gem5Parser (TraceInformation):
    def __init__ (self, program, traceFiles):
        Debug.verboseMessage("Parsing gem5 traces")
        TraceInformation.__init__(self, program)
        self.__initialise()
        self.__parse(traceFiles)
        self._end()
        self._normaliseData()
        self._outputConjectures()
        
    def __initialise (self):
        self.__currentContextv = None
        self.__currentCFG      = None
        self.__currentLNT      = None
        self.__predBB          = None
        self.__currentBB       = None
        self.__currentHeaderID = None
        self.__currentSuperg   = None
        self.__time1           = None
        self.__stack           = []
        self.__contextg        = self._program.getContextGraph()
        rootv                  = self.__contextg.getVertex(self.__contextg.getRootID())
        self.__rootCFG         = self._program.getICFG(rootv.getName())
        self.__firstAddr       = self.__rootCFG.getFirstInstruction().getAddress()
        lastbb                 = self.__rootCFG.getVertex(self.__rootCFG.getExitID())
        for instruction in reversed(lastbb.getInstructions()):
            if instruction.getOp() not in ARM.ARMInstructionSet.Nops:
                self.__lastAddr = instruction.getAddress()
                break
        assert self.__lastAddr, "Unable to find last address"
        Debug.debugMessage("Start address of root function '%s' is %s" % (rootv.getName(), hex(self.__firstAddr)), 1)    
        Debug.debugMessage("End address of root function '%s' is %s" % (rootv.getName(), hex(self.__lastAddr)), 1)
        
    def __parse (self, traceFiles):
        import gzip
        runID = 0
        for filename in traceFiles:
            parsing = False 
            with gzip.open(filename, 'r') as f:
                runID += 1
                self._allruns.add(runID)
                Debug.debugMessage("Analysing gem5 trace file '%s'" % filename, 1)
                for line in f:
                    lexemes  = shlex.split(line)
                    PCLexeme = lexemes[-1]
                    assert len(PCLexeme) == 11, "Unable to parse program counter %s" % PCLexeme
                    try:
                        time     = int(lexemes[0][:-1])
                        PCLexeme = PCLexeme[5:]
                        PC       = int(PCLexeme, 16)
                        if PC == self.__firstAddr:
                            self.__time1           = time
                            startTime              = time
                            parsing                = True
                            self.__currentContextv = self.__contextg.getVertex(self.__contextg.getRootID())
                            self.__currentCFG      = self._program.getICFG(self.__currentContextv.getName())
                            self.__currentLNT      = self._program.getLNT(self.__currentContextv.getName())
                            self.__currentSuperg   = self._program.getSuperBlockCFG(self.__currentContextv.getName())
                            self.__predBB          = None
                            self.__currentBB       = self.__currentCFG.getVertex(self.__currentCFG.getEntryID())
                        if parsing:
                            self.__parseAddress (time, PC, runID)
                        if PC == self.__lastAddr:
                            # Stop parsing
                            parsing = False
                            # Compute the HWMT
                            totalTime = time - startTime
                            self._longestTime = max(self._longestTime, totalTime)
                            print self._longestTime
                            # Falsify conjectures
                            self._endOfFunction(self.__currentSuperg.getSuperBlockPathInformationGraph())
                            self._endRun()
                    except ValueError:
                        Debug.exitMessage("Cannot cast %s into an integer: it is not a hexadecimal string" % PCLexeme)

    def __getCFGWithAddress (self, address):
        for cfg in self._program.getICFGs():
            firstAddress = cfg.getFirstInstruction().getAddress()
            if firstAddress == address:
                return cfg
        assert False, "Unable to find CFG with start address %s" % hex(address)
    
    def __analyseWCETOfBasicBlock (self, executionTime):
        tupleKey = (self.__currentCFG.getName(), self.__currentBB.getOriginalVertexID())
        assert tupleKey in self._executionTimes
        self._executionTimes[tupleKey] = max(self._executionTimes[tupleKey], executionTime)    
        
    def __parseAddress (self, time, address, runID):
        if address == self.__lastAddr:
            self.__analyseWCETOfBasicBlock(time - self.__time1)
        if not self.__currentBB.hasAddress(address):
            # Instructions in the current basic block have finished. Analyse its execution time
            self.__analyseWCETOfBasicBlock(time - self.__time1)
            # Move the time marker forward to the current time to reflect that we are transitioning
            # to a new basic block
            self.__time1 = time
            # Make the switch to the next basic block
            if self.__currentCFG.isCallSite(self.__currentBB.getVertexID()):
                self.__handleCall(address)
            elif self.__currentCFG.getExitID() == self.__currentBB.getVertexID():
                self.__handleReturn()
            else:
                for succID in self.__currentBB.getSuccessorIDs():
                    succv = self.__currentCFG.getVertex(succID)
                    if succv.hasAddress(address):
                        self.__predBB    = self.__currentBB
                        self.__currentBB = succv
                        break
                # Since we have switched basic blocks in the current CFG, analyse the super blocks
                self._analyseCFGVertex(self.__currentSuperg.getSuperBlockPathInformationGraph(), self.__currentBB.getVertexID())     
                self._analyseCFGEdge(self.__currentSuperg.getSuperBlockPathInformationGraph(), self.__predBB.getVertexID(), self.__currentBB.getVertexID())     
            # Analyse loop bounds
            if self.__currentLNT.isLoopHeader(self.__currentBB.getVertexID()):
                tupleKey = (self.__currentCFG.getName(), self.__currentBB.getVertexID())
                assert tupleKey in self._loopBounds and tupleKey in self._loopBoundsInCurrentRun
                self._loopBoundsInCurrentRun[tupleKey] += 1   
                # Check whether this edge is a loop-exit edge
                # If it is the header ID of the exiting loop is returned
            if self.__predBB:
                headerID = self.__currentLNT.isLoopExitEdge(self.__predBB.getVertexID(), self.__currentBB.getVertexID())
                if headerID:
                    tupleKey = (self.__currentCFG.getName(), headerID)
                    assert tupleKey in self._loopBounds and tupleKey in self._loopBoundsInCurrentRun
                    self._loopBounds[tupleKey] = max(self._loopBounds[tupleKey], self._loopBoundsInCurrentRun[tupleKey])
                    self._loopBoundsInCurrentRun[tupleKey] = 0 
            Debug.debugMessage("Now in CFG '%s' at basic block %d" % (self.__currentCFG.getName(), self.__currentBB.getVertexID()), 10)    
            
    def __handleReturn (self):
        if self.__currentCFG.getExitID() == self.__currentBB.getVertexID() and self.__currentCFG != self.__rootCFG:
            # Falsify conjectures
            self._endOfFunction(self.__currentSuperg.getSuperBlockPathInformationGraph())
            (self.__currentContextv, self.__currentCFG, self.__currentLNT, self.__predBB, self.__currentBB, self.__currentSuperg) = self.__stack.pop()
            succIDs = self.__currentBB.getSuccessorIDs()
            assert len(succIDs) == 1
            succv            = self.__currentCFG.getVertex(succIDs[0])
            self.__predBB    = self.__currentBB
            self.__currentBB = succv
    
    def __handleCall (self, address):
        callerFrame = (self.__currentContextv, self.__currentCFG, self.__currentLNT, self.__predBB, self.__currentBB, self.__currentSuperg)
        self.__stack.append(callerFrame)
        newContextID           = self.__currentContextv.getSuccessorWithCallSite(self.__currentBB.getVertexID())
        self.__currentContextv = self.__contextg.getVertex(newContextID)
        self.__currentCFG      = self.__getCFGWithAddress(address)
        self.__currentLNT      = self._program.getLNT(self.__currentCFG.getName())
        self.__predBB          = None
        self.__currentBB       = self.__currentCFG.getVertex(self.__currentCFG.getEntryID())
        self.__currentSuperg   = self._program.getSuperBlockCFG(self.__currentCFG.getName())
        assert self.__currentBB.hasAddress(address), "Calling into '%s' because of address %s but basic block does not contain an instruction with that address" % (self.__currentCFG.getName(), hex(address))      
        