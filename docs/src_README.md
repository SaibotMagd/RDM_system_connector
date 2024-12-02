# Project Synchronization Tool
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

This tool is designed to synchronize the entries in a four-tool system, which includes a 
- project registration system (eGroupware), 
- an electronic lab book (Rspace), 
- an image database (OMERO), 
- a long-term netstorage system (LINstore). 
The tool achieves this by running a daemon that continuously extracts the entries from these four tools and writes them into a database. 

## Features

    Continuous Extraction: The daemon runs continuously to extract entries from the project registration system, electronic lab book, image database, and long-term netstorage system.
    Database Storage: All extracted entries are written into a database for easy management and retrieval.
    Project Matching: The tool connects the project registration system and the long-term netstorage system to find matching projects.
    OMERO Integration: Matching projects and their image data from the long-term netstorage system are added to OMERO using an in-place import.
    Rspace Integration: The project names and netstorage files are connected to rSpace for easy access and management.

## Installation

To install the project synchronization tool, follow these steps:

    Clone the repository
    Install the required dependencies: conda env create --file environment.yml
    Configure the tool to connect to the project registration system, electronic lab book, image database, and long-term netstorage system.
    Run the daemon: python all_to_db.py

## Usage

The daemon will continuously run in the background, extracting entries from the four tools and synchronizing them with the database and the other tools. To view the synchronized entries, you can use the provided user interface or query the database directly.
Contributing

Contributions to the project synchronization tool are welcome! If you find a bug or have a feature request, please open an issue on the GitHub repository. If you would like to contribute code, please fork the repository and submit a pull request.
License

