# The Chempiler

This repo contains the software suite required to control a Chemputer rig.

## Getting Started

Pull the repo and install the requirements file. You might also want to install [yEd](https://www.yworks.com/products/yed/download#download) for editing the GraphML files. I personally recommend using [Pycharm](https://www.jetbrains.com/pycharm/download/#section=windows) as Python IDE, and this repo contains a settings file for colour markup for the ChASM file type. However, if you feel like using something else, I'm not stopping you.

### Prerequisites

* Python 3.6
  * networkx 1.10
  * numpy
  * ply
  * pyserial
  * OpenCV

### Installing

The Chempiler suite comes with a requirements file, so to install all required Python packages simply open a command prompt in the root folder and type:

```
pip install -r requirements.txt
```

This should take care of everything. If for some reason anything behaves funnily, I noted the latest versions of every package I tested the Chempiler with in the requirements file.

### Loading the ChASM markup in Pycharm

The root directory contains a file **PyCharm_ChASM_settings.jar** which holds markup rules for ChASM to make it a tad easier to read. To load the settings, open Pycharm, and click **File** -> **Import Settings...** In the popup prompt navigate to the settings file, and click OK. Make sure all boxes are ticked, and click OK again. Be advised that this restarts Pycharm without prompting you! Once the IDE has restarted, you should get nice syntax highlighting for your ChASM files.

## Project structure

This repository contains the following subfolders and files in the root folder:

```
.
├── client                          # Contains the Chempiler client script, log files and crash dump
├── docs                            # Documentation files
├── platform_server                 # Contains the source files
├── experiments                     # Contains graph and ChASM files for the various tested syntheses
├── LICENSE.txt
├── PyCharm_ChASM_settings.jar      # Contains syntax highlighting settings for ChASM in Pycharm
├── requirements.txt                # Python requirements file
└── README.md
```

## client

This subfolder contains mainly the Chemputer client script. This script actually runs the platform. It first sets up all the logging to make sure data goes where it ought to be. Then it prompts the user to provide three things:

* An experiment code
* A path to a graph file
* A path to a ChASM file

It also queries the following things:

* Should a video be recorded?
* Should it read the crash dump (i.e. continue from the last known state)?
* Is this a simulation?

Once all those pieces of information are provided, the client instantiates a Chemputer object, and calls `run_platform()`.

The **client** subfolder also contains subfolders for log files (both text and video) as well as the crash dump.

## docs

This folder contains Sphinx documentation. The actual HTML output is [here](/docs/_build/html/index.html).

## platform_server

This subfolder contains all the source code in a hopefully somewhat logical order.

```
.
├── ...
├── platform_server
│   ├── core                    # Contains the main Chempiler class
│   ├── modules                 # Contains the various device drivers
|   |   ├── pv_api              # API for the pumps and valves
|   |   └── serial_labware      # Drivers for serial devices
│   ├── sims                    # Contains the device simulation
│   └── tools                   # Contains various helper scripts
|       ├── module_execution    # Contains the Executioners for the modules
│       └── parsing             # Contains the PLY parser
└── ...
```

### core

This subfolder contains only one file, **chempiler.py**, which contains the main Chempiler class.

### modules

This subfolder contains all device drivers. This includes the API for the pumps and valves and all the devices that use serial communication. The serial_labware subfolder contains a parent class **SerialDevice** and drivers for a whole load of other devices. For more info on the SerialLabware project check the appropriate repo.

### sims

This subfolder contains a single file which holds all simulated device classes.

### tools

This subfolder holds all the techincal stuff under the hood. **chempiler_setup.py** parses the graph, instantiates all the devices and gets the platform ready for use. **cmd_execution.py** is a command dispatcher which delegates tasks to the appropriate Executioners. **constants.py** holds a number of global constants and literals. Those are read only, and shouldn't require editing. **vlogging.py** deals with recording log videos.

The subfolder **module_execution** contains all the Executioners. Those are wrapper classes that sit on top of the device drivers. They are aware of the graph, and expose a unified interface to the command dispatcher which sits on top of the Executioners. This way different pieces of hardware of the same family (such as different brands of stirrers or chillers) can be used without having to change the high-level code.

The subfolder **parsing** contains the ChASM parser. For details on why and how have a look at the [PLY documentation](http://www.dabeaz.com/ply/ply.html).

## experiments

This subfolder contains the graph and ChASM files of all the various syntheses performed on the various rigs. Future experiments should also go here.

## Authors
* **Hessam Mehr** - *Current contributor, developing new features
* **Matthew Craven** - *Software development for the chemputer, developing new features
* **Sebastian Steiner** - *Previous contributor project architecture, to ongoing development, debugging, current curator*
* **Graham Keenan** - *Initial work, most of the actual coding*
* **Jakob Wolf** - *Authored the Sildenafil and Diazirine syntheses, debugging*
* **Jaroslaw Granda** - *Current contributor - authored the Rufinamide synthesis*

## Acknowledgments

* Stefan Glatzel (Cronin Group member)
* Anna Andreou (Cronin Group member)
* Gerardo Aragon (Cronin Group member)
* Leroy (Lee) Cronin - PI for the project and inventor of the abstraction
