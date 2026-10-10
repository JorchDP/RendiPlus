# RendiPlus

Optimizador de PC para Windows y macOS, hecho en Python.

## Descargar

Descarga la última versión desde la sección **Releases** de este repositorio:

- **Windows:** `RendiPlus-Windows.zip`. Descomprímelo y abre `RendiPlus.exe`.
- **Mac:** `RendiPlus-Mac.zip`. Descomprímelo y abre `RendiPlus.app`.

Como la app todavía no tiene firma digital, la primera vez Windows puede mostrar
"Windows protegió su PC". Haz clic en **Más información → Ejecutar de todas formas**.
En Mac: clic derecho sobre la app → **Abrir**.

## Cómo abrirlo desde el código

1. Instala lo necesario (solo la primera vez):
   ```
   py -m pip install -r requirements.txt
   ```
   En Mac: `python3 -m pip install -r requirements.txt`
2. Abre la app:
   ```
   py app.py
   ```
   En Mac: `python3 app.py`

Algunas funciones (temporales de Windows, programas de inicio de todos los usuarios,
programación de GPU, puntos de restauración) necesitan permisos de administrador.
Usa el botón **Abrir como administrador** del menú lateral.

## Crear el programa instalable

- **Windows:** doble clic en `construir_windows.bat`. El resultado queda en la carpeta
  `dist\RendiPlus` (abre `RendiPlus.exe`). Se arma como carpeta porque así abre mucho más rápido
  que un .exe de un solo archivo.
- **Mac:** `bash construir_mac.sh`. El resultado queda en `dist/RendiPlus.app`.
- **Automático con GitHub:** si subes el proyecto a GitHub, el flujo `.github/workflows/compilar.yml`
  compila las versiones de Windows y Mac. Al crear una etiqueta de versión (por ejemplo `v1.1`),
  las publica en la sección *Releases*.

## Qué hace cada sección

| Sección | Qué hace |
|---|---|
| Panel | Uso en vivo de CPU, RAM y GPU, puntaje de salud, discos y especificaciones |
| Limpieza | Temporales, cachés de navegadores y apps, papelera, Windows Update, archivos grandes |
| Inicio y procesos | Activa o desactiva programas que arrancan solos; cierra apps pesadas |
| Perfiles | Rendimiento, Equilibrado y Ahorro: plan de energía, modo de juego, transparencias y apps en segundo plano |
| Seguridad | Controla Microsoft Defender: estado, análisis, firmas, amenazas y firewall. En Mac, XProtect y compañía |
| Recomendaciones | Revisa tu hardware, configuración y seguridad, y sugiere la calidad gráfica para tus juegos |
| Historial | Registro de cada cambio, con opción de deshacerlo o restaurar todo |
| Configuración | Temas (Marino, Grafito, Claro), abrir con Windows, bandeja del sistema y sensores |

### Temperatura del procesador en Windows

Windows no entrega esa temperatura por sí solo. Abre
[LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases)
como administrador y RendiPlus la leerá automáticamente.

## Cómo está organizado

```
RendiPlus/
├── app.py                  Ventana, menú lateral y datos compartidos
├── motores/                Lo que hace el trabajo (sin interfaz)
│   ├── sistema.py          Comandos, registro de Windows, permisos, archivos de datos
│   ├── hardware.py         Diagnóstico de componentes y uso en vivo
│   ├── limpieza.py         Análisis y limpieza de archivos basura
│   ├── inicio.py           Programas de inicio y procesos
│   ├── perfiles.py         Perfiles y ajustes de Windows / Mac
│   ├── recomendaciones.py  Reglas, puntaje de salud y calidad gráfica sugerida
│   ├── seguridad.py        Microsoft Defender, firewall y protección de macOS
│   ├── escritorio.py       Bandeja del sistema, inicio con Windows, una sola instancia
│   └── historial.py        Registro de cambios y deshacer
├── interfaz/               Lo que ves en pantalla
│   ├── tema.py             Colores, tipografías y piezas visuales
│   └── pagina_*.py         Una página por sección
├── recursos/               Ícono de la app
└── .github/workflows/      Compilación automática en GitHub
```

## Seguridad

- La limpieza solo toca carpetas de una lista fija, nunca tus documentos, y salta archivos en uso.
- Los archivos grandes solo se muestran; nunca se borran automáticamente.
- Los programas de inicio se desactivan igual que en el Administrador de tareas: no se borran.
- Cada cambio de configuración guarda su valor anterior y se puede deshacer desde Historial.
- RendiPlus no instala un antivirus propio ni apaga el de Windows: solo consulta y usa Microsoft Defender.
- El historial y la configuración se guardan en `%APPDATA%\RendiPlus` (Windows) o
  `~/Library/Application Support/RendiPlus` (Mac).

## Licencia

Copyright (c) 2026 JorchDP. Todos los derechos reservados.
Puedes descargar y usar RendiPlus gratis, pero no copiar, modificar ni redistribuir su
código sin permiso. Revisa [LICENSE](LICENSE) y [LICENCIAS_TERCEROS.md](LICENCIAS_TERCEROS.md).
