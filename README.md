# buildup-data-transformation
Functions for extracting and transforming data from Tascomi and Exacom.

## Setup
Create a `.env` file with API keys for accessing Tascomi Planning and Tascomi Building Control, structured as follows:
```
tascomi_planning_public=
tascomi_planning_private=
tascomi_build_public=
tascomi_build_private=
```

## Contents
### etl_functions

- **APIClient.py** - The Tascomi API Client rewritten to work with Python 3.
- **exacom_utils.py** - Functions for transforming Exacom exports into the phase data schema
- **tascomi_utils.py** - Functions for extracting and cleaning data from Tascomi systems, as well as matching Tascomi Planning and Tascomi Building Control applications

### Proof of concept
`data integration example.ipynb` demonstrates how to generate scheme- and phase-level data according to the BuildUp database schema. Data from one planned development (the Patchworks/Homebase development) is used as an example. 

