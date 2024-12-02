#!/usr/bin/env python
# coding: utf-8
from src.io_metadata import *
from data import *
import datetime
import pandas as pd
import os
import json
from src.io_functions import *
import requests
from tqdm.auto import tqdm

##################################################
# EGROUPWARE -> sqldb
# load all projects from egroupware (last ~20s)

def insert_egroupware(verbose=0):
    """
    Fetches project data from eGroupWare and inserts it into a local database.

    Parameters:
    verbose (int): If set to 1, prints the project registration and schedule data.

    Returns:
    None
    """
    url = "https://egroupware.lin-magdeburg.de/abrechnung/api/projects.php?start=NaN&end=NaN"
    response = requests.get(url)

    if response.status_code == 200:
        content = response.text
    contents = json.loads(content)
    db_name = 'sync_database.db'
    table_name = 'project_registration'
    check_db_table(db_name, table_name)

    # Loop runs over all projects in eGroupWare
    for c in contents:
        # Take only HBI projects TODO: what about the other projects?
        if c['pm_group'] != "HBI":
            continue

        # Insert every project registration into the database
        table_name = 'project_registration'
        # Split project_name & user from pm_title field
        project_name, user = get_project_user_tuple(c['pm_title'])
        user = user if user else ""
        account_lid = str(c.get('account_lid')) if c.get('account_lid') else ""
        user = ";".join([user, account_lid])
        user = user.replace(",", ";").replace("/", ";")
        if user[0] == ";":
            user = user[1:]
        resources = c['resources'].replace(",", ";").replace("/", ";")
        # Get translation & longer versions of short abbreviation to improve tag quality
        resources = convert_abbreviation(resources)
        project_registration = {
            'project_id': c['pm_id'],
            'project_name': project_name,
            'user': user,
            'start_timestamp': c['first'],
            'end_timestamp': c['last'],
            'resources': resources
        }
        if verbose:
            print(project_registration)
        insert_dict_to_database(db_name, table_name, project_registration)

        #####################################################################
        # Insert every schedule for each project into the database
        table_name = 'project_schedule'
        # Take it from eGroupWare
        url = f"https://egroupware.lin-magdeburg.de/abrechnung/api/measurements.php?start=NaN&end=NaN&hrstol=48&project={c['pm_id']}"
        response = requests.get(url)
        response = json.loads(response.text)
        for r in response:
            # Take everything from schedule data that could be used as tag (here: description, name, bemerkung)
            # Take care that it works even if something is empty
            notes = []
            if r.get('cal_description'):
                notes.append('description:' + str(r['cal_description']))
            if r.get('name'):
                notes.append('name:' + str(r['name']))
            if r.get('bemerkung'):
                notes.append('note:' + str(r['bemerkung']))
            notes = ";".join(notes)
            notes = convert_abbreviation(notes)
            project_schedule = {
                'schedule_id': r['cal_id'],
                'project_id': c['pm_id'],
                'part_name': r['cal_title'],
                'user': user,
                'start_timestamp': r['human_cal_start'],
                'end_timestamp': r['human_cal_end'],
                'notes': notes
            }
            insert_dict_to_database(db_name, table_name, project_schedule)
            if verbose:
                print(project_schedule)

#!/usr/bin/env python
# coding: utf-8
##################################################
# RSPACE -> sqldb
# 2 read rspace

def insert_rspace_to_db():
    """
    Fetches sample data from RSpace and inserts it into a local database.

    Parameters:
    None

    Returns:
    None
    """
    rspace_docs = get_sample_data_from_barcode("")
    db_name = 'sync_database.db'
    table_name = 'object'
    check_db_table(db_name, table_name)

    for single_doc in rspace_docs['documents']:
        # Add the RSpace document entries into the database
        table_name = 'object'
        notes = []
        if single_doc.get('tags'):
            notes.append(str(single_doc['tags']))
        if single_doc.get('tags'):
            notes.append(str(single_doc['tagMetaData']))
        notes = ";".join(notes)
        notes = get_cleaned_tag_string(notes)
        object_document = {
            'object_name': single_doc['name'],
            'object_type': 'document',
            'specific_id': single_doc['globalId'],
            'user': single_doc['owner']['username'],
            'created_timestamp': datetime.datetime.strptime(single_doc['created'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S"),
            'modified_timestamp': datetime.datetime.strptime(single_doc['lastModified'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S"),
            'notes': notes,
            'source': 'rspace'
        }
        # If the entry is already in the database, don't insert it again (have to be checked because the ELN ID isn't the unique ID in the database)
        if check_if_entry_exists(db_name, table_name, object_document):
            continue
        insert_dict_to_database(db_name, table_name, object_document)

        #######################################################################
        # Insert the RSpace tag entries into the database
        # Get the object_id from the object table and use it to chain the document and the tag
        object_id = get_object_id_from_specific_id(db_name, table_name, single_doc['globalId'])
        table_name = 'tag'
        notes = notes.split(";")
        for note in notes:
            trans_note = get_cleaned_tag_string(note)
            trans_note = convert_abbreviation(trans_note)
            if trans_note == "":
                continue
            tag = {
                'object_id': object_id,
                'tag_name': note,
                'translated_tag_name': trans_note,
                'created_timestamp': datetime.datetime.strptime(single_doc['created'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S"),
                'modified_timestamp': datetime.datetime.strptime(single_doc['lastModified'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S"),
                'used': 1,
                'description': get_tag_description(trans_note),
                'source': 'rspace'
            }
            insert_dict_to_database(db_name, table_name, tag)
    delete_duplicate_tags()

def convert_rspace_timestamp(timestamp):
    """
    Converts an RSpace timestamp to a standard datetime format.

    Parameters:
    timestamp (str): The RSpace timestamp in the format "%Y-%m-%dT%H:%M:%S.%fZ".

    Returns:
    str: The converted timestamp in the format "%Y-%m-%d %H:%M:%S".
    """
    return datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%S")

def process_rspace_documents(documents, db_name, table_name):
    """
    Process RSpace documents and insert them into the database.

    Args:
        documents (dict): A dictionary containing the RSpace documents.
        db_name (str): The name of the database.
        table_name (str): The name of the table to insert the documents into.
    """
    check_db_table(db_name, table_name)

    for doc in documents['documents']:
        notes = []
        if doc.get('tags'):
            notes.append(str(doc['tags']))
        if doc.get('tagMetaData'):
            notes.append(str(doc['tagMetaData']))

        notes = ";".join(notes)
        notes = get_cleaned_tag_string(notes)

        object_document = {
            'object_name': doc['name'],
            'object_type': 'document',
            'specific_id': doc['globalId'],
            'user': doc['owner']['username'],
            'created_timestamp': convert_rspace_timestamp(doc['created']),
            'modified_timestamp': convert_rspace_timestamp(doc['lastModified']),
            'notes': notes,
            'source': 'rspace'
        }

        if check_if_entry_exists(db_name, table_name, object_document):
            continue

        insert_dict_to_database(db_name, table_name, object_document)
        process_tags(db_name, table_name, doc, object_document)


def process_rspace_folder(folder, db_name, table_name):
    """
    Process RSpace folders and insert them into the database.

    Args:
        folders (dict): A dictionary containing the RSpace documents.
        db_name (str): The name of the database.
        table_name (str): The name of the table to insert the documents into.
    """
    check_db_table(db_name, table_name)

    for doc in folder['records']:
        notes = []
        if doc.get('tags'):
            notes.append(str(doc['tags']))
        if doc.get('tagMetaData'):
            notes.append(str(doc['tagMetaData']))

        notes = ";".join(notes)
        notes = get_cleaned_tag_string(notes)

        object_document = {
            'object_name': doc['name'],
            'object_type': 'folder',
            'specific_id': doc['globalId'],
            'user': doc['owner']['username'],
            'created_timestamp': convert_rspace_timestamp(doc['created']),
            'modified_timestamp': convert_rspace_timestamp(doc['lastModified']),
            'notes': notes,
            'source': 'rspace'
        }

        if check_if_entry_exists(db_name, table_name, object_document):
            continue

        insert_dict_to_database(db_name, table_name, object_document)
        process_tags(db_name, table_name, doc, object_document)


def get_rspace_workspace_folders(sampleParameter, elnName='rspace'):
    """
    Fetches RSpace workspace folders using the API.

    Args:
        sampleParameter (str): A sample parameter for the API request.
        elnName (str): The name of the ELN (default is 'rspace').

    Returns:
        dict: The JSON response containing the workspace folders.
    """
    apiParams = get_secret_api_parameters()
    url = os.path.join(
        *[apiParams['apiUrl'], apiParams['apiInventoryPath'], apiParams['apiWorkspaceFolder']])
    headers = {"accept": "application/json",
               "apiKey": f"{apiParams['apiKey']}"}
    # Create the search-json for searching in RSpace inventory
    if elnName == 'rspace':
        insertDict = {}
        params = {"pageNumber": 0, "pageSize": 20, "orderBy": "name asc"}
        r = requests.get(url, params=params, headers=headers, verify=False)
        r = r.json()
        return r

def process_tags(db_name, table_name, doc, object_document):
    """
    Process the tags of an RSpace document and insert them into the database.

    Args:
        db_name (str): The name of the database.
        table_name (str): The name of the table to insert the tags into.
        doc (dict): The RSpace document.
        object_document (dict): The object document corresponding to the RSpace document.
    """
    object_id = get_object_id_from_specific_id(
        db_name, table_name, doc['globalId'])
    table_name = 'tag'
    notes = object_document['notes'].split(";")

    for note in notes:
        trans_note = get_cleaned_tag_string(note)
        trans_note = convert_abbreviation(trans_note)

        if trans_note == "":
            continue

        tag = {
            'object_id': object_id,
            'tag_name': note,
            'translated_tag_name': trans_note,
            'created_timestamp': convert_rspace_timestamp(doc['created']),
            'modified_timestamp': convert_rspace_timestamp(doc['lastModified']),
            'used': 1,
            'description': get_tag_description(trans_note),
            'source': 'rspace'
        }

        insert_dict_to_database(db_name, table_name, tag)

#!/usr/bin/env python
# coding: utf-8
##################################################
# OMERO -> sqldb

def convert_omero_timestamp(timestamp):
    """
    Converts an OMERO timestamp to a standard datetime format.

    Args:
        timestamp (str): The OMERO timestamp in the format "%Y-%m-%dT%H:%M:%S".

    Returns:
        str: The converted timestamp in the format "%Y-%m-%d %H:%M:%S".
    """
    return datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

def auto_insert_omero_to_database():
    """
    Automatically inserts OMERO data into the database.

    This function connects to the OMERO server, retrieves projects, datasets, and images,
    and inserts them along with their tags into the specified database tables.

    Returns:
    None
    """
    # Import the necessary libraries
    from omero.gateway import BlitzGateway

    # Establish a connection to the OMERO server
    conn = BlitzGateway('inplace', 'omero', host='0.0.0.0', port=4064)
    conn.connect()

    # Define the database and table names
    db_name = 'sync_database.db'
    object_table_name = 'object'
    tag_table_name = 'tag'

    # Check if the database and tables exist, if not, create them
    check_db_table(db_name, object_table_name)
    check_db_table(db_name, tag_table_name)

    # Get all projects from OMERO
    projects = conn.getObjects("Project")

    # Iterate over each project
    for project in projects:
        # Extract project data
        project_data = {
            'object_name': project.simpleMarshal()['name'],
            'object_type': project.simpleMarshal()['type'],
            'specific_id': project.simpleMarshal()['id'],
            'user': project.getOwnerOmeName(),
            'created_timestamp': convert_omero_timestamp(project.creationEventDate().isoformat()),
            'modified_timestamp': convert_omero_timestamp(project.updateEventDate().isoformat()),
            'notes': "",
            'source': 'omero'
        }
        # Insert project data into the database
        insert_dict_to_database(db_name, object_table_name, project_data)

        # Iterate over each tag in the project and add it to the database
        for tag_entry in project.listAnnotations():
            # Extract and process tag data
            trans_note = get_cleaned_tag_string(tag_entry.getValue())
            trans_note = convert_abbreviation(trans_note)
            tag_data = {
                'object_id': project.simpleMarshal()['id'],
                'object_type': project.simpleMarshal()['type'],
                'tag_name': tag_entry.getValue(),
                'translated_tag_name': trans_note,
                'created_timestamp': convert_omero_timestamp(tag_entry.creationEventDate().isoformat()),
                'modified_timestamp': convert_omero_timestamp(tag_entry.creationEventDate().isoformat()),
                'used': 1,
                'description': get_tag_description(trans_note),
                'source': 'omero'
            }
            # Insert tag data into the database
            insert_dict_to_database(db_name, tag_table_name, tag_data)

        # Iterate over each dataset in the project
        for dataset in project.listChildren():
            # Extract dataset data
            dataset_data = {
                'object_name': dataset.simpleMarshal()['name'],
                'object_type': dataset.simpleMarshal()['type'],
                'specific_id': dataset.simpleMarshal()['id'],
                'user': dataset.getOwnerOmeName(),
                'created_timestamp': convert_omero_timestamp(dataset.creationEventDate().isoformat()),
                'modified_timestamp': convert_omero_timestamp(dataset.updateEventDate().isoformat()),
                'notes': dataset.simpleMarshal()['description'],
                'source': 'omero'
            }
            # Insert dataset data into the database
            insert_dict_to_database(db_name, object_table_name, dataset_data)

            # Iterate over each tag in the dataset and add it to the database
            for tag_entry in dataset.listAnnotations():
                # Extract and process tag data
                trans_note = get_cleaned_tag_string(tag_entry.getValue())
                trans_note = convert_abbreviation(trans_note)
                tag_data = {
                    'object_id': dataset.simpleMarshal()['id'],
                    'object_type': dataset.simpleMarshal()['type'],
                    'tag_name': tag_entry.getValue(),
                    'translated_tag_name': trans_note,
                    'created_timestamp': convert_omero_timestamp(tag_entry.creationEventDate().isoformat()),
                    'modified_timestamp': convert_omero_timestamp(tag_entry.creationEventDate().isoformat()),
                    'used': 1,
                    'description': get_tag_description(trans_note),
                    'source': 'omero'
                }
                # Insert tag data into the database
                insert_dict_to_database(db_name, tag_table_name, tag_data)

            # Iterate over each image in the dataset
            for image in dataset.listChildren():
                # Extract image data
                image_data = {
                    'object_name': image.simpleMarshal()['name'],
                    'object_type': image.simpleMarshal()['type'],
                    'specific_id': image.simpleMarshal()['id'],
                    'user': image.getOwnerOmeName(),
                    'created_timestamp': convert_omero_timestamp(image.creationEventDate().isoformat()),
                    'modified_timestamp': convert_omero_timestamp(image.updateEventDate().isoformat()),
                    'notes': image.simpleMarshal()['description'],
                    'source': 'omero'
                }
                # Insert image data into the database
                insert_dict_to_database(db_name, object_table_name, image_data)

                # Iterate over each tag in the image and add it to the database
                for tag_entry in image.listAnnotations():
                    # Extract and process tag data
                    trans_note = get_cleaned_tag_string(tag_entry.getValue())
                    trans_note = convert_abbreviation(trans_note)
                    tag_data = {
                        'object_id': image.simpleMarshal()['id'],
                        'object_type': image.simpleMarshal()['type'],
                        'tag_name': tag_entry.getValue(),
                        'translated_tag_name': trans_note,
                        'created_timestamp': convert_omero_timestamp(tag_entry.creationEventDate().isoformat()),
                        'modified_timestamp': convert_omero_timestamp(tag_entry.creationEventDate().isoformat()),
                        'used': 1,
                        'description': get_tag_description(trans_note),
                        'source': 'omero'
                    }
                    # Insert tag data into the database
                    insert_dict_to_database(db_name, tag_table_name, tag_data)

    conn.close()
    # Remove duplicate objects and tags from the database
    delete_duplicate_objects()
    delete_duplicate_tags()

#!/usr/bin/env python
# coding: utf-8
##################################################
# NETSTORE -> sqldb

def get_netstore_filelist(folder):
    """
    Retrieves a list of files from a specified folder and organizes them by project.

    Args:
        folder (str): The path to the folder containing the files.

    Returns:
        tuple: A tuple containing the list of project names and a dictionary of file lists organized by project.
    """
    filelist = get_inputlist(folder)
    print(filelist[0:5])
    # filelist = filelist[:10000]
    # Read the project names from the folder
    cutfilelist = [x[x.find(folder)+len(folder):] for x in filelist]
    print("found basefolders: ", cutfilelist[0:5])
    projectlist = list(set([x.split("/")[1] for x in cutfilelist]))
    print("found projects: ", projectlist[0:5])
    # Read project, start, end, tags from folders/files
    fileDict = {}
    for project in projectlist:
        tmp = [x for x in filelist if x.find(project) != -1]
        fileDict[project] = tmp
    print(fileDict.keys())
    return fileDict.keys(), fileDict

folder = "/home/omero-import"
# project_list, file_dict = get_netstore_filelist()

def get_file_stats(file_path):
    """
    Retrieves statistics for a given file.

    Args:
        file_path (str): The path to the file.

    Returns:
        dict: A dictionary containing the file statistics.
    """
    # Get file stats
    file_stats = os.stat(file_path)

    # Extract required stats
    file_name = file_path
    file_extension = os.path.splitext(os.path.basename(file_path))[1]
    if file_extension == '.gz':
        file_extension = "." + \
            ".".join(os.path.basename(file_path).split(".")[-2:])
    file_size = file_stats.st_size
    created_timestamp = datetime.datetime.fromtimestamp(
        file_stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
    modified_timestamp = datetime.datetime.fromtimestamp(
        file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')

    # Return stats as a dictionary
    return {
        'object_name': file_name,
        'object_type': file_extension,
        'object_size': file_size,
        'created_timestamp': created_timestamp,
        'modified_timestamp': modified_timestamp,
        'source': 'fs_storage'
    }

def get_current_username():
    """
    Retrieves the current username.

    Returns:
        str: The current username.
    """
    import getpass
    return getpass.getuser()

def auto_insert_netstore_to_database():
    """
    Automatically inserts Netstore file data into the database.

    This function retrieves a list of files from a specified folder, organizes them by project,
    and inserts the project and file data into the specified database tables.

    Returns:
    None
    """
    project_list, file_dict = get_netstore_filelist()
    folder = "/home/omero-import"
    db_name = 'sync_database.db'
    check_db_table(db_name, "fs_storage")
    print(get_current_username())

    for proj in project_list:
        object = {
            'object_name': proj,
            'object_type': 'Project',
            'specific_id': os.path.join(folder, proj),
            'user': get_current_username(),
            'created_timestamp': "",
            'modified_timestamp': "",
            'notes': "",
            'source': 'fs_storage'
        }

        insert_dict_to_database(db_name, "object", object)
        object_id = get_object_id_from_netstore_name(db_name, 'object', proj)

        # if object_id > 921: break ##testcase

        tags = []
        for file in file_dict[proj]:
            tmp = get_file_stats(file)
            tmp['object_id'] = object_id
            insert_dict_to_database(db_name, "fs_storage", tmp)

            # Get the tags and insert them into the taglist
            l = file[file.find(folder)+len(folder):]
            sep = r"/|-|_|\.|,"
            tags += re.split(sep, l)
            # Try to find the possible relevant tags (TODO: create a dictionary to white/black list tags)
            tags = get_possible_tags_list(tags)
            for tag in tags:
                trans_note = get_cleaned_tag_string(tag)
                trans_note = convert_abbreviation(trans_note)
                tag_data = {
                    'object_id': object_id,
                    'object_type': "",
                    'tag_name': tag,
                    'translated_tag_name': trans_note,
                    'created_timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'modified_timestamp': "",
                    'used': 1,
                    'description': get_tag_description(trans_note),
                    'source': 'fs_storage'
                }
                # Insert tag data into the database
                insert_dict_to_database(db_name, "tag", tag_data)
                ###############
                # Get min/max timestamp for files in fs_storage table
                # (min_timestamp, max_timestamp) = get_project_timestamps_from_fs_storage(db_name, object_id)
                ###############
    # Remove duplicate objects and tags from the database
    delete_duplicate_objects()
    delete_duplicate_tags()

if __name__ == "__main__":
    """
    Main function to execute the data insertion process.

    This function sequentially inserts data from various sources into the database
    and removes duplicate entries.

    Returns:
    None
    """
    import time
    db_name = 'sync_database.db'
    table_name = 'object'
    total_runtime = 0
    start_time = time.time()
    insert_egroupware(verbose=0)
    total_runtime += time.time() - start_time
    print("egroupware readout done", time.time() - start_time)
    print("##################################################################################")
    start_time = time.time()
    rspace_docs = get_sample_data_from_barcode("")
    rspace_forms = get_rspace_workspace_folders("")
    process_rspace_folder(rspace_forms, db_name, table_name)
    process_rspace_documents(rspace_docs, db_name, table_name)
    insert_rspace_to_db()
    total_runtime += time.time() - start_time
    print("rspace readout done", time.time() - start_time)
    print("##################################################################################")
    start_time = time.time()
    auto_insert_omero_to_database()
    total_runtime += time.time() - start_time
    print("omero readout done", time.time() - start_time)
    print("##################################################################################")
    start_time = time.time()
    delete_duplicate_objects()
    delete_duplicate_tags()
    delete_duplicate_links()
    total_runtime += time.time() - start_time
    print("database duplettes delection done", time.time() - start_time)
    print("##################################################################################")
    start_time = time.time()
    auto_insert_netstore_to_database()
    total_runtime += time.time() - start_time
    print("netstore readout done", time.time() - start_time)
    
"""
#!/usr/bin/env python
# coding: utf-8
##################################################
## OMERO -> sqldb

def convert_omero_timestamp(timestamp):
    return datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

# Establish connection to OMERO
conn = BlitzGateway('inplace', 'omero', host='0.0.0.0', port=4064)
conn.connect()

# Get all projects from OMERO
projects = conn.getObjects("Project")

# Get sample data from barcode and define database and table names
rspace_docs = get_sample_data_from_barcode("")
db_name = 'sync_database.db'
table_name = 'tag'

# Check if the database and table exist, if not, create them
check_db_table(db_name, table_name)
table_name = 'object'
check_db_table(db_name, table_name)

# Iterate over each project
for project in projects:
    # Add project data to the database
    object_project = {
        'object_name': project.simpleMarshal()['name'],
        'object_type': project.simpleMarshal()['type'],
        'specific_id': project.simpleMarshal()['id'],
        'user': project.getOwnerOmeName(),
        'created_timestamp': convert_omero_timestamp(project.creationEventDate().isoformat()),
        'modified_timestamp': convert_omero_timestamp(project.updateEventDate().isoformat()),
        'notes': "",
        'source': 'omero'
    }
    insert_dict_to_database(db_name, "object", object_project)

    # Iterate over each tag in the project and add it to the database
    for tag_entry in project.listAnnotations():
        trans_note = get_cleaned_tag_string(tag_entry.getValue())
        trans_note = convert_abbreviation(trans_note)
        tag = {
            'object_id': project.simpleMarshal()['id'],
            'object_type': project.simpleMarshal()['type'],
            'tag_name': tag_entry.getValue(),
            'translated_tag_name': trans_note,
            'created_timestamp': convert_omero_timestamp(tag_entry.creationEventDate().isoformat()),
            'modified_timestamp': convert_omero_timestamp(tag_entry.updateEventDate().isoformat()),
            'used': 1,
            'description': get_tag_description(trans_note),
            'source': 'omero'
        }
        insert_dict_to_database(db_name, "tag", tag)

    # Iterate over each dataset in the project
    for dataset in project.listChildren():
        # Add dataset data to the database
        object_dataset = {
            'object_name': dataset.simpleMarshal()['name'],
            'object_type': dataset.simpleMarshal()['type'],
            'specific_id': dataset.simpleMarshal()['id'],
            'user': dataset.getOwnerOmeName(),
            'created_timestamp': convert_omero_timestamp(dataset.creationEventDate().isoformat()),
            'modified_timestamp': convert_omero_timestamp(dataset.updateEventDate().isoformat()),
            'notes': dataset.simpleMarshal()['description'],
            'source': 'omero'
        }
        insert_dict_to_database(db_name, "object", object_dataset)

        # Iterate over each tag in the dataset and add it to the database
        for tag_entry in dataset.listAnnotations():
            trans_note = get_cleaned_tag_string(tag_entry.getValue())
            trans_note = convert_abbreviation(trans_note)
            tag = {
                'object_id': dataset.simpleMarshal()['id'],
                'object_type': dataset.simpleMarshal()['type'],
                'tag_name': tag_entry.getValue(),
                'translated_tag_name': trans_note,
                'created_timestamp': convert_omero_timestamp(tag_entry.creationEventDate().isoformat()),
                'modified_timestamp': convert_omero_timestamp(tag_entry.creationEventDate().isoformat()),
                'used': 1,
                'description': get_tag_description(trans_note),
                'source': 'omero'
            }
            insert_dict_to_database(db_name, "tag", tag)

        # Iterate over each image in the dataset
        for image in dataset.listChildren():
            # Add image data to the database
            object_image = {
                'object_name': image.simpleMarshal()['name'],
                'object_type': image.simpleMarshal()['type'],
                'specific_id': image.simpleMarshal()['id'],
                'user': image.getOwnerOmeName(),
                'created_timestamp': convert_omero_timestamp(image.creationEventDate().isoformat()),
                'modified_timestamp': convert_omero_timestamp(image.updateEventDate().isoformat()),
                'notes': image.simpleMarshal()['description'],
                'source': 'omero'
            }
            insert_dict_to_database(db_name, "object", object_image)

            # Iterate over each tag in the image and add it to the database
            for tag_entry in image.listAnnotations():
                trans_note = get_cleaned_tag_string(tag_entry.getValue())
                trans_note = convert_abbreviation(trans_note)
                tag = {
                    'object_id': image.simpleMarshal()['id'],
                    'object_type': image.simpleMarshal()['type'],
                    'tag_name': tag_entry.getValue(),
                    'translated_tag_name': trans_note,
                    'created_timestamp': convert_omero_timestamp(tag_entry.creationEventDate().isoformat()),
                    'modified_timestamp': convert_omero_timestamp(tag_entry.creationEventDate().isoformat()),
                    'used': 1,
                    'description': get_tag_description(trans_note),
                    'source': 'omero'
                }
                insert_dict_to_database(db_name, "tag", tag)

# Remove duplicate objects and tags from the database
delete_duplicate_objects()
delete_duplicate_tags()
"""
