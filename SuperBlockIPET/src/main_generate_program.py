#!/usr/bin/env python

import argparse
import os
import re
import sys
import config
import generate_program
import program_input_output
import debug

def the_command_line():
    new_filename_prefix = "program"
    
    def clean():
        for paths, dirs, files in os.walk(os.path.abspath(os.curdir)):
            for filename in files:
                if re.match(r'%s[0-9]+\.txt' % new_filename_prefix, filename):
                    full_path = os.path.join(paths, filename)
                    debug.verbose_message("Removing '%s'" % full_path, __name__)
                    os.remove(full_path)
    
    def create_filename():
        files   = [f for f in os.listdir(os.curdir) if os.path.isfile(os.path.join(os.curdir,f))]
        numbers = set()
        for filename in files:
            if re.match(r'%s[0-9]+\.txt' % new_filename_prefix, filename):
                filenumbers = re.findall(r'[0-9]+', filename)
                assert len(filenumbers) == 1
                filenumber = filenumbers[0]
                numbers.add(int(filenumber))
        for i in xrange(1,sys.maxint):
            if i not in numbers:
                return os.path.abspath('%s%d.txt' % (new_filename_prefix, i))
        assert False
        
    class SubprogramsAction(argparse.Action):
        def __call__(self, parser, namespace, value, option_string=None):
            if value <= 0: 
                raise argparse.ArgumentTypeError("The number of subprograms must be a positive integer")
            setattr(namespace, self.dest, value)
            
    class BasicBlockAction(argparse.Action):
        def __call__(self, parser, namespace, value, option_string=None):
            if value <= 0: 
                raise argparse.ArgumentTypeError("The number of basic blocks per program must be a positive integer")
            setattr(namespace, self.dest, value)
            
    class FanOutAction(argparse.Action):
        def __call__(self, parser, namespace, value, option_string=None):
            if value <= 1: 
                raise argparse.ArgumentTypeError("The maximum fan out of a basic block must be at least two to allow branches")
            setattr(namespace, self.dest, value)
            
    # The command-line parser and its options
    parser = argparse.ArgumentParser(description="Generate random program structure (call graph and CFGs)")
    
    parser.add_argument("directory",
                        help="write the program file to this directory")
    
    parser.add_argument("-f",
                        "--filename",
                        help="write the program to this file name",
                        default=create_filename())
    
    parser.add_argument("-c",
                        "--clean",
                        metavar="",
                        type=clean,
                        help="clean files from previous runs",
                        default=False)
    
    parser.add_argument("-d",
                        "--debug",
                        type=int,
                        help="debug mode",
                        default=0)
    
    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="be verbose",
                        default=False)
    
    parser.add_argument("-u",
                        "--udraw",
                        action="store_true",
                        help="generate uDraw files to visualise graphs",
                        default=False)
    
    parser.add_argument("--subprograms",
                        action=SubprogramsAction,
                        type=int,
                        help="number of subprograms",
                        default=1,
                        metavar="<INT>")
    
    parser.add_argument("--loops",
                        type=int,
                        help="maximum number of loops in a CFG",
                        default=0,
                        metavar="<INT>")
    
    parser.add_argument("--self-loops",
                        type=int,
                        help="maximum number of self-loops in a CFG",
                        default=0,
                        metavar="<INT>")
    
    parser.add_argument("--nesting-depth",
                        type=int,
                        help="maximum nesting depth of loops",
                        default=1,
                        metavar="<INT>")
    
    parser.add_argument("--fan-out",
                        action=FanOutAction,
                        type=int,
                        help="maximum fan out of a CFG vertex",
                        default=2,
                        metavar="<INT>")
    
    parser.add_argument("--basic-blocks",
                        type=int,
                        action=BasicBlockAction,
                        help="maximum number of vertices in a CFG",
                        default=10,
                        metavar="<INT>")
    
    parser.add_argument("--breaks",
                        action="store_true",
                        help="allow break-like constructs in the CFG",
                        default=False)
    
    parser.add_argument("--continues",
                        action="store_true",
                        help="allow continue-like constructs in the CFG",
                        default=False)
    
    parser.add_argument("--unstructured",
                        action="store_true",
                        help="add unstructured edges to the CFG",
                        default=False)
    
    parser.parse_args(namespace=config.Arguments)
    
    setattr(config.Arguments, "basepath", os.path.abspath(config.Arguments.directory))
        
if __name__ == "__main__":
    the_command_line()
    program = generate_program.do_it()
    program_input_output.write_file(program, config.Arguments.filename)
    
    