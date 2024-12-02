##extract metadata from archive
import tempfile
import os
import argparse
import sys
#from joblib import Parallel, delayed
import subprocess
from tqdm import tqdm
from pathlib import Path
import tarfile
import zipfile
import os
import pandas as pd # type: ignore
from IPython.display import clear_output # type: ignore

import tarfile
import os
import subprocess
import pandas as pd
import tempfile
from tqdm import tqdm
from IPython.display import clear_output

def is_tar_archive(file):
    """
    This function checks if a file is a tar archive.

    Parameters:
    file (str): The path to the file.

    Returns:
    bool: True if the file is a tar archive, False otherwise.
    """
    try:
        with tarfile.open(file, 'r') as tar:
            return True
    except tarfile.ReadError:
        return False

def search_string_in_file(file, search_string):
    """
    This function searches for a string in a file.

    Parameters:
    file (str): The path to the file.
    search_string (str): The string to search for.

    Returns:
    str: The line containing the string if found, otherwise an empty string.
    """
    textends = ['.txt', '.json', '.xml', '.log', '.rtf', '.csv', '.tsv']
    try:
        if file.endswith(tuple(textends)):
            with open(file, 'r') as f:
                for line in f:
                    if search_string in line:
                        return line
    except:
        return ""

def get_inputlist(folder):
    """
    This function returns a list of files in a folder.

    Parameters:
    folder (str): The path to the folder.

    Returns:
    list: A list of files in the folder.
    """
    file_list = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            file_list.append(os.path.join(root, file))
    return file_list

def get_init():
    """
    This function reads the showinf parameters from a configuration file.

    Returns:
    tuple: A tuple containing the showinf path and parameters.
    """
    import configparser
    config = configparser.ConfigParser()
    config.read("init.ini")
    showinfPath = config['showinf parameter']['showinfPath']
    showinfParameter = config['showinf parameter']['showinfParameter']
    return (showinfPath, showinfParameter)

def get_bf_metadata(fileinput, showinfPath, showinfParameter):
    """
    This function extracts metadata from a file using the Bio-Formats showinf tool.

    Parameters:
    fileinput (str): The path to the file.
    showinfPath (str): The path to the showinf tool.
    showinfParameter (str): The parameters for the showinf tool.

    Returns:
    bytes: The metadata extracted from the file.
    """
    comd = [showinfPath] + showinfParameter.split(" ")
    comd = [i.replace('"',"") for i in comd]
    try:
        output = subprocess.check_output(comd + [fileinput],
                                        shell=False,
                                        stderr=subprocess.DEVNULL)
    except:
        return ""
    return output

def save_to_xml(concatMetadata, outputfolder):
    """
    This function saves a DataFrame to an XML file.

    Parameters:
    concatMetadata (DataFrame): The DataFrame to save.
    outputfolder (str): The path to the output folder.
    """
    concatMetadata.index = range(len(concatMetadata))
    tmpConcat = concatMetadata.to_xml()
    with open(os.path.join(outputfolder, "concat_extraction_results.xml"), "w") as out:
        out.write(tmpConcat)

def save_metadata(metadata, outputfolder, filename):
    """
    This function saves metadata to a file.

    Parameters:
    metadata (str): The metadata to save.
    outputfolder (str): The path to the output folder.
    filename (str): The name of the output file.
    """
    with open(os.path.join(outputfolder, filename), "w") as out:
        out.write(metadata)

def extract_metadata(file, outputfolder, showinfPath, showinfParameter):
    """
    This function extracts metadata from a file and saves it to an output folder.

    Parameters:
    file (str): The path to the file.
    outputfolder (str): The path to the output folder.
    showinfPath (str): The path to the showinf tool.
    showinfParameter (str): The parameters for the showinf tool.

    Returns:
    list: A list containing the extraction error, input file, output file, extension, and output folder.
    """
    metadata = get_bf_metadata(file, showinfPath, showinfParameter)
    head, extension = os.path.splitext(file.split("/")[-1])
    #print(head, extension)
    if len(extension) > 4:
         head += extension
         extension = "unknown"
    if metadata != "":
        metadata = metadata.decode("utf-8")
        filename = head + ".ome.xml"
        save_metadata(metadata, outputfolder, filename)
        print("saved: ", outputfolder, filename)
        result = ['0', file, os.path.join(outputfolder, filename), extension, outputfolder]
    else:
        result = ['1', file, '', extension, outputfolder]
    return result

def process_tar_gz(file_path, outputfolder, tmp=1):
    """
    This function processes a tar.gz file, extracts metadata from its contents, and saves the results to an output folder.

    Parameters:
    file_path (str): The path to the tar.gz file.
    outputfolder (str): The path to the output folder.
    tmp (int): A flag indicating whether to use a temporary directory for extraction. Default is 1.

    Returns:
    DataFrame: A DataFrame containing the extraction results.
    """
    showinfPath, showinfParameter = get_init()
    resultCols = ['extractError', 'inputFile', 'outputFile', 'extension', 'outputFolder']
    concatMetadata = pd.DataFrame(columns=resultCols)
    results = []
    # Open the tar.gz file
    with tarfile.open(file_path, "r") as tar:
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            if tmp==0:
                temp_dir = outputfolder
                # Extract all files to the temporary directory
                for member in tar.getmembers():
                # Check if the member is a file (not a directory)
                    if member.isfile():
                    # Extract the file as a file-like object
                        tar.extract(member, temp_dir)
                # Iterate over all files in the temporary directory
                filelist = get_inputlist(temp_dir)
                for i, file in tqdm(enumerate(filelist)):
                    print(f"work on {i}/{len(filelist)} files in the archive ({i/len(filelist)}%)")
                    # Print the file name
                    results.append(extract_metadata(file, outputfolder, showinfPath, showinfParameter))
                    clear_output(wait=True)
    ## save the concat
    concatMetadata = pd.DataFrame(results, columns=resultCols)
    return concatMetadata

                # Here you can add your own code to process the file

# Call the function with the path to your tar.gz file
#process_tar_gz("/home/omero-import"tmp/extract_metadata_test/ab22_20190529_MRI.tar.gz")
"""
archive = "/home/short_test/short.tar.xz"
#files = get_inputlist('/home/ab22_20190529_MRI')
outputfolder = '/home/short_test/short_metadata'

concatMetadata = process_tar_gz(archive, outputfolder)
save_to_xml(concatMetadata, outputfolder)
"""
