#!/bin/bash

#SBATCH --partition=p_hpca4se
#SBATCH -x huberman
###SBATCH -w huberman
#SBATCH -J FARSITE_SIMPLE
#SBATCH -N 1-1
#SBATCH -n 1
#SBATCH -c 1
#SBATCH --time=000:10:00
#SBATCH --error=FARSITE_SIMPLE.err
#SBATCH --output=FARSITE_SIMPLE.out
#SBATCH --mem-per-cpu=9000
#SBATCH --cpu_bind=verbose
#SBATCH --sockets-per-node=1
#SBATCH --cores-per-socket=1
###SBATCH --threads-per-core=1
###SBATCH --ntasks-per-socket=2

./farsite4P -i Settings_simulacio.txt
