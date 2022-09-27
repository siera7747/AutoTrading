# 매매 데이터 설정 UI
from numpy import mod
import pyupbit
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic
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

ui = resource_path("dataset_U.ui")
form_class = uic.loadUiType(ui)[0]

# 위젯 클래스
class DatasetWidget(QWidget, form_class):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # 업비트의 티커 정보
        print("업비트 티커 정보 저장")
        self.up_tickers = pyupbit.get_tickers(fiat="KRW")

        # 바이낸스 티커 정보
        print("바이낸스 티커 정보 저장")
        binance = ccxt.binance()
        ticker = binance.load_markets()
        self.bi_tickers = []
        for m in ticker:
            if "/USDT" in m:
                self.bi_tickers.append(m)

        # 선물거래 티커 정보
        binance = ccxt.binance(config={
            'options':{
                'defaultType':'future'
            }
        })
        ticker = binance.load_markets()
        self.bf_tickers = []
        for m in ticker:
            if "/USDT" in m:
                self.bf_tickers.append(m)

        self.set_comboBox(self.up_tickers)

    # 모듈 변경 시 콤보 박스 내용물도 변경
    def change_Module(self, module):
        print("모듈 변경. 콤보 아이템 갱신")
        # 아이템 전부 삭제 후 다른 아이템으로 변경
        self.combo_ticker.clear()

        if module == "Upbit":
            self.set_comboBox(self.up_tickers)
        elif module == "Binance":
            self.set_comboBox(self.bi_tickers)
        elif module == "Future":
            self.set_comboBox(self.bf_tickers)

    # 콤보 박스에 아이템 추가 함수
    def set_comboBox(self, items):
        for t in items:
            self.combo_ticker.addItem(str(t))

# 모듈로 이용할 시에는 프로세스가 생성되지 않도록 하기 위함
if __name__ == "__main__":
    # UI 실행
    app = QApplication([])
    m = DatasetWidget()
    m.show()
    app.exec_()