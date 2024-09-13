![Lin_X_NFDI4BIOIMAGE](/doc/imgs/lin_x_nfdi4bioimage.png)
# RDM_system_connector
# **WARNING** 
This is a proof of concept, it has not been decided whether it will be developed into a fully functional tool. 
Feedback is therefore essential, especially as it is unclear whether this type of tool is useful at all, and if so, which parts, as the concept consists of many different parts.

---

# Table of Contents:
- [Purpose of the RDM_system_connector](#RDM_system_connector)
	- [overview graph](#overview_graph)
- Parts:
	- [Internal_project_study_registration](#Internal_project_study_registration)
	- [ELN_(e.g._RSpace,_elabFTW)_+_inventory](#ELN_(e.g._RSpace,_elabFTW)_+_inventory)
	- [Omero_Image_+_metadata_hub](#Omero_Image_+_metadata_hub)
	- [long-term_archive_storage](#long-term_archive_storage)
	- [matching (fuzzy_similarity_matching,_direct_matching,_manual_linking)](#matching (fuzzy_similarity_matching,_direct_matching,_manual_linking))
# RDM_system_connector

- The purpose of this tool will be to connect different platforms that have been or will be used as part of research data management. 
- Every part of the system is replaceable as the connection is the central point of the tool. 
- the benefits in day-to-day research result from the cooperation of different stakeholders who work together on a project and do not necessarily have access to the same systems or do not use them in their work process despite having access
- making essential information usable in all connected systems makes it possible to have it available more quickly and clearly
- in the best case scenario, stakeholders receive information that they were previously unable to obtain
[see a real practical example](/doc/practical_example_lin)

#### overview_graph

```mermaid
graph TD
    A[project registration] --> B[ELN e.g. RSpace]
    B --> C[Omero hub]
    C --> D[Long-term archive storage]
    A -- matching e.g. fuzzy_similarity_matching --> D
```

## Internal_project_study_registration
- the main point of this part is that every scientific project has a study registration somewhere
- the registration can be a proposal (e.g. a pdf/text file to apply for a funding programme or a thesis)
- we use a separate platform (egroupware) where people can register their study and book time slots for specific instruments (e.g. MR, EEG, microscopes, computer servers)
## ELN_(e.g._RSpace,_elabFTW)_+_inventory
- a platform where protocols of preparation procedures or plans for procedures can be written
- there should be basic protocols and subject-specific ones (e.g. keeping track of daily events)
- be used to plan and structure the interaction between people working on different parts of a project (e.g. principal investigators set the protocol and delegate work; technical assistants prepare the tissue; doctoral candidates take the images). 

## Omero_Image_+_metadata_hub
- use inplace import to link the images from [long-term_archive_storage](#long-term_archive_storage) to Omero
- use key-value pairs to display the metadata
- create tags from [(semi-)automatic_tag_creation](/doc/(semi-)_automatic_tag_creation.md) including tag descriptions from [(semi-)_automatic_description&_ontology_linking_creation](/doc/(semi-)_automatic_description_&_ontology_linking_creation.md)
## long-term_archive_storage
- crawl a mounted drive to find images, metadata files, projects, studies and add them to [ELN_(e.g._RSpace,_elabFTW)_+_inventory](#ELN_(e.g._RSpace,_elabFTW)_+_inventory) and [Omero_Image_+_metadata_hub](#Omero_Image_+_metadata_hub)
- use file names, folder names, metadata for [(semi-)_automatic_tag_creation](/doc/(semi-)_automatic_tag_creation.md) and [(semi-)_automatic_description_&_ontology_linking_creation](/doc/(semi-)_automatic_description_&_ontology_linking_creation.md)
## matching (fuzzy_similarity_matching,_direct_matching,_manual_linking)
- **fuzzy** = Calculate the overlap of project names (from [internal_project_study_registration](#internal_project_study_registration) and folder names (from [long-term_archive_storage](#long-term_archive_storage)); 
	- where a percentage of overlap of consecutive letters is specified; if the shortest name (either projectname or foldername) is completely contained in the other, by convention the overlap is set to 100%
- TODO: **direct matching** = define a file (TODO: metadata entry) Define a file or a metadata entry from a file as the project name, which must be identical to that of the study application, character for character; i.e. a 100% match is assumed
	- e.g. our project leaders have to sign an application letter which is included in [internal_project_study_registration](#internal_project_study_registration) and in [long-term_archive_storage](#long-term_archive_storage) for every new project or study. 
	- as both files are identical, the project duration, project manager and project name can be read from them
- TODO: **manual linking** = the linking table in the database could be filled manually to force a specific project/study to be linked to another;  
	- however, a browser interface is planned to display the automatically generated matches, validate them by eye and create your own


