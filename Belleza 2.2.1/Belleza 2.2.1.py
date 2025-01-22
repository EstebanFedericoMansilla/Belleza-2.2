import os
import tempfile
import shutil
import json
import gc
import weakref
import numpy as np
from scipy.interpolate import splprep, splev

from PyQt6.QtCore import Qt, QBuffer, QByteArray, QIODevice
from PyQt6.QtGui import QImage

from PyQt6.QtCore import (
    QBuffer, QByteArray, QIODevice, Qt, QSize, QPoint, 
    QPointF, QTimer, QRect
)

from PyQt6.QtGui import (
    QImage, QShortcut, QKeySequence, QCursor, QPixmap, 
    QPen, QPainterPath, QPainter, QColor, QAction, QIcon
)

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QApplication, QMainWindow, 
    QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem, 
    QSlider, QScrollArea, QGridLayout, QColorDialog, QMessageBox, 
    QFileDialog, QMenu, QInputDialog
)
import gc
import weakref
from PyQt6.QtCore import Qt, QBuffer, QByteArray, QIODevice
from PyQt6.QtGui import QImage

class Layer:
    def __init__(self, width: int, height: int, index: int = 0, name: str = "Nueva Capa"):
        """Inicializa una nueva capa con dimensiones específicas.
        
        Args:
            width (int): Ancho de la capa en píxeles
            height (int): Alto de la capa en píxeles
            index (int): Posición de la capa en la pila
            name (str): Nombre de la capa
        """
        self.index = index
        self.width = width
        self.height = height
        self.name = name
        self.visible = True
        self.opacity = 100
        self.locked = False
        self.selected = False
        
        # Gestión de frames
        self.frames = {}
        self._frame_cache = weakref.WeakValueDictionary()
        
        # Gestión del historial
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo_states = 20
        
        self._init_first_frame()

    def _init_first_frame(self):
        """Inicializa el primer frame de la capa."""
        try:
            frame = QImage(self.width, self.height, QImage.Format.Format_ARGB32_Premultiplied)
            if frame.isNull():
                raise RuntimeError("Error al crear QImage")
            frame.fill(Qt.GlobalColor.transparent)
            self.frames[0] = frame
            self._save_state()
        except Exception as e:
            raise RuntimeError(f"Error al inicializar el primer frame: {str(e)}")

    def _save_state(self):
        """Guarda el estado actual para operaciones de deshacer/rehacer."""
        try:
            if self.frames:
                frame_copies = {k: v.copy() for k, v in self.frames.items()}
                if len(self.undo_stack) >= self.max_undo_states:
                    self.undo_stack.pop(0)
                self.undo_stack.append(frame_copies)
                self.redo_stack.clear()
        except Exception as e:
            print(f"Advertencia: Error al guardar el estado: {str(e)}")

    def add_frame(self, index: int = None) -> int:
        """Añade un nuevo frame a la capa."""
        try:
            new_frame = QImage(self.width, self.height, QImage.Format.Format_ARGB32_Premultiplied)
            if new_frame.isNull():
                raise RuntimeError("Error al crear nuevo frame")
            
            new_frame.fill(Qt.GlobalColor.transparent)
            new_index = index if index is not None else (max(self.frames.keys()) + 1 if self.frames else 0)
            self.frames[new_index] = new_frame
            self._save_state()
            return new_index
        except Exception as e:
            raise RuntimeError(f"Error al añadir frame: {str(e)}")

    def get_frame(self, index: int) -> QImage:
        """Obtiene un frame en el índice especificado."""
        if index not in self.frames:
            self.add_frame(index)
        return self.frames[index]

    def update_frame(self, index: int, image: QImage):
        """Actualiza un frame con nueva imagen."""
        if not isinstance(image, QImage) or image.isNull():
            raise ValueError("Imagen inválida proporcionada para actualización")
        
        try:
            if index not in self.frames:
                self.add_frame(index)
            self.frames[index] = image.copy()
            self._save_state()
        except Exception as e:
            raise RuntimeError(f"Error al actualizar frame: {str(e)}")

    def copy_frame(self, frame_index):
        """Copia un frame en el índice especificado."""
        if frame_index in self.frames:
            return self.frames[frame_index].copy()
        return None

    def undo(self):
        """Deshace la última acción en esta capa."""
        if len(self.undo_stack) > 1:
            current_state = self.undo_stack.pop()
            self.redo_stack.append(current_state)
            previous_state = self.undo_stack[-1]
            self.frames = {k: v.copy() for k, v in previous_state.items()}
            return True
        return False

    def redo(self):
        """Rehace la última acción deshecha."""
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append({k: v.copy() for k, v in state.items()})
            self.frames = {k: v.copy() for k, v in state.items()}
            return True
        return False

    def to_dict(self) -> dict:
        """Convierte la capa a diccionario para serialización."""
        layer_data = {
            'index': self.index,
            'width': self.width,
            'height': self.height,
            'visible': self.visible,
            'opacity': self.opacity,
            'name': self.name,
            'locked': self.locked,
            'selected': self.selected,
            'frames': {}
        }
        
        for frame_idx, frame in self.frames.items():
            try:
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                success = frame.save(buffer, "PNG")
                if not success:
                    raise RuntimeError(f"Error al guardar el frame {frame_idx}")
                
                layer_data['frames'][str(frame_idx)] = buffer.data().toBase64().data().decode()
                buffer.close()
            except Exception as e:
                raise RuntimeError(f"Error al serializar el frame {frame_idx}: {str(e)}")
        
        return layer_data

    @classmethod
    def from_dict(cls, data: dict) -> 'Layer':
        """Crea una nueva capa desde datos de diccionario."""
        try:
            layer = cls(
                width=data['width'],
                height=data['height'],
                index=data['index'],
                name=data['name']
            )
            
            layer.visible = data['visible']
            layer.opacity = data['opacity']
            layer.locked = data['locked']
            layer.selected = data.get('selected', False)
            
            for frame_idx, frame_data in data['frames'].items():
                byte_data = QByteArray.fromBase64(frame_data.encode())
                frame = QImage()
                if not frame.loadFromData(byte_data, "PNG"):
                    raise RuntimeError(f"Error al cargar el frame {frame_idx}")
                layer.frames[int(frame_idx)] = frame
            
            return layer
        except Exception as e:
            raise RuntimeError(f"Error al crear capa desde diccionario: {str(e)}")

    def optimize_memory(self):
        """Optimiza el uso de memoria limpiando recursos."""
        self.undo_stack = self.undo_stack[-self.max_undo_states:]
        self.redo_stack.clear()
        self._frame_cache.clear()
        gc.collect()

    def copy(self):
        """Crea una copia de esta capa."""
        new_layer = Layer(
            width=self.width,
            height=self.height,
            index=self.index,
            name=self.name + " (copia)"
        )
        new_layer.frames = {k: v.copy() for k, v in self.frames.items()}
        new_layer.visible = self.visible
        new_layer.opacity = self.opacity
        new_layer.locked = self.locked
        return new_layer

class AnimationCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Propiedades básicas
        self.background_color = QColor("#c7c7c7")
        self.current_layer = 0
        self.current_frame = 0
        self.layers = []
        self.selection_tool = SelectionTool()
        self.current_tool = "pencil"
        self.smoothing_factor = 50
        self.scale_factor = 1.0
        self.offset = QPoint(0, 0)
        self.last_pan_pos = None
        self.setFixedSize(800, 600)
        self.drawing = False
        self.last_point = None
        self.pen_color = QColor(Qt.GlobalColor.black)
        self.pen_size = 3
        self.pen_opacity = 255
        
        # Configuración del widget
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        
        # Onion skin properties
        self.onion_skin_enabled = False
        self.onion_skin_frames = 1
        self.onion_skin_opacity = 30
        self.stroke_manager = StrokeManager(self)
        # Inicializar cursores personalizados
        self.setup_cursors()
        
        # Initialize canvas
        self._init_canvas()

    def setup_cursors(self):
        """Configura los cursores para todas las herramientas"""
        cursor_size = 28
        
        # Crear cursores para diferentes fondos
        self.light_cursor = self._create_cursor(cursor_size, Qt.GlobalColor.black)
        self.dark_cursor = self._create_cursor(cursor_size, Qt.GlobalColor.white)
        
        # Establecer cursor inicial
        self.custom_cursor = self.light_cursor
        self.setCursor(self.custom_cursor)

    def _create_cursor(self, size, color):
        """Crea un cursor personalizado con área central transparente"""
        cursor_image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        cursor_image.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(cursor_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Configurar el color de contraste
        contrast_color = Qt.GlobalColor.white if color == Qt.GlobalColor.black else Qt.GlobalColor.black
        
        # Definir dimensiones
        center = size // 2
        gap = 6  # Espacio más grande en el centro
        line_start = 2
        line_end = size - 2
        
        # Función helper para dibujar líneas segmentadas
        def draw_segmented_lines(pen_color, width):
            pen = QPen(pen_color)
            pen.setWidth(width)
            painter.setPen(pen)
            
            # Líneas horizontales (izquierda y derecha del centro)
            painter.drawLine(line_start, center, center - gap, center)
            painter.drawLine(center + gap, center, line_end, center)
            
            # Líneas verticales (arriba y abajo del centro)
            painter.drawLine(center, line_start, center, center - gap)
            painter.drawLine(center, center + gap, center, line_end)
        
        # Dibujar borde exterior (contraste)
        draw_segmented_lines(contrast_color, 5)
        
        # Dibujar líneas interiores
        draw_segmented_lines(color, 3)
        
        painter.end()
        
        cursor_pixmap = QPixmap.fromImage(cursor_image)
        return QCursor(cursor_pixmap, center, center)

    def update_cursor(self, pos):
        """Actualiza el cursor basado en el color del fondo"""
        if not self.layers or self.current_layer >= len(self.layers):
            return
            
        layer = self.layers[self.current_layer]
        if self.current_frame not in layer.frames:
            return
            
        # Obtener color bajo el cursor
        frame = layer.frames[self.current_frame]
        pixel_color = frame.pixelColor(int(pos.x()), int(pos.y()))
        
        # Calcular luminosidad
        luminance = (0.299 * pixel_color.red() + 
                    0.587 * pixel_color.green() + 
                    0.114 * pixel_color.blue())
        
        # Cambiar cursor según luminosidad
        self.custom_cursor = self.dark_cursor if luminance < 128 else self.light_cursor
        self.setCursor(self.custom_cursor)

    def mouseMoveEvent(self, event):
        # Actualizar cursor según el color bajo el mouse
        transformed_pos = (event.pos() - self.offset) / self.scale_factor
        self.update_cursor(transformed_pos)
        super().mouseMoveEvent(event)

    def _init_canvas(self):
        first_layer = Layer(800, 600)
        self.layers.append(first_layer)

    def get_current_frame(self):
        if self.layers and self.current_layer < len(self.layers):
            layer = self.layers[self.current_layer]
            if self.current_frame < len(layer.frames):
                return layer.frames[self.current_frame]
        return None

    def set_background_color(self, color):
        self.background_color = color
        self.draw_current_frame()
       
    
    def _draw_point(self, point):
        if not self.layers:
            return
            
        current_layer = self.layers[self.current_layer]
        if current_layer.locked or self.current_frame not in current_layer.frames:
            return
            
        current_frame = current_layer.frames[self.current_frame]
        painter = QPainter(current_frame)
        self._setup_painter(painter)
        painter.drawPoint(point)
        painter.end()
        self.draw_current_frame()  # Cambiar update() por draw_current_frame()

    def _draw_line(self, start, end):
        if not self.layers:
            return
            
        current_layer = self.layers[self.current_layer]
        if current_layer.locked or self.current_frame not in current_layer.frames:
            return
            
        current_frame = current_layer.frames[self.current_frame]
        painter = QPainter(current_frame)
        self._setup_painter(painter)
        painter.drawLine(start, end)
        painter.end()
        self.draw_current_frame()  # Cambiar update() por draw_current_frame()

    def draw_current_frame(self):
        # Crear una imagen temporal para combinar todas las capas
        temp_image = QImage(self.size(), QImage.Format.Format_ARGB32_Premultiplied)
        temp_image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(temp_image)
        
        # Dibujar las capas en orden (de abajo hacia arriba)
        # No necesitamos ordenar por índice, el orden en la lista es suficiente
        for layer in self.layers:
            if layer.visible and layer.frames:
                current_frame = layer.frames.get(self.current_frame, None)
                if current_frame:
                    painter.setOpacity(layer.opacity / 100.0)
                    painter.drawImage(0, 0, current_frame)
        
        painter.end()
        self.current_frame_image = temp_image
        self.update()

    def draw_frame(self, frame_number):
        # Crear una imagen temporal para el frame actual
        temp_image = QImage(self.size(), QImage.Format.Format_ARGB32)
        temp_image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(temp_image)
        
        # Dibujar las capas en orden (de abajo hacia arriba)
        # No necesitamos ordenar por índice, el orden en la lista es suficiente
        for layer in self.layers:
            if layer.visible and frame_number in layer.frames:
                frame_image = layer.frames[frame_number]
                painter.setOpacity(layer.opacity / 100.0)
                painter.drawImage(0, 0, frame_image)
        
        painter.end()
        self.current_frame_image = temp_image
        self.update()


    
    def _draw_point(self, point):
        if not self.layers:
            return
            
        current_layer = self.layers[self.current_layer]
        if current_layer.locked or not current_layer.frames:
            return
            
        if self.current_frame not in current_layer.frames:
            current_layer.add_frame(self.current_frame)
            
        current_frame = current_layer.frames[self.current_frame]
        painter = QPainter(current_frame)
        self._setup_painter(painter)
        painter.drawPoint(point)
        painter.end()
        self.draw_current_frame()

    def _draw_line(self, start, end):
        if not self.layers:
            return
            
        current_layer = self.layers[self.current_layer]
        if current_layer.locked or self.current_frame >= len(current_layer.frames):
            return
            
        current_frame = current_layer.frames[self.current_frame]
        painter = QPainter(current_frame)
        self._setup_painter(painter)
        painter.drawLine(start, end)
        painter.end()
        self.update()

    def _setup_painter(self, painter):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.current_tool == "eraser":
            pen = QPen(Qt.GlobalColor.white)
            pen.setWidth(self.pen_size)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        else:
            pen = QPen(self.pen_color)
            pen.setWidth(self.pen_size)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        painter.setPen(pen)

    

    def set_pen_color(self, color):
        self.pen_color = color

    def set_pen_size(self, size):
        self.pen_size = size

    def set_tool(self, tool):
        self.current_tool = tool

    def set_opacity(self, opacity):
        self.pen_opacity = opacity

    def change_frame(self, frame_index):
        if frame_index >= 0 and self.layers:
            self.current_frame = frame_index
            self.draw_current_frame()  # Usar draw_current_frame en lugar de update

    def undo(self):
        if self.layers and self.current_layer < len(self.layers):
            if self.layers[self.current_layer].undo():
                self.draw_current_frame()
                return True
        return False

    def redo(self):
        if self.layers and self.current_layer < len(self.layers):
            if self.layers[self.current_layer].redo():
                self.draw_current_frame()
                return True
        return False

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                self.undo()
                event.accept()
            elif event.key() == Qt.Key.Key_Y:
                self.redo()
                event.accept()
        # Mantener el código existente para las teclas de dirección
        elif event.key() == Qt.Key.Key_Left:
            if self.current_frame > 0:
                self.current_frame -= 1
                self.draw_current_frame()
                for widget in QApplication.topLevelWidgets():
                    if isinstance(widget, QMainWindow):
                        widget.timeline_widget.update_frame_grid()
                        break
        elif event.key() == Qt.Key.Key_Right:
            if self.layers and self.current_frame < len(self.layers[self.current_layer].frames) - 1:
                self.current_frame += 1
                self.draw_current_frame()
                for widget in QApplication.topLevelWidgets():
                    if isinstance(widget, QMainWindow):
                        widget.timeline_widget.update_frame_grid()
                        break
        event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Apply transformations
        painter.translate(self.offset)
        painter.scale(self.scale_factor, self.scale_factor)
        
        # Draw background with canvas color
        painter.fillRect(self.rect(), QColor("#c7c7c7"))
        
        # Draw onion skin frames if enabled
        if self.onion_skin_enabled:
            # Draw previous frames in red
            for i in range(1, self.onion_skin_frames + 1):
                frame_idx = self.current_frame - i
                if frame_idx >= 0:
                    painter.setOpacity((self.onion_skin_opacity / 100) * (1 - (i - 1) / self.onion_skin_frames))
                    self._draw_onion_frame(painter, frame_idx, QColor(255, 0, 0, 128))
            
            # Draw next frames in blue
            for i in range(1, self.onion_skin_frames + 1):
                frame_idx = self.current_frame + i
                if frame_idx < max(len(layer.frames) for layer in self.layers if layer.frames):
                    painter.setOpacity((self.onion_skin_opacity / 100) * (1 - (i - 1) / self.onion_skin_frames))
                    self._draw_onion_frame(painter, frame_idx, QColor(0, 0, 255, 128))
        
        # Draw current frame layers
        painter.setOpacity(1.0)
        for layer in reversed(self.layers):
            if layer.visible and self.current_frame in layer.frames:
                current_frame = layer.frames[self.current_frame]
                painter.setOpacity(layer.opacity / 100)
                painter.drawImage(0, 0, current_frame)
        
        # Draw current frame image if exists
        if hasattr(self, 'current_frame_image'):
            painter.drawImage(0, 0, self.current_frame_image)
        
        # Draw selection rectangle if active
        if self.current_tool == "selection" and self.selection_tool.selection_rect:
            painter.setPen(QPen(Qt.GlobalColor.blue, 1, Qt.PenStyle.DashLine))
            x, y, w, h = self.selection_tool.selection_rect
            painter.drawRect(x, y, w, h)
    
    def wheelEvent(self, event):
        modifiers = event.modifiers()
        
        # Solo procesar el evento si se presiona una tecla modificadora
        if modifiers & (Qt.KeyboardModifier.ControlModifier | 
                    Qt.KeyboardModifier.AltModifier | 
                    Qt.KeyboardModifier.ShiftModifier):
            
            # Control + scroll para zoom
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                delta = event.angleDelta().y()
                zoom_factor = 1.1 if delta > 0 else 0.9
                new_scale = self.scale_factor * zoom_factor
                
                if 0.1 <= new_scale <= 10.0:
                    mouse_pos = event.position()
                    offset_f = QPointF(self.offset)
                    
                    old_pos = (mouse_pos - offset_f) / self.scale_factor
                    self.scale_factor = new_scale
                    new_pos = (mouse_pos - offset_f) / self.scale_factor
                    
                    delta_pos = (new_pos - old_pos) * self.scale_factor
                    self.offset = QPoint(
                        int(self.offset.x() + delta_pos.x()),
                        int(self.offset.y() + delta_pos.y())
                    )
            
            # Alt + scroll para movimiento horizontal
            elif modifiers & Qt.KeyboardModifier.AltModifier:
                delta = event.angleDelta().x() if event.angleDelta().x() != 0 else event.angleDelta().y()
                pan_speed = -20
                new_x = int(self.offset.x() - (delta / 120) * pan_speed)
                self.offset.setX(new_x)
            
            # Shift + scroll para movimiento vertical
            elif modifiers & Qt.KeyboardModifier.ShiftModifier:
                delta = -event.angleDelta().y()
                pan_speed = 20
                new_y = int(self.offset.y() - (delta / 120) * pan_speed)
                self.offset.setY(new_y)
            
            self.update()
            event.accept()
        else:
            # Si no hay modificadores, dejar que el evento se propague
            event.ignore()
    
    
    def _draw_onion_frame(self, painter, frame_index, tint_color):
        for layer in reversed(self.layers):
            if layer.visible and frame_index in layer.frames:
                frame = layer.frames[frame_index]
                
                # Create tinted copy of the frame
                tinted_frame = QImage(frame.size(), QImage.Format.Format_ARGB32_Premultiplied)
                tinted_frame.fill(Qt.GlobalColor.transparent)
                
                frame_painter = QPainter(tinted_frame)
                frame_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                frame_painter.drawImage(0, 0, frame)
                
                # Apply tint color
                frame_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
                frame_painter.fillRect(tinted_frame.rect(), tint_color)
                frame_painter.end()
                
                # Draw tinted frame
                painter.drawImage(0, 0, tinted_frame)
    
    
    def toggle_onion_skin(self):
        """Toggle onion skin visibility"""
        self.onion_skin_enabled = not self.onion_skin_enabled
        self.update()

    def set_onion_skin_frames(self, frames):
        """Set number of onion skin frames to show"""
        self.onion_skin_frames = max(1, min(5, frames))  # Limit between 1-5 frames
        self.update()

    def set_onion_skin_opacity(self, opacity):
        """Set opacity percentage for onion skin"""
        self.onion_skin_opacity = max(0, min(100, opacity))  # Limit between 0-100%
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            transformed_pos = (event.pos() - self.offset) / self.scale_factor
            
            if self.current_tool == "bucket":
                # Convert position to integer coordinates for flood fill
                point = QPoint(int(transformed_pos.x()), int(transformed_pos.y()))
                target_color = self.get_pixel_color(transformed_pos)
                self._flood_fill(point, target_color, self.pen_color)
                
            elif self.current_tool == "selection":
                if self.selection_tool.selection_rect:
                    x, y, w, h = self.selection_tool.selection_rect
                    if QRect(x, y, w, h).contains(QPoint(int(transformed_pos.x()), int(transformed_pos.y()))):
                        self.selection_tool.start_moving(QPoint(int(transformed_pos.x()), int(transformed_pos.y())))
                    else:
                        self.selection_tool.start_selection(QPoint(int(transformed_pos.x()), int(transformed_pos.y())))
                else:
                    self.selection_tool.start_selection(QPoint(int(transformed_pos.x()), int(transformed_pos.y())))
            else:
                self.drawing = True
                self.current_points = []
                self.current_points.append(transformed_pos)
                self.last_point = transformed_pos
                if self.current_tool != "bucket":
                    self._draw_point(transformed_pos)

    def mouseMoveEvent(self, event):
        transformed_pos = (event.pos() - self.offset) / self.scale_factor
        if self.current_tool == "selection":
            if event.buttons() & Qt.MouseButton.LeftButton:
                if self.selection_tool.moving:
                    self.selection_tool.move_selection(QPoint(int(transformed_pos.x()), int(transformed_pos.y())))
                else:
                    self.selection_tool.update_selection(QPoint(int(transformed_pos.x()), int(transformed_pos.y())))
                self.update()
        else:
            if self.drawing and self.last_point:
                self.current_points.append(transformed_pos)
                current_layer = self.layers[self.current_layer]
                if self.current_frame not in current_layer.frames:
                    current_layer.add_frame(self.current_frame)
                current_frame = current_layer.frames[self.current_frame]
                
                temp_image = current_frame.copy()
                painter = QPainter(temp_image)
                self._setup_painter(painter)
                
                if len(self.current_points) > 2:
                    smooth_path = self.get_smooth_path(self.current_points)
                    painter.drawPath(smooth_path)
                
                painter.end()
                current_layer.frames[self.current_frame] = temp_image
                self.draw_current_frame()
                self.last_point = transformed_pos

    def apply_selection_tool(self):
        if self.current_layer < len(self.layers):
            current_layer = self.layers[self.current_layer]
            if self.current_frame in current_layer.frames:
                frame = current_layer.frames[self.current_frame]
                if self.selection_tool.selection_rect:
                    x, y, w, h = self.selection_tool.selection_rect
                    selected_area = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
                    selected_area.fill(Qt.GlobalColor.transparent)
                    
                    painter = QPainter(selected_area)
                    painter.drawImage(0, 0, frame, x, y, w, h)
                    painter.end()
                    
                    self.selection_tool.selected_content = selected_area
                    current_layer._save_state()
    def move_selected_content(self):
        if self.current_layer < len(self.layers):
            current_layer = self.layers[self.current_layer]  # Get the actual layer object
            if self.current_frame in current_layer.frames and self.selection_tool.selected_content:
                frame = current_layer.frames[self.current_frame]
                new_frame = QImage(frame.size(), QImage.Format.Format_ARGB32_Premultiplied)
                new_frame.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(new_frame)
                painter.drawImage(0, 0, frame)
                
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                x, y, w, h = self.selection_tool.selection_rect
                painter.fillRect(x, y, w, h, Qt.GlobalColor.transparent)
                
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                painter.drawImage(x, y, self.selection_tool.selected_content)
                painter.end()
                
                current_layer.frames[self.current_frame] = new_frame
                current_layer._save_state()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.current_tool == "selection":
                if self.selection_tool.moving:
                    self.move_selected_content()
                else:
                    self.apply_selection_tool()
                self.update()
            elif self.drawing:
                self.drawing = False
                if len(self.current_points) > 1:
                    current_layer = self.layers[self.current_layer]
                    if self.current_frame in current_layer.frames:
                        current_frame = current_layer.frames[self.current_frame]
                        
                        # Create final smooth path
                        smooth_path = self.get_smooth_path(self.current_points)
                        
                        # Draw final path
                        painter = QPainter(current_frame)
                        self._setup_painter(painter)
                        painter.drawPath(smooth_path)
                        painter.end()
                        
                        # Save state for undo/redo
                        current_layer._save_state()
                        self.draw_current_frame()
                
                self.current_points = []
                self.last_point = None

    def get_smooth_path(self, points):
        """
        Creates a smooth path from a list of points using spline interpolation.
        """
        if len(points) < 3:
            path = QPainterPath()
            if points:
                path.moveTo(QPointF(points[0]))
                for point in points[1:]:
                    path.lineTo(QPointF(point))
            return path

        # Usar el mismo muestreo de puntos para mouse y tableta
        if len(points) > 50:
            points = points[::2]  # Tomar uno de cada dos puntos

        # Convert points to numpy arrays
        x = np.array([p.x() for p in points])
        y = np.array([p.y() for p in points])

        # Check if points are not all the same
        if np.std(x) == 0 and np.std(y) == 0:
            path = QPainterPath()
            path.moveTo(QPointF(points[0]))
            return path

        try:
            # Usar el mismo factor de suavizado para ambos dispositivos
            s = self.smoothing_factor * len(points) / 100.0
            
            # Fit spline con los mismos parámetros
            tck, u = splprep([x, y], s=s, k=3)
            
            # Generar la misma cantidad de puntos para la curva
            u_new = np.linspace(0, 1.0, len(points) * 2)
            smooth_points = splev(u_new, tck)

            # Create path with QPointF
            path = QPainterPath()
            path.moveTo(QPointF(smooth_points[0][0], smooth_points[1][0]))
            for i in range(1, len(smooth_points[0])):
                path.lineTo(QPointF(smooth_points[0][i], smooth_points[1][i]))
            
            return path
        except:
            # Fallback to simple path if smoothing fails
            path = QPainterPath()
            path.moveTo(QPointF(points[0]))
            for point in points[1:]:
                path.lineTo(QPointF(point))
            return path

    def _flood_fill(self, start_pos, target_color, replacement_color):
        if not self.layers:
            return
                
        current_layer = self.layers[self.current_layer]
        if current_layer.locked or self.current_frame not in current_layer.frames:
            return
                
        current_frame = current_layer.frames[self.current_frame]
        width = current_frame.width()
        height = current_frame.height()
        
        # Crear una copia del frame actual para trabajar
        working_frame = current_frame.copy()
        
        # Get start pixel color
        start_color = working_frame.pixelColor(start_pos)
        if start_color == replacement_color:
            return
        
        # Create stack for flood fill
        stack = [(start_pos.x(), start_pos.y())]
        visited = set()
        
        # Create painter for drawing
        painter = QPainter(working_frame)
        painter.setPen(QPen(replacement_color))
        
        while stack:
            x, y = stack.pop()
            
            if (x, y) in visited:
                continue
                
            current_color = working_frame.pixelColor(x, y)
            if current_color != start_color:
                continue
                
            painter.drawPoint(x, y)
            visited.add((x, y))
            
            # Check neighboring pixels
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                new_x = x + dx
                new_y = y + dy
                
                if (0 <= new_x < width and 
                    0 <= new_y < height and 
                    (new_x, new_y) not in visited):
                    stack.append((new_x, new_y))
        
        painter.end()
        
        # Actualizar el frame en la capa actual
        current_layer.frames[self.current_frame] = working_frame
        
        # Guardar el estado después de aplicar el flood fill
        current_layer._save_state()
        
        # Actualizar la visualización
        self.draw_current_frame()
    
    def get_pixel_color(self, pos):
        """Helper method to get color at position"""
        if not self.layers:
            return QColor(Qt.GlobalColor.transparent)
            
        current_layer = self.layers[self.current_layer]
        if self.current_frame not in current_layer.frames:
            return QColor(Qt.GlobalColor.transparent)
            
        frame = current_layer.frames[self.current_frame]
        return frame.pixelColor(int(pos.x()), int(pos.y()))

    def resize_canvas(self, new_width, new_height):
        """Resize the canvas and all layers to the new dimensions."""
        for layer in self.layers:
            resized_frames = {}
            for index, frame in layer.frames.items():
                resized_frame = QImage(new_width, new_height, QImage.Format.Format_ARGB32_Premultiplied)
                resized_frame.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(resized_frame)
                painter.drawImage(0, 0, frame)
                painter.end()
                
                resized_frames[index] = resized_frame
            
            layer.frames = resized_frames
            layer.width = new_width
            layer.height = new_height
        
        self.setFixedSize(new_width, new_height)
        self.draw_current_frame()

    

class TimelineWidget(QWidget):
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.layer_height = 100
        self.playing = False
        self.play_timer = QTimer()
        self.play_timer.timeout.connect(self.next_frame)
        self.play_timer.setInterval(1000 // 24)  # 24 FPS por defecto
        self.copied_layer = None
        self.copied_frame = None
        self.speed_slider = None  # Se inicializará en init_ui()
        self.init_ui()


    def init_ui(self): 
        self.main_layout = QVBoxLayout()
        # Layout para el panel de timeline
        timeline_panel = QHBoxLayout()

        # Panel izquierdo (Capas)
        layers_panel = QVBoxLayout()
        layers_header = QHBoxLayout()
        layers_header.addWidget(QLabel("Capas"))

        # Botones de control de capas
        layer_buttons = QHBoxLayout()
        layer_buttons.setSpacing(2)

        add_layer_btn = QPushButton("+")
        add_layer_btn.setFixedSize(25, 25)
        add_layer_btn.clicked.connect(self.add_layer)

        del_layer_btn = QPushButton("-")
        del_layer_btn.setFixedSize(25, 25)
        del_layer_btn.clicked.connect(self.delete_layer)

        rename_layer_btn = QPushButton("✏️")
        rename_layer_btn.setFixedSize(25, 25)
        rename_layer_btn.clicked.connect(self.handle_rename_layer)

        layer_buttons.addWidget(add_layer_btn)
        layer_buttons.addWidget(del_layer_btn)
        layer_buttons.addWidget(rename_layer_btn)

        layers_header.addLayout(layer_buttons)
        layers_header.addStretch()
        layers_panel.addLayout(layers_header)

        # Lista de capas
        self.layer_list = QListWidget()
        self.layer_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.layer_list.itemClicked.connect(self.change_layer)
        self.layer_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.layer_list.customContextMenuRequested.connect(self.show_layer_context_menu)
        self.layer_list.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #3b3b3b;
            }
            QListWidget::item {
                color: white;
                padding: 5px;
                border-radius: 3px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background-color: #0078D7;
                color: white;
                font-weight: bold;
            }
            QListWidget::item:hover {
                background-color: #404040;
            }
        """)
        layers_panel.addWidget(self.layer_list)

        # Panel derecho (Frames y controles)
        frames_panel = QVBoxLayout()

        # Cabecera unificada con todos los controles
        controls_header = QHBoxLayout()
        controls_header.setSpacing(5)

        # Etiqueta Timeline
        controls_header.addWidget(QLabel("Timeline"))

        # Botones de frames
        add_frame_btn = QPushButton("+")
        add_frame_btn.setFixedSize(25, 25)
        add_frame_btn.clicked.connect(self.add_frame)

        del_frame_btn = QPushButton("-")
        del_frame_btn.setFixedSize(25, 25)
        del_frame_btn.clicked.connect(self.delete_frame)

        controls_header.addWidget(add_frame_btn)
        controls_header.addWidget(del_frame_btn)
        controls_header.addSpacing(10)

        # Controles de reproducción
        self.play_button = QPushButton("▶")
        self.play_button.setFixedSize(30, 25)
        self.play_button.clicked.connect(self.toggle_playback)
        controls_header.addWidget(self.play_button)

        # Control de velocidad
        controls_header.addWidget(QLabel("Velocidad:"))
        self.fps_label = QLabel("24 FPS")
        controls_header.addWidget(self.fps_label)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setFixedWidth(100)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(60)
        self.speed_slider.setValue(24)
        self.speed_slider.valueChanged.connect(self.update_playback_speed)
        controls_header.addWidget(self.speed_slider)

        controls_header.addStretch()
        frames_panel.addLayout(controls_header)

        # Grid de frames con scroll
        self.frame_grid = QGridLayout()
        self.frame_grid.setSpacing(2)

        scroll_area = QScrollArea()
        frame_container = QWidget()
        frame_container.setLayout(self.frame_grid)
        scroll_area.setWidget(frame_container)
        scroll_area.setWidgetResizable(True)
        frames_panel.addWidget(scroll_area)

        # Agregar los paneles al timeline_panel
        timeline_panel.addLayout(layers_panel, 1)
        timeline_panel.addLayout(frames_panel, 4)

        # Agregar timeline_panel al layout principal
        self.main_layout.addLayout(timeline_panel)

        # Establecer el layout principal
        self.setLayout(self.main_layout)
        self.update_lists()
    def get_internal_index(self, ui_index):
        # Convierte el índice de la interfaz al índice interno
        internal_index = len(self.canvas.layers) - 1 - ui_index
        print(f"Mapeando UI index {ui_index} a Internal index {internal_index}")  # Depuración
        return internal_index

    def show_layer_context_menu(self, pos):
        menu = QMenu(self)
        
        move_up_action = QAction("Subir dibujo", self)
        move_up_action.triggered.connect(self.move_layer_up)
        move_up_action.setEnabled(self.canvas.current_layer < len(self.canvas.layers) - 1)
        menu.addAction(move_up_action)
        
        move_down_action = QAction("Bajar dibujo", self)
        move_down_action.triggered.connect(self.move_layer_down)
        move_down_action.setEnabled(self.canvas.current_layer > 0)
        menu.addAction(move_down_action)
        
        menu.addSeparator()
        
        copy_layer_action = QAction("Copiar capa", self)
        copy_layer_action.triggered.connect(self.copy_layer)
        menu.addAction(copy_layer_action)
        
        if self.copied_layer is not None:
            paste_layer_action = QAction("Pegar capa", self)
            paste_layer_action.triggered.connect(self.paste_layer)
            menu.addAction(paste_layer_action)
        
        menu.exec(self.layer_list.mapToGlobal(pos))

    def update_playback_speed(self, value):
        self.play_timer.setInterval(1000 // value)
        self.fps_label.setText(f"{value} FPS")

    def copy_layer(self):
        if self.canvas.current_layer < len(self.canvas.layers):
            self.copied_layer = self.canvas.layers[self.canvas.current_layer].copy()
            QMessageBox.information(self, "Éxito", f"Capa '{self.copied_layer.name}' copiada.")

    def paste_layer(self):
        if self.copied_layer:
            new_layer = self.copied_layer.copy()
            new_layer.index = len(self.canvas.layers)
            new_layer.name += f" (copia)"
            self.canvas.layers.insert(0, new_layer)
            self.update_lists()
            self.canvas.draw_current_frame()
            QMessageBox.information(self, "Éxito", f"Capa '{new_layer.name}' pegada.")

    def update_frame_grid(self):
        # Limpiar grid existente
        while self.frame_grid.count():
            item = self.frame_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.canvas.layers:
            max_frames = max(len(layer.frames) for layer in self.canvas.layers)
            
            # Usar el mismo orden que en la lista de capas
            for ui_row, layer in enumerate(self.canvas.layers):
                for col in range(max_frames):
                    frame_btn = QPushButton()
                    frame_btn.setFixedSize(30, 30)
                    
                    if col < len(layer.frames):
                        frame_btn.setText(f"{col+1}")
                        frame_btn.setProperty("col", col)
                        frame_btn.setProperty("row", ui_row)
                        frame_btn.clicked.connect(self.on_frame_clicked)
                        
                        # Configurar menú contextual
                        frame_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                        frame_btn.customContextMenuRequested.connect(
                            lambda pos, r=ui_row, c=col: self.show_frame_context_menu(pos, r, c)
                        )
                        
                        # Resaltar el frame actual
                        if ui_row == self.canvas.current_layer and col == self.canvas.current_frame:
                            frame_btn.setStyleSheet("background-color: lightblue;")
                        else:
                            frame_btn.setStyleSheet("")

                        # Deshabilitar el botón si la capa está invisible
                        frame_btn.setEnabled(layer.visible)
                    else:
                        frame_btn.setEnabled(False)
                    
                    self.frame_grid.addWidget(frame_btn, ui_row, col)

    
    def toggle_layer_visibility(self, layer_index):
        if 0 <= layer_index < len(self.canvas.layers):
            layer = self.canvas.layers[layer_index]
            layer.visible = not layer.visible
            
            # Actualizar la interfaz
            self.update_lists()
            self.canvas.draw_current_frame()
   
    def update_lists(self):
        self.layer_list.clear()
        
        # Estilo para el QListWidget y sus items
        self.layer_list.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #3b3b3b;
            }
            QListWidget::item {
                color: white;
                padding: 0px;         /* Eliminar padding completamente */
                margin: 0px;          /* Eliminar margen completamente */
                height: 22px;         /* Altura fija para cada item */
            }
            QListWidget::item:selected {
                background-color: #0078D7;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #404040;
            }
        """)

        # Crear items para cada capa
        for i, layer in enumerate(self.canvas.layers):
            # Widget contenedor con layout horizontal
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(2, 0, 2, 0)  # Márgenes mínimos
            item_layout.setSpacing(4)                    # Espacio entre el ojo y el texto
            
            # Botón de visibilidad (ojo)
            visibility_btn = QPushButton('👁' if layer.visible else '⭕')
            visibility_btn.setFixedSize(18, 18)          # Tamaño más pequeño para el botón
            visibility_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    padding: 0px;
                    font-size: 12px;
                }
            """)
            visibility_btn.clicked.connect(lambda checked, idx=i: self.toggle_layer_visibility(idx))
            
            # Etiqueta del nombre de la capa
            name_label = QLabel(layer.name)
            name_label.setStyleSheet("""
                QLabel {
                    padding: 0px;
                    font-size: 12px;
                }
            """)
            
            # Agregar widgets al layout
            item_layout.addWidget(visibility_btn)
            item_layout.addWidget(name_label, 1)
            
            # Crear y configurar el item
            item = QListWidgetItem()
            item.setSizeHint(QSize(item_widget.sizeHint().width(), 22))  # Altura fija
            
            # Agregar a la lista
            self.layer_list.addItem(item)
            self.layer_list.setItemWidget(item, item_widget)
            
            # Seleccionar si es la capa actual
            if i == self.canvas.current_layer:
                self.layer_list.setCurrentItem(item)
                item.setSelected(True)

        self.update_frame_grid()
    def update_layer_selection_style(self):
        # Actualizar estilos para todos los items
        for i in range(self.layer_list.count()):
            item = self.layer_list.item(i)
            widget = self.layer_list.itemWidget(item)
            
            if item.isSelected():
                widget.setStyleSheet("""
                    QWidget {
                        background-color: #0078D7;
                    }
                    QLabel {
                        color: white;
                        font-weight: bold;
                    }
                    QPushButton {
                        color: white;
                    }
                """)
            else:
                widget.setStyleSheet("")

        self.update_frame_grid()

    def show_frame_context_menu(self, pos, row, col):
        menu = QMenu(self)
        
        copy_frame_action = QAction("Copiar fotograma", self)
        copy_frame_action.triggered.connect(lambda: self.copy_frame(row, col))
        menu.addAction(copy_frame_action)
        
        if self.copied_frame is not None:
            paste_frame_action = QAction("Pegar fotograma", self)
            paste_frame_action.triggered.connect(lambda: self.paste_frame(row, col))
            menu.addAction(paste_frame_action)
        
        menu.exec(self.sender().mapToGlobal(pos))

    def copy_frame(self, row, col):
        if row < len(self.canvas.layers):
            layer = self.canvas.layers[row]
            if col in layer.frames:
                self.copied_frame = layer.copy_frame(col)
                QMessageBox.information(self, "Éxito", f"Fotograma {col+1} de '{layer.name}' copiado.")

    def paste_frame(self, row, col):
        if self.copied_frame and row < len(self.canvas.layers):
            layer = self.canvas.layers[row]
            layer.frames[col] = self.copied_frame.copy()
            self.update_lists()
            self.canvas.draw_current_frame()
            QMessageBox.information(self, "Éxito", f"Fotograma pegado en '{layer.name}'.")

    def on_frame_clicked(self):
        sender = self.sender()
        if sender:
            col = sender.property("col")
            row = sender.property("row")
            self.canvas.current_layer = row
            self.canvas.change_frame(col)
            self.update_lists()
            self.canvas.setFocus()

    def change_layer(self, item):
        ui_index = self.layer_list.row(item)
        self.canvas.current_layer = ui_index  # Usar el índice directamente
        
        # Asegurar que el item permanezca seleccionado
        self.layer_list.setCurrentItem(item)
        item.setSelected(True)
        
        # Actualizar solo el grid de frames sin actualizar la lista de capas
        self.update_frame_grid()
        self.canvas.update()
    def toggle_playback(self):
        self.playing = not self.playing
        if self.playing:
            self.play_button.setText("⏸")
            self.play_timer.start()
        else:
            self.play_button.setText("▶")
            self.play_timer.stop()

    def next_frame(self):
        if not self.canvas.layers:
            return
            
        current_layer = self.canvas.layers[0]
        if not current_layer.frames:
            return
            
        total_frames = len(current_layer.frames)
        if total_frames > 1:
            next_frame = (self.canvas.current_frame + 1) % total_frames
            self.canvas.change_frame(next_frame)
            self.update_frame_grid()

    
   


    def add_layer(self):
        # Crear nueva capa con índice correcto
        new_index = len(self.canvas.layers)
        new_layer = Layer(
            self.canvas.width(), 
            self.canvas.height(), 
            index=new_index, 
            name=f"Nueva Capa {new_index + 1}"
        )
        
        if self.canvas.layers:
            # Copiar frames existentes para mantener consistencia
            max_frames = len(self.canvas.layers[0].frames)
            for i in range(max_frames):
                new_layer.add_frame(i)
        else:
            # Si es la primera capa, inicializar con un frame
            new_layer._init_first_frame()
        
        # Añadir la capa al final de la lista (aparecerá abajo en la interfaz)
        self.canvas.layers.append(new_layer)
        
        # Actualizar current_layer para que apunte a la nueva capa
        self.canvas.current_layer = len(self.canvas.layers) - 1
        
        # Actualizar los índices de todas las capas
        for i, layer in enumerate(self.canvas.layers):
            layer.index = i
        
        # Actualizar la interfaz
        self.update_lists()
        self.canvas.draw_current_frame()
        
        # Mostrar mensaje de éxito
        QMessageBox.information(self, "Éxito", f"Capa '{new_layer.name}' añadida.")
    def delete_layer(self):
        if len(self.canvas.layers) > 1:
            deleted_layer = self.canvas.layers.pop(self.canvas.current_layer)
            if self.canvas.current_layer >= len(self.canvas.layers):
                self.canvas.current_layer = len(self.canvas.layers) - 1
            self.update_lists()
            self.canvas.draw_current_frame()
            QMessageBox.information(self, "Éxito", f"Capa '{deleted_layer.name}' eliminada.")
        else:
            QMessageBox.warning(self, "Advertencia", "No se puede eliminar la única capa existente.")

    def add_frame(self):
        if self.canvas.layers:
            current_layer = self.canvas.layers[self.canvas.current_layer]  # Usar canvas.current_layer
            current_frame_index = self.canvas.current_frame
            
            # Crear nuevo frame vacío con el tamaño actual del canvas
            new_frame = QImage(current_layer.width, current_layer.height, 
                            QImage.Format.Format_ARGB32_Premultiplied)
            new_frame.fill(Qt.GlobalColor.transparent)
            
            # Crear diccionario temporal para los frames
            new_frames = {}
            
            # Copiar frames existentes hasta el frame actual
            for i in range(current_frame_index + 1):
                if i in current_layer.frames:
                    new_frames[i] = current_layer.frames[i]
            
            # Insertar nuevo frame
            new_frames[current_frame_index + 1] = new_frame
            
            # Copiar frames restantes
            for i in sorted(current_layer.frames.keys()):
                if i > current_frame_index:
                    new_frames[i + 1] = current_layer.frames[i]
            
            # Actualizar frames de la capa
            current_layer.frames = new_frames
            
            # Actualizar frame actual
            self.canvas.current_frame = current_frame_index + 1
            
            # Guardar estado para undo/redo
            current_layer._save_state()
            
            # Actualizar interfaz
            self.update_lists()
            self.canvas.draw_current_frame()
            
    def delete_frame(self):
        if not self.canvas.layers:
            return
            
        current_layer = self.canvas.layers[self.canvas.current_layer]
        if len(current_layer.frames) <= 1:
            QMessageBox.warning(self, "Advertencia", "No se puede eliminar el único fotograma existente en esta capa.")
            return

        # Guardar el índice actual antes de eliminar
        current_frame = self.canvas.current_frame
        
        # Obtener lista ordenada de índices antes de eliminar
        frame_indices = sorted(list(current_layer.frames.keys()))
        if current_frame not in frame_indices:
            return
            
        # Eliminar el frame actual
        del current_layer.frames[current_frame]
        
        # Crear nuevo diccionario para reordenar frames
        new_frames = {}
        new_index = 0
        
        # Reordenar los frames manteniendo el orden secuencial
        for old_index in sorted(current_layer.frames.keys()):
            new_frames[new_index] = current_layer.frames[old_index]
            new_index += 1
        
        # Actualizar frames de la capa
        current_layer.frames = new_frames
        
        # Ajustar el frame actual
        if current_frame >= len(new_frames):
            self.canvas.current_frame = len(new_frames) - 1
        else:
            self.canvas.current_frame = current_frame
            
        # Actualizar la interfaz
        self.update_lists()
        self.canvas.draw_current_frame()
        
        # Mostrar mensaje de éxito
        QMessageBox.information(self, "Éxito", f"Fotograma {current_frame + 1} eliminado.")
        
    def handle_rename_layer(self):
        selected_items = self.layer_list.selectedItems()
        print(f"Selected items: {selected_items}")  # Depuración
        
        if not selected_items:
            QMessageBox.warning(self, "Advertencia", "Por favor, selecciona una capa para renombrar.")
            return

        # Obtener el índice del elemento seleccionado en la interfaz
        ui_index = self.layer_list.row(selected_items[0])
        print(f"UI index seleccionado: {ui_index}")  # Depuración
        
        # Usar el índice directamente ya que ahora el orden coincide
        internal_index = ui_index
        print(f"Índice interno de la capa: {internal_index}")  # Depuración
        
        # Solicitar al usuario el nuevo nombre
        new_name, ok = QInputDialog.getText(self, "Renombrar Capa", "Nuevo nombre de la capa:")
        print(f"Nuevo nombre ingresado: {new_name}, Aceptado: {ok}")  # Depuración
        
        if ok and new_name:
            self.rename_layer(internal_index, new_name)

    def rename_layer(self, layer_index, new_name):
        if 0 <= layer_index < len(self.canvas.layers):
            layer = self.canvas.layers[layer_index]
            old_name = layer.name
            layer.name = new_name
            self.update_lists()
            QMessageBox.information(self, "Éxito", f"Capa renombrada de '{old_name}' a '{new_name}'.")
        else:
            QMessageBox.c
    def move_layer_up(self):
        # Mover una capa hacia arriba significa que se dibujará después (encima)
        if self.canvas.current_layer < len(self.canvas.layers) - 1:
            current_idx = self.canvas.current_layer
            next_idx = current_idx + 1
            
            # Intercambiar capas
            self.canvas.layers[current_idx], self.canvas.layers[next_idx] = \
                self.canvas.layers[next_idx], self.canvas.layers[current_idx]
            
            # Actualizar índices
            self.canvas.layers[current_idx].index, self.canvas.layers[next_idx].index = \
                next_idx, current_idx
            
            # Actualizar la selección
            self.canvas.current_layer = next_idx
            
            # Actualizar la interfaz
            self.update_lists()
            self.canvas.draw_current_frame()

    def move_layer_down(self):
        # Mover una capa hacia abajo significa que se dibujará antes (debajo)
        if self.canvas.current_layer > 0:
            current_idx = self.canvas.current_layer
            prev_idx = current_idx - 1
            
            # Intercambiar capas
            self.canvas.layers[current_idx], self.canvas.layers[prev_idx] = \
                self.canvas.layers[prev_idx], self.canvas.layers[current_idx]
            
            # Actualizar índices
            self.canvas.layers[current_idx].index, self.canvas.layers[prev_idx].index = \
                prev_idx, current_idx
            
            # Actualizar la selección
            self.canvas.current_layer = prev_idx
            
            # Actualizar la interfaz
            self.update_lists()
            self.canvas.draw_current_frame()


class SelectionTool:
    def __init__(self):
        self.start_pos = None
        self.current_pos = None
        self.selection_rect = None
        self.selected_content = None
        self.moving = False
        self.offset = None

    def start_selection(self, pos):
        self.start_pos = pos
        self.current_pos = pos
        self.selection_rect = None
        self.selected_content = None
        self.moving = False

    def update_selection(self, pos):
        self.current_pos = pos
        if not self.moving:
            # Crear rectángulo de selección
            x = min(self.start_pos.x(), pos.x())
            y = min(self.start_pos.y(), pos.y())
            width = abs(self.start_pos.x() - pos.x())
            height = abs(self.start_pos.y() - pos.y())
            self.selection_rect = [x, y, width, height]

    def start_moving(self, pos):
        if self.selection_rect and self.selected_content:
            self.moving = True
            self.offset = pos - QPoint(self.selection_rect[0], self.selection_rect[1])

    def move_selection(self, pos):
        if self.moving and self.selection_rect:
            new_x = pos.x() - self.offset.x()
            new_y = pos.y() - self.offset.y()
            self.selection_rect[0] = new_x
            self.selection_rect[1] = new_y

    def apply_selection_tool(layer, frame_index, selection_tool):
        if frame_index in layer.frames:
            frame = layer.frames[frame_index]
            if selection_tool.selection_rect:
                # Copiar el contenido seleccionado
                x, y, w, h = selection_tool.selection_rect
                selected_area = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
                selected_area.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(selected_area)
                painter.drawImage(0, 0, frame, x, y, w, h)
                painter.end()
                
                selection_tool.selected_content = selected_area

    def move_selected_content(self):
        if self.current_layer < len(self.layers):
            current_layer = self.layers[self.current_layer]  # Get the actual layer object
            if self.current_frame in current_layer.frames and self.selection_tool.selected_content:
                frame = current_layer.frames[self.current_frame]
                new_frame = QImage(frame.size(), QImage.Format.Format_ARGB32_Premultiplied)
                new_frame.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(new_frame)
                painter.drawImage(0, 0, frame)
                
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                x, y, w, h = self.selection_tool.selection_rect
                painter.fillRect(x, y, w, h, Qt.GlobalColor.transparent)
                
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                painter.drawImage(x, y, self.selection_tool.selected_content)
                painter.end()
                
                current_layer.frames[self.current_frame] = new_frame
                current_layer._save_state()

class AnimationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Inicializar atributos de transformación
        self.offset = QPoint(0, 0)
        self.scale_factor = 1.0
        
        # Initialize drawing-related attributes
        self.drawing = False
        self.current_tool = "pencil"  # Default tool
        self.pen_color = QColor(Qt.GlobalColor.black)
        self.pen_size = 3
        self.pen_opacity = 255
        self.stroke_manager = None  # Will be initialized after canvas creation
        
        # Eliminar la barra de título predeterminada
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.init_ui()
        self.showMaximized()
        
        # Initialize stroke manager after canvas is created
        self.stroke_manager = StrokeManager(self.canvas)
        
        # Establecer el foco para capturar eventos de teclado
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def init_ui(self):
        # Configuración básica de la ventana
        self.setWindowTitle('Belleza 2')
        self.setMinimumSize(800, 600)

        # Widget y layout principal
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Crear barra de título personalizada
        title_bar = self.create_title_bar()
        main_layout.addWidget(title_bar)

        # Crear canvas y timeline
        self.canvas = AnimationCanvas()
        self.timeline_widget = TimelineWidget(self.canvas)

        # Configurar atajos de teclado
        self.setup_shortcuts()

        # Crear panel de herramientas
        tools_panel = QVBoxLayout()
        self.setup_tools_panel(tools_panel)

        # Configurar panel de herramientas
        tool_widget = QWidget()
        tool_widget.setLayout(tools_panel)
        tool_widget.setFixedWidth(150)

        # Panel superior con herramientas y canvas
        upper_container = QWidget()
        upper_layout = QHBoxLayout(upper_container)
        upper_layout.addWidget(tool_widget)
        upper_layout.addWidget(self.canvas)

        # Crear layout redimensionable
        self.resizable_layout = ResizableTimelineLayout(self)
        self.resizable_layout.setup_layout(upper_container, self.timeline_widget)

        # Agregar al layout principal
        main_layout.addWidget(self.resizable_layout)

        # Configurar widget principal
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Aplicar estilos
        self.apply_styles()

    def create_title_bar(self):
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        
        # Layout para la barra de título
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        # Menú archivo
        file_menu = QMenu("Archivo", self)
        file_button = QPushButton("Archivo")
        file_button.setStyleSheet("text-align: left; padding: 5px 10px;")
        file_button.clicked.connect(
            lambda: file_menu.exec(file_button.mapToGlobal(QPoint(0, file_button.height())))
        )

        # Configurar acciones del menú
        self.setup_file_menu(file_menu)
        title_layout.addWidget(file_button)
        title_layout.addStretch()

        # Botones de control de ventana
        for button_info in [
            ("🗕", self.showMinimized),
            ("🗖", self.toggle_maximize),
            ("✕", self.close, "close_button")
        ]:
            btn = QPushButton(button_info[0])
            btn.clicked.connect(button_info[1])
            if len(button_info) > 2:
                btn.setObjectName(button_info[2])
            title_layout.addWidget(btn)

        return title_bar

    def setup_tools_panel(self, tools_panel):
        # Herramientas de dibujo
        tools = [
            ("✂️ Selección", "selection"),
            ("🖋 Lápiz", "pencil"),
            ("🧹 Borrador", "eraser"),
            ("🪣 Bote", "bucket")
        ]

        for label, tool in tools:
            btn = QPushButton(label)
            btn.setIconSize(QSize(16, 16))
            btn.clicked.connect(lambda checked, t=tool: self.canvas.set_tool(t))
            tools_panel.addWidget(btn)

        # Control de suavizado
        smooth_layout = QHBoxLayout()
        smooth_layout.addWidget(QLabel("Suavizado:"))
        self.smooth_label = QLabel("50%")  # Create the label as class attribute
        smooth_layout.addWidget(self.smooth_label)
        tools_panel.addLayout(smooth_layout)

        smooth_slider = QSlider(Qt.Orientation.Horizontal)
        smooth_slider.setMinimum(0)
        smooth_slider.setMaximum(100)
        smooth_slider.setValue(50)
        smooth_slider.valueChanged.connect(self.update_smoothing)
        tools_panel.addWidget(smooth_slider)
        
        # Control de tamaño de pincel
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Tamaño:"))
        self.size_label = QLabel("3")  # Crear el size_label como atributo de la clase
        size_layout.addWidget(self.size_label)
        tools_panel.addLayout(size_layout)

        size_slider = QSlider(Qt.Orientation.Horizontal)
        size_slider.setMinimum(1)
        size_slider.setMaximum(50)
        size_slider.setValue(3)
        size_slider.valueChanged.connect(self.update_pen_size)
        tools_panel.addWidget(size_slider)

        # Selector de color
        color_btn = QPushButton("🎨 Color")
        color_btn.clicked.connect(self.show_color_dialog)
        color_btn.setStyleSheet(f"background-color: {self.canvas.pen_color.name()}")
        self.color_btn = color_btn
        tools_panel.addWidget(color_btn)

        # Configuración Onion Skin
        self.setup_onion_skin_controls(tools_panel)

    def setup_shortcuts(self):
        self.copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self)
        self.copy_shortcut.activated.connect(self.copy_current_frame)
        
        self.paste_shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        self.paste_shortcut.activated.connect(self.paste_current_frame)

    def add_slider_control(self, parent_layout, label_text, min_val, max_val, default_val, callback):
        layout = QHBoxLayout()
        layout.addWidget(QLabel(label_text))
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default_val)
        slider.valueChanged.connect(callback)
        
        layout.addWidget(slider)
        parent_layout.addLayout(layout)
        return slider

    def setup_onion_skin_controls(self, parent_layout):
        parent_layout.addWidget(QLabel("Onion Skin"))
        
        toggle_btn = QPushButton("🧅 Toggle Onion Skin")
        toggle_btn.clicked.connect(self.canvas.toggle_onion_skin)
        parent_layout.addWidget(toggle_btn)
        
        self.add_slider_control(parent_layout, "Frames:", 1, 5, 1, 
                            self.canvas.set_onion_skin_frames)
        self.add_slider_control(parent_layout, "Opacity:", 0, 100, 30, 
                            self.canvas.set_onion_skin_opacity)

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QWidget { background-color: #2b2b2b; color: #ffffff; }
            QPushButton {
                background-color: #3b3b3b;
                border: 1px solid #555555;
                padding: 5px;
                border-radius: 3px;
                color: #ffffff;
            }
            QPushButton:hover { background-color: #4b4b4b; }
            QPushButton#close_button:hover { background-color: #c42b1c; }
            QLabel { color: #ffffff; }
            QSlider { background-color: transparent; }
            QSlider::handle { background-color: #555555; }
            QMenu {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 1px solid #404040;
            }
            QMenu::item:selected { background-color: #4b4b4b; }
        """)

        
        
    
    
    def toggle_maximize(self):
        """Alterna entre el estado maximizado y normal de la ventana."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Convert global coordinates to canvas coordinates
            canvas_pos = self.canvas.mapFrom(self, event.pos())
            transformed_pos = (canvas_pos - self.canvas.offset) / self.canvas.scale_factor
            
            # Delegate the event to canvas if it's within its bounds
            if self.canvas.rect().contains(canvas_pos):
                if self.current_tool == "pencil":
                    self.stroke_manager.start_stroke(
                        transformed_pos,
                        self.canvas.pen_color,
                        self.canvas.pen_size,
                        self.canvas.pen_opacity
                    )
                    self.drawing = True
                # Let the canvas handle other tools
                else:
                    self.canvas.mousePressEvent(event)


    def mouseMoveEvent(self, event):
        if self.drawing and self.current_tool == "pencil":
            canvas_pos = self.canvas.mapFrom(self, event.pos())
            transformed_pos = (canvas_pos - self.canvas.offset) / self.canvas.scale_factor
            if self.canvas.rect().contains(canvas_pos):
                self.stroke_manager.add_point(transformed_pos)
                self.canvas.update()
        else:
            self.canvas.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.drawing:
                self.stroke_manager.end_stroke()
                self.drawing = False
                self.canvas.update()
            else:
                self.canvas.mouseReleaseEvent(event)
    
    def prompt_resize_canvas(self):
        """Prompt the user to enter new canvas dimensions."""
        width, ok1 = QInputDialog.getInt(self, "Cambiar Tamaño del Lienzo", "Nuevo Ancho:", self.canvas.width(), 1, 10000)
        if not ok1:
            return
        height, ok2 = QInputDialog.getInt(self, "Cambiar Tamaño del Lienzo", "Nuevo Alto:", self.canvas.height(), 1, 10000)
        if not ok2:
            return
        
        self.canvas.resize_canvas(width, height)
    
    # Agregar método para actualizar el tamaño
    def update_pen_size(self, value):
        """Updates the pen size and label"""
        self.canvas.set_pen_size(value)
        self.size_label.setText(str(value))
    
    def update_smoothing(self, value):
        """Updates the smoothing factor and label"""
        self.canvas.smoothing_factor = value
        self.smooth_label.setText(f"Nivel: {value}%")
        self.canvas.update()
    
    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir Archivo",
            "",
            "Archivos de Animación (*.anim)"
        )
        
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    data = json.load(f)
                
                # Limpiar canvas actual
                self.canvas.layers.clear()
                
                # Restaurar propiedades del canvas
                self.canvas.setFixedSize(*data['canvas_size'])
                self.canvas.background_color = QColor(data['background_color'])
                
                # Restaurar capas
                for layer_data in data['layers']:
                    new_layer = Layer.from_dict(layer_data)
                    self.canvas.layers.append(new_layer)
                
                # Restaurar estados actuales
                self.canvas.current_frame = data['current_frame']
                self.canvas.current_layer = data['current_layer']
                
                # Actualizar interfaz
                self.canvas.draw_current_frame()
                self.timeline_widget.update_lists()
                
                QMessageBox.information(self, "Éxito", "Archivo abierto correctamente")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al abrir el archivo: {str(e)}")
                # Reiniciar el canvas en caso de error
                self.canvas.layers.clear()
                self.canvas._init_canvas()
    def setup_file_menu(self, file_menu):
        # Acciones del menú archivo
        menu_actions = [
            ('Abrir', 'Ctrl+O', self.open_file),
            ('Guardar', 'Ctrl+S', self.save_file),
            None,  # Separador
            ('🖼️ Importar Imagen', 'Ctrl+I', self.import_image),
            ('Exportar Imagen', None, self.export_image),
            ('Exportar Video', None, self.export_video),
            ('Cambiar Tamaño del Lienzo', None, self.prompt_resize_canvas)
        ]
        
        for action_info in menu_actions:
            if action_info is None:
                file_menu.addSeparator()
                continue
                
            name, shortcut, handler = action_info
            action = QAction(name, self)
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(handler)
            file_menu.addAction(action)
    
    
    def import_image(self):
        """
        Importa una imagen y la coloca en una nueva capa.
        Soporta formatos: PNG, JPG, JPEG, BMP
        """
        # Mostrar diálogo de selección de archivo con filtros
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Importar Imagen",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp);;Todos los archivos (*)"
        )
        
        if file_name:
            try:
                # Cargar la imagen seleccionada
                imported_image = QImage(file_name)
                if imported_image.isNull():
                    raise Exception("No se pudo cargar la imagen")

                # Crear nueva capa para la imagen
                new_layer = Layer(
                    self.canvas.width(),
                    self.canvas.height(),
                    index=len(self.canvas.layers),
                    name=f"Imagen {len(self.canvas.layers) + 1}"
                )

                # Preparar el frame para la imagen
                frame = QImage(self.canvas.width(), self.canvas.height(), 
                            QImage.Format.Format_ARGB32_Premultiplied)
                frame.fill(Qt.GlobalColor.transparent)

                # Escalar la imagen manteniendo proporción
                scaled_image = imported_image.scaled(
                    self.canvas.width(),
                    self.canvas.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                # Calcular posición para centrar la imagen
                x = (self.canvas.width() - scaled_image.width()) // 2
                y = (self.canvas.height() - scaled_image.height()) // 2

                # Dibujar la imagen escalada en el frame
                painter = QPainter(frame)
                painter.drawImage(x, y, scaled_image)
                painter.end()

                # Agregar el frame a la nueva capa
                new_layer.frames[self.canvas.current_frame] = frame
                
                # Agregar la capa al canvas
                self.canvas.layers.append(new_layer)
                self.canvas.current_layer = len(self.canvas.layers) - 1

                # Actualizar la interfaz
                self.canvas.draw_current_frame()
                self.timeline_widget.update_lists()
                
                # Mostrar mensaje de éxito con el nombre del archivo
                QMessageBox.information(
                    self, 
                    "Éxito", 
                    f"Imagen importada correctamente:\n{os.path.basename(file_name)}"
                )
                
            except Exception as e:
                # Mostrar mensaje de error si algo falla
                QMessageBox.critical(
                    self, 
                    "Error", 
                    f"Error al importar la imagen:\n{str(e)}"
                )
    
    def save_file(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Archivo",
            "",
            "Archivos de Animación (*.anim)"
        )
        
        if file_name:
            try:
                data = {
                    'canvas_size': (self.canvas.width(), self.canvas.height()),
                    'background_color': self.canvas.background_color.name(),
                    'current_frame': self.canvas.current_frame,
                    'current_layer': self.canvas.current_layer,
                    'layers': [layer.to_dict() for layer in self.canvas.layers]
                }
                
                with open(file_name, 'w') as f:
                    json.dump(data, f)
                
                QMessageBox.information(self, "Éxito", "Archivo guardado correctamente")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al guardar el archivo: {str(e)}")

    def export_image(self):
        """
        Exporta los frames de la animación como imágenes PNG, 
        combinando correctamente todas las capas visibles.
        """
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta para exportar imágenes",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            try:
                # Obtener el número total de frames
                max_frames = max(len(layer.frames) for layer in self.canvas.layers) if self.canvas.layers else 0
                
                # Guardar cada frame
                for frame_index in range(max_frames):
                    # Crear imagen con el color de fondo
                    frame_image = QImage(
                        self.canvas.width(),
                        self.canvas.height(),
                        QImage.Format.Format_ARGB32_Premultiplied
                    )
                    frame_image.fill(self.canvas.background_color)
                    
                    # Configurar el painter
                    painter = QPainter(frame_image)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    
                    # Dibujar cada capa visible desde abajo hacia arriba
                    for layer in self.canvas.layers:  # Las capas ya están en el orden correcto
                        if layer.visible and frame_index in layer.frames:
                            frame = layer.frames[frame_index]
                            if not frame.isNull():
                                painter.setOpacity(layer.opacity / 100.0)
                                painter.drawImage(0, 0, frame)
                    
                    painter.end()
                    
                    # Crear nombre de archivo
                    file_name = os.path.join(directory, f"frame_{frame_index:04d}.png")
                    
                    # Guardar imagen
                    if not frame_image.save(file_name, "PNG"):
                        raise Exception(f"Error al guardar el frame {frame_index}")
                
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Se exportaron {max_frames} imágenes correctamente en:\n{directory}"
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Error al exportar las imágenes: {str(e)}"
                )

    def export_video(self):
        """
        Exporta la animación como video MP4, combinando correctamente todas las capas visibles.
        """
        try:
            import subprocess
        except ImportError:
            QMessageBox.critical(self, "Error", "Se requiere subprocess para exportar video")
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Video",
            "",
            "Video MP4 (*.mp4)"
        )
        
        if file_name:
            try:
                temp_dir = tempfile.mkdtemp()
                
                if self.canvas.layers:
                    max_frames = max(len(layer.frames) for layer in self.canvas.layers)
                    
                    # Exportar frames
                    for frame_idx in range(max_frames):
                        # Crear imagen con el color de fondo
                        frame_image = QImage(
                            self.canvas.width(),
                            self.canvas.height(),
                            QImage.Format.Format_ARGB32_Premultiplied
                        )
                        frame_image.fill(self.canvas.background_color)
                        
                        # Configurar el painter
                        painter = QPainter(frame_image)
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                        
                        # Dibujar cada capa visible desde abajo hacia arriba
                        for layer in self.canvas.layers:  # Las capas ya están en el orden correcto
                            if layer.visible and frame_idx in layer.frames:
                                frame = layer.frames[frame_idx]
                                if not frame.isNull():
                                    painter.setOpacity(layer.opacity / 100.0)
                                    painter.drawImage(0, 0, frame)
                        
                        painter.end()
                        
                        # Guardar frame temporal
                        frame_file = os.path.join(temp_dir, f"frame_{frame_idx:04d}.png")
                        if not frame_image.save(frame_file, "PNG"):
                            raise Exception(f"Error al guardar el frame temporal {frame_idx}")
                    
                    # Crear video con FFmpeg
                    try:
                        fps = self.timeline_widget.speed_slider.value()
                        subprocess.run([
                            'ffmpeg',
                            '-framerate', str(fps),
                            '-i', os.path.join(temp_dir, 'frame_%04d.png'),
                            '-c:v', 'libx264',
                            '-pix_fmt', 'yuv420p',
                            '-y',
                            file_name
                        ], check=True)
                        QMessageBox.information(self, "Éxito", "Video exportado correctamente")
                    except subprocess.CalledProcessError:
                        QMessageBox.critical(self, "Error", "Error al ejecutar FFmpeg")
                    except FileNotFoundError:
                        QMessageBox.critical(self, "Error", "FFmpeg no encontrado. Por favor, instale FFmpeg")
                    finally:
                        # Limpiar archivos temporales
                        shutil.rmtree(temp_dir)
                        
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al exportar el video: {str(e)}")
                if 'temp_dir' in locals():
                    shutil.rmtree(temp_dir)
    
    def show_color_dialog(self):
        color = QColorDialog.getColor(self.canvas.pen_color, self)
        if color.isValid():
            self.canvas.set_pen_color(color)
            self.color_btn.setStyleSheet(f"background-color: {color.name()}")

    def add_layer(self):
        self.timeline_widget.add_layer()  # Usar el método del TimelineWidget

    def add_frame(self):
        self.timeline_widget.add_frame()  # Usar el método del TimelineWidget

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.timeline_widget.toggle_playback()
            event.accept()
        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Up:
                self.timeline_widget.move_layer_up()
                event.accept()
            elif event.key() == Qt.Key.Key_Down:
                self.timeline_widget.move_layer_down()
                event.accept()
        else:
            super().keyPressEvent(event)
    
    def copy_current_frame(self):
        print("Ejecutando copia de frame")  # Debug
        if self.canvas.layers and self.canvas.current_layer < len(self.canvas.layers):
            layer = self.canvas.layers[self.canvas.current_layer]
            if self.canvas.current_frame in layer.frames:
                self.timeline_widget.copied_frame = layer.frames[self.canvas.current_frame].copy()
                print("Frame copiado exitosamente")  # Debug
                

    def paste_current_frame(self):
        print("Ejecutando pegado de frame")  # Debug
        if hasattr(self.timeline_widget, 'copied_frame') and self.timeline_widget.copied_frame:
            if self.canvas.layers and self.canvas.current_layer < len(self.canvas.layers):
                layer = self.canvas.layers[self.canvas.current_layer]
                layer.frames[self.canvas.current_frame] = self.timeline_widget.copied_frame.copy()
                self.timeline_widget.update_lists()
                self.canvas.draw_current_frame()
                print("Frame pegado exitosamente")  # Debug
                


class ResizableTimelineLayout(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Layout principal
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Crear splitter vertical con restricciones de tamaño
        self.vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.vertical_splitter.splitterMoved.connect(self._enforce_size_limits)
        self.main_layout.addWidget(self.vertical_splitter)

    def setup_layout(self, upper_widget, timeline_widget):
        # Agregar widget superior al splitter
        self.vertical_splitter.addWidget(upper_widget)
        
        # Crear contenedor para timeline
        timeline_container = QWidget()
        timeline_container.setMinimumHeight(150)  # Altura mínima
        timeline_layout = QVBoxLayout(timeline_container)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.addWidget(timeline_widget)
        
        # Agregar timeline al splitter
        self.vertical_splitter.addWidget(timeline_container)
        
        # Configurar proporciones iniciales (70% superior, 30% timeline)
        self.vertical_splitter.setStretchFactor(0, 7)
        self.vertical_splitter.setStretchFactor(1, 3)
        
        # Establecer tamaños mínimos y máximos
        self._update_size_constraints()

    def _update_size_constraints(self):
        """Actualiza las restricciones de tamaño basadas en el tamaño total"""
        if self.height() > 0:
            # El timeline puede crecer hasta el 50% del espacio total
            max_timeline_height = self.height() * 0.8
            # El timeline no puede ser menor que 150px
            min_timeline_height = 150
            
            # Obtener los widgets
            upper_widget = self.vertical_splitter.widget(0)
            timeline_widget = self.vertical_splitter.widget(1)
            
            # Establecer restricciones
            if upper_widget and timeline_widget:
                # El widget superior necesita al menos 200px
                upper_widget.setMinimumHeight(200)
                timeline_widget.setMinimumHeight(min_timeline_height)
                timeline_widget.setMaximumHeight(int(max_timeline_height))

    def _enforce_size_limits(self, pos, index):
        """Asegura que los tamaños se mantengan dentro de los límites establecidos"""
        timeline_widget = self.vertical_splitter.widget(1)
        if timeline_widget:
            current_height = timeline_widget.height()
            max_height = self.height() * 0.8
            
            if current_height > max_height:
                # Ajustar las posiciones del splitter para respetar el límite máximo
                sizes = self.vertical_splitter.sizes()
                sizes[1] = int(max_height)
                sizes[0] = self.height() - sizes[1]
                self.vertical_splitter.setSizes(sizes)

    def resizeEvent(self, event):
        """Actualiza las restricciones cuando se redimensiona el widget"""
        super().resizeEvent(event)
        self._update_size_constraints()

class Stroke:
    """
    Clase para manejar trazos individuales con suavizado pixelado.
    """
    def __init__(self, color=Qt.GlobalColor.black, width=1, opacity=255):
        self.points = []
        self.color = color
        self.width = width
        self.opacity = opacity
        self.pixelated = True
        self.pixel_size = 1

    def add_point(self, point):
        """Añade un punto al trazo."""
        self.points.append(point)

    def draw(self, painter):
        """
        Dibuja el trazo con efecto pixelado.
        """
        if not self.points:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        
        # Configurar el pincel
        pen = QPen(self.color)
        pen.setWidth(self.width)
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        pen.setJoinStyle(Qt.PenJoinStyle.BevelJoin)
        painter.setPen(pen)
        
        # Dibujar puntos pixelados
        for point in self.points:
            x = int(point.x() / self.pixel_size) * self.pixel_size
            y = int(point.y() / self.pixel_size) * self.pixel_size
            painter.drawRect(x, y, self.pixel_size, self.pixel_size)

class StrokeManager:
    """
    Gestor de trazos para el canvas de animación.
    """
    def __init__(self, canvas):
        self.canvas = canvas
        self.current_stroke = None
        self.strokes = []
        self.pixel_size = 1
        self.last_point = None

    def start_stroke(self, point, color, width, opacity):
        """Inicia un nuevo trazo."""
        self.current_stroke = Stroke(color, width, opacity)
        self.current_stroke.pixel_size = self.pixel_size
        self.add_point(point)
        self.last_point = point

    def add_point(self, point):
        """Añade un punto al trazo actual."""
        if not self.current_stroke:
            return

        # Interpolar puntos entre el último punto y el actual
        if self.last_point:
            dx = point.x() - self.last_point.x()
            dy = point.y() - self.last_point.y()
            distance = ((dx * dx) + (dy * dy)) ** 0.5
            
            if distance > self.pixel_size:
                steps = int(distance / self.pixel_size)
                for i in range(steps):
                    t = i / steps
                    x = self.last_point.x() + dx * t
                    y = self.last_point.y() + dy * t
                    self.current_stroke.add_point(QPointF(x, y))

        self.current_stroke.add_point(point)
        self.last_point = point

    def end_stroke(self):
        """Finaliza el trazo actual."""
        if self.current_stroke:
            self.strokes.append(self.current_stroke)
            self.current_stroke = None
            self.last_point = None

    def draw_current_stroke(self, painter):
        """Dibuja el trazo actual."""
        if self.current_stroke:
            self.current_stroke.draw(painter)

    def set_pixel_size(self, size):
        """Establece el tamaño de píxel para el efecto pixelado."""
        self.pixel_size = max(1, size)
        if self.current_stroke:
            self.current_stroke.pixel_size = self.pixel_size
    
if __name__ == '__main__':
    app = QApplication([])
    window = AnimationApp()
    window.show()
    app.exec()
