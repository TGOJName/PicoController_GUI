# PicoController_GUI
This is a project to construct a control GUI for Newport (previously named New Focus) [8742](https://www.newport.com/p/8742) picomotor controller that allows control through a gaming console (only Xbox model is tested) for [Laboratory of Exotic Molecules and Atoms](https://www.garciaruizlab.com/).

Execute `picomotor_GUI.py` to run the program; `picomotor_terminal_based.py` is the non-GUI version used for debugging.

## Author Info:
**Created by:** Juntian "Oliver" Tu  
**E-mail:** [juntian@umd.edu](mailto:juntian@umd.edu)  
**Address:** 2261 Atlantic Building, 4254 Stadium Dr, College Park, MD 20742

## Environment Requirement
The project is developed in `Python 3` and based on NewPort's [**PicomotorApp**](https://www.newport.com/p/8742) under 64-bit Windows environment. Other modules included are: [`inputs`](https://pypi.org/project/inputs/), [`PyUSB`](https://pypi.org/project/pyusb/), and [`PyQt5`](https://pypi.org/project/PyQt5/).

The program is designed to work with one 8742 controller and one gaming console.

## Acknowledgements:
Thanks to **Ben Hammel** whose [`python_newport_controller`](https://github.com/bdhammel/python_newport_controller) provides the basic skeleton for this program.