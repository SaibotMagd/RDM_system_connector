#!/usr/bin/env python
# coding: utf-8

"""
This script synchronizes data from various sources (eGroupware, RSpace, OMERO, and Netstore) into a SQL database.
It performs the following steps:

1. Loads all projects from eGroupware and inserts them into the database.
2. Retrieves sample data and workspace folders from RSpace, processes them, and inserts them into the database.
3. Automatically inserts data from OMERO into the database.
4. Deletes duplicate objects, tags, and links from the database.
5. Automatically inserts data from Netstore into the database.

The script measures and prints the runtime for each step.
"""

from src.io_metadata import *
from data import *
import datetime
import pandas as pd
import os
import json
from src.io_functions import *
import requests
from tqdm.auto import tqdm


def main():
    """This is the main function we call when running the python file."""
    pass


if __name__ == "__main__":
    main()