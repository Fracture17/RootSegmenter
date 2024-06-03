from PySide6.QtGui import QColor, QBrush, QPixmap, QMouseEvent, QWheelEvent, QPen, QPolygonF, QTransform
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QFrame
from PySide6.QtCore import Signal, QPoint, QRectF, QPointF
from PySide6.QtCore import Qt

from math import floor


class PhotoViewer(QGraphicsView):
    ZOOM_FACTOR = 1.25

    photoClicked = Signal(QMouseEvent, QPoint)
    photoDragged = Signal(QPoint)
    photoScrolled = Signal(QWheelEvent)
    mouseMoved = Signal(QPoint)

    def __init__(self, parent):
        super(PhotoViewer, self).__init__(parent)

        self.mouseLeftPressed = False
        self.isDragging = False
        self.dragStartPosition = QPoint()
        self.clickThreshold = 10

        self._zoom = 0
        self._scene = QGraphicsScene(self)
        self._photo = QGraphicsPixmapItem()
        self._scene.addItem(self._photo)

        self.pen = QPen()
        self.pen.setWidth(.5)
        self.brush = QBrush(Qt.BrushStyle.SolidPattern)

        self.setScene(self._scene)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def fitViewToImage(self):
        rect = QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)

            unity = self.transform().mapRect(QRectF(0, 0, 1, 1))
            self.scale(1 / unity.width(), 1 / unity.height())

            viewRect = self.viewport().rect()
            sceneRect = self.transform().mapRect(rect)
            factor = min(viewRect.width() / sceneRect.width(), viewRect.height() / sceneRect.height())
            self.scale(factor, factor)

            self._zoom = 0

    def setImage(self, pixmap: QPixmap, resetView: bool = False):
        self.removeAllOverlays()
        self._photo.setPixmap(pixmap)

        if resetView:
            self.fitViewToImage()

    def removeAllOverlays(self):
        for i in self._scene.items()[:-1]:
            self._scene.removeItem(i)

    def addOverlayLine(self, startX, startY, endX, endY, color: str):
        self.pen.setColor(color)

        self._scene.addLine(startX, startY, endX, endY, self.pen)

    def addOverlayText(self, text, x, y, size, textColor):
        self.pen.setColor(textColor)

        textItem = self._scene.addSimpleText(text)
        textItem.setPos(x, y)

        f = textItem.font()
        f.setPixelSize(size)
        textItem.setFont(f)

    def addOverlayEllipse(self, startX, startY, width, height, color: str):
        self.pen.setColor(color)

        self._scene.addEllipse(startX, startY, width, height, self.pen)

    def addOverlaySquare(self, startX, startY, width, height, color: str):
        self.pen.setColor(color)
        self.brush.setColor(color)

        self._scene.addRect(startX, startY, width, height, self.pen, self.brush)

    def wheelEvent(self, event):
        self.photoScrolled.emit(event)

    def zoomIn(self, center: QPoint):
        self._zoom += 1
        self.zoom(self.ZOOM_FACTOR, center)

    def zoomOut(self, center: QPoint):
        self._zoom -= 1
        if self._zoom <= 0:
            self.fitViewToImage()
            self._zoom = 0
        else:
            self.zoom(self.ZOOM_FACTOR ** -1, center)

    def zoom(self, factor, center: QPoint):
        oldPos = self.mapToScene(center)
        self.scale(factor, factor)

        newPos = self.mapToScene(center)
        delta = newPos - oldPos
        self.translate(delta.x(), delta.y())

    def translate(self, dx: float, dy: float):
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        super().translate(dx, dy)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def mousePressEvent(self, event):
        if self._photo.isUnderMouse():
            pos = self.mapToPixel(event.pos())

            if event.buttons() == Qt.LeftButton:
                assert not self.mouseLeftPressed
                assert not self.isDragging

                self.mouseLeftPressed = True
                self.dragStartPosition = event.position()
            else:
                self.photoClicked.emit(event, pos)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.mouseLeftPressed:
            d = event.position() - self.dragStartPosition

            if self.isDragging:
                zoom = self.ZOOM_FACTOR ** self._zoom
                d /= zoom ** .5
                self.translate(d.x(), d.y())
                self.dragStartPosition = event.position()

            if d.manhattanLength() >= 10:
                self.isDragging = True
                self.setCursor(Qt.ClosedHandCursor)
                self.dragStartPosition = event.position()

        pos = self.mapToPixel(event.pos())
        self.mouseMoved.emit(pos)

    def mouseReleaseEvent(self, event):
        if self.mouseLeftPressed:
            if not (event.buttons() & Qt.LeftButton):
                self.mouseLeftPressed = False
                if not self.isDragging:
                    pos = self.mapToPixel(event.pos())
                    self.photoClicked.emit(event, pos)
                else:
                    self.isDragging = False
                    self.setCursor(Qt.ArrowCursor)

    def mapToPixel(self, pos: QPointF) -> QPoint:
        pos = self.mapToScene(pos)
        pos.setX(floor(pos.x()))
        pos.setY(floor(pos.y()))
        return pos.toPoint()
