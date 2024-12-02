# Standard library imports
import datetime
import getpass
import importlib
import itertools
import json
import os
import re
import sqlite3
import csv
import subprocess

# Third-party library imports
import numpy as np
import pandas as pd
import requests
from typing import Dict, Tuple, Optional, List, Union

# OMERO imports
import omero.clients
from omero.gateway import BlitzGateway, ProjectWrapper, DatasetWrapper, ImageWrapper
from omero.model import OriginalFileI, ProjectAnnotationLinkI
# import omero

# Local imports
from src.io_functions import *
from data import *


import os
import csv

def create_bulk_import_file(id, path, docker_vol_path, filename='./data/image_import_files.csv'):
    """
    This function creates a bulk import file for OMERO.

    Parameters:
    id (str): The ID of the dataset.
    path (str): The path to the image file.
    docker_vol_path (str): The path to the Docker volume.
    filename (str): The name of the bulk import file. Default is './data/image_import_files.csv'.

    Returns:
    int: 0 if the operation is successful.
    """

    path = os.path.join(docker_vol_path, path)
    with open(filename, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([f'Dataset:{id}', path])
    return 0

def get_file_list(folder):
    """
    Traverse the specified directory and its subdirectories to collect all the file paths.

    :param folder: The path of the directory to traverse.
    :return: A list of all the file paths.
    """
    file_list = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            file_list.append(os.path.join(root, file))
    return file_list


def get_netstore_filelist(folder="/home/omero-import"):
    """
    Organize the file paths into a dictionary based on the project names found in the file paths.

    :param folder: The path of the directory to traverse.
    :return: A tuple containing a list of project names and a dictionary where each key is a project name and the value is a list of file paths belonging to that project.
    """
    # Get the list of all file paths
    filelist = get_file_list(folder)

    # Print the first 5 file paths for verification
    print("First 5 files: ", filelist[0:5])

    # Extract the project names from the file paths
    cutfilelist = [x[x.find(folder)+len(folder):] for x in filelist]
    print("First 5 base folders: ", cutfilelist[0:5])
    projectlist = list(set([x.split("/")[1] for x in cutfilelist]))
    print("First 5 projects: ", projectlist[0:5])

    # Organize the file paths into a dictionary based on the project names
    fileDict = {}
    for project in projectlist:
        fileDict[project] = [x for x in filelist if project in x]

    # Print the project names for verification
    print("Projects: ", fileDict.keys())

    return projectlist, fileDict


import os
import pandas as pd
import json

def get_remaining_path(full_path: str, base_path: str) -> str:
    """
    This function takes a full path and a base path as input and returns the remaining path.
    If the full path starts with the base path, it removes the base path from the full path and returns the remaining path.
    If the full path does not start with the base path, it returns the full path as is.

    Parameters:
    full_path (str): The full path.
    base_path (str): The base path.

    Returns:
    str: The remaining path.
    """
    if full_path.startswith(base_path):
        return full_path[len(base_path):].lstrip('/')
    else:
        return full_path

def copy_author_from_projectcolumn(df: pd.DataFrame) -> pd.DataFrame:
    """
    This function takes a DataFrame as input and copies the author information from the project column to the author column.
    The author information is expected to be present in the project column in the format "Project Name (Author Name)".
    The function extracts the author name from the project column and appends it to the author column.
    If the author column already contains some information, the new author name is appended to it.
    The function also removes any duplicates from the author column and returns the updated DataFrame.

    Parameters:
    df (pd.DataFrame): The input DataFrame.

    Returns:
    pd.DataFrame: The updated DataFrame.
    """
    for i in range(len(df)):
        tmp = df['project'][i].split("(")
        if len(tmp) < 2:
            continue
        tmp = tmp[-1].split("/")
        tmp = [x.replace(")", "") for x in tmp]
        df.loc[i, 'author'] = ",".join([df['author'][i], ",".join(tmp)])
        tmp = list(set(df.loc[i, 'author'].split(",")))
        tmp = ",".join([x.strip() for x in tmp])
        df.loc[i, 'author'] = tmp
    return df

def load_json_file(file_path: str) -> dict:
    """
    This function takes a file path as input and loads the JSON file at that path.
    It returns the JSON data as a dictionary.

    Parameters:
    file_path (str): The path to the JSON file.

    Returns:
    dict: The JSON data as a dictionary.
    """
    with open(file_path, 'r') as f:
        return json.load(f)

def get_abbreviation_dict() -> dict:
    """
    This function loads the abbreviations JSON file and returns the data as a dictionary.

    Returns:
    dict: The abbreviations data as a dictionary.
    """
    return load_json_file("./abbreviations.json")

def get_description_dict() -> dict:
    """
    This function loads the descriptions JSON file and returns the data as a dictionary.

    Returns:
    dict: The descriptions data as a dictionary.
    """
    return load_json_file("../descriptions.json")

def get_create_table_sql() -> dict:
    """
    This function loads the database create SQL JSON file and returns the data as a dictionary.

    Returns:
    dict: The database create SQL data as a dictionary.
    """
    return load_json_file("./db_create_sql.json")

import os
import sqlite3
from typing import Dict, Tuple

def check_db_table(db_name: str, table_name: str) -> None:
    """
    This function checks if a table exists in a SQLite database.
    If the table does not exist, it creates the table using the SQL code from the get_create_table_sql() function.

    Parameters:
    db_name (str): The name of the SQLite database.
    table_name (str): The name of the table to check.
    """
    conn = sqlite3.connect(os.path.join("./data", db_name))
    c = conn.cursor()

    # Check if table exists
    c.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    table_exists = c.fetchone() is not None

    if not table_exists:
        sql_create_code = get_create_table_sql()
        for sql in sql_create_code.keys():
            c.execute(sql_create_code[sql])

    conn.close()

def insert_dict_to_database(db_name: str, table_name: str, data_dict: Dict[str, any]) -> int:
    """
    This function inserts a dictionary of data into a SQLite database table.
    It takes the database name, table name, and a dictionary of data as input.
    The keys of the dictionary are used as column names and the values are used as the corresponding row values.
    If an IntegrityError is raised, the function commits the changes and closes the connection.
    The function returns 1 if an IntegrityError is raised and 0 otherwise.

    Parameters:
    db_name (str): The name of the SQLite database.
    table_name (str): The name of the table to insert data into.
    data_dict (Dict[str, any]): A dictionary of data to insert into the table.

    Returns:
    int: 1 if an IntegrityError is raised, 0 otherwise.
    """
    columns = ', '.join(data_dict.keys())
    placeholders = ', '.join(['?' for _ in data_dict])
    values = tuple(data_dict.values())

    sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

    # Connect to the database
    conn = sqlite3.connect(os.path.join("./data", db_name))
    cursor = conn.cursor()
    try:
        cursor.execute(sql, values)
    except sqlite3.IntegrityError as e:
        conn.commit()
        conn.close()
        return 1
    conn.commit()
    conn.close()

    return 0

def get_project_user_tuple(pm_title: str) -> Tuple[str, str]:
    """
    This function takes a project title as input and extracts the project name and user information from it.
    The project name is expected to be present before the opening parenthesis in the project title.
    The user information is expected to be present between the opening and closing parentheses in the project title.
    The function returns a tuple containing the project name and user information.
    If there is no user information present in the project title, the function returns the project name and an empty string.

    Parameters:
    pm_title (str): The project title.

    Returns:
    Tuple[str, str]: A tuple containing the project name and user information.
    """
    # check if there's even an author in the project name
    if pm_title.find("(") == -1:
        return (pm_title, "")
    # Extract the name and user information from the pm_title string
    name, user_info = pm_title.split("(", 1)
    name = name.strip()
    # Remove the closing parenthesis and split the user information into a list
    user = user_info.rstrip(")").split(",")
    # Remove any leading or trailing whitespace from each user in the list
    user = [u.strip() for u in user]
    # Join the users back into a single string, separated by semicolons
    user = ";".join(user)

    return name, user

import os
import pandas as pd
import datetime
import sqlite3
from typing import Dict

def get_df_if_exist(file_path: str) -> pd.DataFrame:
    """
    This function takes a file path as input and checks if a file exists at that path.
    If the file exists, it loads the file into a DataFrame and returns the DataFrame.
    If the file does not exist, it returns None.

    Parameters:
    file_path (str): The path to the file.

    Returns:
    pd.DataFrame: The DataFrame if the file exists, None otherwise.
    """
    # Check if the file exists
    if os.path.isfile(file_path):
        # If the file exists, load it into a DataFrame
        df = pd.read_csv(file_path, dtype=str)
        return df
    else:
        return None

def save_df(file_path: str, df: pd.DataFrame) -> None:
    """
    This function takes a file path and a DataFrame as input and saves the DataFrame to a CSV file at the specified path.

    Parameters:
    file_path (str): The path to the file.
    df (pd.DataFrame): The DataFrame to save.
    """
    df.to_csv(file_path, index=False)

def get_int_timestamp_from_iso(iso_timestamp: str) -> int:
    """
    This function takes an ISO timestamp as input and converts it to an integer timestamp.

    Parameters:
    iso_timestamp (str): The ISO timestamp.

    Returns:
    int: The integer timestamp.
    """
    iso_timestamp = datetime.datetime.fromisoformat(
        iso_timestamp.replace('Z', '+00:00'))
    iso_timestamp = int(iso_timestamp.timestamp())
    return iso_timestamp

def get_iso_timestamp_from_int(int_timestamp: int) -> str:
    """
    This function takes an integer timestamp as input and converts it to an ISO timestamp.

    Parameters:
    int_timestamp (int): The integer timestamp.

    Returns:
    str: The ISO timestamp.
    """
    iso_timestamp = datetime.datetime.fromtimestamp(int_timestamp)
    iso_timestamp = iso_timestamp.strftime('%Y-%m-%d %H:%M:%S')
    return iso_timestamp

def check_if_entry_exists(db_name: str, table_name: str, object_document: Dict[str, any]) -> int:
    """
    This function checks if a specific entry exists in a SQLite database table.
    It takes the database name, table name, and a dictionary containing the specific ID as input.
    The function returns 1 if the entry exists and 0 otherwise.

    Parameters:
    db_name (str): The name of the SQLite database.
    table_name (str): The name of the table to check.
    object_document (Dict[str, any]): A dictionary containing the specific ID.

    Returns:
    int: 1 if the entry exists, 0 otherwise.
    """
    # Connect to the database
    conn = sqlite3.connect(os.path.join("./data", db_name))
    cursor = conn.cursor()

    # SQL command to check for the specific value
    sql = f"SELECT EXISTS (SELECT 1 FROM {table_name} WHERE specific_id = ?);"
    values = (object_document['specific_id'],)

    try:
        cursor.execute(sql, values)
        result = cursor.fetchone()
        if result[0] == 1:
            conn.close()
            return 1
        else:
            conn.close()
            return 0
    except sqlite3.Error as e:
        print("An error occurred:", e.args[0])
    conn.close()
    return 0

def get_cleaned_tag_string(input_string: str) -> str:
    """
    This function takes a string as input and cleans it by replacing certain separators with semicolons,
    removing duplicates, and removing stopwords.
    The function returns the cleaned string.

    Parameters:
    input_string (str): The input string.

    Returns:
    str: The cleaned string.
    """
    separators = [",", ";", "-", "/"]
    for sep in separators:
        input_string = input_string.replace(sep, ";")
    # make the string unique in items
    input_string = ";".join(list(set(input_string.split(";"))))
    input_string = remove_stopwords(input_string)
    return input_string

def remove_stopwords(text: str) -> str:
    """
    This function takes a string as input and removes stopwords from it.
    The function returns the string with stopwords removed.

    Parameters:
    text (str): The input string.

    Returns:
    str: The string with stopwords removed.
    """
    stopwords = get_stopwords()
    words = text.split()
    filtered_words = [word for word in words if word.lower() not in stopwords]
    return ' '.join(filtered_words)

import json
import os
import sqlite3
from typing import Dict, List

def get_stopwords(source: str = 'stopwords.json') -> List[str]:
    """
    This function reads a JSON file containing stopwords and returns a list of stopwords.

    Parameters:
    source (str): The path to the JSON file containing stopwords. Default is 'stopwords.json'.

    Returns:
    List[str]: A list of stopwords.
    """
    with open(source) as f:
        data = json.load(f)
        return data['stopwords']
    return []

def get_secret_api_parameters(source: str = '../secrets/api_secrets.json', type: str = 'rspace') -> Dict[str, any]:
    """
    This function reads a JSON file containing secret API parameters and returns a dictionary of parameters for a specific type.

    Parameters:
    source (str): The path to the JSON file containing secret API parameters. Default is '../secrets/api_secrets.json'.
    type (str): The type of API parameters to return. Default is 'rspace'.

    Returns:
    Dict[str, any]: A dictionary of API parameters for the specified type.
    """
    with open(source) as f:
        data = json.load(f)
        return data[type][0]
    return {}

def delete_duplicate_tags(db_name: str = os.path.join("./data", "sync_database.db")) -> int:
    """
    This function deletes duplicate tags from a SQLite database table.
    It takes the database name as input and returns 0 if the operation is successful.

    Parameters:
    db_name (str): The name of the SQLite database. Default is './data/sync_database.db'.

    Returns:
    int: 0 if the operation is successful.
    """
    # Connect to the SQLite database
    conn = sqlite3.connect(db_name)

    # Create a cursor object
    cursor = conn.cursor()

    # Execute the SQL command to delete duplicates
    cursor.execute("""
        DELETE FROM tag
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM tag
            GROUP BY translated_tag_name, object_id
        );
    """)

    # Commit the changes
    conn.commit()

    # Close the connection
    conn.close()
    return 0

import json
import os
import sqlite3
import requests
from typing import Dict, Optional

def delete_duplicate_objects(db_name: str = os.path.join("./data", "sync_database.db")) -> int:
    """
    This function deletes duplicate objects from a SQLite database table.
    It takes the database name as input and returns 0 if the operation is successful.

    Parameters:
    db_name (str): The name of the SQLite database. Default is './data/sync_database.db'.

    Returns:
    int: 0 if the operation is successful.
    """
    # Connect to the SQLite database
    conn = sqlite3.connect(db_name)

    # Create a cursor object
    cursor = conn.cursor()

    # Execute the SQL command to delete duplicates
    cursor.execute("""
        DELETE FROM object
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM object
            GROUP BY object_name, object_type, specific_id, user, created_timestamp, modified_timestamp, notes, source
        );
    """)

    # Commit the changes
    conn.commit()

    # Close the connection
    conn.close()
    return 0

def delete_duplicate_links(db_name=os.path.join("./data", "sync_database.db")):
    """
    This function deletes duplicate links from a SQLite database table.
    It takes the database name as input.

    Parameters:
    db_name (str): The name of the SQLite database. Default is './data/sync_database.db'.
    """
    # Connect to the SQLite database
    conn = sqlite3.connect(db_name)

    # Create a cursor object
    cursor = conn.cursor()

    # Execute the SQL command to delete duplicates
    cursor.execute("""
        DELETE FROM link
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM link
            GROUP BY src_id, src_table, tar_id, tar_table, tar_source, overlap_ratio
        );
    """)

    # Commit the changes
    conn.commit()

    # Close the connection
    conn.close()

def get_secret_api_parameters(source: str = 'api_secrets.json', type: str = 'rspace') -> Dict[str, any]:
    """
    This function reads a JSON file containing secret API parameters and returns a dictionary of parameters for a specific type.

    Parameters:
    source (str): The path to the JSON file containing secret API parameters. Default is 'api_secrets.json'.
    type (str): The type of API parameters to return. Default is 'rspace'.

    Returns:
    Dict[str, any]: A dictionary of API parameters for the specified type.
    """
    with open(source) as f:
        data = json.load(f)
        return data[type][0]
    return {}

def get_sample_data_from_barcode(sampleParameter: str, elnName: str = 'rspace') -> Dict[str, any]:
    """
    This function retrieves sample data from a barcode using the RSpace API.
    It takes the sample parameter and the ELN name as input and returns a dictionary containing the sample data.

    Parameters:
    sampleParameter (str): The sample parameter.
    elnName (str): The ELN name. Default is 'rspace'.

    Returns:
    Dict[str, any]: A dictionary containing the sample data.
    """
    apiParams = get_secret_api_parameters()
    url = os.path.join(
        *[apiParams['apiUrl'], apiParams['apiInventoryPath'], apiParams['apiSearchFile']])
    headers = {"accept": "application/json",
               "apiKey": f"{apiParams['apiKey']}"}

    # create the search-json for searching in rspace-inventory
    if elnName == 'rspace':
        params = {"pageNumber": 0, "pageSize": 20, "orderBy": "name asc"}
        r = requests.get(url, params=params, headers=headers, verify=False)
        r = r.json()
        return r

def get_object_id_from_specific_id(db_name: str, table_name: str, specific_id: str) -> Optional[int]:
    """
    This function retrieves the object ID from a specific ID in a SQLite database table.
    It takes the database name, table name, and specific ID as input and returns the object ID if it exists, or None otherwise.

    Parameters:
    db_name (str): The name of the SQLite database.
    table_name (str): The name of the table to search in.
    specific_id (str): The specific ID to search for.

    Returns:
    Optional[int]: The object ID if it exists, or None otherwise.
    """
    # Connect to the database
    conn = sqlite3.connect(os.path.join("./data", db_name))
    cursor = conn.cursor()

    # SQL command to check for the specific value and retrieve the object_id
    sql = f"SELECT object_id FROM {table_name} WHERE specific_id = ?;"
    values = (specific_id,)  # Note the comma to create a tuple

    try:
        cursor.execute(sql, values)
        result = cursor.fetchone()
        if result is not None:
            conn.close()
            return result[0]  # Return the object_id
        else:
            conn.close()
            return None  # Return None if specific_id is not found
    except sqlite3.Error as e:
        print("An error occurred:", e.args[0])
        conn.close()
    return None

import sqlite3
import os
from typing import Optional
from datetime import datetime
import pandas as pd

def get_object_id_from_netstore_name(db_name: str, table_name: str, netstore_name: str) -> Optional[int]:
    """
    This function retrieves the object ID from a NetStore name in a SQLite database table.
    It takes the database name, table name, and NetStore name as input and returns the object ID if it exists, or None otherwise.

    Parameters:
    db_name (str): The name of the SQLite database.
    table_name (str): The name of the table to search in.
    netstore_name (str): The NetStore name to search for.

    Returns:
    Optional[int]: The object ID if it exists, or None otherwise.
    """
    # Connect to the database
    conn = sqlite3.connect(os.path.join("./data", db_name))
    cursor = conn.cursor()

    # SQL command to check for the specific value and retrieve the object_id
    sql = f"SELECT object_id FROM {table_name} WHERE object_name = ? AND source = ?;"
    values = (netstore_name, 'fs_storage')  # Note the comma to create a tuple

    try:
        cursor.execute(sql, values)
        result = cursor.fetchone()
        if result is not None:
            conn.close()
            return result[0]  # Return the object_id
        else:
            conn.close()
            return None  # Return None if specific_id is not found
    except sqlite3.Error as e:
        print("An error occurred:", e.args[0])
        conn.close()
    return None

def get_int_from_date(date_str: str) -> int:
    """
    This function converts a date string in the format "YYYY-MM-DD" to an integer representing the number of days since the Unix epoch.

    Parameters:
    date_str (str): The date string in the format "YYYY-MM-DD".

    Returns:
    int: The number of days since the Unix epoch.
    """
    # Convert the date string to a datetime object
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")

    # Convert the datetime object to the number of days since the Unix epoch
    days_since_epoch = date_obj.timestamp()

    # Convert the number of days to an integer
    days_since_epoch_int = int(days_since_epoch)

    return days_since_epoch_int

def convert_abbreviations(df: pd.DataFrame, colname: str = "tags") -> pd.DataFrame:
    """
    This function replaces abbreviations in a DataFrame column with their full forms using a dictionary of abbreviations.
    It takes a DataFrame and a column name as input and returns the updated DataFrame.

    Parameters:
    df (pd.DataFrame): The input DataFrame.
    colname (str): The name of the column containing the tags. Default is "tags".

    Returns:
    pd.DataFrame: The updated DataFrame.
    """
    abbDict = get_abbreviation_dict()
    for key, value in abbDict.items():
        df[colname] = df[colname].str.replace(key, value)
    return process_tags(df, colname=colname)

def convert_abbreviation(og_string: str) -> str:
    """
    This function converts a string of abbreviations into a string of full forms using a dictionary of abbreviations.
    It takes a string as input and returns the updated string.

    Parameters:
    og_string (str): The input string containing the abbreviations.

    Returns:
    str: The updated string containing the full forms.
    """
    abbDict = get_abbreviation_dict()
    og_list = list(set(og_string.split(";")))
    return ";".join([abbDict[key] if key in abbDict else key for key in og_list])

def process_tags(df: pd.DataFrame, colname: str = "tags") -> pd.DataFrame:
    """
    This function removes duplicates from a DataFrame column containing tags.
    It takes a DataFrame and a column name as input and returns the updated DataFrame.

    Parameters:
    df (pd.DataFrame): The input DataFrame.
    colname (str): The name of the column containing the tags. Default is "tags".

    Returns:
    pd.DataFrame: The updated DataFrame.
    """
    df[colname] = df[colname].apply(lambda x: ', '.join(set(x.split(', '))))
    return df

import re
import sqlite3
import os
import pandas as pd
import itertools
from typing import List

def get_possible_tags_list(tags: List[str]) -> List[str]:
    """
    This function filters a list of tags based on certain patterns to remove irrelevant or invalid tags.
    It takes a list of tags as input and returns the filtered list of tags.

    Parameters:
    tags (List[str]): The list of tags to filter.

    Returns:
    List[str]: The filtered list of tags.
    """
    patterns = [
        r'\d+',  # Matches any number
        r'^[a-zA-Z]{1,2}$',  # Matches any string of length 1 or 2
        r'^[a-zA-Z\d]{4}$',  # Matches any string of length 4
        # Matches any string that contains both letters and numbers
        r'^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z\d]+$',
        r'^.*\^.*$'  # Matches any string that contains the "^" character
    ]

    # Filter the list
    filtered_lst = list(set(tags))
    filtered_lst = [x.strip() for x in filtered_lst if x != '']
    filtered_lst = [item for item in filtered_lst if not any(
        re.match(pattern, item) for pattern in patterns)]
    return filtered_lst

def get_dataframe(df_type: str, db_name: str = 'sync_database.db') -> pd.DataFrame:
    """
    This function retrieves a DataFrame from a SQLite database based on the specified dataframe type.
    It takes the dataframe type and the database name as input and returns the DataFrame.

    Parameters:
    df_type (str): The type of DataFrame to retrieve.
    db_name (str): The name of the SQLite database. Default is 'sync_database.db'.

    Returns:
    pd.DataFrame: The retrieved DataFrame.
    """
    conn = sqlite3.connect(os.path.join("./data", db_name))
    if df_type == "link":
        sql = f"SELECT * FROM link;"
    elif df_type == "egroupware":
        sql = f"SELECT * FROM project_registration"
    else:
        sql = f"SELECT * FROM object WHERE source = '{df_type}';"

    # Begin a transaction
    conn.execute("BEGIN")

    df = pd.read_sql_query(sql, conn)

    # Commit the transaction
    conn.execute("COMMIT")
    conn.close()
    return df

def calculate_percentage(str1: str, str2: str) -> float:
    """
    This function calculates the percentage of common characters between two strings.
    It takes two strings as input and returns the percentage of common characters.

    Parameters:
    str1 (str): The first string.
    str2 (str): The second string.

    Returns:
    float: The percentage of common characters.
    """
    if str1 in str2 or str2 in str1:
        return 1
    else:
        common_chars = sum(a == b for a, b in zip(str1, str2))
        return (common_chars / min(len(str1), len(str2)))

def get_df_name(var: pd.DataFrame) -> str:
    """
    This function retrieves the name of a DataFrame variable.
    It takes a DataFrame as input and returns the name of the variable.

    Parameters:
    var (pd.DataFrame): The DataFrame variable.

    Returns:
    str: The name of the DataFrame variable.
    """
    import inspect
    callers_local_vars = inspect.currentframe().f_back.f_locals.items()
    df_name = [var_name for var_name,
               var_val in callers_local_vars if var_val is var][0]
    return df_name

def get_col_overlap_df(df1: pd.DataFrame, df2: pd.DataFrame, colname1: str, colname2: str) -> pd.DataFrame:
    """
    This function calculates the percentage of common characters between two columns of two DataFrames.
    It takes two DataFrames and two column names as input and returns a DataFrame containing the combinations of values and their corresponding percentage of common characters.

    Parameters:
    df1 (pd.DataFrame): The first DataFrame.
    df2 (pd.DataFrame): The second DataFrame.
    colname1 (str): The name of the column in the first DataFrame.
    colname2 (str): The name of the column in the second DataFrame.

    Returns:
    pd.DataFrame: A DataFrame containing the combinations of values and their corresponding percentage of common characters.
    """
    data = []
    for (i1, row1), (i2, row2) in itertools.product(df1.iterrows(), df2.iterrows()):
        combination = f"{row1[colname1]}-{row2[colname2]}"
        percentage = calculate_percentage(row1[colname1], row2[colname2])
        data.append((combination, percentage))
    df_names = [get_df_name(df1), get_df_name(df2)]
    df_result = pd.DataFrame(
        data, columns=["-".join(df_names) + "_" + colname1, 'percentage'])
    return df_result.sort_values(by='percentage')

def calculate_binary_overlap(df1: pd.DataFrame, col1: str, df2: pd.DataFrame, col2: str, epsilon: int) -> pd.DataFrame:
    """
    This function calculates the binary overlap between two columns of two DataFrames based on a time difference threshold.
    It takes two DataFrames, two column names, and a time difference threshold as input and returns a DataFrame containing the binary overlap.

    Parameters:
    df1 (pd.DataFrame): The first DataFrame.
    col1 (str): The name of the column in the first DataFrame.
    df2 (pd.DataFrame): The second DataFrame.
    col2 (str): The name of the column in the second DataFrame.
    epsilon (int): The time difference threshold.

    Returns:
    pd.DataFrame: A DataFrame containing the binary overlap.
    """
    # Create an empty DataFrame to store the results
    result = pd.DataFrame(index=df2.index, columns=df1.index)

    # Iterate over each pair of timestamps
    for i in df1.index:
        for j in df2.index:
            # Calculate the time difference
            diff = abs(get_int_timestamp_from_iso(
                df1[col1][i]) - get_int_timestamp_from_iso(df2[col2][j]))
            # If the difference is less than or equal to epsilon, set the result to 1
            if diff <= epsilon:
                result.at[j, i] = 1
            else:
                result.at[j, i] = 0

    return result

import pandas as pd
import sqlite3
from typing import List, Tuple
import subprocess
import os

def create_system_overlap() -> pd.DataFrame:
    """
    This function creates a DataFrame containing the overlap between egroupware and netstore DataFrames based on project, author, and tags columns.
    It returns the DataFrame containing the overlap.

    Returns:
    pd.DataFrame: A DataFrame containing the overlap between egroupware and netstore DataFrames.
    """
    egroupware_df = get_dataframe("egroupware")
    netstore_df = get_dataframe("netstore")

    cpl_overlap_df = pd.DataFrame({})

    for i, col in enumerate(['project', 'author', 'tags']):
        df_result = get_col_overlap_df(egroupware_df, netstore_df, col)
        df_result.columns = [df_result.columns[0],
                             df_result.columns[1] + str(i)]
        cpl_overlap_df = pd.concat([cpl_overlap_df, df_result], axis=1)

    cpl_overlap_df = convert_abbreviations(cpl_overlap_df)

    return cpl_overlap_df

def is_string_in_list(s: str, lst: List[Tuple[str, int]]) -> int:
    """
    This function checks if a string is present in a list of tuples and returns the corresponding value.
    It takes a string and a list of tuples as input and returns the corresponding value if the string is present, or False otherwise.

    Parameters:
    s (str): The string to search for.
    lst (List[Tuple[str, int]]): The list of tuples to search in.

    Returns:
    int: The corresponding value if the string is present, or False otherwise.
    """
    for key, value in lst:
        if s == key:
            return value
    return False

def get_tags_tuple(conn: object, user: str = 'inplace') -> List[Tuple[str, int]]:
    """
    This function retrieves a list of tuples containing tag names and IDs for a specific user.
    It takes a connection object and a user name as input and returns a list of tuples containing tag names and IDs.

    Parameters:
    conn (object): The connection object.
    user (str): The user name. Default is 'inplace'.

    Returns:
    List[Tuple[str, int]]: A list of tuples containing tag names and IDs.
    """
    tags = conn.getObjects("TagAnnotation")
    result = []
    for tag in tags:
        if tag.getOwner().getName() == user:
            result.append((tag.getValue(), tag.getId()))
    return result

def get_tag_description(tag: str, descriptions: dict = None) -> str:
    """
    This function retrieves the description of a tag from a dictionary of descriptions.
    It takes a tag name and a dictionary of descriptions as input and returns the description of the tag if it is present, or an empty string otherwise.

    Parameters:
    tag (str): The tag name.
    descriptions (dict): A dictionary of descriptions. Default is the output of get_description_dict().

    Returns:
    str: The description of the tag if it is present, or an empty string otherwise.
    """
    if descriptions is None:
        descriptions = get_description_dict()

    if tag in descriptions:
        return descriptions[tag]
    else:
        return ""

def delete_duplicates_bulk_import(bulk_file_src_path):
    """
    This function removes duplicate rows from a CSV file containing a list of files/folders to be imported into OMERO.
    It takes the source file path as input.

    Parameters:
    bulk_file_src_path (str): The source file path.
    """
    # Read the CSV file into a DataFrame
    df = pd.read_csv(bulk_file_src_path)

    # Remove duplicate rows
    df = df.drop_duplicates()

    # Write the DataFrame back to the CSV file
    df.to_csv(bulk_file_src_path, index=False)

def omero_inplace_bulk_import(bulk_file_src_path,
                              bulk_file_tar_path='~/groups/omero-import',
                              docker_vol_path='/NETSTORE_omero-import',
                              server="localhost", username="inplace", password="omero"):
    """
    This function performs an bulk inplace import of csv file list of files/folder into target datasets on an OMERO server using Docker.
    It takes the target dataset, source file path, Docker volume path, server address, username, and password as input.

    Parameters:
    bulk_file_src_path (str): The source file path.
    bulk_file_tar_path (str): The target file path. Default is '~/groups/omero-import'.
    docker_vol_path (str): The Docker volume path. Default is '/NETSTORE_omero-import'.
    server (str): The server address. Default is 'localhost'.
    username (str): The username. Default is 'inplace'.
    password (str): The password. Default is 'omero'.
    """
    delete_duplicates_bulk_import(bulk_file_src_path)

    import shutil
    shutil.copy(bulk_file_src_path, os.path.join(
        bulk_file_tar_path, bulk_file_src_path.split('/')[-1]))

    command = ['/opt/omero/server/OMERO.server-5.6.9-ice36/bin/omero import',
               f'-s {server}',
               f'-u {username}',
               f'-w {password}',
               f'--bulk {os.path.join(docker_vol_path, "bulk.yml")}'
               ]

    command = ['docker', 'exec', '-it', 'omeroserver_docker',
               'bash', '-c'] + [' '.join(command)]
    result = subprocess.run(
        command, stdout=subprocess.PIPE, text=True, input=None)

    output = result.stdout
    # print("Current path:", output)

import os
import subprocess
from omero.gateway import BlitzGateway
from omero.model import OriginalFileI, ProjectAnnotationLinkI
import getpass
from typing import Dict, Tuple

def omero_inplace_import(target_ds: str, src: str, docker_vol_path: str = '/NETSTORE_omero-import', server: str = "localhost", username: str = "inplace", password: str = "omero") -> None:
    """
    This function performs an inplace import of a source file into a target dataset on an OMERO server using Docker.
    It takes the target dataset, source file path, Docker volume path, server address, username, and password as input.

    Parameters:
    target_ds (str): The target dataset.
    src (str): The source file path.
    docker_vol_path (str): The Docker volume path. Default is '/NETSTORE_omero-import'.
    server (str): The server address. Default is 'localhost'.
    username (str): The username. Default is 'inplace'.
    password (str): The password. Default is 'omero'.
    """
    src = os.path.join(docker_vol_path, src)

    if type(target_ds) is str:
        target_type = "name"
    else:
        target_type = "id"

    command = ['/opt/omero/server/OMERO.server-5.6.9-ice36/bin/omero import',
               f'-s {server}',
               f'-u {username}',
               f'-w {password}',
               f'-T Dataset:{target_type}:{target_ds}',
               '--transfer=ln_s',
               f'"{src}"']

    command = ['docker', 'exec', '-it', 'omeroserver_docker',
               'bash', '-c'] + [' '.join(command)]
    result = subprocess.run(
        command, stdout=subprocess.PIPE, text=True, input=None)

    output = result.stdout
    print("Current path:", output)

def add_attachment_to_project(username: str, password: str, host: str, port: int, project_id: int, file_path: str) -> None:
    """
    This function adds an attachment to a project on an OMERO server.
    It takes the username, password, host, port, project ID, and file path as input.

    Parameters:
    username (str): The username.
    password (str): The password.
    host (str): The host address.
    port (int): The port number.
    project_id (int): The project ID.
    file_path (str): The file path.
    """
    conn = BlitzGateway(username, password, host=host, port=port)
    conn.connect()

    project = conn.getObject("Project", project_id)

    original_file = OriginalFileI()
    original_file.setName(os.path.basename(file_path))
    original_file.setSize(os.path.getsize(file_path))
    original_file.setPath(file_path)
    original_file = conn.getUpdateService().saveAndReturnObject(original_file)

    link = ProjectAnnotationLinkI()
    link.setParent(project)
    link.setChild(original_file)
    link = conn.getUpdateService().saveAndReturnObject(link)

    conn.close()

def get_project_timestamps_from_fs_storage(db_name: str, object_id: int) -> Tuple[int, int]:
    """
    This function retrieves the minimum created timestamp and the maximum timestamp between created and modified timestamps for a specific object ID in the fs_storage table of a SQLite database.
    It takes the database name and object ID as input and returns a tuple containing the minimum created timestamp and the maximum timestamp.

    Parameters:
    db_name (str): The name of the SQLite database.
    object_id (int): The object ID.

    Returns:
    Tuple[int, int]: A tuple containing the minimum created timestamp and the maximum timestamp.
    """
    conn = sqlite3.connect(os.path.join("./data", db_name))
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT min(created_timestamp)
        FROM fs_storage
        WHERE object_id = '{object_id}'
    """)
    min_timestamp = cursor.fetchone()[0]

    cursor.execute(f"""
        SELECT max(
            CASE
                WHEN created_timestamp > modified_timestamp THEN created_timestamp
                ELSE modified_timestamp
            END
        )
        FROM fs_storage
        WHERE object_id = '{object_id}'
    """)
    max_timestamp = cursor.fetchone()[0]

    conn.close()

    return min_timestamp, max_timestamp

def get_file_stats(file_path: str) -> Dict[str, any]:
    """
    This function retrieves file statistics such as name, extension, size, creation timestamp, and modification timestamp for a given file path.
    It takes a file path as input and returns a dictionary containing the file statistics.

    Parameters:
    file_path (str): The file path.

    Returns:
    Dict[str, any]: A dictionary containing the file statistics.
    """
    file_stats = os.stat(file_path)
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
    return {
        'object_name': file_name,
        'object_type': file_extension,
        'object_size': file_size,
        'created_timestamp': created_timestamp,
        'modified_timestamp': modified_timestamp,
        'source': 'netstore'
    }

def get_current_username() -> str:
    """
    This function retrieves the current username.

    Returns:
    str: The current username.
    """
    return getpass.getuser()

import subprocess
import json
from typing import Dict, List

def create_rspace_folder(folder_name: str, apikey: str = "e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq") -> str:
    """
    This function creates a new folder in RSpace using the provided folder name and API key.
    It takes a folder name and an API key as input and returns the output of the curl command as a string.

    Parameters:
    folder_name (str): The name of the folder to be created.
    apikey (str): The API key for authentication. Default is "e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq".

    Returns:
    str: The output of the curl command as a string.
    """
    data = {
        "name": folder_name,
        "notebook": "false"
    }
    command = [
        "curl",
        "-k",
        "-X", "POST",
        "https://rstest.int.lin-magdeburg.de/api/v1/folders",
        "-H", "accept: application/json",
        "-H", f"apiKey: {apikey}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(data)
    ]
    output = subprocess.check_output(command)
    return output.decode()

def create_rspace_document(doc_name: str, content: str, parent_folder_id: str, tags: str = "", apikey: str = "e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq") -> str:
    """
    This function creates a new document in RSpace using the provided document name, content, parent folder ID, tags, and API key.
    It takes a document name, content, parent folder ID, tags, and an API key as input and returns the output of the curl command as a string.

    Parameters:
    doc_name (str): The name of the document to be created.
    content (str): The content of the document.
    parent_folder_id (str): The ID of the parent folder.
    tags (str): The tags for the document. Default is an empty string.
    apikey (str): The API key for authentication. Default is "e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq".

    Returns:
    str: The output of the curl command as a string.
    """
    data = {
        "name": doc_name,
        "tags": tags,
        "parentFolderId": parent_folder_id,
        "fields": [
            {
                "content": content
            }
        ]
    }
    command = [
        "curl",
        "-k",
        "-X", "POST",
        "https://rstest.int.lin-magdeburg.de/api/v1/documents",
        "-H", "accept: application/json",
        "-H", f"apiKey: {apikey}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(data)
    ]
    output = subprocess.check_output(command)
    return output.decode()

def search_folder(folder_name: str, apikey: str = "e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq", base_url: str = "https://rstest.int.lin-magdeburg.de/api/v1") -> Dict[str, any]:
    """
    This function searches for a folder in RSpace using the provided folder name, API key, and base URL.
    It takes a folder name, an API key, and a base URL as input and returns a dictionary containing the folder information if the folder is found, or 1 otherwise.

    Parameters:
    folder_name (str): The name of the folder to be searched.
    apikey (str): The API key for authentication. Default is "e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq".
    base_url (str): The base URL of the RSpace API. Default is "https://rstest.int.lin-magdeburg.de/api/v1".

    Returns:
    Dict[str, any]: A dictionary containing the folder information if the folder is found, or 1 otherwise.
    """
    url = f"{base_url}/folders/tree"
    command = [
        "curl",
        "-k",
        "-X", "GET",
        url,
        "-H", "accept: application/json",
        "-H", f"apiKey: {apikey}",
        "--silent",
        "--show-error",
        "--fail",
        "--compressed",
        "--get",
        "--data-urlencode", "typesToInclude=folder",
        "--data-urlencode", "pageNumber=0",
        "--data-urlencode", "pageSize=20",
        "--data-urlencode", "orderBy=lastModified desc"
    ]
    output = subprocess.check_output(command)
    output = json.loads(output)
    for out in output['records']:
        if out['name'] == folder_name:
            return out
    return 1

def search_documents(doc_name: str, apikey: str = "e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq", base_url: str = "https://rstest.int.lin-magdeburg.de/api/v1") -> Dict[str, any]:
    """
    This function searches for a document in RSpace using the provided document name, API key, and base URL.
    It takes a document name, an API key, and a base URL as input and returns a dictionary containing the document information if the document is found, or 1 otherwise.

    Parameters:
    doc_name (str): The name of the document to be searched.
    apikey (str): The API key for authentication. Default is "e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq".
    base_url (str): The base URL of the RSpace API. Default is "https://rstest.int.lin-magdeburg.de/api/v1".

    Returns:
    Dict[str, any]: A dictionary containing the document information if the document is found, or 1 otherwise.
    """
    url = f"{base_url}/documents"
    command = [
        "curl",
        "-k",
        "-X", "GET",
        url,
        "-H", "accept: application/json",
        "-H", f"apiKey: {apikey}",
        "--silent",
        "--show-error",
        "--fail",
        "--compressed",
        "--get",
        "--data-urlencode", f"query={json.dumps({'query': doc_name, 'queryType': 'name'})}",
        "--data-urlencode", "pageNumber=0",
        "--data-urlencode", "pageSize=20",
        "--data-urlencode", "orderBy=lastModified desc"
    ]
    output = subprocess.check_output(command)
    output = json.loads(output)
    for out in output['documents']:
        if out['name'] == doc_name:
            return out
    return 1

def get_placeholder_files_for_rspace() -> List[Dict[str, str]]:
    """
    This function returns a list of placeholder files for RSpace.

    Returns:
    List[Dict[str, str]]: A list of dictionaries containing file information.
    """
    files = [
        {'name': 'file1.xls', 'path': '/workspace/editor/structuredDocument/file1.xls',
            'type': 'sheet', 'metadata': 'empty', 'access': 'manuel'},
        {'name': 'file2.pdf', 'path': '/workspace/editor/structuredDocument/file2.pdf',
            'type': 'pdf', 'metadata': 'empty', 'access': 'manuel'},
        {'name': 'file3.tif', 'path': '/workspace/editor/structuredDocument/file3.tif',
            'type': 'image (tif)', 'metadata': 'empty', 'access': 'omero'},
        {'name': 'file4.tar', 'path': '/workspace/editor/structuredDocument/file4.tar',
            'type': 'archive (tar)', 'metadata': 'empty', 'access': 'manuel'},
    ]
    return files

def generate_html_table(files: List[Dict[str, str]] = get_placeholder_files_for_rspace(), header: str = "") -> str:
    """
    This function generates an HTML table from a list of files.
    It takes a list of files and a header as input and returns an HTML table as a string.

    Parameters:
    files (List[Dict[str, str]]): A list of dictionaries containing file information. Default is the output of get_placeholder_files_for_rspace().
    header (str): An optional header for the table. Default is an empty string.

    Returns:
    str: An HTML table as a string.
    """
    table_html = "<table style='border-collapse: collapse; width: 100%;'>\n"
    table_html += "  <tbody>\n"
    table_html += "    <tr>\n"
    table_html += "         <th><strong>File Name</strong></th>\n"
    table_html += "         <th><strong>File Type</strong></th>\n"
    table_html += "         <th><strong>File Metadata</strong></th>\n"
    table_html += "         <th><strong>Data Access</strong></th>\n"
    table_html += "    </tr>\n"

    for file in files:
        file_name = file['name']
        file_path = file['path']
        file_type = file['type']
        file_metadata = file['metadata']
        data_access = file['access']

        table_html += "    <tr>\n"
        table_html += f"      <td><a href='{file_path}'>{file_name}</a></td>\n"
        table_html += f"      <td>{file_type}</td>\n"
        table_html += f"      <td>{file_metadata}</td>\n"
        table_html += f"      <td>{data_access}</td>\n"
        table_html += "    </tr>\n"

    table_html += "  </tbody>\n"
    table_html += "</table>"

    if header != "":
        table_html = header + "\n" + table_html

    return table_html

import subprocess
import json
import pandas as pd
import sqlite3
import os
from typing import Dict

def search_documents(doc_name: str, apikey: str = "e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq", base_url: str = "https://rstest.int.lin-magdeburg.de/api/v1") -> Dict[str, any]:
    """
    This function searches for a document in RSpace using the provided document name, API key, and base URL.
    It takes a document name, an API key, and a base URL as input and returns a dictionary containing the document information if the document is found, or 1 otherwise.

    Parameters:
    doc_name (str): The name of the document to be searched.
    apikey (str): The API key for authentication. Default is "e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq".
    base_url (str): The base URL of the RSpace API. Default is "https://rstest.int.lin-magdeburg.de/api/v1".

    Returns:
    Dict[str, any]: A dictionary containing the document information if the document is found, or 1 otherwise.
    """
    url = f"{base_url}/documents"
    command = [
        "curl",
        "-k",
        "-X", "GET",
        url,
        "-H", "accept: application/json",
        "-H", f"apiKey: {apikey}",
        "--silent",
        "--show-error",
        "--fail",
        "--compressed",
        "--get",
        "--data-urlencode", f"query={json.dumps({'query': doc_name, 'queryType': 'name'})}",
        "--data-urlencode", "pageNumber=0",
        "--data-urlencode", "pageSize=20",
        "--data-urlencode", "orderBy=lastModified desc"
    ]
    output = subprocess.check_output(command)
    output = json.loads(output)
    for out in output['documents']:
        if out['name'] == doc_name:
            return out
    return 1

def get_egroupware_data(db_name: str, project_id: int) -> pd.DataFrame:
    """
    This function retrieves egroupware data for a specific project ID from a SQLite database.
    It takes a database name and a project ID as input and returns a DataFrame containing the egroupware data.

    Parameters:
    db_name (str): The name of the SQLite database.
    project_id (int): The project ID.

    Returns:
    pd.DataFrame: A DataFrame containing the egroupware data.
    """
    conn = sqlite3.connect(os.path.join("./data", db_name))
    project_registration = pd.read_sql_query(
        f"SELECT * from project_registration WHERE project_id = {project_id}", conn)
    project_schedule = pd.read_sql_query(
        f"SELECT * from project_schedule WHERE project_id = {project_id}", conn)
    conn.close()
    joined_df = pd.merge(project_registration,
                         project_schedule, on='project_id', how='inner')
    return joined_df

import pandas as pd
import sqlite3
import os
import itertools

def get_netstore_data(db_name: str, object_id: int, source: str = 'fs_storage') -> pd.DataFrame:
    """
    This function retrieves netstore data for a specific object ID from a SQLite database.
    It takes a database name, an object ID, and a source as input and returns a DataFrame containing the netstore data.

    Parameters:
    db_name (str): The name of the SQLite database.
    object_id (int): The ID of the object to retrieve data for.
    source (str, optional): The source of the object data. Defaults to 'fs_storage'.

    Returns:
    pd.DataFrame: A DataFrame containing the netstore data for the specified object ID.
    """
    conn = sqlite3.connect(os.path.join("./data", db_name))
    object = pd.read_sql_query(
        f"SELECT * from object WHERE source = '{source}' and object_id = {object_id}", conn)
    fs_storage = pd.read_sql_query(
        f"SELECT * from fs_storage WHERE source = '{source}' and object_id = {object_id}", conn)
    conn.close()
    joined_df = pd.merge(object, fs_storage, on='object_id', how='inner')
    return joined_df

def get_col_overlap_df(df1: pd.DataFrame, df2: pd.DataFrame, colname1: str, colname2: str) -> pd.DataFrame:
    """
    This function calculates the percentage of common characters between two columns of two DataFrames.
    It takes two DataFrames and two column names as input and returns a DataFrame containing the combinations of values and their corresponding percentage of common characters.

    Parameters:
    df1 (pd.DataFrame): The first DataFrame.
    df2 (pd.DataFrame): The second DataFrame.
    colname1 (str): The name of the column in the first DataFrame.
    colname2 (str): The name of the column in the second DataFrame.

    Returns:
    pd.DataFrame: A DataFrame containing the combinations of values and their corresponding percentage of common characters.
    """
    data = []
    for (i1, row1), (i2, row2) in itertools.product(df1.iterrows(), df2.iterrows()):
        combination = f"{row1[colname1]}-{row2[colname2]}"
        percentage = calculate_percentage(row1[colname1], row2[colname2])
        data.append((combination, percentage))
    df_names = [get_df_name(df1), get_df_name(df2)]
    df_result = pd.DataFrame(
        data, columns=["-".join(df_names) + "_" + colname1, 'percentage'])
    return df_result.sort_values(by='percentage')

def calculate_binary_overlap(df1, col1, df2, col2, epsilon):
    """
    This function calculates the binary overlap between two columns of two DataFrames based on a given epsilon value.
    It takes two DataFrames, two column names, and an epsilon value as input and returns a DataFrame containing the binary overlap results.

    Parameters:
    df1 (pd.DataFrame): The first DataFrame.
    col1 (str): The name of the column in the first DataFrame.
    df2 (pd.DataFrame): The second DataFrame.
    col2 (str): The name of the column in the second DataFrame.
    epsilon (float): The maximum time difference allowed for a match.

    Returns:
    pd.DataFrame: A DataFrame containing the binary overlap results.
    """
    # Create an empty DataFrame to store the results
    result = pd.DataFrame(index=df2.index, columns=df1.index)

    # Iterate over each pair of timestamps
    for i in df1.index:
        for j in df2.index:
            # Calculate the time difference
            diff = abs(get_int_timestamp_from_iso(
                df1[col1][i]) - get_int_timestamp_from_iso(df2[col2][j]))
            # If the difference is less than or equal to epsilon, set the result to 1
            if diff <= epsilon:
                result.at[j, i] = 1
            else:
                result.at[j, i] = 0

    return result

def get_dataframe(df_type, db_name='sync_database.db'):
    """
    This function retrieves data from a SQLite database based on the specified data type.
    It takes a data type and a database name as input and returns a DataFrame containing the retrieved data.

    Parameters:
    df_type (str): The type of data to retrieve.
    db_name (str, optional): The name of the SQLite database. Defaults to 'sync_database.db'.

    Returns:
    pd.DataFrame: A DataFrame containing the retrieved data.
    """
    conn = sqlite3.connect(os.path.join("./data", db_name))
    if df_type == "link-fs_storage":
        sql = f"SELECT * FROM link WHERE tar_source = 'fs_storage';"
    if df_type == "link-omero":
        sql = f"SELECT * FROM link WHERE tar_source = 'omero';"
    if df_type == "link":
        sql = f"SELECT * FROM link;"
    if df_type == "egroupware":
        sql = f"SELECT * FROM project_registration"
    if df_type in ["rspace", "fs_storage", "omero"]:
        sql = f"SELECT * FROM object WHERE source = '{df_type}';"

    # Begin a transaction
    conn.execute("BEGIN")

    df = pd.read_sql_query(sql, conn)

    # Commit the transaction
    conn.execute("COMMIT")
    conn.close()
    return df

def get_filelist_from_database(tar_id, db_name='sync_database.db'):
    """
    This function retrieves a file list from a SQLite database based on the specified target ID.
    It takes a target ID and a database name as input and returns a DataFrame containing the file list.

    Parameters:
    tar_id (int): The target ID to retrieve the file list for.
    db_name (str, optional): The name of the SQLite database. Defaults to 'sync_database.db'.

    Returns:
    pd.DataFrame: A DataFrame containing the file list.
    """
    conn = sqlite3.connect(os.path.join("./data", db_name))
    fs = pd.read_sql_query(
        f"SELECT * from fs_storage WHERE object_id = {tar_id}", conn)
    obj = pd.read_sql_query(
        f"SELECT tar_id AS object_id, * from link WHERE tar_id = {tar_id}", conn)

    joined_df = pd.merge(fs,
                         obj, on='object_id', how='inner')

    pr = pd.read_sql_query(
        f"SELECT project_id AS src_id, * from project_registration WHERE project_id = {joined_df['src_id'][0]}", conn)

    joined_df = pd.merge(joined_df,
                         pr, on='src_id', how='inner')

    return joined_df

# read out the objects linked together in the link-table (src_id = egroupware; tar_id = netstore)


import pandas as pd
import sqlite3
import os
import datetime

def get_link_object_from_id(db_name, table_name, id):
    """
    This function retrieves data from a SQLite database based on the specified table name and ID.
    It takes a database name, a table name, and an ID as input and returns a DataFrame containing the retrieved data.

    Parameters:
    db_name (str): The name of the SQLite database.
    table_name (str): The name of the table to retrieve data from.
    id (int): The ID to retrieve data for.

    Returns:
    pd.DataFrame: A DataFrame containing the retrieved data.
    """
    conn = sqlite3.connect(os.path.join("./data", db_name))

    if table_name == "project_registration":
        sql = f"SELECT * FROM {table_name} WHERE project_id = {id};"

    if table_name == "object":
        sql = f"SELECT * FROM {table_name} WHERE object_id = {id} and source = 'fs_storage';"

    conn.execute("BEGIN")
    df = pd.read_sql_query(sql, conn)
    conn.execute("COMMIT")
    conn.close()
    return df

def check_for_omero_entries(db_name, omero_name, object_type):
    """
    This function checks for existing entries in the OMERO source of a SQLite database based on the specified OMERO name and object type.
    It takes a database name, an OMERO name, and an object type as input and returns a DataFrame containing the retrieved data.

    Parameters:
    db_name (str): The name of the SQLite database.
    omero_name (str): The OMERO name to check for.
    object_type (str): The object type to check for.

    Returns:
    pd.DataFrame: A DataFrame containing the retrieved data.
    """
    conn = sqlite3.connect(os.path.join("./data", db_name))

    sql = f"SELECT * FROM 'object' WHERE object_name = '{omero_name}' and source = 'omero' and object_type = '{object_type}';"

    conn.execute("BEGIN")
    df = pd.read_sql_query(sql, conn)
    conn.execute("COMMIT")
    conn.close()
    return df

def get_dataset_fs_storage_name(db_name, base_path):
    """
    This function retrieves data from the fs_storage source of a SQLite database based on the specified base path.
    It takes a database name and a base path as input and returns a DataFrame containing the retrieved data.

    Parameters:
    db_name (str): The name of the SQLite database.
    base_path (str): The base path to retrieve data for.

    Returns:
    pd.DataFrame: A DataFrame containing the retrieved data.
    """
    conn = sqlite3.connect(os.path.join("./data", db_name))

    sql = f"SELECT * FROM fs_storage WHERE object_name LIKE '{base_path}%' and source = 'fs_storage';"

    conn.execute("BEGIN")
    df = pd.read_sql_query(sql, conn)
    conn.execute("COMMIT")
    conn.close()

    if df.empty:
        return None
    return df

def convert_omero_timestamp(timestamp):
    """
    This function converts an OMERO timestamp to a standard timestamp format.
    It takes a timestamp as input and returns the converted timestamp.

    Parameters:
    timestamp (str): The timestamp to convert.

    Returns:
    str: The converted timestamp.
    """
    return datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

def auto_insert_omero_to_database():
    """
    This function automatically inserts OMERO data into a SQLite database.
    It establishes a connection to the OMERO server, extracts data from projects, datasets, and images,
    and inserts the data into the database. It also handles tags and removes duplicates.
    """
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
    delete_duplicate_links()


import sqlite3
import os
import pandas as pd
import datetime
import getpass
import re

def get_tags_from_id(db_name, id, df_type='fs_storage'):
    """
    This function retrieves tags from the database based on the object id and source.

    Parameters:
    db_name (str): The name of the database.
    id (int): The object id.
    df_type (str): The source type. Default is 'fs_storage'.

    Returns:
    df (DataFrame): A pandas DataFrame containing the tag data.
    """
    conn = sqlite3.connect(os.path.join("./data", db_name))
    sql = f"SELECT * FROM tag WHERE object_id = {id} and source = '{df_type}';"

    # Begin a transaction
    conn.execute("BEGIN")

    df = pd.read_sql_query(sql, conn)

    # Commit the transaction
    conn.execute("COMMIT")
    conn.close()
    return df

def get_file_stats(file_path):
    """
    This function retrieves file statistics such as name, extension, size, creation and modification timestamps.

    Parameters:
    file_path (str): The path of the file.

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
    This function retrieves the current username.

    Returns:
    str: The current username.
    """
    return getpass.getuser()

def auto_insert_fs_storage_to_database():
    """
    This function automatically inserts file storage data into the database.
    It retrieves project list and file dictionary from a netstore, then iterates over each project.
    For each project, it inserts object data into the database and retrieves the object id.
    Then, it iterates over each file in the project, retrieves file stats, and inserts them into the fs_storage table.
    It also extracts tags from the file path, cleans and converts them, and inserts them into the tag table.
    Finally, it removes duplicate objects and tags from the database.
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

            # get the tags and insert it into the taglist
            l = file[file.find(folder)+len(folder):]
            sep = r"/|-|_|\.|,"
            tags += re.split(sep, l)
            # try to find the possible relevant tags (TODO: create a dictionary to white/black list tags)
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
                # get min/max timestamp for files in fs_storage table
                # (min_timestamp, max_timestamp) = get_project_timestamps_from_fs_storage(db_name, object_id)
                ###############
    # Remove duplicate objects and tags from the database
    delete_duplicate_objects()
    delete_duplicate_tags()

def convert_omero_timestamp(timestamp):
    """
    This function converts a timestamp from OMERO format to a standard format.

    Parameters:
    timestamp (str): The timestamp in OMERO format.

    Returns:
    str: The timestamp in standard format.
    """
    return datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")

def auto_insert_omero_to_database():
    """
    This function automatically inserts OMERO data into the database.
    It establishes a connection to the OMERO server, retrieves all projects, and iterates over each project.
    For each project, it extracts project data, inserts it into the database, and iterates over each tag in the project,
    extracting and processing tag data and inserting it into the database.
    It then iterates over each dataset in the project, extracts dataset data, inserts it into the database,
    and iterates over each tag in the dataset, extracting and processing tag data and inserting it into the database.
    It then iterates over each image in the dataset, extracts image data, inserts it into the database,
    and iterates over each tag in the image, extracting and processing tag data and inserting it into the database.
    Finally, it removes duplicate objects and tags from the database.
    """
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

    # Remove duplicate objects and tags from the database
    delete_duplicate_objects()
    delete_duplicate_tags()
    conn.close()
    return 0

def convert_rspace_timestamp(timestamp):
    """
    This function converts a timestamp from RSpace format to a standard format.

    Parameters:
    timestamp (str): The timestamp in RSpace format.

    Returns:
    str: The timestamp in standard format.
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

def get_rspace_workspace_folders(sampleParameter, elnName='rspace'):
    """
    This function retrieves workspace folders from RSpace inventory.

    Parameters:
    sampleParameter (str): The sample parameter.
    elnName (str): The ELN name. Default is 'rspace'.

    Returns:
    dict: The JSON response containing the workspace folders.
    """
    apiParams = get_secret_api_parameters()
    url = os.path.join(
        *[apiParams['apiUrl'], apiParams['apiInventoryPath'], apiParams['apiWorkspaceFolder']])
    headers = {"accept": "application/json",
               "apiKey": f"{apiParams['apiKey']}"}
    # create the search-json for searching in rspace-inventory
    if elnName == 'rspace':
        insertDict = {}
        params = {"pageNumber": 0, "pageSize": 20, "orderBy": "name asc"}
        r = requests.get(url, params=params, headers=headers, verify=False)
        r = r.json()
        return r

def insert_egroupware(verbose=0):
    """
    This function inserts project registration and schedule data from egroupware into the database.

    Parameters:
    verbose (int): Verbosity level. Default is 0.
    """
    url = "https://egroupware.lin-magdeburg.de/abrechnung/api/projects.php?start=NaN&end=NaN"
    response = requests.get(url)

    if response.status_code == 200:
        content = response.text
    contents = json.loads(content)
    db_name = 'sync_database.db'
    table_name = 'project_registration'
    check_db_table(db_name, table_name)
    # loop runs over all projects in egroupware
    for c in contents:
        # take only HBI projects TODO: what about the other projects?
        if c['pm_group'] != "HBI":
            continue
        # insert every project registration into the database
        table_name = 'project_registration'
        # split project_name & user from pm_title field
        project_name, user = get_project_user_tuple(c['pm_title'])
        user = user if user else ""
        account_lid = str(c.get('account_lid')) if c.get('account_lid') else ""
        user = ";".join([user, account_lid])
        user = user.replace(",", ";").replace("/", ";")
        if user[0] == ";":
            user = user[1:]
        resources = c['resources'].replace(",", ";").replace("/", ";")
        # get translation & longer versions of short abbrevation to improve tag quality
        resources = convert_abbreviation(resources)
        project_registration = {'project_id': c['pm_id'],
                                'project_name': project_name,
                                'user': user,
                                'start_timestamp': c['first'],
                                'end_timestamp': c['last'],
                                'resources': resources}
        if verbose:
            print(project_registration)
        insert_dict_to_database(db_name, table_name, project_registration)
        #####################################################################
        # insert every schedule for each project into the database
        table_name = 'project_schedule'
        # take it from egroupware
        url = f"https://egroupware.lin-magdeburg.de/abrechnung/api/measurements.php?start=NaN&end=NaN&hrstol=48&project={c['pm_id']}"
        response = requests.get(url)
        response = json.loads(response.text)
        for r in response:
            # take everything from schedule data that could be used as tag (here: description. name, bemerkung)
            # take care that it works even if something is empty
            notes = []
            if r.get('cal_description'):
                notes.append('description:' + str(r['cal_description']))
            if r.get('name'):
                notes.append('name:' + str(r['name']))
            if r.get('bemerkung'):
                notes.append('note:' + str(r['bemerkung']))
            notes = ";".join(notes)
            notes = convert_abbreviation(notes)
            project_schedule = {'schedule_id': r['cal_id'],
                                'project_id': c['pm_id'],
                                'part_name': r['cal_title'],
                                'user': user,
                                'start_timestamp': r['human_cal_start'],
                                'end_timestamp': r['human_cal_end'],
                                'notes': notes}
            insert_dict_to_database(db_name, table_name, project_schedule)
            if verbose:
                print(project_schedule)

def create_object(project_name: str, type: str) -> object:
    """
    This function creates a new project or dataset in OMERO.

    Parameters:
    project_name (str): The name of the project or dataset.
    type (str): The type of the object. It can be 'Project' or 'Dataset'.

    Returns:
    object: The newly created project or dataset object.
    """
    # Use omero.gateway.Projectwrapper:
    conn = BlitzGateway('inplace', 'omero', host='0.0.0.0', port=4064)
    conn.connect()
    if type == 'Project':
        new_project = ProjectWrapper(conn, omero.model.ProjectI())
    if type == 'Dataset':
        new_project = DatasetWrapper(conn, omero.model.DatasetI())
    new_project.setName(project_name)
    new_project.save()
    conn.close()
    # print("New Project, Id:", new_dataset.id)
    return new_project

def get_object_by_id(object_name, project_id) -> object:
    """
    This function retrieves an object from OMERO based on its name and ID.

    Parameters:
    object_name (str): The name of the object.
    project_id (int): The ID of the object.

    Returns:
    object: The retrieved object if found, otherwise None.
    """
    conn = BlitzGateway('inplace', 'omero', host='0.0.0.0', port=4064)
    conn.connect()
    if object_name == 'Tag':
        object_name = 'TagAnnotation'
    project = conn.getObject(object_name, project_id)
    # print(type(project))
    if project is not None:
        conn.close()
        return project
    conn.close()
    return None

def create_tag(tag_name, tag_description) -> object:
    """
    This function creates a new tag in OMERO.

    Parameters:
    tag_name (str): The name of the tag.
    tag_description (str): The description of the tag.

    Returns:
    object: The newly created tag object.
    """
    conn = BlitzGateway('inplace', 'omero', host='0.0.0.0', port=4064)
    conn.connect()
    tag_ann = omero.gateway.TagAnnotationWrapper(conn)
    tag_ann.setValue(tag_name)
    tag_ann.setDescription(tag_description)
    tag_ann.save()
    conn.close()
    return tag_ann

# high = parent object relative to low object (project -> dataset -> image -> tag)
def create_link(high_object, low_object, type='tag'):
    """
    This function creates a link between two objects in OMERO.

    Parameters:
    high_object (object): The parent object.
    low_object (object): The child object.
    type (str): The type of the link. Default is 'tag'.
    """
    conn = BlitzGateway('inplace', 'omero', host='localhost', port=4064)
    conn.connect()
    try:
        if type == 'tag':  # high_object = project; low_object = tag
            high_object.linkAnnotation(low_object)
        if type == 'projectdataset':
            link = omero.model.ProjectDatasetLinkI()
            # We can use a 'loaded' object, but we might get an Exception
            # link.setChild(dataset_obj)
            # Better to use an 'unloaded' object (loaded = False)
            link.setChild(omero.model.DatasetI(low_object.getId(), False))
            link.setParent(omero.model.ProjectI(high_object.getId(), False))
            conn.getUpdateService().saveObject(link)
    except Exception as e:
        print(f"Unexpected error: {e}")
    conn.close()
    # Handle other unexpected errors

def get_object_by_name(object_name, object_class="Project") -> object:
    """
    This function retrieves an object from OMERO based on its name and class.

    Parameters:
    object_name (str): The name of the object.
    object_class (str): The class of the object. Default is 'Project'.

    Returns:
    object: The ID of the retrieved object if found, otherwise None.
    """
    # Connect to the OMERO server
    conn = BlitzGateway('inplace', 'omero', host='localhost', port=4064)
    conn.connect()

    # Query for projects with a given name
    projects = conn.getObjects(object_class)

    # Check if the project you're looking for is in the list
    project_id = None
    for project in projects:
        if project.getName() == object_name:
            project_id = project.getId()
            return project_id
            break
    # Close the connection to the OMERO server
    conn.close()
    return None

def create_rspace_folder(folder_name, apikey="e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq"):
    """
    This function creates a new folder in RSpace.

    Parameters:
    folder_name (str): The name of the folder.
    apikey (str): The API key. Default is 'e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq'.

    Returns:
    str: The output of the command.
    """
    data = {
        "name": folder_name,
        "notebook": "false"
    }

    command = [
        "curl",
        "-k",  # deaktivate ssl verification
        "-X", "POST",
        "https://rstest.int.lin-magdeburg.de/api/v1/folders",
        "-H", "accept: application/json",
        "-H", f"apiKey: {apikey}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(data)
    ]
    output = subprocess.check_output(command)
    # print(output.decode())
    return output.decode()

def create_rspace_document(doc_name, content, parent_folder_id, tags="", apikey="e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq"):
    """
    This function creates a new document in RSpace.

    Parameters:
    doc_name (str): The name of the document.
    content (str): The content of the document.
    parent_folder_id (int): The ID of the parent folder.
    tags (str): The tags for the document. Default is an empty string.
    apikey (str): The API key. Default is 'e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq'.

    Returns:
    str: The output of the command.
    """
    import subprocess
    import json

    data = {
        "name": doc_name,
        "tags": tags,
        "parentFolderId": parent_folder_id,
        "fields": [
            {
                "content": content
            }
        ]
    }

    command = [
        "curl",
        "-k",  # deaktivate ssl verification
        "-X", "POST",
        "https://rstest.int.lin-magdeburg.de/api/v1/documents",
        "-H", "accept: application/json",
        "-H", f"apiKey: {apikey}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(data)
    ]
    output = subprocess.check_output(command)
    # print(output.decode())
    return output.decode()

def search_folder(folder_name, apikey="e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq", base_url="https://rstest.int.lin-magdeburg.de/api/v1"):
    """
    This function searches for a folder in RSpace.

    Parameters:
    folder_name (str): The name of the folder.
    apikey (str): The API key. Default is 'e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq'.
    base_url (str): The base URL. Default is 'https://rstest.int.lin-magdeburg.de/api/v1'.

    Returns:
    dict: The folder information if found, otherwise 1.
    """
    url = f"{base_url}/folders/tree"
    command = [
        "curl",
        "-k",
        "-X", "GET",
        url,
        "-H", "accept: application/json",
        "-H", f"apiKey: {apikey}",
        "--silent",
        "--show-error",
        "--fail",
        "--compressed",
        "--get",
        "--data-urlencode", "typesToInclude=folder",
        "--data-urlencode", "pageNumber=0",
        "--data-urlencode", "pageSize=20",
        "--data-urlencode", "orderBy=lastModified desc"
    ]
    output = subprocess.check_output(command)
    output = json.loads(output)
    # search all findings for the folder_name and return it
    for out in output['records']:
        # TODO: if there're more than one folder sharing the same name; solve it!
        # here it works because it return just one
        if out['name'] == folder_name:
            return (out)
    return 1

def search_documents(doc_name, apikey="e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq", base_url="https://rstest.int.lin-magdeburg.de/api/v1"):
    """
    This function searches for a document in RSpace.

    Parameters:
    doc_name (str): The name of the document.
    apikey (str): The API key. Default is 'e7HV1YLT8BvhM2dSoVvzIyVK0svNexJq'.
    base_url (str): The base URL. Default is 'https://rstest.int.lin-magdeburg.de/api/v1'.

    Returns:
    dict: The document information if found, otherwise 1.
    """
    import json
    import subprocess
    url = f"{base_url}/documents"
    command = [
        "curl",
        "-k",
        "-X", "GET",
        url,
        "-H", "accept: application/json",
        "-H", f"apiKey: {apikey}",
        "--silent",
        "--show-error",
        "--fail",
        "--compressed",
        "--get",
        "--data-urlencode", f"query={json.dumps({'query': doc_name, 'queryType': 'name'})}",
        "--data-urlencode", "pageNumber=0",
        "--data-urlencode", "pageSize=20",
        "--data-urlencode", "orderBy=lastModified desc"
    ]
    output = subprocess.check_output(command)
    output = json.loads(output)
    # search all findings for the folder_name and return it
    for out in output['documents']:
        # TODO: if there're more than one folder sharing the same name; solve it!
        # here it works because it return just one
        if out['name'] == doc_name:
            return (out)
    return 1

def get_placeholder_files_for_rspace():
    """
    This function returns placeholder files for RSpace.

    Returns:
    list: A list of placeholder files.
    """
    # placeholder for real files in netstore or omero
    # TODO: connect files in omero with rspace
    files = [
        {'name': 'file1.xls', 'path': '/workspace/editor/structuredDocument/file1.xls',
            'type': 'sheet', 'metadata': 'empty', 'access': 'manuel'},
        {'name': 'file2.pdf', 'path': '/workspace/editor/structuredDocument/file2.pdf',
            'type': 'pdf', 'metadata': 'empty', 'access': 'manuel'},
        {'name': 'file3.tif', 'path': '/workspace/editor/structuredDocument/file3.tif',
            'type': 'image (tif)', 'metadata': 'empty', 'access': 'omero'},
        {'name': 'file4.tar', 'path': '/workspace/editor/structuredDocument/file4.tar',
            'type': 'archive (tar)', 'metadata': 'empty', 'access': 'manuel'},
    ]
    return files

def create_rspace_files_table(header, tar_id, db_name='sync_database.db'):
    """
    This function creates a table of files for RSpace.

    Parameters:
    header (str): The header of the table.
    tar_id (int): The ID of the tar file.
    db_name (str): The name of the database. Default is 'sync_database.db'.

    Returns:
    list: A list of files.
    """
    files = []
    fs_storage_df = get_filelist_from_database(tar_id)
    # print(fs_storage_df)
    for i, project_name in enumerate(fs_storage_df['project_name']):

        project_name = project_name.split("/omero-import/")[-1].split("/")[0]
        project_id = get_object_by_name(project_name,
                                        object_class="Project")

        conn = BlitzGateway('inplace', 'omero', host='0.0.0.0', port=4064)
        conn.connect()

        project = conn.getObject("Project", project_id)

        try:
            for dataset in project.listChildren():
                omero_link = (
                    f"http://localhost:4080/webclient/?show=dataset-{dataset.getId()}")
                # TODO: use only the filename for the specific file (e.g. this code only works for one img file in a dataset)
                img_filename = ''
                for img in dataset.listChildren():
                    img_filename = img.getName()
                    if img_filename == '':
                        continue
            # print(omero_image_object)
                    files.append({'name': img_filename,
                                  'path': fs_storage_df['object_name'][i],
                                  'type': fs_storage_df['object_type'][i],
                                  'metadata': 'empty',
                                  'access': omero_link})
        except:
            conn.close()
            return []
    conn.close()
    return files

def create_rspace_document_header(egroupware_project_name, fs_storage_project_folder, overlap_ratio):
    """
    This function creates a header for an RSpace document.

    Parameters:
    egroupware_project_name (str): The name of the egroupware project.
    fs_storage_project_folder (str): The name of the fs_storage project folder.
    overlap_ratio (float): The overlap ratio.

    Returns:
    str: The header.
    """
    header = f"<p>egroupware_project: {egroupware_project_name}\n</p>"
    header += f"<p>netstore_folder: {fs_storage_project_folder}\n</p>"
    header += f"<p>similarity ratio (egroupware_project; netstore_folder): {overlap_ratio}\n</p>"
    return header

def generate_html_table(files=get_placeholder_files_for_rspace(), header=""):
    """
    This function generates an HTML table.

    Parameters:
    files (list): A list of files. Default is the output of get_placeholder_files_for_rspace().
    header (str): The header of the table. Default is an empty string.

    Returns:
    str: The HTML table.
    """
    table_html = "<table style='border-collapse: collapse; width: 100%;' border='1' width='300' cellpadding='5'>\n"
    table_html += "  <tbody>\n"
    table_html += "    <tr>\n"
    table_html += "         <th><strong>Omero Image Name</strong></th>\n"
    table_html += "         <th><strong>File Type</strong></th>\n"
    table_html += "         <th><strong>File Metadata</strong></th>\n"
    table_html += "         <th><strong>Data Access</strong></th>\n"
    table_html += "    </tr>\n"

    for file in files:
        file_name = file['name']
        file_path = file['path']
        file_type = file['type']
        file_metadata = file['metadata']
        data_access = file['access']

        table_html += "    <tr>\n"
        table_html += f"      <td><a href='{file_path}'>{file_name}</a></td>\n"
        table_html += f"      <td>{file_type}</td>\n"
        table_html += f"      <td>{file_metadata}</td>\n"
        table_html += f"      <td><a href='{data_access}'>{data_access}</a></td>\n"
        table_html += "    </tr>\n"

    table_html += "  </tbody>\n"
    table_html += "</table>"

    if header != "":
        table_html = header + "\n" + table_html

    return table_html

""" ## TODO: untested function
    def get_egroupware_schedule_overlap(placeholder1, placeholder2):
            ## this part calc the overlap between schedule
            result = calculate_binary_overlap(egroupware_joined_df, 
                                            'start_timestamp_y', 
                                            netstore_joined_df, 
                                            'created_timestamp_y', 
                                            1)        
            for i, ns in enumerate(netstore_joined_df['fs_id']):                   
                if list(result.iloc[i])[0] == 0:                
                    continue            
                link = {'src_id': project_id,
                                        'src_table': 'project_registration',
                                        'tar_id': object_id,
                                        'tar_table': 'object', 
                                        'overlap_ratio': list(result.iloc[i])[0],
                                        'manual_validated': 0,
                                        'created_timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        'modified_timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        'notes': "object[source == 'fs_storage']; get_col_overlap_df(netstore_joined_df.iloc[0:1], egroupware_joined_df.iloc[0:1], 'object_name_x', 'project_name')"}  
                print(link)
                insert_dict_to_database(db_name, 'link', link)
            """
