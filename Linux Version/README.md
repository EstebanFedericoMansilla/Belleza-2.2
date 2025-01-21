# Belleza

Este es el paquete para Linux **Belleza**, una aplicación de animación 2D cuadro a cuadro sencilla.

## Autor
- **Esteban Federico Mansilla**

## Mantenedor del paquete para Quirinux
- **Charlie Martínez**

## Paquete compatible con
- Debian
- Devuan
- Derivadas

## Compilación del paquete .deb

1) Descargar la carpeta belleza_2.2.0_all
2) dpkg -b belleza_2.2.0_all

## Instalación

### Para Quirinux:
- Instalación disponible desde el **Centro de Software**.

### Otras distribuciones:

Descargar el instalador .deb desde:

[https://repo.quirinux.org/pool/main/b/belleza/]

Si su distribución incluye alguna herramienta gráfica preinstalada, basta con hacer doble clic sobre el fichero `belleza_2.2.2_all.deb`.

### Instrucciones para Ubuntu:

1. Sitúese en el directorio donde se encuentra el fichero y utilice el siguiente comando:

   ```bash
    sudo apt install ./belleza_2.2.2_all.deb
    ```

2. Después de la instalación, la aplicación estará disponible en el menú de aplicaciones bajo la categoría **Animación** en Quirinux o **Graphics** en las demás distribuciones.

### Instalación por comandos para otras distros de base Debian:

1. Sitúese en el directorio donde se encuentra el fichero y utilice el siguiente comando con `sudo` o `su root` según su distribución:

   ```bash
    dpkg -i install ./belleza_2.2.2_all.deb
    ```

2. Después de la instalación, la aplicación estará disponible en el menú de aplicaciones bajo la categoría **Animación** en Quirinux o **Graphics** en las demás distribuciones.

## Uso

1. Inicie la aplicación desde el menú de aplicaciones o mediante el comando:

    ```bash
    belleza
    ```

2. Si desea crear un nuevo proyecto de animación, seleccione **"Nuevo Proyecto"** en el menú principal. La aplicación le permitirá dibujar y animar imágenes cuadro por cuadro.

3. Para exportar su proyecto, use las opciones disponibles en el menú **"Exportar"**, donde podrá guardar sus animaciones como imágenes o videos.

## Dependencias

El paquete Belleza requiere las siguientes dependencias:

- python3-pyqt6
- python3-numpy
- python3-scipy
- python3-pil
- ffmpeg (para exportar videos)

## Licencia

Este programa es de código abierto.

## Más información

Puede encontrar el código fuente, más información y detalles sobre el proyecto en:

[https://github.com/EstebanFedericoMansilla](https://github.com/EstebanFedericoMansilla)
