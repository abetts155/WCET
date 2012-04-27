package adam.betts.calculations;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Random;
import java.util.Set;

import adam.betts.graphs.ControlFlowGraph;
import adam.betts.graphs.trees.LoopNests;
import adam.betts.programs.Program;
import adam.betts.programs.Subprogram;
import adam.betts.utilities.Debug;
import adam.betts.vertices.Vertex;
import adam.betts.vertices.trees.HeaderVertex;
import adam.betts.vertices.trees.TreeVertex;

public class Database
{

    /*
     * The program used during trace parsing to populate the database
     */
    protected Program program;

    /*
     * The calculation engine used after parsing
     */
    protected CalculationEngine engine;

    /*
     * The WCETs of the units of computation: either edges or vertices in the
     * graph
     */
    protected HashMap <Integer, HashMap <Integer, Long>> unitWCETs = new HashMap <Integer, HashMap <Integer, Long>>();

    /*
     * Loop bounds for each subprogram
     */
    protected HashMap <Integer, HashMap <Integer, HashMap <Integer, Integer>>> loopBounds = new HashMap <Integer, HashMap <Integer, HashMap <Integer, Integer>>>();

    /*
     * Infeasible path data for each subprogram
     */
    protected HashMap <Integer, HashMap <Integer, HashSet <Integer>>> observedPaths = new HashMap <Integer, HashMap <Integer, HashSet <Integer>>>();

    /*
     * To record number of tests for each subprogram
     */
    protected HashMap <Integer, Long> tests = new HashMap <Integer, Long>();

    /*
     * METs of each subprogram
     */
    protected HashMap <Integer, Long> mets = new HashMap <Integer, Long>();

    public Database (final Program program)
    {
        this.program = program;
    }

    public void generateData (boolean random)
    {
        HashMap <Integer, HashMap <Integer, Integer>> headerBounds = new HashMap <Integer, HashMap <Integer, Integer>>();

        Random randomGenerator = new Random();

        for (Subprogram s : program)
        {
            Debug.debugMessage(getClass(),
                    "Generating data for " + s.getSubprogramName(), 2);

            int subprogramID = s.getSubprogramID();
            unitWCETs.put(subprogramID, new HashMap <Integer, Long>());
            ControlFlowGraph cfg = s.getCFG();
            for (Vertex v : cfg)
            {
                long data = 1;

                if (random)
                {
                    data = Math.abs(randomGenerator.nextLong());

                    if (data == 0)
                    {
                        data = 1;

                    }
                }

                unitWCETs.get(subprogramID).put(v.getVertexID(), data);
            }

            LoopNests lnt = s.getCFG().getLNT();
            for (int level = lnt.getHeight() - 1; level >= 0; --level)
            {
                Iterator <TreeVertex> levelIt = lnt.levelIterator(level);
                while (levelIt.hasNext())
                {
                    TreeVertex v = levelIt.next();

                    if (v instanceof HeaderVertex)
                    {
                        HashMap <Integer, Integer> properAncestorBounds = new HashMap <Integer, Integer>();
                        HeaderVertex headerv = (HeaderVertex) v;
                        int vertexID = headerv.getVertexID();

                        for (int ancestorID : lnt.getProperAncestors(vertexID))
                        {
                            int levelDifference = headerv.getLevel()
                                    - lnt.getVertex(ancestorID).getLevel();

                            int bound = (int) (Math.pow(10, levelDifference) / 2) - levelDifference;

                            Debug.debugMessage(getClass(), "Exponent = "
                                    + levelDifference + ", bound = " + bound, 1);

                            if (random)
                            {
                                bound = Math.abs(randomGenerator.nextInt());

                                if (bound == 0)
                                {
                                    bound = 1;
                                }
                            }

                            properAncestorBounds.put(ancestorID, bound);
                        }

                        headerBounds.put(vertexID, properAncestorBounds);
                    }
                }
            }

            loopBounds.put(subprogramID, headerBounds);
        }

        for (Subprogram s : program)
        {
            Debug.debugMessage(getClass(),
                    "Subprogram " + s.getSubprogramName(), 2);

            int subprogramID = s.getSubprogramID();

            for (int headerID : loopBounds.get(subprogramID).keySet())
            {
                for (int ancestorID : loopBounds.get(subprogramID)
                        .get(headerID).keySet())
                {
                    Debug.debugMessage(
                            getClass(),
                            "Bound of "
                                    + headerID
                                    + " w.r.t "
                                    + ancestorID
                                    + " = "
                                    + loopBounds.get(subprogramID)
                                            .get(headerID).get(ancestorID), 1);
                }
            }
        }
    }

    public final long getUnitWCET (int subprogramID, int unitID)
    {
        return unitWCETs.get(subprogramID).get(unitID);
    }

    public final int getLoopBound (int subprogramID, int headerID,
            int ancestorID)
    {
        return loopBounds.get(subprogramID).get(headerID).get(ancestorID);
    }

    public Set <Integer> getInfeasibleUnits (int subprogramID, int unitID)
    {
        Set <Integer> infeasible = new HashSet <Integer>();
        for (int ID : unitWCETs.get(subprogramID).keySet())
        {
            /*
             * Add the vertex or edge ID to the set of infeasible units only if
             * it was not seen during its execution
             */
            if (!observedPaths.get(subprogramID).get(unitID).contains(ID))
            {
                infeasible.add(ID);
            }
        }
        return infeasible;
    }

    public final int unitsCovered (int subprogramID)
    {
        int count = 0;
        for (int edgeID : unitWCETs.get(subprogramID).keySet())
        {
            if (unitWCETs.get(subprogramID).get(edgeID) != 0)
            {
                count++;
            }
        }
        return count;
    }

    public final boolean isCovered (int subprogramID, int unitID)
    {
        return unitWCETs.get(subprogramID).get(unitID) > 0;
    }

    public final long getTests (int subprogramID)
    {
        return tests.get(subprogramID);
    }

    public final long getMET (int subprogramID)
    {
        return mets.get(subprogramID);
    }
}
