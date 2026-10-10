# Licencias de terceros

RendiPlus usa las siguientes bibliotecas. Cada una mantiene su propia licencia, que
aplica a esa biblioteca y no al código de RendiPlus.

| Biblioteca | Para qué la usa RendiPlus | Licencia |
|---|---|---|
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | Interfaz gráfica | MIT |
| [psutil](https://github.com/giampaolo/psutil) | Uso de CPU, RAM, discos y procesos | BSD 3-Clause |
| [nvidia-ml-py](https://pypi.org/project/nvidia-ml-py/) | Uso y temperatura de GPUs NVIDIA | BSD |
| [pystray](https://github.com/moses-palmer/pystray) | Ícono en la bandeja del sistema (Windows) | LGPL v3 |
| [Pillow](https://github.com/python-pillow/Pillow) | Imagen del ícono de la bandeja | MIT-CMU (HPND) |
| [pywin32](https://github.com/mhammond/pywin32) | Lectura de temperaturas en Windows | PSF |
| [PyInstaller](https://github.com/pyinstaller/pyinstaller) | Crear el programa instalable | GPL v2 con excepción para el bootloader (permite distribuir programas cerrados) |

## Sobre pystray (LGPL v3)

pystray se usa sin modificaciones. Su código fuente y su licencia están disponibles en
https://github.com/moses-palmer/pystray.

## Programas externos

RendiPlus puede leer temperaturas desde [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor)
(MPL 2.0) si el usuario lo instala y lo abre por su cuenta. LibreHardwareMonitor no
viene incluido en RendiPlus.
