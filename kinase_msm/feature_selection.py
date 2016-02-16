import os
import glob
import os
from multiprocessing import Pool
from msmbuilder.utils import verboseload, verbosedump
from kinase_msm.data_loader import load_yaml_file
from kinase_msm.featurize_project import _check_output_folder_exists

"""
Set of routines to select common features amongst
proteins based upon their sequence similarity.
Creates a new folder to dump features of interest in there.
"""

def _get_common_features(yaml_file, featurizer):
    raise NotImplementedError("Not yet")

def _slice_file(job_tuple):
    inp_file, feature_ind, output_folder = job_tuple
    featurized_file = verboseload(inp_file)
    sliced_file = featurized_file[:, feature_ind]
    sliced_file_out = os.path.join(output_folder, os.path.basename(inp_file))
    verbosedump(sliced_file, sliced_file_out)
    return

def _feature_slicer(yaml_file, dict_feat_ind, folder_name, view):
    protein_list = yaml_file["protein_list"]


    for protein in protein_list:
        _check_output_folder_exists(yaml_file, protein, folder_name)
        feature_folder = os.path.join(yaml_file["base_dir"],
                                  protein, yaml_file["feature_dir"])
        output_folder = os.path.join(yaml_file["base_dir"],
                                  protein, folder_name)
        flist = glob.glob(os.path.join(feature_folder,"*.jl"))

        feature_ind = dict_feat_ind[protein]
        jobs = [(inp_file, feature_ind, output_folder) for inp_file in flist]
        view.map(_slice_file, jobs)

    return

def series_feature_slicer(yaml_file, dict_feat_ind=None,
                          featurizer=None,
                          folder_name="sliced_feature_dir",
                         view=None):

    """
    :param yaml_file: The project yaml file with
    :param dict_feat_ind: Dict of wanted feature indices for each protein. Defaults to
    none when you want the code to figure out what features to keep.
    :param featurizer: The featurizer object that was used to generat.
    :param folder_name: Name of the output folder. Defaults to sliced_feature_dir
    :param view: pool of workers. Defaults to multiprocessing
    :return: None
    """

    yaml_file = load_yaml_file(yaml_file)

    if view is None:
        view = Pool()

    #if we want to do this and we cant find the sequence
    if dict_feat_ind is None and ("alignment_file" not in yaml_file
                                  or featurizer is None
                                  or (not hasattr(featurizer, "describe_features"))):
        raise ValueError("To find common features, we need both "
                         "the alignment file in the yaml file"
                         "AND a featurizer obj that supports describe_features")


    if dict_feat_ind is None:
        dict_feat_ind = _get_common_features(yaml_file, featurizer)

    _feature_slicer(yaml_file, dict_feat_ind, folder_name, view)

    return
