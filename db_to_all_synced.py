#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import itertools
from src.io_functions import *
from data import *
import omero.clients
from omero.gateway import BlitzGateway
import importlib
import sqlite3
from datetime import timedelta

def create_links():
    """
    Creates links between different data sources in the database.

    This function deletes duplicate objects, tags, and links, and then creates links between
    eGroupWare and Netstore, and between eGroupWare and OMERO based on overlapping data.

    Returns:
    None
    """
    delete_duplicate_objects()
    delete_duplicate_tags()
    delete_duplicate_links()

    db_name = 'sync_database.db'
    check_db_table(db_name, "link")
    omero_df = get_dataframe('omero')
    fs_storage_df = get_dataframe("fs_storage")
    # link_df = get_dataframe("link")
    egroupware_df = get_dataframe("egroupware")
    # Get project name and files from database per object_id
    # (fs_storage_df['object_id'] restricted to "fs_storage")
    # netstore_joined_df = get_netstore_data(db_name, 919)
    netstore_df = get_dataframe('fs_storage')
    omero_df = get_dataframe('omero')

    # Create the link(s):

    check_db_table(db_name, 'link')

    # Create the links in the database between eGroupWare and Netstore
    for project_id in egroupware_df['project_id']:
        # print("project_id", project_id, ": project_name: ", egroupware_df[egroupware_df['project_id'] == project_id]['project_name'].iloc[0])
        for object_id in netstore_df['object_id']:
            netstore_joined_df = get_netstore_data(db_name, object_id)
            egroupware_joined_df = get_egroupware_data(db_name, project_id)
            overlap_df = get_col_overlap_df(
                netstore_joined_df.iloc[0:1], egroupware_joined_df.iloc[0:1], 'object_name_x', 'project_name')
            check = 0
            for p in list(overlap_df['percentage']):
                if p >= 0.8:
                    print(
                        f"I matched the eGroupWare-Netstore: {list(egroupware_joined_df.iloc[0:1]['project_name'])}-{list(netstore_joined_df.iloc[0:1]['object_name_x'])} = {p}")
                    # check = 1

                    link = {'src_id': project_id,
                            'src_table': 'project_registration',
                            'tar_id': object_id,
                            'tar_table': 'object',
                            'tar_source': 'fs_storage',
                            'overlap_ratio': p,
                            'manual_validated': 0,
                            'created_timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'modified_timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'notes': f"{list(egroupware_joined_df.iloc[0:1]['project_name'])[0]}-{list(netstore_joined_df.iloc[0:1]['object_name_x'])[0]} object[source == 'fs_storage'] get_col_overlap_df(netstore_joined_df.iloc[0:1], egroupware_joined_df.iloc[0:1], 'object_name_x', 'project_name')"}
                    # print(link)
                    insert_dict_to_database(db_name, 'link', link)

    # Create the links between eGroupWare and OMERO in the database
    for project_id in egroupware_df['project_id']:
        # print("project_id", project_id, ": project_name: ", egroupware_df[egroupware_df['project_id'] == project_id]['project_name'].iloc[0])
        for object_id in omero_df['object_id']:
            omero_joined_df = omero_df[omero_df['object_id'] == object_id]
            omero_joined_df = omero_joined_df[omero_joined_df['object_type'] == 'Project']
            egroupware_joined_df = get_egroupware_data(db_name, project_id)
            overlap_df = get_col_overlap_df(
                egroupware_joined_df.iloc[0:1], omero_joined_df.iloc[0:1], 'project_name', 'object_name')
            check = 0
            for p in list(overlap_df['percentage']):
                if p >= 0.8:
                    print(
                        f"I matched the eGroupWare-OMERO: {list(egroupware_joined_df.iloc[0:1]['project_name'])}-{list(omero_joined_df.iloc[0:1]['object_name'])} = {p}")
                    # check = 1

                    link = {'src_id': project_id,
                            'src_table': 'project_registration',
                            'tar_id': object_id,
                            'tar_table': 'object',
                            'tar_source': 'omero',
                            'overlap_ratio': p,
                            'manual_validated': 0,
                            'created_timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'modified_timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'notes': f"{list(egroupware_joined_df.iloc[0:1]['project_name'])[0]}-{list(omero_joined_df.iloc[0:1]['object_name'])[0]}; object[source == 'omero']; get_col_overlap_df(egroupware_joined_df.iloc[0:1], omero_joined_df.iloc[0:1], 'project_name', 'object_name')"}
                    # print(link)
                    insert_dict_to_database(db_name, 'link', link)

    delete_duplicate_objects()
    delete_duplicate_tags()
    delete_duplicate_links()

def sync_omero():
    """
    Synchronizes OMERO data with the database and performs necessary operations.

    This function inserts OMERO data into the database, creates links between different data sources,
    and synchronizes the data with OMERO.

    Returns:
    None
    """
    auto_insert_omero_to_database()
    db_name = 'sync_database.db'
    docker_vol_path = "/OMERO"
    # netstore_joined_df = get_netstore_data(db_name, 919)
    netstore_df = get_dataframe('fs_storage')
    omero_df = get_dataframe('omero')
    link_df = get_dataframe('link-fs_storage')
    conn = BlitzGateway('inplace', 'omero', host='0.0.0.0', port=4064)
    conn.connect()
    # tags = conn.getObjects("TagAnnotation")
    # Auto insert linked entries to OMERO and RSpace
    for index, row in link_df.iterrows():
        if float(row['overlap_ratio']) >= 0.8:
            # Get a dataframe with eGroupWare info for a specific link
            src_df = get_link_object_from_id(
                db_name, row['src_table'], row['src_id'])
            # Get a dataframe with Netstore info for a specific link
            tar_df = get_link_object_from_id(
                db_name, row['tar_table'], row['tar_id'])
            # Set the name variable to the project name from eGroupWare
            # TODO: (add an artificial "_new" because it already exists, to test the creation)
            try:
                egroupware_project_name = src_df['project_name'][0]
                omero_project_name = egroupware_project_name
                fs_storage_project_folder = tar_df['object_name'][0]
            except:
                print("wrong target df!", row)
                continue
            # TODO: lern_multi3 is too large to fast import in OMERO so skip it!
            # if fs_storage_project_folder == "zlern_multi3":
            #    continue

            #############################################################################
            #### OMERO Sync #############################################################
            # Check if project already exists in OMERO
            # search_result = omero_df[omero_df['project'].str.contains(egroupware_project_name)]
            # if search_result.empty:
            # If the project already exists in OMERO, don't create it again
            project_id = get_object_by_name(egroupware_project_name)
            if check_for_omero_entries(db_name, list(tar_df['object_name'])[0], object_type="Project").empty and project_id == None:
                print("I create: ", egroupware_project_name)
                project = create_object(
                    egroupware_project_name, type="Project")
                project_id = project.getId()
            else:
                continue
            # Get the path of the images to take it as dataset inside the project
            # TODO: Use every specific path for every image (currently it just uses the longest path)
            # TODO: Add the real server path as key:value; also all the other non-bioformat/non-importable data as key:value pairs with links
            src = f"/fs_storage_omero-import/{fs_storage_project_folder}"
            base_path = f"/home/omero-import/{fs_storage_project_folder}"

            filelist = list(get_dataset_fs_storage_name(
                db_name, base_path)['object_name'])
            filelist = sorted(filelist, key=len)
            fs_storage_dataset_folder = get_remaining_path(
                filelist[0], base_path).split("/")[0]
            print(
                f"fs_storage_project_folder = {fs_storage_project_folder}; \n fs_storage_dataset_folder = {fs_storage_dataset_folder}")

            project = conn.getObject("Project", project_id)
            dataset_id = ""
            for child in project.listChildren():
                dataset = conn.getObject("Dataset", child.getId())
                dataset_id = dataset.getId()
            if dataset_id == "":
                dataset = create_object(fs_storage_dataset_folder, "Dataset")
                dataset_id = dataset.getId()
                create_link(project, dataset, "projectdataset")
                create_bulk_import_file(dataset_id,
                                        os.path.join(
                                            src.split("/")[-1], fs_storage_dataset_folder),
                                        docker_vol_path="/NETSTORE_omero-import"
                                        )
            # print(f"try to import: {src} into {project_id}:{dataset.getId()}")
            print("I add to dataset_id = ", dataset_id,
                  os.path.join(src.split("/")[-1], fs_storage_dataset_folder))
            # src path includes the "real folder of the project", but for import you need to include the docker volume mainfolder
            """
            omero_inplace_import(dataset_id,
                                 os.path.join(
                                     src.split("/")[-1], fs_storage_dataset_folder),
                                 docker_vol_path='/NETSTORE_omero-import',
                                 server="localhost",
                                 username="inplace",
                                 password="omero")
            """
            # Create the tags from link_df in OMERO and link it to the specific projects
            # Check if tag already exists:
            tag_tuple = get_tags_tuple(conn)

            # Split the tags string using both separators: "-" & ","
            # possible_tags = [item for sublist in row['egroupware_df-egroupware_df_tags'].split('-') for item in sublist.split(',')]
            # possible_tags =
            tag_df = get_tags_from_id(
                db_name, row['tar_id'], df_type='fs_storage')
            possible_tags = list(tag_df['translated_tag_name'])
            # print(possible_tags)
            tag_descriptions_dict = get_description_dict()
            for p_tag in possible_tags:
                tag_id = is_string_in_list(p_tag, tag_tuple)
                try:
                    if not tag_id:
                        description = get_tag_description(
                            p_tag, tag_descriptions_dict)
                        tag = create_tag(p_tag, description)
                        create_link(project, tag)
                    else:
                        print(f'add tag to project {project.getId()}')
                        tag = conn.getObject("TagAnnotation", tag_id)
                        create_link(project, tag)
                except:
                    print("tag processing error in OMERO db")
            """
    """
    # Import has to be done before RSpace
    auto_insert_omero_to_database()
    conn.close()
    # TODO: Make the bulk import work (can't copy the import-list file, rights issues)
    try:
        omero_inplace_bulk_import(bulk_file_src_path="./data/image_import_files.csv",
                                  bulk_file_tar_path="/home/cni/slicer-omero/omero_server_volume",
                                  docker_vol_path=docker_vol_path,
                                  server="localhost", username="inplace", password="omero")
    except:
        print("no bulk import files, file!, so nothing to import to OMERO")

def sync_rspace():
    """
    Synchronizes RSpace data with the database and performs necessary operations.

    This function retrieves data from the database, creates links between different data sources,
    and synchronizes the data with RSpace.

    Returns:
    None
    """
    netstore_df = get_dataframe('fs_storage')
    omero_df = get_dataframe('omero')
    link_df = get_dataframe('link-fs_storage')
    conn = BlitzGateway('inplace', 'omero', host='0.0.0.0', port=4064)
    conn.connect()
    # tags = conn.getObjects("TagAnnotation")
    # Auto insert linked entries to OMERO and RSpace
    print(len(link_df))
    for index, row in link_df.iterrows():
        if float(row['overlap_ratio']) >= 0.8:
            # Get a dataframe with eGroupWare info for a specific link
            src_df = get_link_object_from_id(
                db_name, row['src_table'], row['src_id'])
            # Get a dataframe with Netstore info for a specific link
            tar_df = get_link_object_from_id(
                db_name, row['tar_table'], row['tar_id'])
            # Set the name variable to the project name from eGroupWare
            # TODO: (add an artificial "_new" because it already exists, to test the creation)
            try:
                egroupware_project_name = src_df['project_name'][0]
                omero_project_name = egroupware_project_name
                fs_storage_project_folder = tar_df['object_name'][0]
            except:
                print("no target df!", row)
                continue
            # TODO: lern_multi3 is too large to fast import in OMERO so skip it!
            # if fs_storage_project_folder == "zlern_multi3":
            #    continue

            ##############################################################################
            #### RSpace Sync #############################################################
            # Placeholder variable to print if a folder and/or document is being created
            new = [0, 0]
            print("fs_storage_folder: ", fs_storage_project_folder)
            print("egroupware_project_name: ", egroupware_project_name)
            tag_df = get_tags_from_id(
                db_name, row['tar_id'], df_type='fs_storage')
            possible_tags = ",".join(list(tag_df['translated_tag_name']))

            header = create_rspace_document_header(
                egroupware_project_name, fs_storage_project_folder, row['overlap_ratio'])
            files = create_rspace_files_table(
                header, row['tar_id'], db_name='sync_database.db')
            # If there are no files in the possible document inside the folder, don't create it
            if files == []:
                continue

            html_table = generate_html_table(files, header)
            # Check if a folder sharing the same name of egroupware_project_name already exists:
            folder_json = search_folder(egroupware_project_name)
            if folder_json == 1:
                new[0] = 1
                # Create the folder in RSpace named by egroupware_project
                folder_json = json.loads(
                    create_rspace_folder(egroupware_project_name))
            # Create the notebook in RSpace named by fs_storage_folder name
            # Use dataset as document name in RSpace
            src = f"/fs_storage_omero-import/{fs_storage_project_folder}"
            base_path = f"/home/omero-import/{fs_storage_project_folder}"
            filelist = list(get_dataset_fs_storage_name(
                db_name, base_path)['object_name'])
            filelist = sorted(filelist, key=len)
            fs_storage_dataset_folder = get_remaining_path(
                filelist[0], base_path).split("/")[0]

            document_json = search_documents(fs_storage_dataset_folder)
            if document_json == 1:
                new[1] = 1
                # Create a document in RSpace named by egroupware_project
                document_json = json.loads(create_rspace_document(
                    fs_storage_dataset_folder, html_table, folder_json['id'], possible_tags))
            if new[0]:
                print(f"I created a new folder: {egroupware_project_name}")
            if new[1]:
                print(f"I created a new document: {fs_storage_dataset_folder}")
            print(
                "########################################################################################")

    conn.close()

def main():
    """
    Main function to execute the synchronization process.

    This function removes the OMERO import file if it exists, creates links between different data sources,
    and synchronizes the data with OMERO and RSpace.

    Returns:
    None
    """
    if os.path.exists("./data/image_import_files.csv"):
        os.remove("./data/image_import_files.csv")
    else:
        print("OMERO import file already reset")
    create_links()
    sync_omero()
    sync_rspace()
"""
if __name__ == "__main__":
    db_name = 'sync_database.db'
    docker_vol_path = "/OMERO"
    main()
"""
    
# TODO: clear the trash code below (if its trash)
"""

    # old code: should not work
    # auto insert linked entries rspace

    link_df = get_dataframe("link")
    print(link_df.head())
    fs_storage_df = get_dataframe("fs_storage")

    for index, row in link_df.iterrows():
        new = [0, 0]
        if float(row['percentage0']) >= 0.8:
            # scrap the possible omero_project_name & the actual folder on fs_storage from diff column in link_df
            tmp = row.iloc[0].split("(")
            egroupware_project_name = tmp[0].strip()
            if len(egroupware_project_name.split("-")) > 1:
                egroupware_project_name = egroupware_project_name.split("-")[0]
            tmp = tmp[-1].split(")")
            # it gives the filesystem folder for
            if tmp[-1][1] == "-":
                fs_storage_folder = tmp[-1][1:].strip()
            else:
                fs_storage_folder = tmp[-1].split("-")[-1]

            print("fs_storage_folder: ", fs_storage_folder)
            print("egroupware_project_name: ", egroupware_project_name)
            header = f"<p>egroupware_project_name: {egroupware_project_name}\n</p>"
            header += f"<p>fs_storage_folder: {fs_storage_folder}\n</p>"
            header += f"<p>similarity ratio (egroupware_project_name; ntstore_folder): {row['percentage0']}\n</p>"
            # create placeholder html_table
            html_table = generate_html_table(files, header)
            # check if a folder sharing the same name of egroupware_project_name already exists:
            folder_json = search_folder(egroupware_project_name)
            if folder_json == 1:
                new[0] = 1
                # create the folder in rspace named by egroupware_project
                folder_json = json.loads(
                    create_rspace_folder(egroupware_project_name))
            # create the notebook in rspace named by fs_storage_folder name
            document_json = search_documents(fs_storage_folder)
            if document_json == 1:
                new[1] = 1
                # create a document in rspace named by egroupware_project
                document_json = json.loads(create_rspace_document(
                    fs_storage_folder, html_table, folder_json['id'], row['egroupware_df-egroupware_df_tags']))
            if new[0]:
                print(f"I created a new folder: {egroupware_project_name}")
            if new[1]:
                print(f"I created a new document: {fs_storage_folder}")
            print("############################################")
    """

# TODO: create tumbnails for the images and readout metadata
"""
    import os
    from pathlib import Path
    import nibabel as nib
    import numpy as np

    def filelist(startpath):
        files = []
        for path in Path(startpath).rglob('*'):
            if path.is_file():
                files.append(str(path))
        return files

    fs_storage_df = get_dataframe("fs_storage")
    for index, row in fs_storage_df.iterrows():
        fs_storage_folder = row['project']
        full_path = f"/home/omero-import/{fs_storage_folder}"
        #print(full_path)
        if os.path.isdir(full_path):
            files = filelist(full_path)
            for i, f in enumerate(files):
                if f.split(".")[-1] == "gz" and f.split(".")[-2] == "nii":
                    print(f)

                    # Load the NIfTI image
                    img = nib.load(f)

                    # Get the image data as a numpy array
                    data = img.get_fdata()

                    # Calculate the maximum intensity projection along the z-axis
                    mip = np.max(data, axis=2)

                    # If you want to save the MIP as a new NIfTI image
                    new_img = nib.Nifti1Image(mip, affine=img.affine)
                    nib.save(new_img, "/".join(f.split("/")[:-1] + ['mip_image.nii']))
                    break
    """



