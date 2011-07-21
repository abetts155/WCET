package adam.betts.programs;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.TreeSet;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.SAXException;

import adam.betts.edges.Edge;
import adam.betts.graphs.ControlFlowGraph;
import adam.betts.instructions.Instruction;
import adam.betts.instructions.InstructionSet;
import adam.betts.outputs.UDrawGraph;
import adam.betts.utilities.Debug;
import adam.betts.utilities.Globals;
import adam.betts.utilities.Enums.BranchType;
import adam.betts.vertices.BasicBlock;
import adam.betts.vertices.Vertex;
import adam.betts.vertices.call.CallVertex;

public class ProgramCreator
{
	protected final Program program;

	public ProgramCreator (Program program)
	{
		this.program = program;
		String programFileName = Globals.getProgramFileName ();
		int i = programFileName.lastIndexOf ('.');
		try
		{
			if (i == -1)
			{
				throw new IOException (
						programFileName
								+ " does not have a file extension. Cannot deduce whether to parse XML or read disassembly.");
			}
			else
			{
				String fileExtension = programFileName.substring (i + 1,
						programFileName.length ());

				program.programName = programFileName.substring (0, i);

				if (fileExtension.equals ("asm"))
				{
					Debug.debugMessage (getClass (),
							"Reading a disassembly file", 3);
					new Disassembler ();
				}
				else if (fileExtension.equals ("xml"))
				{
					Debug.debugMessage (getClass (), "Reading an XML file", 3);
					new XMLReader ();
				}
				else
				{
					throw new IOException (
							programFileName
									+ " does not have a valid file extension. Can only recognise '.xml' and '.asm' extensions.");

				}
			}
		}
		catch (Exception e)
		{
			e.printStackTrace ();
			System.exit (1);
		}
	}

	private void trim ()
	{
		/*
		 * The binary has a lot of system calls, which can over complicate the
		 * analysis, so remove them
		 */
		LinkedList<Integer> stack = new LinkedList<Integer> ();
		HashSet<Integer> visited = new HashSet<Integer> ();
		HashSet<Integer> unreachable = new HashSet<Integer> (
				program.idToSubprogram.keySet ());

		try
		{
			for (String rootName: Globals.getRoots ())
			{
				if (!program.nameToId.containsKey (rootName))
				{
					throw new NoSuchRootException (rootName);
				}

				int rootID = program.nameToId.get (rootName);
				stack.add (rootID);
				while (!stack.isEmpty ())
				{
					int subprogramID = stack.removeLast ();

					Debug.debugMessage (getClass (), "Visiting "
							+ program.idToSubprogram.get (subprogramID)
									.getSubprogramName (), 4);

					unreachable.remove (subprogramID);
					visited.add (subprogramID);

					CallVertex callv = program.callg.getVertex (subprogramID);
					Iterator<Edge> succIt = callv.successorIterator ();
					while (succIt.hasNext ())
					{
						Edge e = succIt.next ();
						int calleeID = e.getVertexID ();
						if (!visited.contains (calleeID))
						{
							stack.addLast (calleeID);
						}
					}
				}
			}
		}
		catch (NoSuchRootException e)
		{
			System.err.println (e.getMessage ());
			System.exit (1);
		}

		/*
		 * Fix the call graph, removing calls to unreachable subprograms
		 */
		Debug.debugMessage (getClass (),
				"Removing the following subprograms: ", 4);
		int i = 0;
		for (int subprogramID: unreachable)
		{
			String subprogramName = program.idToSubprogram.get (subprogramID)
					.getSubprogramName ();
			Debug.debugMessage (getClass (), i++ + ") " + subprogramName, 4);
			program.callg.removeVertex (subprogramID);
			program.idToSubprogram.remove (subprogramID);
			program.nameToId.remove (subprogramName);
		}
	}

	private class XMLReader
	{
		public XMLReader ()
		{
			Debug.verboseMessage ("Reading XML file");
			parseXML ();

			if (Globals.hasRoot ())
			{
				/*
				 * Only trim subprograms from the analysis if a root has been
				 * given on the command line
				 */
				trim ();
			}

			for (String subprogramName: program.nameToId.keySet ())
			{
				int subprogramID = program.nameToId.get (subprogramName);
				Debug.debugMessage (getClass (),
						"Setting entry and exit points in CFG of "
								+ subprogramName, 4);
				ControlFlowGraph cfg = program.idToSubprogram
						.get (subprogramID).getCFG ();
				cfg.addAllPredecessorEdges ();
				cfg.setEntry ();
				cfg.setExit ();
			}
		}

		private void parseXML ()
		{
			File file = new File (Globals.getProgramFileName ());
			try
			{
				DocumentBuilder builder = DocumentBuilderFactory.newInstance ()
						.newDocumentBuilder ();
				Document document = builder.parse (file);
				Element rootElement = document.getDocumentElement ();

				/*
				 * First find out all the IDs of each CFG as we need them when
				 * inserting subprogram call edges
				 */
				Debug.verboseMessage ("First pass of CFGs");
				NodeList nodes = rootElement.getElementsByTagName ("cfg");
				for (int i = 0; i < nodes.getLength (); i++)
				{
					Node node = nodes.item (i);

					if (node instanceof Element)
					{
						Element child = (Element) node;
						int subprogramID = Integer.parseInt (child
								.getAttribute ("id"));
						String subprogramName = child.getAttribute ("name");
						Debug.debugMessage (getClass (), "Adding sub-program "
								+ subprogramName + " with id " + subprogramID,
								2);
						program.addSubprogram (subprogramID, subprogramName);
					}
				}

				/*
				 * Now add the basic blocks to the CFGs
				 */
				Debug.verboseMessage ("Second pass of CFGs");
				for (int i = 0; i < nodes.getLength (); i++)
				{
					Node node = nodes.item (i);

					if (node instanceof Element)
					{
						Element child = (Element) node;
						String subprogramName = child.getAttribute ("name");
						Debug.debugMessage (getClass (), "In sub-program "
								+ subprogramName, 4);
						int subprogramID = program.nameToId
								.get (subprogramName);
						ControlFlowGraph cfg = program.idToSubprogram.get (
								subprogramID).getCFG ();
						cfg.setSubprogramName (subprogramName);
						parseCFG (child, cfg, subprogramID);
						cfg.setFirstAndLastAddress ();
					}
				}
			}
			catch (ParserConfigurationException e)
			{
				Debug.debugMessage (getClass (),
						"Error instantiating XML parser", 1);
				System.exit (1);
			}
			catch (SAXException e)
			{
				Debug.debugMessage (getClass (),
						"SAX exception with XML parser", 1);
				System.exit (1);
			}
			catch (IOException e)
			{
				Debug.debugMessage (getClass (),
						"IO exception with XML parser", 1);
				System.exit (1);
			}
		}

		private void parseCFG (Element element,
				ControlFlowGraph cfg,
				int subprogramID)
		{
			NodeList nodes = element.getElementsByTagName ("bb");
			for (int i = 0; i < nodes.getLength (); i++)
			{
				Node node = nodes.item (i);

				if (node instanceof Element)
				{
					Element child = (Element) node;
					String bbID = child.getAttribute ("id");
					Debug.debugMessage (getClass (), "Added BB " + bbID, 4);
					cfg.addBasicBlock (Integer.parseInt (bbID));
					NodeList instNodes = child.getElementsByTagName ("inst");
					parseInstructions (instNodes, (BasicBlock) cfg
							.getVertex (Integer.parseInt (bbID)));
					NodeList succNodes = child.getElementsByTagName ("succ");
					parseSuccessors (succNodes, Integer.parseInt (bbID), cfg,
							subprogramID);
				}
			}
		}

		private void parseInstructions (NodeList nodes, BasicBlock bb)
		{
			for (int i = 0; i < nodes.getLength (); i++)
			{
				Node node = nodes.item (i);

				if (node instanceof Element)
				{
					Element child = (Element) node;
					String address = child.getAttribute ("addr");
					String instructionStr = child.getAttribute ("instr");
					Debug.debugMessage (getClass (), "Added instruction @ "
							+ address + " '" + instructionStr + "'", 4);
					bb.addInstruction (new Instruction (Long.parseLong (address
							.substring (2), 16), instructionStr));
				}
			}
		}

		private void parseSuccessors (NodeList nodes,
				int vertexID,
				ControlFlowGraph cfg,
				int subprogramID)
		{
			for (int i = 0; i < nodes.getLength (); i++)
			{
				Node node = nodes.item (i);

				if (node instanceof Element)
				{
					Element child = (Element) node;
					NodeList childNodes = child.getElementsByTagName ("link");
					for (int j = 0; j < childNodes.getLength (); j++)
					{
						Node childNode = childNodes.item (j);

						if (childNode instanceof Element)
						{
							Element grandChild = (Element) childNode;
							String type = grandChild.getAttribute ("type");
							int subprogramID2 = Integer.parseInt (grandChild
									.getAttribute ("cfg"));

							if (subprogramID2 != subprogramID)
							{
								program.callg.addCall (subprogramID,
										subprogramID2, vertexID);
							}
							else
							{
								int succID = Integer.parseInt (grandChild
										.getAttribute ("bb"));
								cfg.addEdge (vertexID, succID, BranchType
										.valueOf (type.toUpperCase ()));

								Debug.debugMessage (getClass (), "Added edge "
										+ vertexID + "=>" + succID, 4);
							}
						}
					}
				}
			}
		}
	}

	private class Disassembler
	{
		/*
		 * Global variable to ensure basic block ids are unique across all CFGs
		 */
		private int bbID = 1;

		/*
		 * A dummy target destination for return-type instructions
		 */
		private final long DUMMY_DESTINATION = -1;

		/*
		 * The instruction set of the disassembly file
		 */
		private InstructionSet instructionSet;

		private HashMap<String, Long> subprogramToFirstAddress = new LinkedHashMap<String, Long> ();
		private HashMap<String, Long> subprogramToLastAddress = new LinkedHashMap<String, Long> ();
		private HashMap<Long, String> lastAddressToSubprogram = new LinkedHashMap<Long, String> ();
		private HashMap<Long, String> firstAddressToSubprogram = new LinkedHashMap<Long, String> ();
		private HashMap<String, TreeSet<Instruction>> subprogramToInstructions = new LinkedHashMap<String, TreeSet<Instruction>> ();
		private HashMap<String, HashMap<Long, Long>> subprogramToBranchInstructions = new LinkedHashMap<String, HashMap<Long, Long>> ();
		private HashMap<String, HashSet<Long>> subprogramToBranchTargets = new LinkedHashMap<String, HashSet<Long>> ();
		private HashMap<String, HashSet<Long>> subprogramToUnconditionalBranches = new LinkedHashMap<String, HashSet<Long>> ();
		private HashMap<String, TreeSet<Long>> subprogramToLeader = new LinkedHashMap<String, TreeSet<Long>> ();

		public Disassembler ()
		{
			instructionSet = new InstructionSet ();

			Debug.verboseMessage ("Identifying jumps");
			try
			{
				identifyJumps ();
			}
			catch (IOException e)
			{
				System.exit (1);
			}

			Debug.verboseMessage ("Identifying leaders");
			identifyLeaders ();

			Debug.verboseMessage ("Identifying basic blocks");
			identifyBasicBlocks ();

			Debug.verboseMessage ("Adding edges to CFGs");
			addEdges ();

			Debug.verboseMessage ("Trimming program");
			trim ();

			Debug.verboseMessage ("Removing dead code");
			Debug.debugMessage (getClass (), "#Subprograms = "
					+ program.nameToId.size (), 2);
			for (String subprogramName: program.nameToId.keySet ())
			{
				Debug.debugMessage (getClass (), "In " + subprogramName, 2);
				int subprogramID = program.nameToId.get (subprogramName);
				program.idToSubprogram.get (subprogramID).getCFG ()
						.removeDeadCode ();
			}

			if (Globals.uDrawDirectorySet ())
			{
				for (String subprogramName: program.nameToId.keySet ())
				{
					int subprogramID = program.nameToId.get (subprogramName);
					final ControlFlowGraph cfg = program.idToSubprogram.get (
							subprogramID).getCFG ();
					UDrawGraph.makeUDrawFile (cfg, subprogramName);
				}
			}
		}

		private void identifyJumps () throws IOException
		{
			try
			{
				String str;
				String subprogramName = null;
				int subprogramID = 0;
				boolean parse = false;

				String disassemblyFileName = Globals.getProgramFileName ();
				BufferedReader in = new BufferedReader (new FileReader (
						disassemblyFileName));
				while ( (str = in.readLine ()) != null)
				{
					/*
					 * Only parse the text section of the disassembly
					 */
					if (str.startsWith ("Disassembly"))
					{
						parse = str.contains (".text");
					}
					else if (parse)
					{
						/*
						 * To extract the sub-program name to which assembly
						 * instructions belong: match a non-null sequence of
						 * hexadecimal characters, followed by a single
						 * whitespace character, followed by '<', followed by
						 * any character, followed by '>', followed by ":" For
						 * example "00403100 <_foo>:" is matched
						 */
						if (str.matches ("[0-9A-Fa-f]+\\s<.*>.*"))
						{
							String[] lexemes = str.split ("\\s+");
							subprogramName = lexemes[1].substring (1,
									lexemes[1].length () - 2);
							subprogramID += 1;

							Debug.debugMessage (getClass (),
									"New sub-program identified: "
											+ subprogramName
											+ " starting @ address "
											+ lexemes[0], 2);

							if (program.nameToId.containsKey (subprogramName))
							{
								Debug.debugMessage (getClass (), subprogramName
										+ " already exists. Changing it to "
										+ subprogramName + "_" + subprogramID,
										2);
								subprogramName += "_" + subprogramID;
							}

							subprogramToBranchInstructions.put (subprogramName,
									new HashMap<Long, Long> ());
							subprogramToBranchTargets.put (subprogramName,
									new HashSet<Long> ());
							subprogramToUnconditionalBranches.put (
									subprogramName, new HashSet<Long> ());

							subprogramToInstructions.put (subprogramName,
									new TreeSet<Instruction> (
											new Comparator<Instruction> ()
											{
												public int compare (Instruction instr1,
														Instruction instr2)
												{
													if (instr1.getAddress () < instr2
															.getAddress ())
													{
														return -1;
													}
													else if (instr1
															.getAddress () > instr2
															.getAddress ())
													{
														return 1;
													}
													else
													{
														return 0;
													}
												}
											}));

							subprogramToLeader.put (subprogramName,
									new TreeSet<Long> (new Comparator<Long> ()
									{
										public int compare (Long long1,
												Long long2)
										{
											if (long1 < long2)
											{
												return -1;
											}
											if (long1 > long2)
											{
												return 1;
											}
											else
											{
												return 0;
											}
										}

									}));

							program
									.addSubprogram (subprogramID,
											subprogramName);
						}
						/*
						 * To extract assembly instructions from the listing
						 * file: match a (potentially null sequence of) any
						 * character, followed by a non-null sequence of
						 * hexadecimal characters, followed by ':', followed by
						 * (a potentially null sequence of) any character. For
						 * example "  40000FE0: 81 23 e0 08 nop" is matched
						 */
						else if (str.matches ("\\s*[0-9A-Fa-f]+:.*"))
						{
							switch (instructionSet.getISA ())
							{
								case PISA:
									parsePISAInstruction (str, subprogramName);
									break;
								case ARM:
									parseARMInstruction (str, subprogramName);
									break;
								case ALPHA:
									parseALPHAInstruction (str, subprogramName);
									break;
								case SPARC:
									parseSPARCInstruction (str, subprogramName);
									break;
								case X86:
									parseX86Instruction (str, subprogramName);
									break;
								default:
									Debug
											.debugMessage (
													getClass (),
													"Cannot handle this instruction set",
													1);
									System.exit (1);
							}

						}
					}
				}
				in.close ();
			}
			catch (Exception e)
			{
				System.err.println ("Error: " + e.getMessage ());
				e.printStackTrace ();
				System.exit (1);
			}
		}

		private void parsePISAInstruction (String str, String subprg)
		{
			String[] lexemes = str.split ("\\s+");
			final int addressIndex = 1;
			final int opCodeIndex = 6;
			final int destinationIndex = 7;

			if (lexemes.length > 6)
			{
				String addressStr = lexemes[addressIndex].substring (0,
						lexemes[addressIndex].length () - 1);
				StringBuffer buffer = new StringBuffer ();
				for (int i = opCodeIndex; i < lexemes.length; ++i)
				{
					buffer.append (lexemes[i] + " ");
				}
				Instruction instr = new Instruction (Long.parseLong (
						addressStr, 16), buffer.toString ());
				TreeSet<Instruction> instructions = subprogramToInstructions
						.get (subprg);
				instructions.add (instr);

				String opCode = lexemes[opCodeIndex];
				if (instructionSet.getBranches ().contains (opCode))
				{
					Debug.debugMessage (getClass (), addressStr + " " + opCode
							+ " is branch/jump instruction", 4);

					long destination;
					if (instructionSet.getUnconditionalBranches ().contains (
							opCode)
							|| opCode.equals (instructionSet
									.getSubprogramCallInstruction ()))
					{
						destination = Long.parseLong (
								lexemes[destinationIndex], 16);
					}
					else
					{
						int i1 = buffer.lastIndexOf (",");
						if (i1 == -1)
						{
							/*
							 * The destination of "bc1f" and "bc1t" instructions
							 * is directly after the instruction
							 */
							i1 = buffer.indexOf (" ");
						}

						int i2 = buffer.indexOf ("<");
						destination = Long.parseLong (buffer.substring (i1 + 1,
								i2 - 1), 16);
					}

					subprogramToBranchTargets.get (subprg).add (destination);
					subprogramToBranchInstructions.get (subprg).put (
							Long.parseLong (addressStr, 16), destination);

					if (instructionSet.getUnconditionalBranches ().contains (
							opCode))
					{
						subprogramToUnconditionalBranches.get (subprg).add (
								Long.parseLong (addressStr, 16));
					}
				}
			}
		}

		private void parseARMInstruction (String str, String subprg)
		{
			final String[] lexemes = str.split ("\\s+");
			final int addressIndex = 1;
			final int opCodeIndex = 3;
			final int destinationIndex = 4;

			String addressStr = lexemes[addressIndex].substring (0,
					lexemes[addressIndex].length () - 1);
			StringBuffer buffer = new StringBuffer ();
			for (int i = opCodeIndex; i < lexemes.length; ++i)
			{
				buffer.append (lexemes[i] + " ");
			}
			Instruction instr = new Instruction (Long
					.parseLong (addressStr, 16), buffer.toString ());
			TreeSet<Instruction> instructions = subprogramToInstructions
					.get (subprg);
			instructions.add (instr);

			String opCode = lexemes[opCodeIndex];
			if (instructionSet.getBranches ().contains (opCode))
			{
				Debug.debugMessage (getClass (), addressStr + " " + opCode
						+ " is branch/jump instruction", 4);

				long destination = Long.parseLong (lexemes[destinationIndex],
						16);
				subprogramToBranchTargets.get (subprg).add (destination);
				subprogramToBranchInstructions.get (subprg).put (
						Long.parseLong (addressStr, 16), destination);

				if (instructionSet.getUnconditionalBranches ()
						.contains (opCode))
				{
					subprogramToUnconditionalBranches.get (subprg).add (
							Long.parseLong (addressStr, 16));
				}
			}
		}

		private void parseALPHAInstruction (String str, String subprg)
		{
			final String[] lexemes = str.split ("\\s+");
			final int addressIndex = 1;
			final int opCodeIndex = 6;
			final int destinationIndex = 7;
			final int symbolIndex = 8;

			String addressStr = lexemes[addressIndex].substring (0,
					lexemes[addressIndex].length () - 1);
			StringBuffer buffer = new StringBuffer ();
			for (int i = opCodeIndex; i < lexemes.length; ++i)
			{
				buffer.append (lexemes[i] + " ");
			}
			Instruction instr = new Instruction (Long
					.parseLong (addressStr, 16), buffer.toString ());
			TreeSet<Instruction> instructions = subprogramToInstructions
					.get (subprg);
			instructions.add (instr);

			String opCode = lexemes[opCodeIndex];
			if (instructionSet.getBranches ().contains (opCode))
			{
				Debug.debugMessage (getClass (), addressStr + " " + opCode
						+ " is branch/jump instruction", 4);

				long destination;
				if (opCode.equals (instructionSet
						.getSubprogramCallInstruction ()))
				{
					int i1 = lexemes[destinationIndex].lastIndexOf (",");
					long baseAddress = Long.parseLong (
							lexemes[destinationIndex].substring (i1 + 1), 16);
					long offset = 0;
					if (lexemes[symbolIndex].contains ("+0x"))
					{
						int i2 = lexemes[symbolIndex].lastIndexOf ("x");
						int i3 = lexemes[symbolIndex].lastIndexOf (">");
						offset = Long.parseLong (lexemes[symbolIndex]
								.substring (i2 + 1, i3), 16);
					}
					destination = baseAddress - offset;
				}
				else
				{
					int i = lexemes[destinationIndex].lastIndexOf (",");
					destination = Long.parseLong (lexemes[destinationIndex]
							.substring (i + 1), 16);
				}

				subprogramToBranchTargets.get (subprg).add (destination);
				subprogramToBranchInstructions.get (subprg).put (
						Long.parseLong (addressStr, 16), destination);

				if (instructionSet.getUnconditionalBranches ()
						.contains (opCode))
				{
					subprogramToUnconditionalBranches.get (subprg).add (
							Long.parseLong (addressStr, 16));
				}
			}
		}

		private void parseSPARCInstruction (String str, String subprg)
		{
			final String[] lexemes = str.split ("\\s+");
			final int addressIndex = 0;
			final int opCodeIndex = 5;
			final int destinationIndex = 6;

			String addressStr = lexemes[addressIndex].substring (0,
					lexemes[addressIndex].length () - 1);
			StringBuffer buffer = new StringBuffer ();
			for (int i = opCodeIndex; i < lexemes.length; ++i)
			{
				buffer.append (lexemes[i] + " ");
			}
			Instruction instr = new Instruction (Long
					.parseLong (addressStr, 16), buffer.toString ());
			TreeSet<Instruction> instructions = subprogramToInstructions
					.get (subprg);
			instructions.add (instr);

			try
			{
				String opCode = lexemes[opCodeIndex];
				if (instructionSet.getBranches ().contains (opCode))
				{
					Debug.debugMessage (getClass (), addressStr + " " + opCode
							+ " is branch/jump instruction", 4);

					if (instructionSet.getUnconditionalBranches ().contains (
							opCode))
					{
						subprogramToUnconditionalBranches.get (subprg).add (
								Long.parseLong (addressStr, 16));
					}

					try
					{
						/*
						 * The SPARC architecture has "ret" and "retl"
						 * instructions which are effectively unconditional
						 * jumps without a target. Initially set the destination
						 * as the dummy target and wait to see a target is found
						 */
						long destination = DUMMY_DESTINATION;

						if (lexemes.length > destinationIndex)
						{
							destination = Long.parseLong (
									lexemes[destinationIndex], 16);

							/*
							 * Only add the destination address as a branch
							 * target if it an actual address, and not a dummy
							 * value
							 */
							subprogramToBranchTargets.get (subprg).add (
									destination);
						}

						subprogramToBranchInstructions.get (subprg).put (
								Long.parseLong (addressStr, 16), destination);
					}
					catch (NumberFormatException e)
					{
						Debug
								.debugMessage (
										getClass (),
										lexemes[destinationIndex]
												+ " is not a valid destination of the branch",
										1);
					}
				}
			}
			catch (ArrayIndexOutOfBoundsException e)
			{
				Debug.debugMessage (getClass (), str
						+ " does not have have an opcode", 1);
			}
		}

		private void parseX86Instruction (String str, String subprg)
		{
			final String[] lexemes = str.split ("\\s+");

			int addressIndex = 1;
			int opCodeIndex = -1;
			int destinationIndex = -1;

			/*
			 * X86 instructions are variable length. Skip past all the
			 * hexadecimal lexemes as they are the instructions
			 */
			boolean opCodeFound = false;
			StringBuffer buffer = new StringBuffer ();
			for (int i = addressIndex + 1; i < lexemes.length; ++i)
			{
				if (!opCodeFound && !lexemes[i].matches ("[0-9A-Fa-f]+"))
				{
					opCodeIndex = i;
					destinationIndex = i + 1;
					opCodeFound = true;
				}
				if (opCodeFound)
				{
					buffer.append (lexemes[i] + " ");
				}
			}

			if (opCodeIndex == -1)
			{
				System.err.println ("Could not find the opcode in " + str);
				System.exit (1);
			}

			String addressStr = lexemes[addressIndex].substring (0,
					lexemes[addressIndex].length () - 1);
			Instruction instr = new Instruction (Long
					.parseLong (addressStr, 16), buffer.toString ());
			TreeSet<Instruction> instructions = subprogramToInstructions
					.get (subprg);
			instructions.add (instr);

			String opCode = lexemes[opCodeIndex];
			if (instructionSet.getBranches ().contains (opCode))
			{
				Debug.debugMessage (getClass (), addressStr + " " + opCode
						+ " is branch/jump instruction", 4);

				try
				{
					long destination = Long.parseLong (
							lexemes[destinationIndex], 16);
					subprogramToBranchTargets.get (subprg).add (destination);
					subprogramToBranchInstructions.get (subprg).put (
							Long.parseLong (addressStr, 16), destination);

					if (instructionSet.getUnconditionalBranches ().contains (
							opCode))
					{
						subprogramToUnconditionalBranches.get (subprg).add (
								Long.parseLong (addressStr, 16));
					}
				}
				catch (NumberFormatException e)
				{
					Debug
							.debugMessage (
									getClass (),
									instr.getInstruction ()
											+ " contains register-indirect branch. Cannot determine destination of branch.",
									4);
				}
			}
		}

		private void identifyLeaders ()
		{
			for (String subprogramName: subprogramToInstructions.keySet ())
			{
				int subprogramID = program.nameToId.get (subprogramName);
				Debug.debugMessage (getClass (), "Identifying leaders in "
						+ subprogramName, 2);

				TreeSet<Long> leaders = subprogramToLeader.get (subprogramName);
				long previousAddress = 0;
				long firstAddress = Long.MAX_VALUE;
				long lastAddress = 0;
				boolean firstInstruction = true;

				for (Instruction instr: subprogramToInstructions
						.get (subprogramName))
				{
					long address = instr.getAddress ();

					if (firstInstruction)
					{
						firstInstruction = false;
						leaders.add (address);
						Debug.debugMessage (getClass (), Long
								.toHexString (address)
								+ " is the first instruction", 3);
					}
					if (subprogramToBranchInstructions.get (subprogramName)
							.containsKey (previousAddress))
					{
						leaders.add (address);
						Debug.debugMessage (getClass (), Long
								.toHexString (previousAddress)
								+ " is a branch instruction", 3);
					}
					if (subprogramToBranchTargets.get (subprogramName)
							.contains (address))
					{
						leaders.add (address);
						Debug.debugMessage (getClass (), Long
								.toHexString (address)
								+ " is a branch target", 3);
					}

					previousAddress = address;

					if (address < firstAddress)
					{
						firstAddress = address;
					}
					if (address > lastAddress)
					{
						lastAddress = address;
					}
				}

				Debug.debugMessage (getClass (), firstAddress
						+ " is its first address", 4);
				Debug.debugMessage (getClass (), lastAddress
						+ " is its last address", 4);

				firstAddressToSubprogram.put (firstAddress, subprogramName);
				lastAddressToSubprogram.put (lastAddress, subprogramName);
				subprogramToFirstAddress.put (subprogramName, firstAddress);
				subprogramToLastAddress.put (subprogramName, lastAddress);
				program.idToSubprogram.get (subprogramID).getCFG ()
						.setFirstAddress (firstAddress);
				program.idToSubprogram.get (subprogramID).getCFG ()
						.setLastAddress (lastAddress);
			}
		}

		private void identifyBasicBlocks ()
		{
			for (String subprogramName: subprogramToInstructions.keySet ())
			{
				int subprogramID = program.nameToId.get (subprogramName);
				TreeSet<Long> leaders = subprogramToLeader.get (subprogramName);
				BasicBlock bb = null;

				for (Instruction instr: subprogramToInstructions
						.get (subprogramName))
				{
					long address = instr.getAddress ();

					if (leaders.contains (address))
					{
						ControlFlowGraph cfg = program.idToSubprogram.get (
								subprogramID).getCFG ();
						cfg.setSubprogramName (subprogramName);
						cfg.addBasicBlock (bbID);
						bb = cfg.getBasicBlock (bbID);
						bb.addInstruction (instr);
						if (address == cfg.getFirstAddress ())
						{
							cfg.setEntryID (bbID);
						}
						bbID++;
					}
					else
					{
						bb.addInstruction (instr);
					}
				}
			}
		}

		private void addEdges ()
		{
			for (String subprogramName: program.nameToId.keySet ())
			{
				Debug.debugMessage (getClass (), "Adding edges to CFG of "
						+ subprogramName, 2);

				int subprogramID = program.nameToId.get (subprogramName);
				ControlFlowGraph cfg = program.idToSubprogram
						.get (subprogramID).getCFG ();
				for (Vertex u: cfg)
				{
					BasicBlock v = (BasicBlock) u;

					boolean addUnconditional = true;
					Instruction instr = ((BasicBlock) v).getLastInstruction ();

					if (instr.getOperation ().equals (
							instructionSet.getSubprogramCallInstruction ()))
					{
						if (subprogramToBranchInstructions.get (subprogramName)
								.containsKey (instr.getAddress ()))
						{
							/*
							 * Guard against register-indirect branches
							 */
							long target = subprogramToBranchInstructions.get (
									subprogramName).get (instr.getAddress ());

							if (firstAddressToSubprogram.containsKey (target))
							{
								String destination = firstAddressToSubprogram
										.get (target);
								program.callg.addCall (subprogramName,
										destination, v.getVertexID ());

								Debug.debugMessage (getClass (),
										"Adding call from " + subprogramName
												+ " to " + destination + " @ "
												+ v.getVertexID (), 4);
							}
						}
					}
					else if (instructionSet.getBranches ().contains (
							instr.getOperation ()))
					{
						long target = subprogramToBranchInstructions.get (
								subprogramName).get (instr.getAddress ());

						if (target < subprogramToFirstAddress
								.get (subprogramName)
								|| target > subprogramToLastAddress
										.get (subprogramName))
						{
							/*
							 * Some of branch instructions can "emulate" a
							 * subprogram call. Therefore, if the branch target
							 * is not in the address range of this subprogram
							 * then flow of control is directed to a different
							 * subprogram
							 */
							if (firstAddressToSubprogram.containsKey (target))
							{
								String destination = firstAddressToSubprogram
										.get (target);
								program.callg.addCall (subprogramName,
										destination, v.getVertexID ());

								Debug.debugMessage (getClass (),
										"Adding call from " + subprogramName
												+ " to " + destination + " @ "
												+ v.getVertexID (), 4);
							}
						}
						else
						{
							BasicBlock w = cfg.getBasicBlock (target);
							cfg.addEdge (v.getVertexID (), w.getVertexID (),
									BranchType.TAKEN);

							Debug.debugMessage (getClass (), "Adding edge "
									+ v.getVertexID () + "=>"
									+ w.getVertexID (), 4);
						}

						/*
						 * Only add a not-taken edge if the branch instruction
						 * is not an unconditional jump
						 */
						if (subprogramToUnconditionalBranches.get (
								subprogramName).contains (instr.getAddress ()))
						{
							addUnconditional = false;
						}
					}

					if (addUnconditional)
					{
						if (v.getLastAddress () != subprogramToLastAddress
								.get (subprogramName))
						{
							/*
							 * Only add a successor if this is not the return
							 * basic block of the subprogram
							 */
							BasicBlock w = cfg.getBasicBlock (v
									.getLastAddress ()
									+ instructionSet.getAddressOffset ());
							if (w != null)
							{
								cfg.addEdge (v.getVertexID (),
										w.getVertexID (), BranchType.NOTTAKEN);

								Debug.debugMessage (getClass (), "Adding edge "
										+ v.getVertexID () + "=>"
										+ w.getVertexID (), 4);
							}
						}
					}
				}
			}
		}
	}

	@SuppressWarnings("serial")
	private class NoSuchRootException extends Exception
	{
		private final String rootName;

		public NoSuchRootException (String rootName)
		{
			super ();
			this.rootName = rootName;
		}

		public String getMessage ()
		{
			StringBuffer buffer = new StringBuffer ("The root subprogram '"
					+ rootName + "' does not exist in this program. ");
			HashSet<String> suggestions = new HashSet<String> ();

			for (String subprogramName: program.nameToId.keySet ())
			{
				if (subprogramName.matches (rootName + "[a-zA-Z0-9_]+")
						|| subprogramName.matches ("[a-zA-Z_]" + rootName))
				{
					suggestions.add (subprogramName);
				}
			}
			if (suggestions.size () > 0)
			{
				int i = 1;
				buffer.append ("Did you mean: ");
				for (String subprogramName: suggestions)
				{
					buffer.append ("'" + subprogramName + "'");
					if (i++ < suggestions.size ())
					{
						buffer.append (" or ");
					}
				}
				buffer.append ("?");
			}
			else
			{
				buffer
						.append ("Unable to find a subprogram with a similar name.");
			}
			return buffer.toString ();
		}
	}
}