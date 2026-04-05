#!/bin/bash

#SBATCH --partition=p_hpca4se
#SBATCH -x huberman
###SBATCH -w huberman
#SBATCH -J LCPMAKE
#SBATCH -N 1-1
#SBATCH -n 1
#SBATCH -c 1
#SBATCH --time=000:10:00
#SBATCH --error=LCPMAKE.err
#SBATCH --output=LCPMAKE.out
#SBATCH --mem-per-cpu=9000
#SBATCH --cpu_bind=verbose
#SBATCH --sockets-per-node=1
#SBATCH --cores-per-socket=1
###SBATCH --threads-per-core=1
###SBATCH --ntasks-per-socket=2

./lcpmake -latitude 41  -landscape  -elevation -slope  -aspect  -fuel  -cover




