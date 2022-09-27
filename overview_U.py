# 개요창2 - 업비트 버전
from pyupbit import WebSocketManager
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic
import ccxt
import time
import sys
import os

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ui = resource_path("overview_U.ui")
form_class = uic.loadUiType(ui)[0]

# 데이터를 읽어들이는 쓰레드
class Worker(QThread):
    # 시그널
    receiveUData = pyqtSignal(dict)
    receiveBData = pyqtSignal(dict)
    
    # 생성자. 티커 데이터를 받아옴
    def __init__(self, ticker, module):
        super().__init__()
        self.ticker = ticker
        self.module = module
    
    def run(self):
        # 모듈에 따라 다른 코드 실행
        if self.module == "Upbit":
            # 웹소켓 매니저 객체 생성
            wm = WebSocketManager("ticker", [self.ticker])
            
            self.alive = True

            # 웹소켓 매니저에서 데이터 받아오기
            while self.alive:
                data = wm.get()
                # 시그널로 데이터 방출
                self.receiveUData.emit(data)
            wm.terminate()

        elif self.module == "Binance":
            self.alive = True
            binance = ccxt.binance()
            # 티커 현재가 정보 가져오기
            while self.alive:
                data = binance.fetch_ticker(self.ticker)

                # 시그널로 데이터 방출
                self.receiveBData.emit(data)
                
                time.sleep(1)
        elif self.module == "Future":
            self.alive = True
            binance = ccxt.binance(config={
                'options':{
                    'defaultType':'future'
                }
            })
            # 티커 현재가 정보 가져오기
            while self.alive:
                data = binance.fetch_ticker(self.ticker)

                # 시그널로 데이터 방출
                self.receiveBData.emit(data)
                
                time.sleep(1)

    # 프로세스 강제 종료
    def end(self):
        self.alive = False

# 위젯 클래스
class OverviewWidget(QWidget, form_class):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.ticker = "KRW-XRP"

        self.split_Ticker("Upbit")

        # 쓰레드 객체 생성 후 실행
        self.w = Worker(self.ticker, "Upbit")
        # 시그널 받기
        self.w.receiveUData.connect(self.getData_U)
        self.w.receiveBData.connect(self.getData_B)
        self.w.start()

    # 종료 버튼 이벤트
    def closeEvent(self, event):
        self.w.end()

    # 티커 변경
    def changeTicker(self, ticker, module):
        # 기존 쓰레드 종료
        self.w.end()
        # 데이터 갱신
        self.ticker = ticker

        self.split_Ticker(module)

        # 쓰레드 객체 생성 후 실행
        self.w = Worker(ticker, module)
        # 시그널 받기
        self.w.receiveUData.connect(self.getData_U)
        self.w.receiveBData.connect(self.getData_B)
        self.w.start()

    # 티커 자르는 함수
    def split_Ticker(self, module):
        if module == "Upbit":
            # 티커 자르기
            split_ticker = self.ticker.split('-')

            # 티커 설정
            self.tic_fiat = split_ticker[0]
            self.tic_coin = split_ticker[1]
        elif module == "Binance" or module == "Future":
            # 티커 자르기
            split_ticker = self.ticker.split('/')

            # 티커 설정
            self.tic_fiat = split_ticker[1]
            self.tic_coin = split_ticker[0]

    # 시그널에 연결된 슬롯. 업비트 데이터를 받아서 출력한다.
    def getData_U(self, data):
        d = data
        # 현재가
        self.price.setText(str(d['prev_closing_price']))
        # 변화율. 소수점 2자리까지
        self.diff.setText(f"{d['signed_change_rate'] * 100:.2f}" + '%')
        # 색상 변경
        self.updateStyle()

        # 거래량
        tic = self.tic_fiat
        self.volume.setText(f"{str(d['acc_trade_volume_24h'])} {tic}")
        # 거래금액. 억 단위. 소수점 2자리까지
        self.label_7.setText("거래금액(24H)")
        self.value.setText(f"{d['acc_trade_price_24h'] / 1000000000:,.2f} 억")
        # 시가
        self.open.setText(str(d['opening_price']))
        # 고가
        self.high.setText(str(d['high_price']))
        # 저가
        self.low.setText(str(d['low_price']))
        # 최근 거래가
        self.label_13.setText("최근 거래가")
        self.trade.setText(str(d['trade_price']))

    # 바이낸스 데이터를 받아서 출력
    def getData_B(self, data):
        d = data
        # 현재가
        self.price.setText(str(d['last']))
        # 변화율. 소수점 2자리까지
        self.diff.setText(f"{round(d['percentage'], 2)}" + '%')
        # 색상 변경
        self.updateStyle()

        # 거래량
        tic = self.tic_fiat
        self.volume.setText(f"{str(d['baseVolume'])} {tic}")
        # 평균 거래가
        self.label_7.setText("체결강도 평균가")
        self.value.setText(f"{round(d['vwap'], 2)}")
        # 시가
        self.label_11.setText("시작가(24H)")
        self.open.setText(str(d['open']))
        # 고가
        self.high.setText(str(d['high']))
        # 저가
        self.low.setText(str(d['low']))
        # 전날종가
        self.label_13.setText("평균가")
        self.trade.setText(str(round(d['average'], 3)))

    # 색상 변경
    def updateStyle(self):
        # 상승, 하락 여부 판단
        # 하락 시에는 파란색
        if self.diff.text()[0] == '-':
            self.price.setStyleSheet("color:blue")
            self.diff.setStyleSheet("color : white ; background-color : blue")
        # 상승 시에는 빨간색
        else:
            self.price.setStyleSheet("color:red")
            self.diff.setStyleSheet("color : white ; background-color : red")


# 모듈로 이용할 시에는 프로세스가 생성되지 않도록 하기 위함
if __name__ == "__main__":
    # UI 실행
    app = QApplication([])
    m = OverviewWidget()
    m.show()
    app.exec_()