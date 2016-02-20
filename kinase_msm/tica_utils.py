#!/bin/evn python
from kinase_msm.data_loader import load_yaml_file
import numpy as np
import os
from kinase_msm.mdl_analysis import ProteinSeries, Protein
from kinase_msm.data_loader import load_frame
from kinase_msm.data_transformer import create_assignment_matrix, create_tics_array
from msmbuilder.utils.nearest import KDTree
"""
Set of helper scripts for sampling tics
"""


def find_nearest(a, a0, prev_pt=None):

    b= a[:,:,tic_index]
    "Element in nd array `a` closest to the scalar value `a0`"
    dis_to_wanted = np.abs(b - a0)
    if prev_pt is None:
        idx = np.nanargmin(dis_to_wanted)
    else:
        #need to min distance along
        sorted_dis = np.argsort(dis_to_wanted)

    return b.flat[idx]


def pull_frames(yaml_file, protein_name, tic_index, n_frames, key_mapping,
                     assignment_matrix, tics_array,tica_data,scheme="linear"):
    """
    :param yaml_file: The loaded yaml file
    :param protein_name: name of the protein
    :param tic_index: tic index to sample along
    :param n_frames:number of watned frames
    :param key_mapping:mapping of len of matrix of assignments to the
     traj names
    :param assignment_matrix:matrix of assignment
    :param tics_array:3d array of all tica daata
    :param tica_data:Dictionary of tica files
    :param scheme:One of 3
    linear:Samples the tic linearly
    random:Samples the tic randomly
    edge: Samples the tic edges only
    :return:
    :output: This will write out a log file and a xtc file. The log file will
    contain the values of the tic that were obtained while the xtc file will contain
    the tic itself.
    """

    #get some statistics about the data

    all_vals = []
    for traj_tica_data in tica_data.values():
        all_vals.extend(traj_tica_data[:,tic_index])

    #sort it because all three sampling schemes use it
    all_vals = np.sort(all_vals)
    #get lineraly placed points
    if scheme=="linear":
        max_tic_movement = all_vals[-1]
        min_tic_movement = all_vals[0]
        spaced_points = np.linspace(min_tic_movement, max_tic_movement, n_frames)

    elif scheme=="random":
        spaced_points = np.sort(np.random.choice(all_vals, n_frames))

    elif scheme=="edge":
        _cut_point = np.int(n_frames / 2)
        spaced_points = np.hstack((all_vals[:_cut_point],all_vals[-_cut_point:]))
    else:
        raise Exception("Scheme has be to one of linear, random or edge")

    traj_list = []
    actual_tic_val_list=[]
    prev_pt=None
    #make a tree
    tree = KDTree(tics_array[:,:,tic_index])


    for v,i in enumerate(spaced_points):
        if v==0:
            #get the closest point to the desired
            k=1
            dis, ind = tree.query(i,k)
            traj_index, frame_index = ind
            traj_name = key_mapping[traj_index[0]]
            prev_pt = tica_data[traj_name][frame_index[0]]
        else:
            #get a bumch of points closest to desired value
            k=100
            dis, ind = tree.query(i,k)
            tic_dis = []
            for frm_cand in ind:
                _traj_index, _frame_index = frm_cand
                traj_name = key_mapping[_traj_index[0]]
                current_pt = tica_data[traj_name][_frame_index[0]]
                tic_dis.append(np.linalg.norm(current_pt-prev_pt))
            #argsort it from smallest distance to previous pt to largest
            to_keep = np.argsort(tic_dis)[0]
            #get that traj_ind and frame_index
            traj_index, frame_index = ind[to_keep]
            #update previous pt
            traj_name = key_mapping[traj_index[0]]
            prev_pt = tica_data[traj_name][frame_index[0]]

        #write out where we get it from
        actual_tic_val_list.append([v,i, actual_tic_val,traj_name,frame_index[0]])
        #get the actual
        traj_list.append(load_frame(yaml_file["base_dir"],
                                    protein_name,traj_name,frame_index[0]))

    trj = traj_list[0]
    for i in traj_list[1:]:
        trj += i

    save_dir = os.path.join(yaml_file["mdl_dir"],protein_name)
    #dump the log file
    with open(os.path.join(save_dir, "tic%d.log"%tic_index),"w") as fout:
        fout.write("Index Tic Value, Actual Value, TrajName, FrmInd\n")
        for line in actual_tic_val_list:
            for item in line:
                fout.write("%s "%item)
            fout.write("\n")
    
    trj.save_xtc(os.path.join(save_dir,"tic%d.xtc"%tic_index))

    trj[0].save_pdb(os.path.join(save_dir,"prot.pdb"))

    return

def _load_protein_matrices(yaml_file, protein_name):
    """
    Helper routine to load matrices for a protein
    :param yaml_file: yaml file to work with
    :param protein_name: name of the protein
    :return:
     prj :The protein Series
     prt : The protein project
     key_mapping: mapping of the assigment matrix 0-axis to traj names
     assignment_matrix: Massive matrix of
     tics_mapping: mapping of the tics_array matrix 0-axis to traj names
     tics_array: Multi dimensional array where the 0th axis is equal to the
     number of trajectors, the 1st axis is equal to largest traj and the
     3rd dimension is equal to the number of tics in the mdl.
    """
    prj = ProteinSeries(yaml_file)
    prt = Protein(prj, protein_name)

    key_mapping, assignment_matrix  = create_assignment_matrix(prt.fixed_assignments)
    tics_mapping , tics_array  = create_tics_array(prt.fixed_assignments, prt.kmeans_mdl,
                                        prt.tica_data)

    return prj, prt, key_mapping, assignment_matrix, tics_mapping, tics_array

def sample_one_tic(yaml_file,protein_name,tic_index,n_frames, scheme="linear"):
    """
    :param yaml_file: The project's yaml file
    :param protein: The name of protein
    :param tic_index: Tic index to sample along
    :param n_frames: The number of frames wanted
    :return: Dumps a tic%d.xtc and tic%d.log for a given
    protein inside its model.
    """

    prj, prt, key_mapping, assignment_matrix,\
    tics_mapping, tics_array = _load_protein_matrices(yaml_file, protein_name)


    yaml_file = load_yaml_file(yaml_file)
    pull_frames(yaml_file,protein_name,tic_index,n_frames,key_mapping,assignment_matrix,
                tics_array, prt.tica_data,scheme)
    return

def sample_tic_region(yaml_file, protein_name, tic_region,
                      n_frames=50, fname=None):
    """
    Helper function for sampling tic in a particular tic_region.
    :param yaml_file: The projects yaml file
    :param protein_name: The name of the protein
    :param tic_region(dict): The tic_region. Can be multidimensional with
    1 number per tic coordinate(defaults to 0 for all non-mentioned regions)
    :param n_frames: The number of frames around the coordinate
    :return:
    """

    yaml_file = load_yaml_file(yaml_file)

    prj = ProteinSeries(yaml_file)
    prt = Protein(prj, protein_name)

    fake_coordinate = np.zeros(prt.n_tics_)

    for i in tic_region.keys():
        fake_coordinate[i] = tic_region[i]

    key_list = list(prt.tica_data.keys())
    tree = KDTree([prt.tica_data[i] for i in key_list])

    dis, ind = tree.query(fake_coordinate, n_frames)

    traj_list = []
    for i in ind:
        t, f = i
        traj_list.append(load_frame(yaml_file["base_dir"],
                                    protein_name,key_list[t],f))

    trj = traj_list[0] + traj_list[1:]
    save_dir = os.path.join(yaml_file["mdl_dir"], protein_name)

    if fname is None:
        fname = "sampled_tic_region.xtc"

    trj.save_xtc(os.path.join(save_dir,fname))
    trj[0].save_pdb(os.path.join(save_dir,"prot.pdb"))

    return


def sample_for_all_proteins(yaml_file, protein=None, tics=None, n_frames=100,
                            scheme="linear"):
    """
    :param yaml_file: The project yaml file.
    :param protein: The name of the protein. If none, then it is
    done for all the protein names in the yaml_file. If it is a list,
    it is iteratively done for each of the protein else its only called
    once.
    :param tics: list of tics to sample from. If None, then
    it is done for all the tics specified in the yaml file
    :param n_frames number of frames wanted for each tic
    :param scheme:One of 3 sampling schemes
    linear:Samples the tic linearly
    random:Samples the tic randomly
    edge: Samples the tic edges only
    :return:
    """

    yaml_file = load_yaml_file(yaml_file)
    if protein is None :
        protein =  yaml_file[protein_list]

    if tics==None:
        tics = range(yaml_file["params"]["tica__n_components"])

    for protein_name in protein:
        for tic_index in tics:
            sample_one_tic(yaml_file, protein_name, tic_index, n_frames,
                           scheme)

    return


def _map_tic_component(tic_component, df, trj):
    '''
    Function map a tic component to all atoms and optionally all residues
    by summing over all the feature importances where the residue index
    appears
    :param tic_component: The feature weight vector to use
    :param df: Dataframe describing each feature
    :param trj: mdtraj trajctory obj
    :return:atom_importance and residue importance
    '''
    n_atoms = trj.top.n_atoms
    n_residues = trj.top.n_residues

    atom_importance_vector = np.zeros((1,n_atoms))
    residue_importance_vector =  np.zeros((1,n_residues))

    #over all features
    for i in df.iterrows():
        #over all every residue in that feature
        for j in i[1]["resid"]:
            #add to running total
            residue_importance_vector[0, j] += abs(tic_component[i[0]])

    for r in trj.topology.residues:
        for a in r.atoms:
            atom_importance_vector[0, a.index] = residue_importance_vector[0, r.index]


    return atom_importance_vector, residue_importance_vector


