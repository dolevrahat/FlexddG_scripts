#!/usr/bin/python

from __future__ import print_function


import os
import argparse


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ref_2015', dest='ref_2015',action='store_true',default=False)
    parser.add_argument('--dry_run', dest='dry_run',action='store_true',default=False)
    parser.add_argument('--test_run', dest='test_run',action='store_true',default=False)

    parser.add_argument('--mutation_chain','-mc', dest='mutation_chain')
    parser.add_argument('--mutation_resi','-mr', dest='mutation_resi')
    parser.add_argument('--mutation_icode','-mi' ,dest='mutation_icode',default='')
    parser.add_argument('--allowed_aa', dest='allowed_aa',default='ACDEFGHIKLMNPQRSTVWY')
    parser.add_argument('--chains_to_move', dest='chains_to_move')
    return parser


###################################################################################################################################################################
# Important: The variables below are set to values that will make the run complete faster (as a tutorial example), but will not give scientifically valid results.
#            Please change them to the "normal" default values before a real run.
###################################################################################################################################################################

rosetta_scripts_path = "$ROSETTA_BIN/rosetta_scripts.linuxgccrelease"

def run_params(test_run):
    path_to_script = 'scripts/ddG-backrub.xml'

    if test_run:
        nstruct = 10 # Normally 35
        max_minimization_iter = 50 # Normally 5000
        abs_score_convergence_thresh = 200.0 # Normally 1.0
        number_backrub_trials = 10 # Normally 35000
        backrub_trajectory_stride = 5
    else:
        nstruct = 35 # Normally 35
        max_minimization_iter = 5000 # Normally 5000
        abs_score_convergence_thresh = 1.0 # Normally 1.0
        number_backrub_trials = 10000 # Normally 35000
        backrub_trajectory_stride = 1000
    return (path_to_script,nstruct,max_minimization_iter,abs_score_convergence_thresh,number_backrub_trials,backrub_trajectory_stride)

def run_flex_ddg_saturation( name, input_pdb_path, chains_to_move, mut_aa,mutation_chain, mutation_resi, mutation_icode,talaris ):
    output_directory = os.path.join( 'output_saturation/', os.path.join( '%s_%s' % (name, mut_aa)) )
    if not os.path.isdir(output_directory):
        os.makedirs(output_directory)

    resfile_path = os.path.join( output_directory, 'mutate_%s%s%s_to_%s.resfile' % (mutation_chain, mutation_resi, mutation_icode, mut_aa) )
    with open( resfile_path, 'w') as f:
        f.write( 'NATRO\nstart\n%s%s %s PIKAA %s\n' % (mutation_resi, mutation_icode, mutation_chain, mut_aa) )

    flex_ddg_args = [
 #       'mpirun',
        rosetta_scripts_path,
        "-s %s" % os.path.abspath(input_pdb_path),
        '-parser:protocol', os.path.abspath(path_to_script),
        '-parser:script_vars',
        'chainstomove=' + chains_to_move,
        'mutate_resfile_relpath=' + os.path.abspath( resfile_path ),
        'number_backrub_trials=%d' % number_backrub_trials,
        'max_minimization_iter=%d' % max_minimization_iter,
        'abs_score_convergence_thresh=%.1f' % abs_score_convergence_thresh,
        'backrub_trajectory_stride=%d' % backrub_trajectory_stride ,
        '-restore_talaris_behavior ' + str(talaris),
        '-in:file:fullatom',
        '-ignore_unrecognized_res',
        '-ignore_zero_occupancy False',
        '-ex1',
        '-ex2 > flexddg.log\n'
    ]

    return((flex_ddg_args,output_directory))

if __name__ == '__main__':
    homedir = os.getcwd()
    args = arg_parser().parse_args()
    test_run = args.test_run
    dry_run = args.dry_run
    talaris = not args.ref_2015
    (path_to_script,nstruct,max_minimization_iter,abs_score_convergence_thresh,number_backrub_trials,backrub_trajectory_stride) =\
    run_params(test_run)
    (mutation_chain, mutation_resi, mutation_icode) = (args.mutation_chain,args.mutation_resi,args.mutation_icode)
    allowed_aa = args.allowed_aa
    chains_to_move = args.chains_to_move
    for case_name in os.listdir('inputs'):
        case_path = os.path.join( 'inputs', case_name )
        for f in os.listdir(case_path):
            if f.endswith('.pdb'):
                input_pdb_path = os.path.join( case_path, f )
                break
        for mut_aa in allowed_aa:
            (flexddg_args,rundir) = run_flex_ddg_saturation('%s_%s%s%s' % (case_name, mutation_chain, mutation_resi, mutation_icode), \
            input_pdb_path, chains_to_move, mut_aa,mutation_chain, mutation_resi, mutation_icode,talaris)
            os.chdir(rundir)
            with open('flexddg.sbatch','w') as b_file:
                b_file.write('#!/bin/sh\n')
                b_file.write('#SBATCH --get-user-env\n#SBATCH --mem-per-cpu=1600m\n#SBATCH --time=50:00:00\n')
                b_file.write('#SBATCH --array=1-%s\n\n' % nstruct)
                b_file.write('#SBATCH --tasks=3 0\n')
                b_file.write('#SBATCH --nice\n')
                b_file.write('ROSETTA_BIN="/vol/ek/share/rosetta/rosetta_src_2019.14.60699_bundle/main/source/bin"\n\n')
                b_file.write('mkdir $SLURM_ARRAY_TASK_ID && cd $SLURM_ARRAY_TASK_ID\n')
                b_file.write('%s' % ' '.join(flexddg_args))
            if not dry_run:
               os.system('sbatch flexddg.sbatch')
            os.chdir(homedir)


