#! /usr/bin/env python
import re
import sys
import os
from collections import defaultdict
import argparse
import subprocess as sp
from joblib import Parallel, delayed
from tqdm import tqdm
import fastq2matrix as fm

parser = argparse.ArgumentParser(description='Find fastq files in a directory and return a list of tuples with the sample name and the path to the fastq files from both pairs.')
parser.add_argument('--dir',nargs="+", type=str, help='Directory to search for fastq files',required=True)
parser.add_argument('--r1', metavar='r1_pattern', type=str, help='Pattern to match R1 files',required=True)
parser.add_argument('--r2', metavar='r2_pattern', type=str, help='Pattern to match R2 files',required=True)
parser.add_argument('--ref', metavar='ref', type=str, help='Reference genome',required=True)
parser.add_argument('--outdir', metavar='outdir', type=str, help='Output directory',required=True)
parser.add_argument('--threads-per-job', metavar='threads_per_job', default=10,type=int, help='Number of threads per job')
parser.add_argument('--jobs', metavar='jobs', type=int, default=4,help='Number of jobs to run in parallel')

args = parser.parse_args()

class Sample:
    def __init__(self,prefix,r1,r2):
        self.prefix = prefix
        self.r1 = sorted(r1)
        self.r2 = sorted(r2)
        if len(r1)!=len(r2):
            raise ValueError("Number of R1 and R2 files do not match")
        if len(r1)==1:
            self.multiple = False
        else:
            self.multiple = True

    def __repr__(self):
        return f"Sample(prefix={self.prefix},r1={self.r1},r2={self.r2})"

    def combine_reads(self):
        if len(self.r1)>1:
            sp.call(f"cat {' '.join(self.r1)} > {self.prefix}_1.fastq.gz",shell=True)
            sp.call(f"cat {' '.join(self.r2)} > {self.prefix}_2.fastq.gz",shell=True)
        else:
            sp.call(f"ln -s {self.r1[0]} {self.prefix}_1.fastq.gz",shell=True)
            sp.call(f"ln -s {self.r2[0]} {self.prefix}_2.fastq.gz",shell=True)

def sort_out_paried_files(files,r1_suffix,r2_suffix):
    prefixes = defaultdict(lambda:{"r1":[],"r2":[]})

    for f in files:
        tmp1 = re.search("%s" % r1_suffix,f)
        tmp2 = re.search("%s" % r2_suffix,f)
        p = None
        if tmp1:
            p = tmp1.group(1).split("/")[-1]
            prefixes[p]['r1'].append(f)
        elif tmp2:
            p = tmp2.group(1).split("/")[-1]
            prefixes[p]['r2'].append(f)

    runs = []
    for p,vals in prefixes.items():
        if len(vals['r1'])!=1 or len(vals['r2'])!=1:
            if len(vals['r1'])!=len(vals['r2']):
                raise ValueError(f"Number of R1 and R2 files for sample {p} do not match")
            vals['r1'].sort()
            vals['r2'].sort()
            runs.append(
                Sample(p,vals['r1'],vals['r2'])
            )
        else:
            runs.append(
                Sample(p,vals['r1'],vals['r2'])
            )
    return runs

def find_fastq_files(directories,r1_pattern,r2_pattern):
    """
    Find fastq files in a directory and return a
    list of tuples with the sample name and the
    path to the fastq files from both pairs.
    """
    files = []
    for d in directories:
        for a,b,c in os.walk(d):
            for f in c:
                files.append(f"{os.path.abspath(a)}/{f}")
#    print(files)
    fastq_files = sort_out_paried_files(files,r1_pattern,r2_pattern)

    return fastq_files


samples = find_fastq_files(args.dir,args.r1,args.r2)

commands = []
for s in samples:
    
    commands.append(f"fastq2vcf.py all --ref {args.ref} -1 {s.r1[0]} -2 {s.r2[0]} --prefix {s.prefix} --bam-qc --cram --threads {args.threads_per_job}")

print(commands)
if not os.path.exists(args.outdir):
    os.makedirs(args.outdir)
os.chdir(args.outdir)

parallel = Parallel(n_jobs=args.jobs, return_as='generator')
[r for r in tqdm(parallel(delayed(fm.run_cmd)(cmd) for cmd in commands),total=len(commands),desc="Running jobs")]
    

