import nibabel as nib
import numpy as np
from scipy import stats
from numpy import ma
import scipy.special as special
from statsmodels.stats import multitest
import itertools
import os
from os.path import join as opj
# from nipype.interfaces import afni
import nibabel as nib
import json
import numpy as np
import matching
import pandas as pd
from multiprocessing import Pool
import statsmodels.api as sm
from statsmodels.sandbox.stats.multicomp import fdrcorrection0
from functools import partial
from multiprocessing import Pool
import multiprocessing.managers
from tqdm.tqdm import tqdm


class MyManager(multiprocessing.managers.BaseManager):
    pass
MyManager.register('np_zeros', np.zeros, multiprocessing.managers.ArrayProxy)



def calc_score_stats(brain_npy_handle_list, pvals, tvals, coeff_vals, score_list, roi, input_coordinates):
    '''
    Returns: pval, tval and coeff of Independent variable
    '''


    x,y,z,counter = input_coordinates
    # print('Creating voxel connectivity vector of all subjects for coordinates: %s,%s,%s'%(x,y,z))
    # if counter % 100 == 0:
        # print('Coordinate Counter: %s'%(counter))


    voxel_corr_subject_array = []
    for brain_npy in brain_npy_handle_list:
        voxel_corr_subject_array.append(brain_npy[x,y,z])

    Y = voxel_corr_subject_array
    X = sm.add_constant(score_list)

    # print('Length of Y is %s',len(Y))
    # print('Length of X is %s',len(X))

    # print('Fitting GLM')
    model = sm.OLS(Y,X).fit()

    # print('Done')

    pvals[x,y,z] = model.pvalues[1]
    tvals[x,y,z] = model.tvalues[1]
    coeff_vals[x,y,z] = model.params[1]

    # print('coeff_vals for coordinate %s %s %s is %s'%(x,y,z,model.params[1]))


def count_voxel_stats(pvals_list, qvals_list, map_logp_list, map_logq_list):
#     P_brain_voxel_list, Q_brain_voxel_list = Pval_Qval_tuple

    map_logp_list = np.absolute(map_logp_list)
    map_logq_list = np.absolute(map_logq_list)

#     min p value
    min_pval = np.min(pvals_list)

#     min q value
    min_qval = np.min(qvals_list)

#     p value less than 0.1
    p_lt_point_1 = np.shape(np.where(pvals_list < 0.1))[1]

#     p value less than 0.01
    p_lt_point_01 = np.shape(np.where(pvals_list < 0.01))[1]

#     p value less than 0.05
    p_lt_point_05 = np.shape(np.where(pvals_list < 0.05))[1]

#     p value less than 0.1
    q_lt_point_1 = np.shape(np.where(qvals_list < 0.1))[1]

#     p value less than 0.01
    q_lt_point_01 = np.shape(np.where(qvals_list < 0.01))[1]

#     p value less than 0.05
    q_lt_point_05 = np.shape(np.where(qvals_list < 0.05))[1]

# Voxels with abs(sign(C1MinusC2)(-1*log10(Q)))) >1.3 (t 0.5)
    logq_gt_1point3 = np.shape(np.where(map_logq_list > 1.3))[1]

# Voxels with abs(sign(C1MinusC2)(-1*log10(Q)))) >1 (t 0.1)
    logq_gt_1 = np.shape(np.where(map_logq_list > 1))[1]

# Voxels with abs(sign(C1MinusC2)(-1*log10(Q)))) >2 (t 0.01)
    logq_gt_2 = np.shape(np.where(map_logq_list > 2))[1]

# Voxels with abs(sign(C1MinusC2)(-1*log10(P)))) >1.3 (t 0.5)
    logp_gt_1point3 = np.shape(np.where(map_logp_list > 1.3))[1]

# Voxels with abs(sign(C1MinusC2)(-1*log10(P)))) >1 (t 0.1)
    logp_gt_1 = np.shape(np.where(map_logp_list > 1))[1]

# Voxels with abs(sign(C1MinusC2)(-1*log10(P)))) >2 (t 0.01)
    logp_gt_2 = np.shape(np.where(map_logp_list > 2))[1]


    return min_pval,min_qval,p_lt_point_1,p_lt_point_01,p_lt_point_05,q_lt_point_1,    q_lt_point_01,q_lt_point_05, logq_gt_1point3, logq_gt_1 ,logq_gt_2 ,logp_gt_1point3, logp_gt_1, logp_gt_2


def fdr_correction_and_viz(Pvals_path, Tvals_path, coef_path,  mask_path, save_destination, affine, header, combination):
    alpha = 0.05

    Pvals = np.load(Pvals_path)
    Tvals= np.load(Tvals_path)
    coeff_vals = np.load(coef_path)

    mask = nib.load(mask_path).get_data()

    brain_indices = np.where(mask != 0 )

    # from statsmodels.sandbox.stats.multicomp import fdrcorrection0

    Pvals_shape = Pvals.shape

    Qvals = np.zeros(Pvals_shape)

    # sign(c1-c2) * -1 * log10(p)
    map_logp = np.multiply(np.sign(coeff_vals),(-1*np.log10(Pvals)))


    roi_voxel_stats_matrix = np.zeros((Pvals_shape[3], 14)) # cozthere are 14 statistical attributes



    for roi in range(Pvals_shape[3]):

        print('Computing Stats for ROI: ',roi)

        #         pvals = ma.masked_array(Pvals[0], mask = mask, fill_value = 0)

        pvals = Pvals[:,:,:,roi]
        pvals_shape = pvals.shape

        #         inp = pvals[~pvals.mask]

        # Flatten inp and check if you get back the original matrix after
        #         inp = inp.ravel()

        pvals_list = pvals[brain_indices]

        _, qvals_list  = fdrcorrection0(pvals_list,alpha)

#       from IPython.core.debugger import Tracer; Tracer()()
        # map_logq_list = map_logq[brain_indices]
        map_logp_list = map_logp[:,:,:,roi][brain_indices]

        # print("Size of map_logp_list ",map_logp_list.shape)
#         print("Brain Indices: ", brain_indices)

        coeff_vals_list = coeff_vals[:,:,:,roi][brain_indices]


        #     Calculate voxel stats using the below function

        Qvals[:,:,:,roi][brain_indices] = qvals_list



        map_logq_list = np.multiply(np.sign(coeff_vals_list),(-1*np.log10(qvals_list)))

        # print("Size of map_logq_list ",map_logq_list.shape)

        roi_voxel_stats_matrix[roi,:] = count_voxel_stats(pvals_list, qvals_list,map_logp_list, map_logq_list)


        # print('Stats Computed for ROI: ',roi)

    #       Save the CSV file and the Additional Brain file to visualize


    # sign(c1-c2) * -1 * log10(q)
    map_logq = np.multiply(np.sign(coeff_vals),(-1*np.log10(Qvals)))



    save_destination_new = opj(save_destination,combination)
    if not os.path.exists(save_destination_new):
        os.mkdir(save_destination_new)

    print('Saving Files in directory: ', save_destination_new)

    print('Saving Stats CSV : ',)
    csv_name = opj(save_destination_new,'roi_voxel_stats_' + combination + '.csv')
    np.savetxt(csv_name,roi_voxel_stats_matrix,delimiter=',',header='min_pval,min_qval,p_lt_point_1,p_lt_point_01,\
     p_lt_point_05, q_lt_point_1, q_lt_point_01,q_lt_point_05, logq_gt_1point3, logq_gt_1 ,logq_gt_2 ,\
     logp_gt_1point3, logp_gt_1, logp_gt_2')

    print('Saving Pvals.nii.gz')
    Pvals_name = opj(save_destination_new,'Pvals.nii.gz')
    Pvals_brain_with_header = nib.Nifti1Image(Pvals, affine= affine,header = header)
    nib.save(Pvals_brain_with_header,Pvals_name)

    print('Saving Tvals.nii.gz')
    Tvals_name = opj(save_destination_new,'Tvals.nii.gz')
    Tvals_brain_with_header = nib.Nifti1Image(Tvals, affine= affine,header = header)
    nib.save(Tvals_brain_with_header,Tvals_name)

    print('Saving Qvals.nii.gz')
    Qvals_name = opj(save_destination_new,'Qvals.nii.gz')
    Qvals_brain_with_header = nib.Nifti1Image(Qvals, affine= affine,header = header)
    nib.save(Qvals_brain_with_header,Qvals_name)

    print('Saving coeff_vals.nii.gz')
    coeff_vals_name = opj(save_destination_new,'coeff_vals.nii.gz')
    coeff_vals_brain_with_header = nib.Nifti1Image(coeff_vals, affine= affine,header = header)
    nib.save(coeff_vals_brain_with_header,coeff_vals_name)

    print('Saving map_logp.nii.gz')
    map_logp_name = opj(save_destination_new,'map_logp.nii.gz')
    map_logp_brain_with_header = nib.Nifti1Image(map_logp, affine= affine,header = header)
    nib.save(map_logp_brain_with_header,map_logp_name)

    print('Saving map_logq.nii.gz')
    map_logq_name = opj(save_destination_new,'map_logq.nii.gz')
    map_logq_brain_with_header = nib.Nifti1Image(map_logq, affine= affine,header = header)
    nib.save(map_logq_brain_with_header,map_logq_name)







# Now construct a function that takes a list of SUB_ID's and returns the FC Maps paths
def get_subject_fc_file(subject_id_list,fc_file_path, bugs):
    import re

    return_fc_maps = []
    fc_file_list = np.load(fc_file_path)
    print('Brain files: ',fc_file_list)
    for subject_id in subject_id_list:
#         print("For subject: ",subject_id)
        found =  False
        for brain in fc_file_list:
            sub_id_extracted = re.search('.+_subject_id_(\d+)', brain).group(1)
            if str(subject_id) in bugs:
                # print("In Bugs with subject id ",subject_id)
                found = True
            elif (subject_id == int(sub_id_extracted)):
                found = True
                return_fc_maps.append(brain)
#                 print("Found for subject: ",subject_id)
        if found == False: # Some subject was not found Problem!
            print ('Unable to locate Subject so not including in analysis Query: ',int(subject_id),' Extracted but not included: ',int(sub_id_extracted))
            # return 0
    return return_fc_maps

# Now construct a function that takes a list of SUB_ID's and returns the FC Maps paths and scores
def get_subject_fc_file_and_score(subid_and_scores_list,fc_file_path, bugs):
    import re
    subject_id_list = subid_and_scores_list[0].squeeze()
    if isinstance(subid_and_scores_list[1], np.ndarray):
        phenotype_score = subid_and_scores_list[1].squeeze()
    else:
        return get_subject_fc_file(subject_id_list,fc_file_path, bugs)


    # phenotype_score = np.array(phenotype_score)
    return_fc_maps = []
    return_phenotypic_scores = []
    fc_file_list = np.load(fc_file_path)
    print('Brain files: ',fc_file_list)
    for ix, subject_id in enumerate(subject_id_list):
#         print("For subject: ",subject_id)
        found =  False
        for brain in fc_file_list:
            sub_id_extracted = re.search('.+_subject_id_(\d+)', brain).group(1)
            if str(subject_id) in bugs:
                # print("In Bugs with subject id ",subject_id)
                found = True
            elif (subject_id == int(sub_id_extracted)):
                found = True
                return_fc_maps.append(brain)
                return_phenotypic_scores.append(phenotype_score[ix])
#                 print("Found for subject: ",subject_id)
        if found == False: # Some subject was not found Problem!
            print ('Unable to locate Subject: ',int(subject_id),'extracted: ',int(sub_id_extracted))
            # return 0
    return return_fc_maps, return_phenotypic_scores


def applyGLM(subject_list,score_list,mask_path,save_destination, num_proc):
    # Create pool of num_proc workers
    pool = Pool(num_proc)

    mask_data = nib.load(mask_path).get_data()

    # import pdb;pdb.set_trace()
    x,y,z,t = np.load(subject_list[0],mmap_mode='r').shape

    print('Calculating input list to give to workers')
    input_list = [] # for storing the iteration brain coordinates
    counter = 1
    for i in range(x):
        for j in range(y):
            for k in range(z):
                if mask_data[i,j,k] != 0: # Brain region
                    input_list.append([i,j,k,counter])
                    # counter += 1 # for checking progress..

    print('Number of GLMs to be done for each roi= ', len(input_list))

    pvals = np.zeros((x,y,z,t))
    tvals = np.zeros((x,y,z,t))
    coeff_vals = np.zeros((x,y,z,t))

    m = MyManager()
    m.start()

    print("Starting with the workers")
    # t = 2
    for roi in tqdm(range(t)):
        # print('*****************************************************************')
        # print('Reading the ROI %s npy brain files in mmap mode'%(roi)) # ############# Memory issue .. work with one ROI at a time.
        # print('*****************************************************************')

        brain_npy_handle_list = []
        for in_file in subject_list:
            brain_npy_handle_list.append(np.load(in_file,mmap_mode='r')[:,:,:,roi])

        pvals_shared = m.np_zeros((x,y,z))
        tvals_shared = m.np_zeros((x,y,z))
        coeff_vals_shared = m.np_zeros((x,y,z))

        func = partial(calc_score_stats, brain_npy_handle_list, pvals_shared, tvals_shared, coeff_vals_shared,\
                                                                                                        score_list, roi)


        pool.map(func, input_list)

        # import pdb;pdb.set_trace()
        pvals[:,:,:,roi] = pvals_shared
        tvals[:,:,:,roi] = tvals_shared
        coeff_vals[:,:,:,roi] = coeff_vals_shared


    print('Saving files in ',save_destination)
    if not os.path.exists(save_destination):
        os.makedirs(save_destination) # to create a nested directory structure
    Tvals_path = opj(save_destination,'Tvals')
    Pvals_path = opj(save_destination,'Pvals')
    coeff_vals_path = opj(save_destination,'coeff_vals')

    np.save(Tvals_path,tvals)
    np.save(Pvals_path,pvals)
    np.save(coeff_vals_path,coeff_vals)

    print('Saved')

    return Pvals_path+'.npy', Tvals_path+'.npy', coeff_vals_path+'.npy'




def main(paths, bugs, applyFisher, categoryInfo= None, match=1, motion_param_regression=0, global_signal_regression=0, band_pass_filtering=0, \
    smoothing=0, num_proc = 7):
    json_path=paths[0]
    base_directory=paths[1]
    motion_correction_bet_directory=paths[2]
    parent_wf_directory=paths[3]
    functional_connectivity_directory=paths[4]
    coreg_reg_directory=paths[5]
    atlas_resize_reg_directory=paths[6]
    subject_list = paths[7]
    datasink_name=paths[8]
    fc_datasink_name=paths[9]
    atlasPath=paths[10]
    brain_path=paths[11]
    mask_path=paths[12]
    atlas_path=paths[13]
    tr_path=paths[14]
    motion_params_path=paths[15]
    func2std_mat_path=paths[16]
    MNI3mm_path=paths[17]
    demographics_file_path = paths[18]
    phenotype_file_path = paths[19]
    data_directory = paths[20]
    # hypothesis_test_dir = paths[21]
    score_corr_dir = paths[23]

    #  Runall:


    if categoryInfo == None:
            # phenotype_file_path = '/home1/varunk/data/ABIDE1/RawDataBIDs/composite_phenotypic_file.csv'

        df = pd.read_csv(phenotype_file_path) # , index_col='SUB_ID'

        df = df.sort_values(['SUB_ID'])
        # df = df.sort_values(['SUB+AF8-ID'])

        if bugs == None:
            bugs = ['51232','51233','51242','51243','51244','51245','51246','51247','51270','51310','50045', '51276', '50746', '50727', '51276']

        # Bugs:
        # 50045 - ROI Missing
        # 51276, 50746, 50727 - Many in between ROIs Missing
        # 51276 - Many in between ROIs Missing

        # '0051242' in bugs


        # selecting Autistic males(DSM IV) of age <= 18 years
        # df_aut_lt18_m = df.loc[(df['SEX'] == 1) & (df['AGE_AT_SCAN'] <=18) & (df['DSM_IV_TR'] == 1) ]
        # df_aut_lt18_m = df.loc[(df['SEX'] == 1) & (df['AGE_AT_SCAN'] <=18) & (df['DSM_IV_TR'] == 1) & (df['EYE_STATUS_AT_SCAN'] == 1)] # eyes open
        # df_aut_lt18_m = df.loc[(df['SEX'] == 1) & (df['AGE_AT_SCAN'] <=18) & (df['DSM_IV_TR'] == 1) & (df['EYE_STATUS_AT_SCAN'] == 2)] # eyes closed
        # df_aut_lt18_m = df.loc[(df['SEX'] == 1) & (df['AGE_AT_SCAN'] >=12) & (df['AGE_AT_SCAN'] <=18) & (df['DSM_IV_TR'] == 1) & (df['EYE_STATUS_AT_SCAN'] == 1)] # eyes open age 12-18
        # df_aut_lt18_m = df.loc[(df['SEX'] == 1) & (df['AGE_AT_SCAN'] >=6) & (df['AGE_AT_SCAN'] <12) & (df['DSM_IV_TR'] == 1) & (df['EYE_STATUS_AT_SCAN'] == 1)] # eyes open age 6 - lt 12
        # df_aut_lt18_m = df.loc[(df['SEX'] == 1) & (df['AGE_AT_SCAN'] <=18) & (df['DSM_IV_TR'] == 1)] # AGE <= 18


        # In[205]:


        # df_aut_lt18_m.shape


        # In[206]:


        # df_td_lt18_m = df.loc[(df['SEX'] == 1) & (df['AGE_AT_SCAN'] <=18) & (df['DSM_IV_TR'] == 0) ]
        # df_td_lt18_m = df.loc[(df['SEX'] == 1) & (df['AGE_AT_SCAN'] <=18) & (df['DSM_IV_TR'] == 0) & (df['EYE_STATUS_AT_SCAN'] == 1)] # eyes open
        # df_td_lt18_m = df.loc[(df['SEX'] == 1) & (df['AGE_AT_SCAN'] <=18) & (df['DSM_IV_TR'] == 0) & (df['EYE_STATUS_AT_SCAN'] == 2)] # eyes closed
        # df_td_lt18_m = df.loc[(df['SEX'] == 1) & (df['AGE_AT_SCAN'] >=12) & (df['AGE_AT_SCAN'] <=18) & (df['DSM_IV_TR'] == 0) & (df['EYE_STATUS_AT_SCAN'] == 1)] # eyes open age 12- 18
        # df_td_lt18_m = df.loc[(df['SEX'] == 1) & (df['AGE_AT_SCAN'] >=6) & (df['AGE_AT_SCAN'] <12) & (df['DSM_IV_TR'] == 0) & (df['EYE_STATUS_AT_SCAN'] == 1)] # eyes open age 6 - lt 12
        # df_td_lt18_m = df.loc[(df['SEX'] == 1) & (df['AGE_AT_SCAN'] <=18) & (df['DSM_IV_TR'] == 0)] # AGE <= 18

        # df_aut_lt18_m = df.loc[(df['SEX'] == 1) & (df['AGE_AT_SCAN'] <=18) & (df['DSM_IV_TR'] == 0) & (df['EYE_STATUS_AT_SCAN'] == 2)] # TD eyes closed

        # In[207]:


        # df_td_lt18_m.shape


        # In[208]:


        # table_males_np = table_males.as_matrix(columns=['SUB_ID','DX_GROUP', 'DSM_IV_TR', 'AGE_AT_SCAN' ,'SEX' ,'EYE_STATUS_AT_SCAN'])


        # In[209]:






        if demographics_file_path == None:
            demographics_file_path = '/home1/varunk/Autism-Connectome-Analysis-brain_connectivity/notebooks/demographics.csv'

        if phenotype_file_path == None:
            phenotype_file_path = '/home1/varunk/data/ABIDE1/RawDataBIDs/composite_phenotypic_file.csv'


        df_demographics = pd.read_csv(demographics_file_path)
        df_phenotype = pd.read_csv(phenotype_file_path)
        df_phenotype = df_phenotype.sort_values(['SUB_ID'])



        # Volume matching
        # print('Volume Matching')
        # volumes_bins = np.array([[0,150],[151,200],[201,250],[251,300]])
        # matched_df_TD = df_phenotype
        # matched_df_AUT = df_phenotype
        # matched_df_TD, matched_df_AUT = matching.volumes_matching(volumes_bins, df_demographics, matched_df_TD, matched_df_AUT)
        #



        # Age 6 - 18 Autistic vs Healthy

        # df_td_lt18_m = df_phenotype.loc[(df_phenotype['SEX'] == 1) & (df_phenotype['DX_GROUP'] == 2) \
        #                                                     & (df_phenotype['EYE_STATUS_AT_SCAN'] == 1) ]
        #
        #
        # df_aut_lt18_m = df_phenotype.loc[(df_phenotype['SEX'] == 1) & (df_phenotype['DSM_IV_TR'] == 1) \
        #                                                     & (df_phenotype['EYE_STATUS_AT_SCAN'] == 1) ]


        # Age 6 - 18 Aspergers vs Healthy

        # df_td_lt18_m = df_phenotype.loc[(df_phenotype['SEX'] == 1) & (df_phenotype['DX_GROUP'] == 2) \
        #                                                     & (df_phenotype['EYE_STATUS_AT_SCAN'] == 1) ]
        #
        #
        # df_aut_lt18_m = df_phenotype.loc[(df_phenotype['SEX'] == 1) & (df_phenotype['DSM_IV_TR'] == 2) \
        #                                                     & (df_phenotype['EYE_STATUS_AT_SCAN'] == 1) ]


        # Age 6 - 18 Aspergers vs Autistic


        # df_td_lt18_m = df_phenotype.loc[(df_phenotype['SEX'] == 1) & (df_phenotype['DSM_IV_TR'] == 2) \
        #                                                     & (df_phenotype['EYE_STATUS_AT_SCAN'] == 1) ]
        #
        # df_aut_lt18_m = df_phenotype.loc[(df_phenotype['SEX'] == 1) & (df_phenotype['DSM_IV_TR'] == 1) \
        #                                                     & (df_phenotype['EYE_STATUS_AT_SCAN'] == 1) ]


        # ------------------  Only healthy ---------------------------------------

        # healthy_subjects = df_phenotype.loc[(df_phenotype['SEX'] == 1) & (df_phenotype['DX_GROUP'] == 2) \
        #                                                     & (df_phenotype['EYE_STATUS_AT_SCAN'] == 1) ]
        #
        #
        # # import pdb; pdb.set_trace()
        # healthy_subjects = healthy_subjects.reindex(np.random.permutation(healthy_subjects.index))
        #
        # df_td_lt18_m = healthy_subjects[0: int(healthy_subjects.shape[0]/2.0)]
        #
        # df_aut_lt18_m = healthy_subjects[int(healthy_subjects.shape[0]/2.0)+1 :]


        # ------------------  Only healthy again Saity Check---------------------------------------

        # healthy_subjects = df_phenotype.loc[(df_phenotype['SEX'] == 1) & (df_phenotype['DX_GROUP'] == 2) \
        #                                                     & (df_phenotype['EYE_STATUS_AT_SCAN'] == 1) ]
        #
        # df_td_lt18_m = healthy_subjects[0: int(healthy_subjects.shape[0]/2.0)]
        # df_aut_lt18_m = healthy_subjects[0: int(healthy_subjects.shape[0]/2.0)]

        # Age 12 - 18


        # df_td_lt18_m = matched_df_TD.loc[(matched_df_TD['SEX'] == 1) & (matched_df_TD['DSM_IV_TR'] == 0) \
        #                                                     & (matched_df_TD['EYE_STATUS_AT_SCAN'] == 1)
        #                                                     & (matched_df_TD['AGE_AT_SCAN'] >= 12 )
        #                                                     & (matched_df_TD['AGE_AT_SCAN'] <= 18) ]
        #
        # df_aut_lt18_m = matched_df_AUT.loc[(matched_df_AUT['SEX'] == 1) & (matched_df_AUT['DSM_IV_TR'] == 1) \
        #                                                     & (matched_df_AUT['EYE_STATUS_AT_SCAN'] == 1)
        #                                                     & (matched_df_AUT['AGE_AT_SCAN'] >= 12 )
        #                                                     & (matched_df_AUT['AGE_AT_SCAN'] <= 18) ]

        # Age 6 - 18 Autistic with FIQ score not equal to NAN and -9999

        score_name = 'ADI_R_VERBAL_TOTAL_BV'

        print('**************** Correlating score: ',score_name)
        df_aut_lt18_m = df_phenotype.loc[(df_phenotype['SEX'] == 1) & (df_phenotype['DSM_IV_TR'] == 1) \
                                                            & (df_phenotype['EYE_STATUS_AT_SCAN'] == 1) & pd.notnull(df_phenotype[score_name]) & (df_phenotype[score_name] != -9999)]

        df_aut_subid = df_aut_lt18_m.as_matrix(columns=['SUB_ID'])
        df_aut_score = df_aut_lt18_m.as_matrix(columns=[score_name])


        # Age 6 - 18 Healthy with FIQ score not equal to NAN and -9999

        # score_name = 'FIQ'
        #
        # df_TD_lt18_m = df_phenotype.loc[(df_phenotype['SEX'] == 1) & (df_phenotype['DX_GROUP'] == 2) \
        #                                                     & (df_phenotype['EYE_STATUS_AT_SCAN'] == 1) & pd.notnull(df_phenotype[score_name]) & (df_phenotype[score_name] != -9999)]
        #
        #
        # # Fir simplicity of code I am just naming TD as Autistic so that rest of the code doesn't change
        #
        # df_aut_lt18_m = df_TD_lt18_m
        # df_aut_subid = df_aut_lt18_m.as_matrix(columns=['SUB_ID'])
        # df_aut_score = df_aut_lt18_m.as_matrix(columns=[score_name])





    combination = 'motionRegress' + str(int(motion_param_regression)) + \
     'global' + str(int(global_signal_regression)) + 'smoothing' + str(int(smoothing)) +\
     'filt' + str(int(band_pass_filtering))

    print("Combination: ",combination)
    print(motion_param_regression,band_pass_filtering, global_signal_regression, smoothing)

    save_destination = opj(score_corr_dir,combination)
    print('Saving files in ',save_destination)
    if not os.path.exists(save_destination):
        os.makedirs(save_destination) # to create a nested directory structure

    # save_destination_TD = opj(hypothesis_test_dir,combination,'TD_subects.csv')
    save_destination_AUT = opj(score_corr_dir,combination,'AUT_subjects.csv')

    print("Storing the subjects' information used")
    # df_td_lt18_m.to_csv('TD_subects.csv')
    # df_td.to_csv(save_destination_TD)
    # print('Saved TD_subects.csv')
    # df_aut_lt18_m.to_csv('AUT_subjects.csv')
    df_aut_lt18_m.to_csv(save_destination_AUT)
    print('Saved AUT_subects.csv')




    # for motion_param_regression, band_pass_filtering, global_signal_regression, smoothing in itr:

    fc_file_list_nii = opj(base_directory,fc_datasink_name,combination,'fc_map_brain_file_list.npy')

    fc_file_list_npy = opj(base_directory,fc_datasink_name,combination,'fc_map_npy_file_list.npy')

    fc_file_list = fc_file_list_npy

    print('Reading the brain paths from: ',fc_file_list)
#     apply_fisher = True

    # import pdb;pdb.set_trace()
    autistic_list_npy, df_aut_score = (get_subject_fc_file_and_score([df_aut_subid, df_aut_score], fc_file_list, bugs))
    print("Number of autistic participants ", len(autistic_list_npy))

    autistic_list_nii = get_subject_fc_file_and_score([df_aut_subid, None], fc_file_list_nii, bugs)







    # td_list = (get_subject_fc_file(df_td_subid.squeeze(), fc_file_list, bugs))
    # print("Number of TD participants ", len(td_list))

    # participants_considered = min(len(autistic_list), len(td_list))

    # participants_considered = 2

    # print("Number of participants being Considered per group:", participants_considered)

    autistic_list = autistic_list_npy#[0:participants_considered]
    # td_list = td_list#[0:participants_considered]

    # Created the below mask manually using BET
    # mask = opj(base_directory,parent_wf_directory,motion_correction_bet_directory,coreg_reg_directory,'resample_mni/MNI152_T1_2mm_brain_resample_mask.nii.gz')
    # mask = opj(base_directory,parent_wf_directory,motion_correction_bet_directory,coreg_reg_directory,'atlas_resize_reg_directory/resample_atlas/fullbrain_atlas_thr0-2mm_resample_binarize.nii.gz')
    mask_path = '/home1/varunk/atlas/Full_brain_atlas_thr0-2mm/fullbrain_atlas_thr0-3mm_binarized.nii.gz'
    save_destination = opj(score_corr_dir,combination)

    print('Applying GLM in each voxel')
    Pvals_path, Tvals_path, coeff_vals_path = applyGLM(subject_list = autistic_list,score_list=df_aut_score,mask_path=mask_path,save_destination= save_destination,\
            num_proc = num_proc)



    print('Now doing FDR Correctiona and Visualization')
    brain_path = autistic_list_nii[0] # getting a header to be used later to save brain files
    brain_data = nib.load(brain_path)
    affine=brain_data.affine
    header = brain_data.header

    Pvals_path = opj(save_destination,'Pvals.npy')
    Tvals_path = opj(save_destination,'Tvals.npy')
    coeff_vals_path = opj(save_destination,'coeff_vals.npy')
    fdr_correction_and_viz(Pvals_path, Tvals_path, coeff_vals_path, mask_path, save_destination, affine, header, combination )






    # Created above a prarallel proc pipeline that loops over all the brain voxels inside the mask and
        # Create another list of corr values spanning all the subjects
        # Extract FIQ values of the same subjects
        # Use statmodels to caculate the fit of the line and t vals and p vals
