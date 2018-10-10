# Shenmue-Export-Tools
Tools for Exporting Meshes from Shenmue for Blender and Noesis Under MIT License

## Noesis

<b>Installation</b>

To install the Noesis plugin copy ```fmt_kion_mt5.py``` and ```inc_powervr.py``` into the noesis ```plugins/python``` folder. From there the plugin will recognize the .mt5 file extension from the Shenmue game data. ```fmt_kion_mt5.py``` contains the logic for reading the actual files. ```inc_powervr.py``` contains tools for reading PVR files, including some of the twiddled rectangluar images that are unique to Shenmue. The ```inc_powervr.py``` extension is set to .kvm, as to not overwrite Noesis's internal PVR handling for other textures.

Also a quick note is that Shenmue uses mirrored texture wrapping. So the textures on wheels and bikes will be displayed incorrectly. I'm not sure if this functionalinty has been added to the Noesis API, or not. But this bug can be ammeded if it is, or if there is a better method of clamping and repeating that I am not aware of.

<b>Screenshots</b>

![Shenmue Noesis 01](https://i.imgur.com/OgCfaYV.jpg)
![Shenmue Noesis 02](https://i.imgur.com/OgCfaYV.jpg)

## Blender

For some reason I decided to punish myself by attempting to write a Blender Plugin. The functionality is the same as the Noesis plugin, as I simply translated the Noesis Plugin to work with Blender. Since information on writing a Blender import plugin can be hard to come by, maybe this can act as an example.

<b>Installation</b>

The ```io_mesh_hcm``` needs to be copied into the ```C:\Users\%your_user%\AppData\Roaming\Blender Foundation\Blender\2.xx\scripts\addons\``` and then enabled from the ```User Preferences``` menu. From there you can goto File -> Import "Shenmue Model (mt5)". One really important aspect to mention about the Blender Plugin, is that if the textures for a given .mt5 model is not in the same source folder, textures will not be applied and you will end up with an invisble model.

For exporting textures as png files with the correct name, please use the included ```PythonPVR``` included in this repository.

<b>Screenshots</b>

![Shenmue Blender 01](https://i.imgur.com/1JJ7m1g.png)
![Shenmue Blender 02](https://i.imgur.com/9uBF3Ux.png)

## PythonPVR

The PythonPVR folder contains a set of tools, written in Python to read PVR images (thus the name). In practicality, it's very similar to the Noesis PVR tools included with the Noesis Plugin, but isolated to run independently on its own.

<b>Installation</b>

Download the repository zip and extract "PythonPVR" to its own directory. Copy a .pvm or .mt5 file to the PythonPVR folder (with __main__.py), for example "Map01.MT5". Run the program with ```python __main.py__ Map01.MT5```. The textures internal to the .mt5 file will be exported to the "output" folder included in the directory. Copy the source .mt5 file and the resulting .pngt files from the output folder into a new folder, and then you will be able to use those files with the Blender plugin.

![Shenmue Python PVR](https://i.imgur.com/v7t8AhQ.png)

## License

MIT License
