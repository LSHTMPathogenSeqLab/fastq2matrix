import setuptools


setuptools.setup(

    name="fastq2matrix",
    version="0.1.0",
    packages=["fastq2matrix"],
    license="MIT",
    long_description="Utilities to get from fastq files to a variant matrix",
    scripts= [
        'scripts/fastq2vcf.py',
        ],

)
