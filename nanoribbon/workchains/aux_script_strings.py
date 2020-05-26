
cube_cutter = r"""
cat > cube_cutter.py << EOF

from glob import glob
import numpy as np
import gzip

for fn in glob("*.cube"):
    # parse
    lines = open(fn).readlines()
    header = np.fromstring("".join(lines[2:6]), sep=' ').reshape(4,4)
    natoms, nx, ny, nz = header[:,0].astype(int)
    cube = np.fromstring("".join(lines[natoms+6:]), sep=' ').reshape(nx, ny, nz)

    # plan
    dz = header[3,3]
    angstrom = int(1.88972 / dz)
    z0 = nz/2 + 1*angstrom # start one angstrom above surface
    z1 = z0   + 3*angstrom # take three layers at one angstrom distance
    zcuts = range(z0, z1+1, angstrom)

    # output
    ## change offset header
    lines[2] = "{:5d} 0.000000 0.000000 {:12.6f}\n".format(natoms,  z0*dz)
    ## change shape header
    lines[5] = "{:6d} 0.000000 0.000000 {:12.6f}\n".format(len(zcuts), angstrom*dz)
    with gzip.open(fn+".gz", "w") as f:
        f.write("".join(lines[:natoms+6])) # write header
        np.savetxt(f, cube[:,:,zcuts].reshape(-1, len(zcuts)), fmt="%.5e")
EOF

python ./cube_cutter.py
"""

cube_clipper_cropper = r"""
cat > cube_clipper_cropper.py << EOF


import numpy as np
import itertools

import io

import gzip
from glob import glob

ang_2_bohr = 1.889725989

    #CUBE_PATH = "./_spin.cube"

def read_cube_file(file_lines):

    fit = iter(file_lines)

    title = next(fit)
    comment = next(fit)

    line = next(fit).split()
    natoms = int(line[0])

    origin = np.array(line[1:], dtype=float)

    shape = np.empty(3,dtype=int)
    cell = np.empty((3, 3))
    for i in range(3):
        n, x, y, z = [float(s) for s in next(fit).split()]
        shape[i] = int(n)
        cell[i] = n * np.array([x, y, z])

    numbers = np.empty(natoms, int)
    positions = np.empty((natoms, 3))
    for i in range(natoms):
        line = next(fit).split()
        numbers[i] = int(line[0])
        positions[i] = [float(s) for s in line[2:]]

    positions /= ang_2_bohr # convert from bohr to ang

    data = np.empty(shape[0]*shape[1]*shape[2], dtype=float)
    cursor = 0
    for i, line in enumerate(fit):
        ls = line.split()
        data[cursor:cursor+len(ls)] = ls
        cursor += len(ls)

    data = data.reshape(shape)

    cell /= ang_2_bohr # convert from bohr to ang

    return numbers, positions, cell, origin, data

def write_cube_file_gzip(filename, numbers, positions, cell, data, origin = np.array([0.0, 0.0, 0.0])):

    positions *= ang_2_bohr
    origin *= ang_2_bohr

    natoms = positions.shape[0]

    f = gzip.open(filename, 'w')

    f.write(filename+'\n')

    f.write('cube\n')

    dv_br = cell*ang_2_bohr/data.shape

    f.write("{:5d} {:12.6f} {:12.6f} {:12.6f}\n".format(natoms, origin[0], origin[1], origin[2]))

    for i in range(3):
        f.write("{:5d} {:12.6f} {:12.6f} {:12.6f}\n".format(data.shape[i], dv_br[i][0], dv_br[i][1], dv_br[i][2]))

    for i in range(natoms):
        at_x, at_y, at_z = positions[i]
        f.write("{:5d} {:12.6f} {:12.6f} {:12.6f} {:12.6f}\n".format(numbers[i], 0.0, at_x, at_y, at_z))

    # 6 columns !!!

    fmt=' {:11.4e}'
    for ix in range(data.shape[0]):
        for iy in range(data.shape[1]):
            for line in range(data.shape[2] // 6 ):
                f.write((fmt*6 + "\n").format(*data[ix, iy, line*6 : (line+1)*6]))
            left = data.shape[2] % 6
            if left != 0:
                f.write((fmt*left + "\n").format(*data[ix, iy, -left:]))

    f.close()


def clip_data(data, absmin=None, absmax=None):
    if absmin:
        data[np.abs(data) < absmin] = 0
    if absmax:
        data[data > absmax] = absmax
        data[data < -absmax] = -absmax

def crop_cube(data, pos, cell, origin, x_crop=None, y_crop=None, z_crop=None):

    dv = np.diag(cell)/data.shape

    # corners of initial box
    i_p0 = origin
    i_p1 = origin + np.diag(cell)

    # corners of cropped box
    c_p0 = np.copy(i_p0)
    c_p1 = np.copy(i_p1)

    for i, i_crop in enumerate([x_crop, y_crop, z_crop]):
        pmax, pmin = np.max(pos[:, i]), np.min(pos[:, i])

        if i_crop:
            c_p0[i] = pmin - i_crop/2
            c_p1[i] = pmax + i_crop/2

            # make grids match
            shift_0 = (c_p0[i] - i_p0[i]) % dv[i]
            c_p0[i] -= shift_0

            shift_1 = (c_p1[i] - i_p0[i]) % dv[i]
            c_p1[i] -= shift_1

    # crop
    crop_s = ((c_p0 - i_p0) / dv).astype(int)
    crop_e = data.shape - ((i_p1 - c_p1) / dv).astype(int)

    data = data[crop_s[0]:crop_e[0], crop_s[1]:crop_e[1], crop_s[2]:crop_e[2]]

    origin = c_p0

    new_cell = c_p1 - c_p0

    # make new origin 0,0,0
    new_pos = pos - origin

    return data, np.diag(new_cell), new_pos

for fn in glob("*.cube"):
    filezip=fn+'.gz'
    #if 'spin' in fn:
    #    filezip='./_spin_full.cube.gz'
        
    with open(fn, 'rb') as f:
        file_lines = f.readlines()
        file_str = "".join(file_lines)
    
    
    numbers, positions, cell, origin, data = read_cube_file(file_lines)
    
    new_data, new_cell, new_pos = crop_cube(data, positions, cell, origin, x_crop=None, y_crop=3.5, z_crop=3.5)
    
    clip_data(new_data, absmin=1e-4)
    
    write_cube_file_gzip(filezip, numbers, new_pos, new_cell, new_data)

EOF

python ./cube_clipper_cropper.py
"""
