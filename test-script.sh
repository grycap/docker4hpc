#!/bin/sh
#
#This is an example script example.sh
#
#These commands set up the Grid Environment for your job:
#PBS -N ExampleJob
#PBS -l nodes=1,walltime=00:01:00
#PBS -q np_workq
#PBS -M YOURUNIQNAME@umich.edu
#PBS -m abe
#PBS -V

#print the time and date
hostname && date && echo "hola"

whoami
id

#wait 2 seconds
sleep 2

#print the time and date again
hostname && date