#!/usr/bin/python2.6

import sys, optparse, os
import ParseProgramFile, Debug, IPGs, Trees, UDrawGraph, IPGCalculations, Database

# The command-line parser and its options
cmdline = optparse.OptionParser(add_help_option=False)

cmdline.add_option("-d",
                  "--debug",
                  action="store",
                  dest="debug",
                  type="int",
                  help="Debug mode.",
                  default=False)

cmdline.add_option("-h",
                  "--help",
                  action="help",
                  help="Display this help message.")

cmdline.add_option("-v",
                 "--verbose",
                 action="store_true",
                 dest="verbose",
                 help="Be verbose.",
                 default=False)

cmdline.add_option("-C",
                  "--deep-clean",
                  action="store_true",
                  dest="deepclean",
                  help="Clean previous runs of GPGPU-sim and uDrawgraph files.",
                  default=False)

cmdline.add_option("-u",
                 "--udraw",
                 action="store_true",
                 dest="udraw",
                 help="Generate uDrawGraph files.",
                 default=False)

(opts, args) = cmdline.parse_args(sys.argv[1:])
Debug.verbose = opts.verbose
Debug.debug = opts.debug

def removeFile (fullPath):
    Debug.verboseMessage("Removing '%s'" % fullPath)
    os.remove(fullPath)

def preClean (abspath):
    for paths, dirs, files in os.walk(os.path.abspath(os.curdir)):
        files.sort()
        for filename in files:
            if filename.endswith('.udraw') or filename.endswith('.ilp'):
                removeFile(os.path.join(paths, filename))
                
if __name__ == "__main__":
    if opts.deepclean:
        preClean(os.path.abspath(os.curdir))
    if len(args) == 1:
        infile = args[0]
        assert infile.endswith('.txt'), "Please pass a program file with a '%s' suffix" % ('.txt')
        # Create the CFGs
        filename = os.path.basename(infile)
        basepath = os.path.abspath(os.path.dirname(infile))
        basename = os.path.splitext(filename)[0]
        program = ParseProgramFile.createProgram(infile)
        for icfg in program.getICFGs():
            UDrawGraph.makeUdrawFile(icfg, "%s.%s.%s" % (basename, icfg.getName(), "icfg"))
            lnt = Trees.LoopNests(icfg, icfg.getEntryID())
            UDrawGraph.makeUdrawFile(lnt, "%s.%s.%s" % (basename, icfg.getName(), "lnt"))
            ipg = IPGs.IPG(icfg)
            UDrawGraph.makeUdrawFile(ipg, "%s.%s.%s" % (basename, icfg.getName(), "ipg"))
            miniIPGs = IPGCalculations.BuildMiniIPGs(basename, icfg, lnt, ipg)
            data     = Database.CreateWCETData(icfg, lnt, ipg)
            IPGCalculations.CreateICFGILP(basepath, basename, data, icfg, lnt)
            IPGCalculations.CreateIPGILP(basepath, basename, data, ipg, lnt, miniIPGs)
    else:
        Debug.exitMessage("You need to specify the name of a file containing CFGs")