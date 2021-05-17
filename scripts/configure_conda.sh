#!/bin/bash

#Activate conda with any of the next commands
#source ~/miniconda3/bin/activate
#source ~/.bashrc
eval "$(conda shell.bash hook)"

#update conda environment after installing modules with pip may result into inconsistencies
function activate_environment() {
    echo "* Verifying/installing conda environment: $1"
#    conda activate $1 2>/dev/null || {
#        echo "** Installing conda environement: $1"
#        conda env update --file $basedir/fedbiomed-network/envs/development/conda/$1.yaml;
#        conda activate $1
#    }
     conda env update --file $basedir/fedbiomed-network/envs/development/conda/$1.yaml 2>/dev/null
}

#
# find the directory containing all sources
#
basedir=$(cd $(dirname $0)/../.. || exit ; pwd)
cd $basedir || exit

# prerequisite, these repo must be present in development mode
fed1=fedbiomed-network
fed2=fedbiomed-node
fed3=fedbiomed-researcher

for i in $fed1 $fed2 $fed3
do
    if [ ! -d $basedir/$i ]
    then
        echo "Directory $basedir/$i is missing"
        exit
    fi
done

# configure all conda environements
activate_environment fedbiomed

for i in $fed1 $fed2 $fed3
do
    activate_environment $i
    conda deactivate
done
conda deactivate