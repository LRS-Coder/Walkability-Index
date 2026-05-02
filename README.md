[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/LRS-Coder/Walkability-Index/HEAD?urlpath=lab)

# Walkability-Index

The Walkability-Index program is designed to download, transform, and visualise building-related data
for towns and cities within Northern Ireland. The buildings are coloured according to their walkability
score, based on amenities accessible within a specified walking time measured along the location’s walking
network. The overall walkability score is derived from weighted groups of amenities, with higher weights
assigned to more desirable amenities such as public transport. The purpose of this program is to highlight
towns, cities, or areas within them where walkability could be improved, consequently enhancing the
quality of life of residents.

## Install and Run Program Locally

### Install Git and Anaconda 

In order to download and run the program locally, `git` and `conda` must be installed on your computer. Instructions for installing git can be found [here](https://git-scm.com/downloads), and instructions for installing Anaconda can be found [here](https://docs.anaconda.com/anaconda/install/).

Once you have `git` and `conda` installed open your command prompt or terminal and run the following commands:

### Clone Repository

```python
git clone https://github.com/LRS-Coder/Walkability-Index.git
cd Walkability-Index
```

### Activate Environment

```python
conda env create -f environment.yml
conda activate walkability
```

### Run Program

```python
python main.py
```

## Run in Binder

Click on the Binder badge at the top of the README.

Once JupyterLab has loaded open the terminal.

In the terminal type:
```bash
python main.py
```
**Note:** When running the program in binder, maps will not automatically open after creation. They are saved as '.html' (interactive) or '.png' (static) files in the data folder and can be viewed by clicking on the relevant file.

## License

[MIT](https://github.com/LRS-Coder/Walkability-Index/blob/main/LICENSE)

## Requirements

- python
- osmnx
- networkx
- geopandas
- folium
- pyproj
- shapely
- pandas
- branca
- matplotlib
