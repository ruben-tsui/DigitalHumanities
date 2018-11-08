# -*- coding: utf-8 -*-
"""
Created on Fri Nov  2 07:47:41 2018
Last modified on Fri Nov  2 19:09:00 2018
@author: Ruben G. Tsui (RubenTsui@gmail.com)
@in_collaboration_with:
Dr. Zeb Raft
Institute of Chinese Literature and Philosophy
Academia Sinica

Purpose:
Given: 
    A folder with multiple sub-folders containing *.html files
    (not all having the same prefixes) of the format:
        xxxxx_nnnn.html
    where:
        xxxxx = file prefix
        nnnn  = serial number (possibly non-unique across sub-folders)
Do:
    (1) Batch-renaming all file prefixes to a common prefix based on a supplied RegEx.
    (2) Re-numbering all the files with unique serial numbers.
    (3) Moving files from all sub-folders to the top-level "root" folder.

User intervention/clean-up required:
    The empty sub-folders left vacant by step (3) above need to be deleted manually.

User-supplied info:
    Books (dict object): Provide RegEx patterns and the locations of your raw *.html files.
    book: select the desired book to work on.
"""

import time
start_time = time.time()

import os, glob, re

################################################################################
# USER-SUPPLIED INFO
# All relevant info concerning a "book"
# key (string)  = book names
# value (tuple) = (RegEx, top-level folder location)
Books  = {'PreTangProse':  ('Yan ?Kejun',              'C:/NLP/Raft/Four Hanji texts/PreTangProse'),
          'PreTangPoetry': ('preqin|PreTangRemainder', 'C:/NLP/Raft/Four Hanji texts/PreTangPoetry'),
          'other books': ()
         }
book   = 'PreTangPoetry'  # selected book

################################################################################

os.chdir(Books[book][1])  # change working directory to specified folder
to_fn = book              # desired common file prefix 
from_fn = Books[book][0]  # RegEx pattern to use

print("Now processing '{}'.".format(book))

# Rename file prefixes
DocPath = r"./"  # this is what we call "root" folder in the documentation
doclist1 = []    # contains original names (and paths) of files 
doclist2 = []    # renamed files, but with original paths
for f in glob.glob(DocPath + '/**/*.html', recursive=True):
    basen = os.path.basename(f)
    folder = os.path.dirname(f)
    fn = re.sub(from_fn, to_fn, basen)  # do RegEx substitution
    fn = os.path.join(folder, fn)  # we want to "rename" files with the "root" folder, effectively 
    doclist1.append(f)
    doclist2.append(fn)
    os.rename(f, fn)

print("Total no. of files renamed: {}.".format(len(doclist2)))

# How many digits do we need as the consecutive serial numbers?
# e.g. if len(doclist2[]) is 54321 then numdigits becomes 5 
numdigits = len(str(len(doclist2)))

# Move all files in all sub-folders to "root" folder
print("Moving files to {}.".format(os.getcwd()))
doclist3 = []  # renamd files, moved to the "root" folder
serialno = 0  # the numbering will start at 00000
for f in doclist2:
    basen = os.path.basename(f)
    folder = os.path.dirname(f)
    # the following regex matches underscore + a sequence of digits;
    # then the above matched string is replaced by the current zero-filled serial no.
    fn = re.sub(r"_(\d+).html", "_{}.html".format(str(serialno).zfill(numdigits)), basen)
    fn = os.path.join(DocPath, fn)  # we want to "rename" files with the "root" folder, effectively moving them
    doclist3.append(fn)
    os.rename(f, fn)
    serialno += 1

# Report total no. of seconds elapsed
elapsed_time = round(time.time() - start_time, 2)
print("Elapsed time: {} sec".format(elapsed_time))
