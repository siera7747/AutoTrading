from pybithumb import WebSocketManager
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic

class Worker(QThread):
    receiveData = pyqtSignal(dict)

    def run(self):
        wm = WebSocketManager("ticker", ["BTC_KRW"], ["24H", "MID"])
        self.alive = True

        while self.alive:
            # 네트워크 에러시 
            try:
                data = wm.get()
                self.receiveData.emit(data)
            except:
                pass

        wm.terminate()

    def end(self):
        self.alive = False

class OverviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi("UI\overview_B.ui", self)

        self.w = Worker()
        self.w.receiveData.connect(self.getData)
        self.w.start()

    def closeEvent(self, event):
        self.w.end()

    def getData(self, data):
        d = data['content']
        if d['tickType'] == "24H":
            self.price.setText(f"{int(d['closePrice']): ,}")                            # 현재 가격
            self.diff.setText(f"{d['chgRate']}%")                                       # 가격 변화
            self.volume.setText(f"{float(d['volume']):,.4f}" + ' ' + d['symbol'][0:3])  # 거래량
            self.value.setText(f"{float(d['value'])/100000000:,.1f} 억")                # 거래 금액
            self.updateStyle()
        else:
            self.price.setText(f"{int(d['closePrice']): ,}")
            self.diff.setText(f"{d['chgRate']}%")
            self.strength.setText(f"{d['volumePower']} %")
            self.high.setText(f"{int(d['highPrice']): ,}")
            self.low.setText(f"{int(d['lowPrice']): ,}")
            self.prev.setText(f"{int(d['prevClosePrice']): ,}")
            self.updateStyle()
            self.updateStrengthStyle(d['volumePower'])

            # 자작 코드
            self.symbol.setText(d['symbol'])
            self.tickType.setText(d['tickType'])
            self.date.setText(d['date'])
            self.time.setText(d['time'])
            self.openPrice.setText(d['openPrice'])
            self.closePrice.setText(d['closePrice'])
            self.sellVolume.setText(d['sellVolume'])
            self.buyVolume.setText(d['buyVolume'])
            self.prevClosePrice.setText(d['prevClosePrice'])
            self.chgAmt.setText(d['chgAmt'])

    def updateStrengthStyle(self, strength):
        strength = float(strength)
        if strength > 100:
            self.strength.setStyleSheet("color:red")
        elif strength == 100:
            self.strength.setStyleSheet("color:black")
        else:
            self.strength.setStyleSheet("color:blue")

    def updateStyle(self):
        if self.diff.text()[0] == '-':
            self.price.setStyleSheet("color:blue")
            self.diff.setStyleSheet("color:white ; background-color:blue")
        else:
            self.price.setStyleSheet("color:red")
            self.diff.setStyleSheet("color:white ; background-color:red")

if __name__ == "__main__":
    app = QApplication([])
    m = OverviewWidget()
    m.show()
    app.exec_()