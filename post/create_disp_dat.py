#!/bin/env python
"""
create_disp_dat.py

Create disp.dat file from nodout file.

This is replacing StuctPost, which relied on LS-PREPOST, to extract data from
d3plot* files.  (LS-PREPOST no longer works gracefully on the cluster w/o
GTK/video support.)  Instead of working with d3plot files, this approach now
utilizes ASCII nodout files.  Also replaced the Matlab scritps, so this should
run self-contained w/ less dependencies.

EXAMPLE
=======
create_disp_dat.py

=======
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
"""

__author__ = "Mark Palmeri"
__email__ = "mlp6@duke.edu"
__license__ = "Apache v2.0"


def main():
    import sys

    if sys.version_info[:2] < (2, 7):
        sys.exit("ERROR: Requires Python >= 2.7")

    # let's read in some command-line arguments
    args = parse_cli()

    # default to make a binary file if output file type isn't indicated
    if (not args.vtk and not args.dat):
        args.dat = True

    # open nodout file
    if args.nodout.endswith('gz'):
        import gzip
        print("Extracting gzip-compressed data . . .\n")
        nodout = gzip.open(args.nodout, 'r')
    else:
        print("Extracting data . . .\n")
        nodout = open(args.nodout, 'r')

    # create output file
    if (args.dat):
        create_dat(args, nodout)

    if (args.vtk):
        create_vtk(args, nodout)

def create_dat(args, nodout):
    import sys

    # open dispout for binary writing
    dispout = open(args.dispout, 'wb')

    header_written = False
    timestep_read = False
    timestep_count = 0
    for line in nodout:
        if 'nodal' in line:
            timestep_read = True
            timestep_count = timestep_count + 1
            if timestep_count == 1:
                sys.stdout.write('Time Step: ')
                sys.stdout.flush()
            sys.stdout.write('%i ' % timestep_count)
            sys.stdout.flush()
            data = []
            continue
        if timestep_read is True:
            if line.startswith('\n'):  # done reading the time step
                timestep_read = False
                # if this was the first time, everything needed to be read to
                # get node count for header
                if not header_written:
                    header = generate_header(data, nodout)
                    write_headers(dispout, header)
                    header_written = True
                process_timestep_data(data, dispout)
            else:
                raw_data = line.split()
                corrected_raw_data = correct_Enot(raw_data)
                data.append(list(map(float, corrected_raw_data)))

    # close all open files
    dispout.close()
    nodout.close()

def create_vtk(args, nodout):
    # this uses the StructuredGrid VTK XML format outlined here:
    # http://vtk.org/VTK/img/file-formats.pdf
    # pages 11-15
    import sys

    disp_position = open('pos_temp.txt', 'w')
    disp_displace = open('disp_temp.txt', 'w')

    # firstStep flag is True only for the first timestep. This is useful
    # because there are certain expension operations that need to be done only
    # once. These operations include creating the temporary positions file and
    # figuring out the number of values along each dimension.
    firstStep = True

    firstLine = True
    timestep_read = False
    timestep_count = 0
    # time value for each timestep
    timestep_values = []
    # number of total nodes, used to write node_ids into vtk
    numNodes = 0
    # x, y, and z hold the range (min, max) of values in each dimension.
    # they also hold the step values/differences between consecutive
    # values in each dimension. This is used to calculate the number of elements
    # going in each dimension.
    x = []
    y = []
    z = []
    xStepFound = False
    yStepFound = False
    zStepFound = False

    disp_position = open('pos_temp.txt', 'w')
    for line in nodout:
        if 'n o d a l' in line:
            raw_data = line.split()
            # get time value of timestep
            # consider using regular expressions rather than hardcoding this value?
            timestep_values.append(str(float(raw_data[28])))
        if 'nodal' in line:

            # open temporary files for writing displacements
            disp_displace = open('disp_temp.txt', 'w')

            timestep_read = True
            timestep_count = timestep_count + 1
            if timestep_count == 1:
                sys.stdout.write('Time Step: ')
                sys.stdout.flush()
            sys.stdout.write('%i ' % timestep_count)
            sys.stdout.flush()
            continue
        if timestep_read:
            if line.startswith('\n'):  #done reading a time step
                timestep_read = False
                # get last read coordinates - now have range of x, y, z coordinates
                # as well as x, y, z steps. this allows us to get number of steps in
                # x, y, z directions, which is necessary to construct the VTK file.

                if firstStep:
                    x.append(float(lastReadCoords[0]))
                    y.append(float(lastReadCoords[1]))
                    z.append(float(lastReadCoords[2]))

                # no longer reading the first step, so can close temporary
                # point coordinate file.
                if firstStep:
                    disp_position.close()
                    firstStep = False
                # done creating .vts file for this timestep, so we can close
                # temporary displacement file.
                disp_displace.close()

                createVTKFile(args, x, y, z, numNodes, timestep_count)


            else:
                # reading position and displacement data inside a timestep
                raw_data = line.split()
                # correcting for cases when the E is dropped from number formatting
                raw_data = correct_Enot(raw_data)
                raw_data = [str(float(i)) for i in raw_data]
                # get minimum range of x, y, z coordinates
                if firstLine is True:
                    x.append(float(raw_data[10]))
                    y.append(float(raw_data[11]))
                    z.append(float(raw_data[12]))
                # everything inside the following if statement must only be
                # done once for the first timestep values. This assumes that
                # number of nodes and dimensions of mesh are immutable between
                # timesteps.
                if firstStep:
                    if not firstLine:
                    # check to see if we have x, y, z differences
                        xStep = float(lastReadCoords[0])-float(raw_data[10])
                        if xStep != 0.0 and not xStepFound:
                            x.append(xStep)
                            xStepFound = True

                        yStep = float(lastReadCoords[1])-float(raw_data[11])
                        if yStep != 0.0 and not yStepFound:
                            y.append(yStep)
                            yStepFound = True

                        zStep = float(lastReadCoords[2])-float(raw_data[12])
                        if zStep != 0.0 and not zStepFound:
                            z.append(zStep)
                            zStepFound = True

                    # save the position coordinates in case they are the last ones to be read.
                    # this is useful for getting the range of x, y, z coordinates
                    lastReadCoords = raw_data[10:13]
                    # write positions to temporary file. since positions
                    # are the same for all timesteps, this only needs to be done once.
                    # same with number of nodes.
                    disp_position.write(' '.join(raw_data[10:13])+'\n')
                    numNodes += 1

                if firstLine:
                    firstLine = False

                # write displacements to temporary file
                disp_displace.write(' '.join(raw_data[1:4])+'\n')


    # writing last timestep file
    disp_displace.close()
    createVTKFile(args, x, y, z, numNodes, timestep_count)
    sys.stdout.write('\n')
    sys.stdout.flush()
    # time dependence! look at .pvd file stucture for instructions on how to create this.
    # here is an example of the .pvd file format:
    # http://public.kitware.com/pipermail/paraview/2008-August/009062.html
    createPVDFile(args, timestep_values)

    # cleanup. comment the code following this if you would like to look at
    # the temporary position and displacement files for debugging purposes.
    import os
    os.remove('disp_temp.txt')
    os.remove('pos_temp.txt')
def parse_cli():
    '''
    parse command-line interface arguments
    '''
    import argparse

    parser = argparse.ArgumentParser(description="Generate disp.dat "
                                     "data from an ls-dyna nodout file.",
                                     formatter_class=
                                     argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--nodout",
                        help="ASCII file containing nodout data",
                        default="nodout")
    parser.add_argument("--dispout", help="name of the binary displacement "
                        "output file", default="disp.dat")
    parser.add_argument("--dat", help="create a binary file", action='store_true')
    parser.add_argument("--vtk", help="create a vtk file", action='store_true')
    args = parser.parse_args()

    return args


def generate_header(data, outfile):
    '''
    generate headers from data matrix of first time step
    '''
    import re
    header = {}
    header['numnodes'] = data.__len__()
    header['numdims'] = 4  # node ID, x-val, y-val, z-val
    ts_count = 0
    t = re.compile('time')
    if outfile.name.endswith('gz'):
        import gzip
        n = gzip.open(outfile.name)
    else:
        n = open(outfile.name)

    with n as f:
        for line in f:
            if t.search(line):
                ts_count = ts_count + 1
    # the re.search detects 1 extra line, so subtract 1
    header['numtimesteps'] = ts_count - 1

    return header


def write_headers(outfile, header):
    '''
    write binary header information to reformat things on read downstream
    'header' is a dictionary containing the necessary information
    '''
    import struct
    outfile.write(struct.pack('fff', header['numnodes'],
                              header['numdims'], header['numtimesteps']))


def process_timestep_data(data, outfile):
    '''
    operate on each time step data row
    '''
    import struct
    # write all node IDs, then x-val, then y-val, then z-val
    [outfile.write(struct.pack('f', data[j][i]))
        for i in [0, 1, 2, 3]
        for j in range(len(data))]

def correct_Enot(raw_data):
    '''
    ls-dyna seems to drop the 'E' when the negative exponent is three digits,
    so check for those in the line data and change those to 'E-100' so that
    we can convert to floats
    '''
    import re
    for i in range(len(raw_data)):
        raw_data[i] = re.sub(r'(?<!E)\-[1-9][0-9][0-9]', 'E-100', raw_data[i])
    return raw_data

def createVTKFile(args, x, y, z, numNodes, timestep):
    '''
    creates .vts file for visualizing the displacement data during a single timestep
    in Paraview.
    '''
    import os
    # quick check to make sure file extension is correct
    if ('.' in args.dispout):
        fileName = args.dispout[:args.dispout.find('.')]
    else:
        fileName = args.dispout
    # open .vts file for writing)
    if not os.path.exists(fileName):
        os.makedirs(fileName)
    dispout = open(os.path.join(fileName,fileName+str(timestep)+'.vts'), 'w')

    # writing the VTK file outline
    dispout.write('<VTKFile type="StructuredGrid" version="0.1" byte_order="LittleEndian">\n')
    numXValues = abs(round((x[2]-x[0])/x[1]))
    numYValues = abs(round((y[2]-y[0])/y[1]))
    numZValues = abs(round((z[2]-z[0])/z[1]))

    dispout.write('\t<StructuredGrid WholeExtent="0 %d 0 %d 0 %d">\n' % (numXValues, numYValues, numZValues))
    dispout.write('\t\t<Piece Extent="0 %d 0 %d 0 %d">\n' % (numXValues, numYValues, numZValues))
    dispout.write('\t\t\t<PointData Scalars="node_id" Vectors="displacement">\n')
    # writing node ids
    dispout.write('\t\t\t\t<DataArray type="Float32" Name="node_id" format="ascii">\n')
    for i in range(1, numNodes+1):
        dispout.write('\t\t\t\t\t%.1f\n' % i)
    dispout.write('\t\t\t\t</DataArray>\n')
    # writing displacement values
    dispout.write('\t\t\t\t<DataArray NumberOfComponents="3" type="Float32" Name="displacement" format="ascii">\n')
    displace_temp = open('disp_temp.txt', 'r')
    for line in displace_temp:
        dispout.write('\t\t\t\t\t'+line)
    displace_temp.close()
    dispout.write('\t\t\t\t</DataArray>\n')
    dispout.write('\t\t\t</PointData>\n')
    # writing point position values
    dispout.write('\t\t\t<Points>\n')
    dispout.write('\t\t\t\t<DataArray type="Float32" Name="Array" NumberOfComponents="3" format="ascii">\n')
    pos_temp = open('pos_temp.txt', 'r')
    for line in pos_temp:
        dispout.write('\t\t\t\t\t'+line)
    pos_temp.close()
    dispout.write('\t\t\t\t</DataArray>\n')
    dispout.write('\t\t\t</Points>\n')
    dispout.write('\t\t</Piece>\n')
    dispout.write('\t</StructuredGrid>\n')
    dispout.write('</VTKFile>')

    dispout.close()

def createPVDFile(args, timestep_values):
    '''
    creates .pvd file that encompasses displacement for all timesteps.
    The .pvd file can be loaded into Paraview, and the timesteps can be scrolled through
    using the time slider bar.
    '''
    import os
    # quick check to make sure file extension is correct
    if ('.' in args.dispout):
        fileName = args.dispout[:args.dispout.find('.')]
    else:
        fileName = args.dispout
    # open .pvd file for writing)
    if not os.path.exists(fileName):
        os.makedirs(fileName)
    dispout = open(os.path.join(fileName,fileName+'.pvd'), 'w')
    dispout.write('<VTKFile type="Collection" version="0.1">\n')
    dispout.write('\t<Collection>\n')

    timestep = 1
    for i in timestep_values:
        dispout.write('\t\t<DataSet timestep="{0}" file="{1}"/>\n'.format(i, fileName+str(timestep)+'.vts'))
        timestep += 1
    dispout.write('\t</Collection>\n')
    dispout.write('</VTKFile>\n')

if __name__ == "__main__":
    main()
