#!/usr/bin/python
'''

Copyright 2015 Mark L. Palmeri (mlp6@duke.edu)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

20100520
  * consolidated sigmas into one input tuple
  * corrected need for abs value on the symmetry searches
  * corrected the Guassian amplitude calculation to actually include the sigmas!
  * converted the 'fields' read from the nodefile to floats right off the bat

2012-08-27 (Palmeri)
  * Added 'none' symmetry option in case no symmetry is being used in the model

'''

__author__ = "Mark Palmeri"
__email__ = "mlp6@duke.edu"

import sys
import math
import fem_mesh

def main():
    """
    Generate Guassian-weighted point load distribution
    """
    fem_mesh.check_version()

    opts = read_cli()

    # setup the new output file with a very long, but unique, filename
    loadfilename = ("gauss_exc_sigma_%.3f_%.3f_%.3f_center_%.3f_%.3f_%.3f_amp_%.3f_amp_cut_%.3f_%s.dyn" %
                    (opts.sigma[0], opts.sigma[1], opts.sigma[2],
                     opts.center[0], opts.center[1], opts.center[2],
                     opts.amp, opts.amp_cut, opts.sym))
    LOADFILE = open(loadfilename, 'w')
    LOADFILE.write("$ Generated using %s:\n" % sys.argv[0])
    LOADFILE.write("$ %s\n" % opts)

    LOADFILE.write("*LOAD_NODE_POINT\n")

    # loop through all of the nodes and see which ones fall w/i the Gaussian
    # excitation field
    sym_node_count = 0
    node_count = 0
    NODEFILE = open(opts.nodefile,'r')
    for i in NODEFILE:
        # make sure not to process comment and command syntax lines
        if i[0] != "$" and i[0] != "*":
            i = i.rstrip('\n')
            # dyna scripts should be kicking out comma-delimited data; if not,
            # then the user needs to deal with it
            fields = i.split(',')
            fields = [float(j) for j in fields]
            # check for unexpected inputs and exit if needed (have user figure
            # out what's wrong)
            if len(fields) != 4:
                print("ERROR: Unexpected number of node columns")
                print(fields)
                sys.exit(1)
            # compute the Gaussian amplitude at the node
            exp1 = math.pow((fields[1]-opts.center[0])/opts.sigma[0], 2)
            exp2 = math.pow((fields[2]-opts.center[1])/opts.sigma[1], 2)
            exp3 = math.pow((fields[3]-opts.center[2])/opts.sigma[2], 2)
            nodeGaussAmp = opts.amp * math.exp(-(exp1 + exp2 + exp3))

            # write the point load only if the amplitude is above the cutoff
            # dyna input needs to be limited in precision
            if nodeGaussAmp > opts.amp*opts.amp_cut:

                node_count += 1
                # check for quarter symmetry force reduction (if needed)
                if opts.sym == 'qsym':
                    if (math.fabs(fields[1]) < opts.search_tol and
                       math.fabs(fields[2]) < opts.search_tol):
                        nodeGaussAmp = nodeGaussAmp/4
                        sym_node_count += 1
                    elif (math.fabs(fields[1]) < opts.search_tol or
                          math.fabs(fields[2]) < opts.search_tol):
                        nodeGaussAmp = nodeGaussAmp/2
                        sym_node_count += 1
                # check for half symmetry force reduction (if needed)
                elif opts.sym == 'hsym':
                    if math.fabs(fields[1]) < opts.search_tol:
                        nodeGaussAmp = nodeGaussAmp/2
                        sym_node_count += 1
                elif opts.sym != 'none':
                    sys.exit('ERROR: Invalid symmetry option specified.')

                LOADFILE.write("%i,3,1,-%.4f\n" % (int(fields[0]),
                                                   nodeGaussAmp))

    # wrap everything up
    NODEFILE.close()
    LOADFILE.write("*END\n")
    LOADFILE.write("$ %i loads generated\n" % node_count)
    LOADFILE.write("$ %i exist on a symmetry plane / edge\n" % sym_node_count)
    LOADFILE.close()

def read_cli():
    """
    read CLI arguments
    """
    import argparse as ap

    p = ap.ArgumentParser(description="Generate *LOAD_NODE_POINT data "
                          "with Gaussian weighting about dim1 = 0, "
                          "dim2 = 0, extending through dim3.  All "
                          "spatial units are in the unit system for the "
                          "node definitions.",
                          formatter_class=ap.ArgumentDefaultsHelpFormatter)
    p.add_argument("--nodefile",
                   help="Node definition file (*.dyn)",
                   default="nodes.dyn")
    p.add_argument("--sigma",
                   type=float,
                   help="Standard devisions in 3 dims",
                   nargs=3,
                   default=(1.0, 1.0, 1.0))
    p.add_argument("--amp",
                   type=float,
                   help="Peak Gaussian amplitude",
                   default=1.0)
    p.add_argument("--amp_cut",
                   type=float,
                   help="Cutoff from peak amplitude to discard (so a lot "
                   "of the nodes don't have neglible loads on them)",
                   default=0.05)
    p.add_argument("--center",
                   type=float,
                   help="Gaussian center",
                   nargs=3,
                   default=(0.0, 0.0, -2.0))
    p.add_argument("--search_tol",
                   type=float,
                   help="Node search tolerance",
                   default=0.0001)
    p.add_argument("--sym",
                   help="Mesh symmetry (qsym or hsym)",
                   default="qsym")

    opts = p.parse_args()

    return opts

if __name__ == "__main__":
    main()

