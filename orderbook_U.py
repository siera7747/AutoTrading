# 업비트 버전 호가창
from PyQt5.QtWidgets import *
from PyQt5 import uic
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

ui = resource_path("hoga_U.ui")
form_class = uic.loadUiType(ui)[0]

# 호가 데이터 얻어오는 쓰레드
class OrderbookTh(QThread):
    # 데이터 관리를 위한 시그널
    dataReceive = pyqtSignal(list)

    # 생성자. 티커 데이터를 받아옴
    def __init__(self, ticker, module):
        super().__init__()
        self.ticker = ticker
        self.module = module

    def run(self):
        self.alive = True
        if self.module == "Upbit":
            while self.alive:
                data = pyupbit.get_orderbook(self.ticker)
                # 데이터 가공
                orderbook = self.set_updata(data)
                
                # 시그널에 데이터 전달
                self.dataReceive.emit(orderbook)

                time.sleep(0.3)
        elif self.module == "Binance":
            binance = ccxt.binance()
            while self.alive:
                data = binance.fetch_order_book(self.ticker)
                asks = data['asks']
                bids = data['bids']
                orderbook = [asks, bids]
                
                # 시그널에 데이터 전달
                self.dataReceive.emit(orderbook)

                time.sleep(2)
        elif self.module == "Future":
            binance = ccxt.binance(config={
                'options':{
                    'defaultType':'future'
                }
            })
            while self.alive:
                data = binance.fetch_order_book(self.ticker)
                asks = data['asks']
                bids = data['bids']
                orderbook = [asks, bids]
                
                # 시그널에 데이터 전달
                self.dataReceive.emit(orderbook)

                time.sleep(1)            

    # 업비트 호가 데이터 정리
    def set_updata(self, orderbook):
        datas = orderbook[0]['orderbook_units']

        asks = []
        bids = []

        for data in datas:
            d = [data['ask_price'], data['ask_size']]
            asks.append(d)
            d = [data['bid_price'], data['bid_size']]
            bids.append(d)

        orderbookdata = [asks, bids]
        return orderbookdata

    # 프로세스 강제 종료
    def end(self):
        self.alive = False

class OrderbookWidget(QWidget, form_class):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # 애니메이션 저장할 리스트
        self.asksAnim = []
        self.bidsAnim = []

        # 테이블 아이템 생성
        for i in range(10):
            d = QTableWidgetItem("")
            # 아이템 정렬(수평 오른쪽, 수직 중앙)
            d.setTextAlignment(Qt.AlignRight | Qt.AlignCenter)
            self.askTable.setItem(i, 0, d)

            d = QTableWidgetItem("")
            d.setTextAlignment(Qt.AlignRight | Qt.AlignCenter)
            self.askTable.setItem(i, 1, d)

            # 프로그레스 바 객체 생성
            d = QProgressBar(self.askTable)
            d.setAlignment(Qt.AlignRight | Qt.AlignCenter)
                # 프로그레스 바 색상 설정 - 빨간색
            d.setStyleSheet("""
                QProgressBar {background-color:rgba(0,0,0,0);border:1}
	            QProgressBar::Chunk {background-color:rgba(255,0,0,0.5);border:1}
            """)
            # 애니메이션 객체
            anim = QPropertyAnimation(d, b"value")
            # 애니메이션 속도
            anim.setDuration(200)
            # 애니메이션 초기값
            anim.setStartValue(0)
            # 애니메이션 저장
            self.asksAnim.append(anim)
            self.askTable.setCellWidget(i, 2, d)

            d = QTableWidgetItem("")
            d.setTextAlignment(Qt.AlignRight | Qt.AlignCenter)
            self.bidTable.setItem(i, 0, d)

            d = QTableWidgetItem("")
            d.setTextAlignment(Qt.AlignRight | Qt.AlignCenter)
            self.bidTable.setItem(i, 1, d)

            # 프로그레스 바 객체 생성
            d = QProgressBar(self.bidTable)
            d.setAlignment(Qt.AlignRight | Qt.AlignCenter)
                # 프로그레스 바 색상 설정 - 초록색
            d.setStyleSheet("""
                QProgressBar {background-color:rgba(0,0,0,0);border:1}
	            QProgressBar::Chunk {background-color:rgba(0,255,0,0.4);border:1}
            """)
            # 애니메이션 객체
            anim = QPropertyAnimation(d, b"value")
            # 애니메이션 속도
            anim.setDuration(200)
            # 애니메이션 초기값
            anim.setStartValue(0)
            # 애니메이션 저장
            self.bidsAnim.append(anim)
            self.bidTable.setCellWidget(i, 2, d)

        # 쓰레드 객체 생성
        self.ow = OrderbookTh("KRW-XRP", "Upbit")

        # 시그널에 슬롯 연결
        self.ow.dataReceive.connect(self.updateOrderbook)

        # 쓰레드 실행
        self.ow.start()

    # 티커 변경
    def changeTicker(self, ticker, module):
        print(f"호가창 티커를 {ticker}로 변경")
        # 기존 쓰레드 종료
        self.ow.end()
        
        # 쓰레드 객체 생성 후 실행
        self.ow = OrderbookTh(ticker, module)
        # 시그널에 슬롯 연결
        self.ow.dataReceive.connect(self.updateOrderbook)
        self.ow.start()

    def updateOrderbook(self, data):
        # 값을 저장할 리스트
        valueList = []
        # 데이터가 없으면 진행하지 않음
        if len(data[0]) == 0:
            print("데이터 없음")
            return
        # 데이터 갯수가 10개가 넘지 않는지 확인
        if len(data[0]) < 10:
            hoganum = len(data[0])
        else:
            hoganum = 10
        # 호가총액 구하기
        for idx in range(hoganum):
            # 매도 호가 데이터 - 역순
            item = data[0][(hoganum-1)-idx]
            value = round((item[0] * item[1]), 5)
            valueList.append(value)

            # 매수 호가 데이터
            item = data[1][idx]
            value = round((item[0] * item[1]), 5)
            valueList.append(value)
        # 리스트에서 최대값을 구함
        maxTradingValue = max(valueList)

        # 테이블 아이템의 값을 변경
        for i in range(hoganum):
            # 매도 호가 데이터 - 역순
            item = data[0][(hoganum-1)-i]
            value = round((item[0] * item[1]), 5)

            d = self.askTable.item(i, 0)
            d.setText(str(item[0]))

            d = self.askTable.item(i, 1)
            d.setText(str(item[1]))

            # 프로그레스 바 값 설정
            d = self.askTable.cellWidget(i, 2)
            # 바 최대 범위 설정
            # 최대 범위가 너무 큰 경우 조정
            if maxTradingValue > 2147483647:
                d.setRange(0, 2147483646)
            else:
                d.setRange(0, int(maxTradingValue))
            # 바 포맷 변경 - 수치를 퍼센트 대신 문자열로 변경
            d.setFormat(f"{value}")
            # 애니메이션 시작, 끝 값 설정
            # 시작 값은 이전에 저장되어 있던 값
            self.asksAnim[i].setStartValue(d.value())
            # 끝 값은 새로 받은 값
            self.asksAnim[i].setEndValue(int(value))
            # 애니메이션 실행
            self.asksAnim[i].start()

            # 매수 호가 데이터
            item = data[1][i]
            value = round((item[0] * item[1]), 5)

            d = self.bidTable.item(i, 0)
            d.setText(str(item[0]))

            d = self.bidTable.item(i, 1)
            d.setText(str(item[1]))

            # 프로그레스 바 값 설정
            d = self.bidTable.cellWidget(i, 2)
            # 최대 범위가 너무 큰 경우 조정
            if maxTradingValue > 2147483647:
                d.setRange(0, 2147483646)
            else:
                d.setRange(0, int(maxTradingValue))
            # 바 포맷 변경 - 수치를 퍼센트 대신 문자열로 변경
            d.setFormat(f"{value}")
            # 애니메이션 시작, 끝 값 설정
            # 시작 값은 이전에 저장되어 있던 값
            self.bidsAnim[i].setStartValue(d.value())
            # 끝 값은 새로 받은 값
            self.bidsAnim[i].setEndValue(int(value))
            # 애니메이션 실행
            self.bidsAnim[i].start()


if __name__ == "__main__":
    # 애플리케이션 객체 생성
    app = QApplication([])
    
    # 위젯 연결
    ow = OrderbookWidget()
    # 위젯 표시
    ow.show()

    # 이벤트 루프 생성
    app.exec_()