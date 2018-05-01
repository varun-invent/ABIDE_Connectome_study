import postProcessingFcVolMatchedModularDynamicPipeline as ppfc
# import preprocessingPipelineImprovedModular as prep
import preprocessingPipelineImprovedModularWOAnatDynamic as prep

import scoreCorrelation as sc

import hypothesisTest as ht
import fdrBrainResultsModular as fdres
import os
import json
from os.path import join as opj
import itertools
from bids.grabbids import BIDSLayout
import time



# ------------- Paths ----------------------------------------------------------------------------------------


path_cwd = os.getcwd()
path_split_list = path_cwd.split('/')
s = path_split_list[0:-1] # for getting to the parent dir of pwd
s = opj('/',*s) # *s converts list to path, # very important to add '/' in the begining so it is read as directory later

# New path to store results:

results_path = '/mnt/project1/home1/varunk/results/'


json_path = 'scripts/json/paths.json'
with open(json_path, 'rt') as fp:
    task_info = json.load(fp)



base_directory = opj(results_path,task_info["base_directory_for_results"])
motion_correction_bet_directory = task_info["motion_correction_bet_directory"]
parent_wf_directory = task_info["parent_wf_directory"]
functional_connectivity_directory = task_info["functional_connectivity_directory"]
# functional_connectivity_directory = 'temp_fc'
coreg_reg_directory = task_info["coreg_reg_directory"]
atlas_resize_reg_directory = task_info["atlas_resize_reg_directory"]
data_directory = opj(s,task_info["data_directory"])
datasink_name = task_info["datasink_name"]
fc_datasink_name = task_info["fc_datasink_name"]
# fc_datasink_name = 'temp_dataSink'
atlasPath = opj(s,task_info["atlas_path"]) # Standard Brainnetome path


brain_path = opj(base_directory,datasink_name,'preprocessed_brain_paths/brain_file_list.npy')
mask_path = opj(base_directory,datasink_name,'preprocessed_mask_paths/mask_file_list.npy')
atlas_path = opj(base_directory,datasink_name,'atlas_paths/atlas_file_list.npy') # Brainetome atlas in functional space
tr_path = opj(base_directory,datasink_name,'tr_paths/tr_list.npy')
motion_params_path = opj(base_directory,datasink_name,'motion_params_paths/motion_params_file_list.npy')

func2std_mat_path = opj(base_directory, datasink_name,'joint_xformation_matrix_paths/joint_xformation_matrix_file_list.npy')

MNI3mm_path = opj(base_directory,parent_wf_directory,motion_correction_bet_directory,coreg_reg_directory,'resample_mni/MNI152_T1_2mm_brain_resample.nii')

hypothesis_test_dir = opj(base_directory, task_info["hypothesis_test_dir"])

fdr_results_dir = task_info["fdr_results_dir"]

score_corr_dir =  opj(base_directory,task_info["score_corr_dir"])

demographics_file_path = '/home1/varunk/Autism-Connectome-Analysis-brain_connectivity/notebooks/demographics.csv'
phenotype_file_path = '/home1/varunk/data/ABIDE1/RawDataBIDs/composite_phenotypic_file.csv'
# categoryInfo = '/home1/varunk/data/NYU_Cocaine-BIDS/grouping.csv'
categoryInfo = None

# --------------- Creating Log --------------------

# Get time

current_time = time.asctime( time.localtime(time.time()) )

if not os.path.exists(base_directory):
    os.makedirs(base_directory)

log_path = opj(base_directory,"log.txt")
log = open(log_path, 'a')
print("-------------Starting the analysis at %s--------------\n"%(current_time))
log.write("-------------Starting the analysis at %s--------------\n"%(current_time))
log.flush()



# ----------------------------------------------------------------------------------------------------------------------------------------------------------

vols = 120 # needed for volume matching. Tells how many volumes you need to keep.
number_of_skipped_volumes = 4
#  True volumes will be vols - number_of_skipped_volumes


num_proc = 7


number_of_subjects = -1
# number_of_subjects = 7 # Number of subjects you wish to work with

log.write("Vols for matching: %s\n"%(vols))
log.write("Number_of_skipped_volumes: %s\n"%(number_of_skipped_volumes))
log.flush()
# ----------------------------- Getting Subjects -------------------------------
# ----------------------------------- BIDS -------------------------------------
layout = BIDSLayout(data_directory)


if number_of_subjects == -1:
    number_of_subjects = len(layout.get_subjects())

# ABIDE II Bugs

bugs_abide2 = ['28093', '28093', '28681',  '28682', '28683',  '28687', '28711', '28712', '28713', '28741', '28745',  '28751', '28755', '28756', '28757', '28758',
'28759', '28761', '28762','28763', '28764','28765','28766','28767','28768','28769','28770','28771','28772','28773','28774','28775','28776','28777','28778','28779',
'28780','28781','28782','28783'
]

bugs = bugs_abide2

subject_list = (layout.get_subjects())[0:number_of_subjects]
# subject_list = list(map(int, subject_list))

# Ignore Bugs
subject_list = list(set(subject_list) - set(bugs))

subject_list.sort()




# -----------------------------------File List----------------------------------
# group1FilesPath = ''
# group2FilesPath = ''
#
# group1FilesList = np.genfromtxt(group1FilesPath,dtype='unicode')
# group2FilesList = np.genfromtxt(group2FilesPath,dtype='unicode')
#
# fileList = group1FilesPath + group2FilesPath



# -----------------------------------------------------------------------------

paths = [json_path,
base_directory,
motion_correction_bet_directory,
parent_wf_directory,
functional_connectivity_directory,
coreg_reg_directory,
atlas_resize_reg_directory,
subject_list,
datasink_name,
fc_datasink_name,
atlasPath,
brain_path,
mask_path,
atlas_path,
tr_path,
motion_params_path,
func2std_mat_path,
MNI3mm_path,
demographics_file_path,
phenotype_file_path,
data_directory,
hypothesis_test_dir,
fdr_results_dir,
score_corr_dir
]

PREPROC = 1
POSTPROC = 1
HYPOTEST = 0
FDRES = 0
SCORE_CORR = 0

match = 0 # Age matching
applyFisher = True

# itr = (list(itertools.product([0, 1], repeat=3)))
# itr = [(1,1,1,1,1)]
# itr = [(1,0,1,1,1)]
itr = [(0,0,1,1,0)]

log.write("Operations:\n")
log.write("Preprocess = %s\n"%(PREPROC))
log.write("Postprocess = %s\n"%(POSTPROC))
log.write("Hypothesis Test = %s\n"%(HYPOTEST))
log.write("FDR correction and Vizualization = %s\n"%(FDRES))
log.write("Score-Connectivity Correlation  = %s\n"%(SCORE_CORR))
log.flush()

# ---------------------- Preprocess --------------------------------------------

ANAT = 1

itr_preproc = [1,1,0,1]
# itr_preproc = [0,0,0]
extract, slicetimer,motionOutliers, mcflirt= list(map(str, itr_preproc))
options_binary_string = extract+slicetimer+motionOutliers+mcflirt

log.write("Preprocessing Params\n")
log.write("Remove begining slices  = %s\n"%(extract))
log.write("Slice time correction  = %s\n"%(slicetimer))
log.write("Calculate motionOutliers  = %s\n"%(motionOutliers))
log.write("Do motion correction using McFLIRT  = %s\n"%(mcflirt))

log.flush()


if PREPROC == 1:
    print('Preprocessing')
    prep.main(paths,options_binary_string, ANAT, num_proc)


# ------------------------PostProcess------------------------------------------
if POSTPROC == 1:
    print('PostProcessing')
    log.write("Postprocessing Params\n")

    for motion_param_regression, global_signal_regression, smoothing, band_pass_filtering, volCorrect in itr:
        log.write("motion_param_regression  = %s\n"%(motion_param_regression))
        log.write("global_signal_regression  = %s\n"%(global_signal_regression))
        log.write("smoothing  = %s\n"%(smoothing))
        log.write("band_pass_filtering  = %s\n"%(band_pass_filtering))
        log.write("volCorrect  = %s\n"%(volCorrect))



        combination = 'motionRegress' + str(int(motion_param_regression)) + \
         'global' + str(int(global_signal_regression)) + 'smoothing' + str(int(smoothing)) +\
         'filt' + str(int(band_pass_filtering))

        print("Combination: ",combination)
        functional_connectivity_directory =  combination
        print(motion_param_regression,  global_signal_regression, smoothing,band_pass_filtering)
        ppfc.main(paths, vols, motion_param_regression, global_signal_regression, band_pass_filtering, smoothing, volCorrect, \
        number_of_skipped_volumes, num_proc)


# ------------------- Hypothesis Test ------------------------------------------
# ABIDE1 BUGS
bugs = ['51232','51233','51242','51243','51244','51245','51246','51247','51270','51310','50045', '51276', '50746', '50727', '51276']

if HYPOTEST == 1:
    print('Hypothesis Test')

    # itr = (list(itertools.product([0, 1], repeat=3)))
    #
    # itr = [(1,1,0,1,1)]

    # bugs = ['51232','51233','51242','51243','51244','51245','51246','51247','51270','51310','50045', '51276', '50746', '50727', '51276']

    # bugs = []

    for motion_param_regression, global_signal_regression, smoothing,band_pass_filtering, volCorrect in itr:
        ht.main(paths, bugs,applyFisher,categoryInfo, match, motion_param_regression, global_signal_regression, band_pass_filtering, \
            smoothing, num_proc)

# -------------------- FDR and results -----------------------------------------

if FDRES == 1:
    print('FDR Correction and computing files for visualization of results')
    # itr = (list(itertools.product([0, 1], repeat=3)))

    # itr = [(1,1,0,1,1)]
    for params in itr:
        fdres.main(paths, params, num_proc = 7)


if SCORE_CORR == 1:
    print('Calculating Correlation-Score correaltions')

    # itr = (list(itertools.product([0, 1], repeat=3)))
    #
    # itr = [(1,1,0,1,1)]


    # bugs = []

    for motion_param_regression, global_signal_regression, smoothing,band_pass_filtering, volCorrect in itr:
        sc.main(paths, bugs,applyFisher,categoryInfo, match, motion_param_regression, global_signal_regression, band_pass_filtering, \
            smoothing, num_proc)
