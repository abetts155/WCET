package adam.betts.utilities;

import java.util.Arrays;

import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.Option;
import org.apache.commons.cli.Options;

import adam.betts.calculations.IPETModel;
import adam.betts.utilities.Enums.IProfile;
import adam.betts.utilities.Enums.ISA;
import adam.betts.utilities.Enums.LpSolveVerbosity;
import adam.betts.utilities.Enums.OutputFormats;

public class DefaultOptions
{
	public static Option helpOption;
	private static Option verboseOption;
	private static Option debugOption;
	private static Option programFileOption;
	private static Option traceFileOption;
	private static Option outFileOption;
	private static Option rootOption;
	private static Option iprofileOption;
	private static Option uDrawDirectoryOption;
	private static Option outputFormatOption;
	private static Option lpSolveDirectoryOption;
	private static Option lpSolveVerbosityOption;
	private static Option loopContraintLevelOption;

	public final static void addDefaultOptions (Options options)
	{
		helpOption = new Option ("h", "help", false, "Display this message.");
		options.addOption (helpOption);

		verboseOption = new Option ("v", "verbose", false, "Be verbose.");
		options.addOption (verboseOption);

		debugOption = new Option ("d", "debug", true, "Debug mode.");
		debugOption.setOptionalArg (true);
		options.addOption (debugOption);
	}

	public final static void addProgramOption (Options options)
	{
		programFileOption = new Option ("p", "program", true,
				"File containing program structure (either XML or disassembly)."
						+ "\nSupported instruction set architectures: "
						+ Arrays.toString (ISA.values ()).replace ("[", "")
								.replace ("]", "") + ".");
		programFileOption.setRequired (true);
		options.addOption (programFileOption);
	}

	public final static void addRootOption (Options options)
	{
		rootOption = new Option ("r", "root", true,
				"Entry point(s) of the program.");
		rootOption.setRequired (true);
		rootOption.setArgs (Option.UNLIMITED_VALUES);
		options.addOption (rootOption);
	}

	public final static void setDefaultOptions (CommandLine line)
	{
		Debug.setVerbose (line.hasOption (verboseOption.getOpt ()));

		if (line.hasOption (debugOption.getOpt ()))
		{
			String arg = line.getOptionValue (debugOption.getOpt ());
			if (arg != null)
			{
				try
				{
					int debugLevel = Integer.parseInt (arg);
					if (debugLevel < Debug.LOWEST_DEBUG
							|| debugLevel > Debug.HIGHEST_DEBUG)
					{
						throw new IllegalArgumentException ();
					}
					else
					{
						Debug.setDebugLevel (debugLevel);
					}
				}
				catch (NumberFormatException e)
				{
					System.err.println ("'" + arg
							+ "' is not a valid argument to the debug option.");
					System.exit (1);
				}
				catch (IllegalArgumentException e)
				{
					System.err
							.println (arg
									+ " is not a valid debug level. It should be in the range: "
									+ Debug.LOWEST_DEBUG + ".."
									+ Debug.HIGHEST_DEBUG + ".");
					System.exit (1);
				}
			}
			else
			{
				System.err
						.println ("You must specify the level of debug mode as an argument to the debug option.");
				System.exit (1);
			}
		}
	}

	public final static void setProgramOption (CommandLine line)
	{
		Globals.setProgramFileName (line.getOptionValue (programFileOption
				.getOpt ()));
	}

	public final static void setRootOption (CommandLine line)
	{
		for (String arg: line.getOptionValues (rootOption.getOpt ()))
		{
			Globals.setRoot (arg);
		}
	}

	public final static void addInstrumentationProfileOption (Options options,
			boolean requiredOption,
			int numberOfArgs)
	{
		iprofileOption = new Option ("i", "instrument", true,
				"Instrument virtually according to a particular profile."
						+ "\nSupported arguments are: "
						+ Arrays.toString (IProfile.values ())
								.replace ("[", "").replace ("]", ""));
		iprofileOption.setRequired (requiredOption);
		iprofileOption.setArgs (numberOfArgs);
		options.addOption (iprofileOption);
	}

	public final static void setInstrumentationProfileOption (CommandLine line)
	{
		if (line.hasOption (iprofileOption.getOpt ()))
		{
			String[] iprofileOpts = line.getOptionValues (iprofileOption
					.getOpt ());
			for (int i = 0; i < iprofileOpts.length; ++i)
			{
				String iprofile = iprofileOpts[i];
				try
				{
					Globals.addInstrumentationProfile (IProfile
							.valueOf (iprofile.toUpperCase ()));
				}
				catch (IllegalArgumentException e)
				{
					System.err.println (iprofile
							+ " is not a valid instrumentation profile");
					System.exit (1);
				}
			}
		}
	}

	public final static void addOutputFormatOption (Options options)
	{
		outputFormatOption = new Option ("f", "format", true,
				"Output the CFGs to a file."
						+ "\nSupported formats are: "
						+ Arrays.toString (OutputFormats.values ()).replace (
								"[", "").replace ("]", ""));
		outputFormatOption.setRequired (true);
		options.addOption (outputFormatOption);
	}

	public final static void setOutputFormatOption (CommandLine line)
	{
		String arg = line.getOptionValue (outputFormatOption.getOpt ());
		try
		{
			OutputFormats format = OutputFormats.valueOf (arg.toUpperCase ());
			Globals.setOutputFormat (format);
		}
		catch (IllegalArgumentException e)
		{
			System.err.println (arg + " is not a valid output option.");
			System.exit (1);
		}
	}

	public final static void addTraceFileOption (Options options)
	{
		traceFileOption = new Option ("t", "trace", true, "The trace file.");
		traceFileOption.setRequired (true);
		options.addOption (traceFileOption);
	}

	public final static void setTraceFileOption (CommandLine line)
	{
		Globals.setTraceFileName (line.getOptionValue (traceFileOption
				.getOpt ()));
	}

	public final static void addOutFileOption (Options options)
	{
		outFileOption = new Option ("o", "output", true, "The output file.");
		outFileOption.setRequired (true);
		options.addOption (outFileOption);
	}

	public final static void setOutFileOption (CommandLine line)
	{
		Globals.setOutputFileName (line
				.getOptionValue (outFileOption.getOpt ()));
	}

	public final static void addUDrawDirectoryOption (Options options)
	{
		uDrawDirectoryOption = new Option ("U", "udraw", true,
				"Create uDraw files and output to this directory.");
		uDrawDirectoryOption.setRequired (false);
		options.addOption (uDrawDirectoryOption);
	}

	public final static void setUDrawDirectoryOption (CommandLine line)
	{
		if (line.hasOption (uDrawDirectoryOption.getOpt ()))
		{
			Globals.setUDrawDirectory (line
					.getOptionValue (uDrawDirectoryOption.getOpt ()));
		}
	}

	public final static void addIPETOptions (Options options)
	{
		lpSolveDirectoryOption = new Option ("L", "lpsolve", true,
				"Write the lp_solve models to files inside this directory.");
		lpSolveDirectoryOption.setRequired (false);
		options.addOption (lpSolveDirectoryOption);

		lpSolveVerbosityOption = new Option (
				"l",
				"lpsolve-verbose",
				true,
				"Force the verbosity of lp_solve to the selected level.\nSupported arguments are: "
						+ Arrays.toString (LpSolveVerbosity.values ()).replace (
								"[", "").replace ("]", ""));
		lpSolveVerbosityOption.setRequired (false);
		options.addOption (lpSolveVerbosityOption);

		loopContraintLevelOption = new Option (
				"c",
				"constraint-level",
				true,
				"Only consider relative capacity constraints up to this level of loop nesting. Must be a positive number.");
		loopContraintLevelOption.setRequired (false);
		options.addOption (loopContraintLevelOption);
	}

	public final static void setIPETOptions (CommandLine line)
	{

		String arg = line.getOptionValue (lpSolveDirectoryOption.getOpt ());
		if (arg != null)
		{
			IPETModel.setILPDirectory (arg);

		}

		arg = line.getOptionValue (lpSolveVerbosityOption.getOpt ());
		if (arg != null)
		{
			try
			{
				IPETModel.setLpSolveVerbosity (arg.toUpperCase ());
			}
			catch (IllegalArgumentException e)
			{
				System.err.println (arg
						+ " is not a valid verbosity level of lp_solve.");
				System.exit (1);
			}
		}

		arg = line.getOptionValue (loopContraintLevelOption.getOpt ());
		if (arg != null)
		{
			try
			{
				int level = Integer.parseInt (arg);
				if (level < 1)
				{
					throw new IllegalArgumentException ();
				}
				else
				{
					IPETModel.setLoopConstraintLevel (level);
				}
			}
			catch (NumberFormatException e)
			{
				System.err.println ("'" + arg + "' is not a valid argument to "
						+ loopContraintLevelOption.getLongOpt ());
				System.exit (1);
			}
			catch (IllegalArgumentException e)
			{
				System.err
						.println (arg
								+ " is not a valid loop constraint level. It must be a positive number.");
				System.exit (1);
			}
		}
	}
}