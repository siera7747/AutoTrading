from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtChart import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import pybithumb
import time

class ChartWorker(QThread):
    dataSent = pyqtSignal(float)
    def run(self):
        self.alive = True
        while self.alive:
            price = pybithumb.get_current_price("BTC")
            self.dataSent.emit(price)
            time.sleep(1)

    def end(self):
        self.alive = False

class ChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi("UI\chart_B.ui", self)

        # 1) 데이터 추가
        self.priceData = QLineSeries()

        # 2) 도화지 연결
        self.priceChart = QChart()
        self.priceChart.addSeries(self.priceData)
        self.priceChart.legend().hide()
        self.priceChart.layout().setContentsMargins(0,0,0,0) # 모든 여백 제거

        ax = QDateTimeAxis()
        ax.setFormat("hh:mm:ss")
        ax.setTickCount(4)
        self.priceChart.addAxis(ax, Qt.AlignBottom)

        ay = QValueAxis()
        ay.setVisible(False)
        self.priceChart.addAxis(ay, Qt.AlignRight)

        self.priceData.attachAxis(ax)
        self.priceData.attachAxis(ay)
        
        # 3) 위젯에 출력
        self.priceView.setChart(self.priceChart)
        self.priceView.setRenderHints(QPainter.Antialiasing)

        self.cw = ChartWorker()
        self.cw.dataSent.connect(self.appendData)
        self.cw.start()
 
        self.viewLimit = 60

    def closeEvent(self, event):
        self.cw.end()

    def appendData(self, price):
        if len(self.priceData) == self.viewLimit:
            self.priceData.remove(0)

        curr = QDateTime.currentDateTime()
        self.priceData.append(curr.toMSecsSinceEpoch(), price)

        pvs = self.priceData.pointsVector()
        x = pvs[0].x()

        s = QDateTime.fromMSecsSinceEpoch( x )
        e = s.addSecs(self.viewLimit)

        ax = self.priceChart.axisX()
        ax.setRange( s, e )

        ay = self.priceChart.axisY()
        dataY = [item.y() for item in pvs]

        minVal = min(dataY)
        maxVal = max(dataY)
        margin = (maxVal - minVal) * 0.2

        ay.setRange( minVal - margin, maxVal + margin)



if __name__ == "__main__":
    app = QApplication([])
    m = ChartWidget()
    m.show()
    app.exec_()