# Belleza (versión para Linux)

Este es el paquete **Belleza**, una aplicación de animación 2D cuadro a cuadro sencilla.

**Autor:** Esteban Federico Mansilla.  
**Mantenedor del paquete para Quirinux:** Charlie Martínez.  
**Compatibilidad:** Paquete compatible con Debian, Devuan y derivadas.

---

## Instalación

### Para Quirinux

Instalación disponible desde el Centro de Software.

### Para otras distribuciones

Si su distribución incluye alguna herramienta gráfica preinstalada, basta con hacer doble clic sobre el fichero `belleza_2.2.2_all.deb`.

### Instalación por comandos

Sitúese en el directorio donde se encuentra el fichero y utilice el siguiente comando con `sudo` o `su` según su distribución:

```bash
apt install ./belleza_2.2.2_all.deb
```

Después de la instalación, la aplicación estará disponible en el menú de aplicaciones bajo la categoría **"Animación"** en Quirinux o **"Graphics"** en las demás distribuciones.

---

## Uso

1. Inicie la aplicación desde el menú de aplicaciones o mediante el comando:

    ```bash
    belleza
    ```

2. Para crear un nuevo proyecto de animación, seleccione **"Nuevo Proyecto"** en el menú principal. La aplicación le permitirá dibujar y animar imágenes cuadro por cuadro.

3. Para exportar su proyecto, use las opciones disponibles en el menú **"Exportar"**, donde podrá guardar sus animaciones como imágenes o videos.

---

## Atajos de teclado

### Herramientas principales
- **1**: Herramienta lápiz.  
- **2**: Herramienta borrador.  
- **3**: Herramienta cubo.  
- **4**: Herramienta de selección.  
- **5**: Selector de color.  
- **6**: Alternar piel de cebolla.

### Configuración de herramientas
- **+**: Aumentar tamaño del lápiz.  
- **-**: Disminuir tamaño del lápiz.

### Edición y navegación
- **Ctrl + Z**: Elimina trazos.  
- **Ctrl + Y**: Rehace trazos eliminados.  
- **Ctrl + C**: Copia un fotograma.  
- **Ctrl + V**: Pega un fotograma.  
- **F5**: Duplica un fotograma.  
- **Control + scroll del mouse**: Zoom (acercar/alejar).  
- **Alt + scroll**: Mover horizontalmente.  
- **Shift + scroll**: Mover verticalmente.  
- **Botón secundario**: Opciones de agregado, copiado y pegado de capas y fotogramas, así como para subir o bajar dibujos en el lienzo.  
- **Flechas izquierda/derecha**: Moverse entre fotogramas.

### Atajos del menú Archivo
- **Ctrl + O**: Abrir archivo.  
- **Ctrl + S**: Guardar archivo.  
- **Ctrl + I**: Importar imagen.

### Barra espaciadora
- Reproduce y detiene la animación (debe habilitarse primero con el botón de reproducir animación).  
- Repite acciones de agregar y eliminar fotogramas.  
- Acelera el flujo de trabajo al omitir los diálogos de confirmación al agregar o eliminar fotogramas.

---

## Dependencias

El paquete **Belleza** requiere las siguientes dependencias:

- `python3-pyqt6`
- `python3-numpy`
- `python3-scipy`
- `python3-pil`
- `python3-pyqt6`
- `ffmpeg` (para exportar videos)

---

## Licencia

Este programa es de código abierto.

---

## Más información

Puede encontrar el código fuente, más información y detalles sobre el proyecto en:

[GitHub - EstebanFedericoMansilla](https://github.com/EstebanFedericoMansilla)
