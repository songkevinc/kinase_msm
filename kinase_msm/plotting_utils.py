#!/bin/evn python

import pandas as pd
import numpy as np
from .mdl_analysis import _map_obs_to_state

"""
set of helper routines to plot things
"""

def global_tic_boundaries(prt_list, tic_list, n_bins=100):

    """
    :param prt_list: list of proteins loaded using the Protein class
    :param tic_list: list of tics to compute for
    :return:a dictionary where the key is the tic index and the value is
    list containing the linearly spaced tic value going from the global min
    and max
    """
    assert isinstance(prt_list,list)
    results_dict = {}
    for tic_index in tic_list:
        min_tic_val = min([prot.tic_min[tic_index] for prot in prt_list])
        max_tic_val =  max([prot.tic_max[tic_index] for prot in prt_list])
        results_dict[tic_index] = np.linspace(min_tic_val,max_tic_val,n_bins)
    return results_dict

def _one_dim_histogram(populations_, x_dict, x_array):
    n_bins = len(x_array)-1

    H_overall = np.zeros(n_bins)

    n_states_= populations_.shape[0]
    H={}
    for i in range(n_states_):
        H[i],x=np.histogram(x_dict[i],bins=x_array,
                              normed=True)
        H_overall = H_overall + populations_[i]*H[i]

    #convert to kcal/mol by
    H_overall = -0.6*np.log(H_overall)
    return H, H_overall

def _two_dim_histogram(populations_, x_obs, y_obs, x_array, y_array):
    n_bins = len(x_array)-1

    H_overall = np.zeros((n_bins,n_bins))
    n_states_= populations_.shape[0]
    H={}

    for i in range(n_states_):
        H[i], x, y=np.histogram2d(x_obs[i], y_obs[i],
                                bins=[x_array, y_array],
                                normed=True)
        H_overall = H_overall + populations_[i]*H[i]

    #convert to kcal/mol by
    H_overall = -0.6*np.log(H_overall)
    return H, H_overall

def tica_histogram(prj, prt, tic_list, x_array=None, y_array=None, n_bins=100):

    #simple check for making sure we have a list
    if not isinstance(tic_list, list):
        tic_list = [tic_list]

    c_x = prt.tic_dict[tic_list[0]]

    if x_array is None:
        lin_spaced_tic = global_tic_boundaries([prt],tic_list,n_bins)
        x_array = lin_spaced_tic[tic_list[0]]
        if y_array is None and len(tic_list)==2:
            y_array =lin_spaced_tic[tic_list[1]]
            c_y = prt.tic_dict[tic_list[1]]

    x_center = (x_array[:-1] + x_array[1:]) / 2

    if len(tic_list)==1:
        H, H_overall = _one_dim_histogram(prt.msm.populations_,
                                          c_x, x_array)
    elif len(tic_list)==2:
        H, H_overall = _two_dim_histogram(prt.msm.populations_,
                                          c_x, c_y, x_array, y_array)
    else:
        raise Exception("cant do this")

    return H, H_overall, x_center


def bootstrap_one_dim_tic_free_energy(prj,prt,tic_index,n_bins=100 ,lin_spaced_tic=None):
    """
    :param prj: Project that the protein is a part of
    :param prt: the protein itself
    :param tic_index: The tic index that is needed
    :param n_bins: n_bins
    :param lin_spaced_tic: linearly sampled tic
    :param errorbars: whether or not to compute multiple free enegies
    using bayes msm mdl
    :return: a pandas dataframe containing the free energy for the
    every point along the tic coordinate. The mdl index column contains
    an integer for each of the bayesian mdls.
    """
    free_energy = []

    if lin_spaced_tic is None:
        lin_spaced_tic = global_tic_boundaries([prt],tic_index,n_bins)[tic_index]
    else:
        n_bins = len(lin_spaced_tic) - 1

    #get the centers stacked nicely
    _labels = ["mean","lower","upper"]
    nlbl = len(_labels)

    tic_cen = np.repeat([(lin_spaced_tic[:-1] + lin_spaced_tic[1:]) / 2],
                        nlbl,axis=0).flatten()
    protein_name = np.repeat(prt.name, nlbl * n_bins).flatten()

    mdl_index = np.array([np.repeat(_labels[i],n_bins)
                          for i in range(nlbl)]).flatten()

    #get data
    H,H_msm,_ = tica_histogram(prj,prt,tic_index,x_array=lin_spaced_tic)

    mean_ = prt.bootrap_msm.mapped_populations_mean_
    lower_ = prt.bootrap_msm.mapped_populations_mean_\
                      - 1.96*prt.bootrap_msm.mapped_populations_sem_
    upper_ = prt.bootrap_msm.mapped_populations_mean_\
                      + 1.96*prt.bootrap_msm.mapped_populations_sem_

    _data = [mean_, lower_, upper_]

    for pop,lbl in zip(_data, _labels):
        H_overall=np.zeros(n_bins)
        for j in range(prt.n_states_):
            H_overall = H_overall + pop[j]*H[j]
        #convert to free enenrgy
        H_overall = -0.6*np.log(H_overall)
        free_energy.extend(H_overall)

    df=pd.DataFrame([list(tic_cen),list(free_energy),list(protein_name),list(mdl_index)]).T
    df.columns=["tic_value","free_energy","protein_name","mdl_index"]
    return df


def one_dim_tic_free_energy(prj, prt, tic_index, n_bins=100 ,
                        lin_spaced_tic=None, errorbars=False):
    """
    :param prj: Project that the protein is a part of
    :param prt: the protein itself
    :param tic_index: The tic index that is needed
    :param n_bins: n_bins
    :param lin_spaced_tic: linearly sampled tic
    :param errorbars: whether or not to compute multiple free enegies
    using the msm mdl
    :return: a pandas dataframe containing the free energy for the
    every point along the tic coordinate. The mdl index column contains
    "mle" for the msm free energy and an integer for the bayesian mdl
    """
    free_energy = []

    if lin_spaced_tic is None:
        lin_spaced_tic = global_tic_boundaries([prt],tic_index,n_bins)[tic_index]
    else:
        n_bins = len(lin_spaced_tic) - 1

    #get the centers stacked nicely
    tic_center = np.repeat([(lin_spaced_tic[:-1] + lin_spaced_tic[1:]) / 2],
                           1 , axis=0).flatten()
    protein_name = np.repeat(prt.name,n_bins).flatten()

    mdl_index = np.repeat("mle",n_bins).flatten()

    #get data
    H,H_msm,_ = tica_histogram(prj,prt,[tic_index],x_array=lin_spaced_tic)

    free_energy.extend(H_msm)

    msm_df=pd.DataFrame([list(tic_center),list(free_energy),
                         list(protein_name),list(mdl_index)]).T

    msm_df.columns=["tic_value","free_energy","protein_name","mdl_index"]

    if errorbars:
        bootstrap_df = bootstrap_one_dim_tic_free_energy(prj,prt,tic_index, lin_spaced_tic=lin_spaced_tic)
        df = pd.concat([msm_df, bootstrap_df])
        return df
    else:
        return msm_df


def two_dim_tic_free_energy(prj, prt, tic_list, x_array=None, y_array=None, n_bins=100):
    #basic sanity tests

    assert(len(tic_list)==2)
    if x_array is None:
        lin_spaced_tic = global_tic_boundaries([prt],tic_list,n_bins)
        x_array = lin_spaced_tic[tic_list[0]]
        y_array = lin_spaced_tic[tic_list[1]]
    else:
        n_bins = len(x_array) - 1

    H_overall = np.zeros((n_bins,n_bins))
   #get data
    c_x = prt.tic_dict[tic_list[0]]
    c_y = prt.tic_dict[tic_list[1]]
    for i in range(prt.n_states_):
        H,x,y=np.histogram2d(c_x[i],c_y[i],bins=[x_array,y_array],normed=True)
        H_overall = H_overall + prt.msm.populations_[i]*H
    H_copy = -0.6*np.log(H_overall)

    return H_copy

def one_dim_free_energy(prt, x_obs, bins):
    """
    :param prj: Series we are working with
    :param prt: Protein
    :param x_obs: Dictonary of obs for every frame
    :param bins: either a list of lin_space_points or number of bins to use
    :return: a pandas dataframe containing the free energy for the
    every point along the tic coordinate.
    """
    free_energy=[]
    state_x_obs_dict = _map_obs_to_state(prt, x_obs)

    if bins is None or type(bins)==int:
        max_val = np.max(np.concatenate(list(x_obs.values())))
        min_val = np.min(np.concatenate(list(x_obs.values())))
        bins = np.linspace(min_val, max_val, bins)
    else:
        n_bins = len(bins) - 1

    #get the centers stacked nicely
    bin_center = np.repeat([(bins[:-1] + bins[1:]) / 2],
                           1 , axis=0).flatten()
    protein_name = np.repeat(prt.name, n_bins).flatten()

    mdl_index = np.repeat("mle", n_bins).flatten()

    #get data
    H,H_msm, =  _one_dim_histogram(prt.msm.populations_,
                                   x_dict=state_x_obs_dict,
                                   x_array=bins)

    free_energy.extend(H_msm)

    msm_df=pd.DataFrame([list(bin_center),list(free_energy),
                         list(protein_name),list(mdl_index)]).T

    msm_df.columns=["tic_value","free_energy","protein_name","mdl_index"]

    return

def two_dim_free_energy(prt, x_obs, y_obs, bins=None):
    """
    :param prt: protein model
    :param x_obs: x_obs for every trajectory
    :param y_obs: y_obs for every trajetory
    :param bins: either list of lists or int
    :return:
    """
    state_x_obs_dict = _map_obs_to_state(prt, x_obs)
    state_y_obs_dict = _map_obs_to_state(prt, y_obs)
    if bins is None or type(bins)==int:
        max_x_val = np.max(np.concatenate(list(x_obs.values())))
        min_x_val = np.min(np.concatenate(list(x_obs.values())))
        max_y_val = np.max(np.concatenate(list(y_obs.values())))
        min_y_val = np.min(np.concatenate(list(y_obs.values())))
        x_array = np.linspace(min_x_val, max_x_val, bins)
        y_array = np.linspace(min_y_val, max_y_val, bins)
    else:
        x_array = bins[0]
        y_array = bins[1]

    H, H_msm = _two_dim_histogram(prt.msm.populations_,
                                  state_x_obs_dict,
                                  state_y_obs_dict,
                                  x_array,
                                  y_array)
    return H, H_msm




