from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic
import pybithumb
import time

class OrderbookWorker(QThread):
    dataReceive = pyqtSignal(dict)
    
    def run(self):
        self.alive = True
        while self.alive:
            # 네트워크 에러 처리
            try:
                data = pybithumb.get_orderbook("BTC", limit=15) # 파이빗썸은 리미트 만큼 호가창을 준다
                self.dataReceive.emit(data)
            except:
                pass

            time.sleep(0.3) # 초당 3.33회 조회

    def end(self):
        self.alive = False

class OrderbookWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi("UI\orderbook_B.ui", self)

        self.asksAnim = []
        self.bidsAnim = []

        for i in range(15):
            d = QTableWidgetItem(str(""))
            d.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.askTable.setItem(i, 0, d)
            d = QTableWidgetItem(str(""))
            d.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.askTable.setItem(i, 1, d)
            d = QProgressBar(self.askTable)
            d.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            d.setStyleSheet("""
                QProgressBar    {background-color: rgba(0,0,0,0) }
                QProgressBar::Chunk {background-color: rgba(255, 0, 0, 0.5)}
            """)
            anim = QPropertyAnimation(d, b"value")
            anim.setDuration(200)
            anim.setStartValue(0)
            self.asksAnim.append(anim)
            self.askTable.setCellWidget(i, 2, d)

            d = QTableWidgetItem(str(""))
            d.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.bidTable.setItem(i, 0, d)
            d = QTableWidgetItem(str(""))
            d.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.bidTable.setItem(i, 1, d)
            d = QProgressBar(self.bidTable)
            d.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            d.setStyleSheet("""
                QProgressBar    {background-color: rgba(0,0,0,0) }
                QProgressBar::Chunk {background-color: rgba(0, 255, 0, 0.4)}
            """)
            self.bidTable.setCellWidget(i, 2, d)
            anim = QPropertyAnimation(d, b"value")
            anim.setDuration(200)
            anim.setStartValue(0)
            self.bidsAnim.append(anim)
            

        self.ow = OrderbookWorker()
        self.ow.dataReceive.connect(self.updateOrderbook)
        self.ow.start()

    def closeEvent(self, event):
        self.ow.end()

    def updateOrderbook(self, param):
        valueList = [ ]
        for i in range(15):
            item = param['asks'][14 - i]
            value = item['price'] * item['quantity']
            valueList.append(value)

            item = param['bids'][i]
            value = item['price'] * item['quantity']
            valueList.append(value)

        maxTradingValue = max(valueList)

        for i in range(15):
            item = param['asks'][14 - i]
            value = item['price'] * item['quantity']

            d = self.askTable.item(i, 0)
            d.setText(str(item['price']))
            d = self.askTable.item(i, 1)
            d.setText(str(item['quantity']))
            d = self.askTable.cellWidget(i, 2)
            d.setRange(0, int(maxTradingValue))
            d.setFormat(f"{value}")
            self.asksAnim[i].setStartValue(d.value())
            self.asksAnim[i].setEndValue(int(value))
            self.asksAnim[i].start()

            item = param['bids'][i]
            value = item['price'] * item['quantity']
            d = self.bidTable.item(i, 0)
            d.setText(str(item['price']))
            d = self.bidTable.item(i, 1)
            d.setText(str(item['quantity']))
            d = self.bidTable.cellWidget(i, 2)
            d.setRange(0, int(maxTradingValue))
            d.setFormat(f"{value}")
            self.bidsAnim[i].setStartValue(d.value())
            self.bidsAnim[i].setEndValue(int(value))
            self.bidsAnim[i].start()

        print("-" * 10)

if __name__ == "__main__":
    app = QApplication([])
    ow = OrderbookWidget()
    ow.show()
    app.exec_()

