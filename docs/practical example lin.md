# practical example lin
- three different individuals are working on the same study (based on a project)
	- PI (principle investigator; e.g. leader of the working group)
	- TA (technical assistant; e.g. staff member usually not scientist or without scientific expertise)
	- DC (doctoral candidate; e.g. usually the person who has the most knowledge about this particular study)

Before linking:
- PI usually uses in his daily work:
	- [ELN](https://en.wikipedia.org/wiki/Electronic_lab_notebook) e.g. [RSpace](https://github.com/rspace-os) w/o inventory to read the protocols of TA & DC
	- [Omero](https://omero.readthedocs.io/en/stable/) Image + metadata hub to look at the images
    - [Long-term archive storage](https://en.wikipedia.org/wiki/Research_data_archiving) to check for data completion and process
- TA usually uses:
    - [Internal project study registration](https://en.wikipedia.org/wiki/EGroupware) especially the schedule 
    - [ELN](https://en.wikipedia.org/wiki/Electronic_lab_notebook) e.g. [RSpace](https://github.com/rspace-os) & Inventory to protocol daily work
- DC usually uses:
    - [Internal project study registration](https://en.wikipedia.org/wiki/EGroupware) especially the schedule to book instruments or invite subjects] 
    - [ELN](https://en.wikipedia.org/wiki/Electronic_lab_notebook) e.g. [RSpace](https://github.com/rspace-os) & Inventory to protocol daily work and plans
	- [Omero](https://omero.readthedocs.io/en/stable/) Image + metadata hub to check data quality and create visualizations
	- [Long-term archive storage](https://en.wikipedia.org/wiki/Research_data_archiving) to process the data

After linking:
- PI: 
	- in the [ELN](README.md#ELN%20(e.g.%20RSpace,%20elabFTW)%20&%20inventory) that the DC has scanned images and can view them with the [link to omero](README.md#Omero%20Image%20&%20metadata%20hub); 
	- asking ‘how the aquise is running’ ([project registration schedule](README.md#Internal%20project%20study%20registration)) or whether all data has already been recorded ([omero](README.md#Omero%20Image%20&%20metadata%20hub)) is unnecessary, 
	- as is counting the data records on the [long-term storage](README.md#long-term%20archive%20storage).
- TA: 
	- can see if images have already been scanned [ELN](README.md#ELN%20(e.g.%20RSpace,%20elabFTW)%20&%20inventory)
	- can see when new subjects will arrive or working will be necessary ([project registration schedule](README.md#Internal%20project%20study%20registration))
	- can follow what the study is about and how analysis is progressing [ELN](README.md#ELN%20(e.g.%20RSpace,%20elabFTW)%20&%20inventory)
- DC: 
	- can immediately recognise whether a TA's work is ready to start taking pictures [ELN](README.md#ELN%20(e.g.%20RSpace,%20elabFTW)%20&%20inventory)
	- the linking of [omero](README.md#Omero%20Image%20&%20metadata%20hub) and [long-term storage](README.md#long-term%20archive%20storage) makes it possible 
		- to get the absolute links to the data very quickly, even if there are a lot of files on the network drive and the display of the paths would take too long, 
		- links are also arranged subject-specifically and it can be iterated over the data of all subjects for group analyses without searching for the files on the network storage

