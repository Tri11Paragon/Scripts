from PyQt5 import QtWidgets, QtCore, QtGui
import sys


class TransparentScene(QtWidgets.QGraphicsScene):
    def __init__(self):
        super().__init__()
        text = self.addText("Mode: 1")
        text.setDefaultTextColor(QtGui.QColor("white"))
        # Add a semi-transparent background rect
        rect = self.addRect(text.boundingRect().adjusted(-10, -10, 10, 10),
                            QtGui.QPen(QtCore.Qt.NoPen),
                            QtGui.QBrush(QtGui.QColor(0, 0, 0, 128)))
        rect.setZValue(-1)  # Put behind text


class TransparentView(QtWidgets.QGraphicsView):
    def __init__(self):
        super().__init__()
        scene = TransparentScene()
        self.setScene(scene)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    view = TransparentView()
    view.resize(200, 100)
    view.show()
    sys.exit(app.exec_())
