from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtChart import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import pyupbit
import time
import ccxt
import sys
import os

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ui = resource_path("chart_U.ui")
form_class = uic.loadUiType(ui)[0]

class ChartWorker(QThread):
    dataSent = pyqtSignal(float)

    # 생성자. 티커 데이터를 받아옴
    def __init__(self, ticker, module):
        super().__init__()
        self.ticker = ticker
        self.module = module
        print(f"{self.ticker}")
        print(f"{self.module}")

    def run(self):
        self.alive = True
        if self.module == "Upbit":
            print("업비트 차트 데이터 가져오기")
            while self.alive:
                price = pyupbit.get_current_price(self.ticker)
                self.dataSent.emit(price)
                time.sleep(1)
        elif self.module == "Binance":
            print("바이낸스 차트 데이터 가져오기")
            binance = ccxt.binance()
            while self.alive:
                current = binance.fetch_ticker(self.ticker)
                price = current['close']
                self.dataSent.emit(price)
                time.sleep(2)
        elif self.module == "Future":
            print("선물거래 차트 데이터")
            binance = ccxt.binance(config={
                'options':{
                    'defaultType':'future'
                }
            })
            while self.alive:
                current = binance.fetch_ticker(self.ticker)
                price = current['close']
                self.dataSent.emit(price)
                time.sleep(1)

    def end(self):
        self.alive = False

class ChartWidget(QWidget, form_class):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

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

        self.cw = ChartWorker("KRW-XRP", "Upbit")
        self.cw.dataSent.connect(self.appendData)
        self.cw.start()
 
        self.viewLimit = 60

    # 티커 변경
    def changeTicker(self, ticker, module):
        print(f"티커를 {ticker}로 변경")
        # 기존 쓰레드 종료
        self.cw.end()

        # 차트 초기화
        print("기존 차트 데이터 삭제")
        for i in range(0, len(self.priceData)):
            self.priceData.remove(0)

        print("데이터 삭제 완료")

        self.cw = ChartWorker(ticker, module)
        self.cw.dataSent.connect(self.appendData)
        self.cw.start()

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