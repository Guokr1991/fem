python ../../mesh/GenMesh.py --xyz -1.5 0.0 0.0 1.5 -3.0 0.0 --numElem 75 75 150
python ../../mesh/bc.py --pml
python ../../mesh/GaussExc.py --sigma 0.25 0.25 0.75 --center 0.0 0.0 -1.5 
ls-dyna-s ncpu=2 i=gauss_pml.dyn
rm d3* 
python ../../post/create_disp_dat.py --dat --vtk
python ../../post/create_res_sim_mat.py --dynadeck gauss_pml.dyn
