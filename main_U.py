# 메인 윈도우
from PyQt5.QtWidgets import *
from PyQt5.QtChart import *
from PyQt5 import uic
from PyQt5.QtCore import *
import St_001_MM_U 
import St_001_MM_Bn
from pandas import DataFrame
import time
import threading
import sys
import os

from multiprocessing import freeze_support
freeze_support()

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ui = resource_path("main_U.ui")
form_class = uic.loadUiType(ui)[0]

# 자동매매 로직을 실행하는 쓰레드
class Worker(QThread):
    # 시그널 정의
    tradingMessageSent = pyqtSignal(str)
    # 종료 시그널
    exitlogin_Up = pyqtSignal(St_001_MM_U.OrderbookAlgorizm)
    exitlogin_Bi = pyqtSignal(St_001_MM_Bn.BinanceModule)
    # 시스템 로그
    systemlog = pyqtSignal(str)
    dellog = pyqtSignal(bool)

    # data는 티커, 총재산, 원화, 티커 원금 데이터
    def __init__(self, orderbook, flag, module, log):
        super().__init__()
        self.systemlog.emit("스레드 생성. 변수 설정")
        # 모듈 객체
        self.module = module
        # 호가창 테이블 리스트
        self.orderbook = orderbook
        # 손절, 익절 기준치, 매매 종료 후 매도 여부
        self.loss = flag[0]
        self.profit = flag[1]
        self.bid = flag[2]
        # 로그
        self.log = log

    # 로그 상태 확인
    def check_log(self):
        if self.log[1].toPlainText() == '':
            print("로그 내용 없음")
            return True
        else:
            print("로그 내용 있음")
            return False

    # 종료 메서드
    def end(self):
        self.systemlog.emit("스레드 종료")
        self.alive = False
        self.module.exit()
        self.quit()
        self.systemlog.emit("로그아웃")
        if self.module.module == "Upbit":
            self.exitlogin_Up.emit(self.module)
        else:
            self.exitlogin_Bi.emit(self.module)

    # 쓰레드 실행 시 실행되는 함수
    def run(self):
        self.systemlog.emit("스레드 실행")
        # 매매 진행 중인지 확인하기 위한 변수
        self.alive = True
        # 매수, 매도 주기를 나타내는 변수.
        roll_over = True

        # 매매 주기 카운트
        count = 0

        # 자동매매 로직 실행
        while self.alive:
            self.systemlog.emit("반복문 시작")

            # 티커 자르기
            split_ticker = self.module.ticker.split('/')

            # 티커 설정
            tic_fiat = split_ticker[1]
            tic_coin = split_ticker[0]

            # 예외처리
            try:
                # 매매 주기마다 실행
                if roll_over:
                    self.systemlog.emit("매매 실행")
                    prin_fiat = self.module.get_balance(str(tic_fiat))
                    prin_coin = self.module.get_balance(str(tic_coin))
                    currentprice = self.module.get_currentprice(self.module.ticker)
                    prin = prin_fiat + (prin_coin * currentprice)
                    # 결과 저장
                    # file_path = resource_path('result.txt')
                    with open('result.txt', 'a', encoding='UTF-8') as f:
                        f.write(f"매매 시작. 원화 : {round(prin_fiat, 5)} / 코인 : {round(prin_coin, 5)} / 재산 : {round(prin, 5)}\n")
                        f.close()

                    self.tradingMessageSent.emit(f"매매 시작. 원화 : {round(prin_fiat, 5)} / 코인 : {round(prin_coin, 5)} / 재산 : {round(prin, 5)}")
                    # 호가창 테이블로부터 현재 매도, 매수 데이터를 데이터프레임으로 얻는다.
                    askdata = self.get_Tabledata(self.orderbook[0])
                    biddata = self.get_Tabledata(self.orderbook[1])
                    orderbookdata = [askdata, biddata]
                    # 모듈을 통해 매매 실행 - 현재 호가 데이터 넘기고 주문 데이터 받음
                    order = self.module.excute_algorizm(orderbookdata)
                    self.systemlog.emit("매매 종료")
                    roll_over = False
            except:
                self.systemlog.emit("매매 중 취소/오류 발생")
                self.systemlog.emit("반복문 종료")
                if self.alive:
                    self.tradingMessageSent.emit(f"매매 오류 발생. 종료")
                    self.end()
                break
            
            # 체결 확인
            self.module.wait_done(order)

            # 종료 플래그
            if self.alive == False:
                break
            
            # 총 자산 구하기
            currentlist = self.module.get_allbalance()

            # 현재 자산
            current_fiat = currentlist[0]
            current_coin = currentlist[1]
            current = currentlist[2]
            
            # 시작 가격 대비 손절, 익절 적용
            # 손절, 익절 기준값이 0인 경우 기준치를 계산하지 않음
            if self.loss == 0:
                self.systemlog.emit("손절 기준 없음")
                loss = 0
            else:
                self.systemlog.emit("손절 기준 계산")
                loss = self.module.prin * (1 - (self.loss / 100))
                self.systemlog.emit(f"{loss}")

            if self.profit == 0:
                self.systemlog.emit("익절 기준 없음")
                profit = 0
            else:
                self.systemlog.emit("익절 기준 계산")
                profit = self.module.prin * (1 + (self.profit / 100))
                self.systemlog.emit(f"{profit}")
            
            # 종료 플래그
            if self.alive == False:
                break

            # 현재 매매 상황 로그에 올리기
            # 결과 저장
            # file_path = resource_path('result.txt')
            with open('result.txt', 'a', encoding='UTF-8') as f:
                f.write(f"매매 종료. 현재 원화 : {round(current_fiat, 5)} / 현재 코인 : {round(current_coin, 5)} / 현재 재산 : {round(current, 5)}\n")
                f.close()
            self.tradingMessageSent.emit(f"매매 종료. 현재 원화 : {round(current_fiat, 5)} / 현재 코인 : {round(current_coin, 5)} / 현재 재산 : {round(current, 5)}")

            # 손, 익절 여부 판단용 데이터. 손절 기준치, 익절 기준치, 현재 자산
            checkdata = [loss, profit, current, self.bid]

            # 종료 플래그
            if self.alive == False:
                break

            # 재산이 손절기준보다 떨어지거나 익절기준보다 높아지면 스레드 종료
            if self.module.check_end(checkdata):
                self.end()
                break
            else:
                roll_over = True

            # # 로그 초기화
            # if count == 10:
            #     print("10번 반복했으니 메인로그 초기화")
            #     isDel = True
            #     count = 0
            # else:
            #     print("시스템 로그만 초기화")
            #     isDel = False
            # self.dellog.emit(isDel)

            # # 로그 삭제될때까지 대기
            # print("로그 초기화 대기")
            # self.wait_logInit()

            time.sleep(2)

    # 로그 삭제 대기 함수
    def wait_logInit(self):
        while(True):
            print(self.check_log())
            if self.check_log() == True:
                print("로그 초기화 완료")
                time.sleep(1)
                break
            time.sleep(1)

    # 테이블 데이터를 데이터프레임으로 반환하는 함수
    def get_Tabledata(self, table):
        self.systemlog.emit("테이블 데이터 변환")
        # 행, 열 갯수
        rowcount = table.rowCount()
        colcount = table.columnCount()

        # 데이터가 들어갈 리스트
        item = []
        data = []

        # 데이터 수집
        for i in range(0, rowcount):
            item = []
            for j in range(0, colcount-1):
                d = table.item(i, j)
                item.append(d.text())
            data.append(item)

        # 데이터프레임으로 변환
        df = DataFrame(data, columns=['호가', '잔고'])

        return df

class MyWindow(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        # uic.loadUi("UI/main_U.ui", self)
        self.setupUi(self)

        # 버튼 텍스트 설정 - 로그인 
        self.btn.setText("login")

        # 버튼 클릭 시 로그인 실행
        self.btn.clicked.connect(self.login)

        # 콤보박스 기본값 저장
        self.ticker = "KRW-XRP"
        self.module = "Upbit"

        # 모듈 설정
        self.set_Module(self.module)

        # 티커 적용
        self.datasetWidget.combo_ticker.setCurrentText(self.ticker)

        # 콤보 박스 내부 값이 기존과 다르게 설정될 때마다 호가창, 개요창을 그에 맞게 변경
        self.datasetWidget.combo_ticker.currentTextChanged.connect(self.changedTicker)

        # 모듈 버튼 선택
        self.datasetWidget.rBtn_U.clicked.connect(self.select_Module)
        self.datasetWidget.rBtn_B.clicked.connect(self.select_Module)
        self.datasetWidget.rBtn_BF.clicked.connect(self.select_Module)

        # 데이터 저장/로드 버튼
        self.datasetWidget.Btn_Save.clicked.connect(self.save_click)
        self.datasetWidget.Btn_Load.clicked.connect(self.load_click)

        # 코인 전량 매도 버튼
        self.datasetWidget.btn_sell.clicked.connect(self.sell_click)

        self.print_balance()

    # 코인 매도 버튼 클릭
    def sell_click(self):
        reply = self.set_checkMsgbox("현재 선택한 코인을 전량 시장가 매도하시겠습니까")
        if reply == QMessageBox.No:
            return
        # 코인 시장가 매도
        self.m.sell_market_order(self.ticker, self.bal_coin)
        # 잔고 확인, 표시
        self.print_balance()

    # 세이브 버튼 클릭
    def save_click(self):
        reply = self.set_checkMsgbox("현재 설정을 저장하시겠습니까")
        if reply == QMessageBox.No:
            return
        data = []
        # 최소 가격 간격
        price_range = self.datasetWidget.spin_pricerange.value()
        data.append(price_range)
        # 매매 금액 비율
        prin_rate = self.datasetWidget.line_prin.text()
        data.append(prin_rate)
        # 코인 페어 비율
        ticker_rate = self.datasetWidget.line_ticker.text()
        data.append(ticker_rate)
        # 손절 기준치
        loss = self.datasetWidget.line_loss.text()
        data.append(loss)
        # 익절 기준치
        profit = self.datasetWidget.line_profit.text()
        data.append(profit)
        # 가격 범위 설정 값 가져오기(매수, 매도)
        range_bidmin = self.datasetWidget.spin_bidmin.value()
        data.append(range_bidmin)
        range_bidmax = self.datasetWidget.spin_bidmax.value()
        data.append(range_bidmax)
        range_bidnum = self.datasetWidget.spin_bidnum.value()
        data.append(range_bidnum)
        range_askmin = self.datasetWidget.spin_askmin.value()
        data.append(range_askmin)
        range_askmax = self.datasetWidget.spin_askmax.value()
        data.append(range_askmax)
        range_asknum = self.datasetWidget.spin_asknum.value()
        data.append(range_asknum)
        # 데이터 저장
        self.save_data(data)
        self.systemLog("설정 저장 완료")

    # 로드 버튼 클릭
    def load_click(self):
        reply = self.set_checkMsgbox("마지막으로 저장한 설정을 불러오시겠습니까")
        if reply == QMessageBox.No:
            return
        # 데이터 불러오기
        data = self.load_data()
        # 최소 가격 간격
        self.datasetWidget.spin_pricerange.setValue(int(data[0]))
        # 매매 금액 비율
        self.datasetWidget.line_prin.setText(data[1])
        # 코인 페어 비율
        self.datasetWidget.line_ticker.setText(data[2])
        # 손절 기준치
        self.datasetWidget.line_loss.setText(data[3])
        # 익절 기준치
        self.datasetWidget.line_profit.setText(data[4])
        # 가격 범위 설정 값 가져오기(매수, 매도)
        self.datasetWidget.spin_bidmin.setValue(int(data[5]))
        self.datasetWidget.spin_bidmax.setValue(int(data[6]))
        self.datasetWidget.spin_bidnum.setValue(int(data[7]))
        self.datasetWidget.spin_askmin.setValue(int(data[8]))
        self.datasetWidget.spin_askmax.setValue(int(data[9]))
        self.datasetWidget.spin_asknum.setValue(int(data[10]))
        self.systemLog("불러오기 완료")

    # 모듈 선택 함수
    def select_Module(self):
        # 로그 내역 초기화
        self.del_systemlog(True)
        self.systemLog("모듈 변경")
        if self.datasetWidget.rBtn_U.isChecked():
            self.systemLog("Upbit")
            self.module = "Upbit"
            self.datasetWidget.change_Module(self.module)
            self.set_Module(self.module)
        elif self.datasetWidget.rBtn_B.isChecked():
            self.systemLog("Binance")
            self.module = "Binance"
            self.datasetWidget.change_Module(self.module)
            self.set_Module(self.module)
        elif self.datasetWidget.rBtn_BF.isChecked():
            self.systemLog("Future")
            self.module = "Future"
            self.datasetWidget.change_Module(self.module)
            self.set_Module(self.module)

    # 티커 변경할 때마다 실행되는 함수
    def changedTicker(self):
        self.systemLog("티커 변경")
        # 콤보 박스가 비워졌을 때는 실행하지 않음
        if self.datasetWidget.combo_ticker.currentText() == "":
            self.systemLog("콤보 박스 비었음")
            return
        if self.datasetWidget.combo_ticker.currentText() != self.ticker:
            self.ticker = self.datasetWidget.combo_ticker.currentText()
            
            # 개요창, 호가창, 차트 데이터 변경
            self.overviewWidget.changeTicker(self.ticker, self.module)
            time.sleep(0.2)
            self.chartWidget.changeTicker(self.ticker, self.module)
            time.sleep(0.2)
            self.orderbookWidget.changeTicker(self.ticker, self.module)
            time.sleep(0.2)

        # 티커 설정
        self.split_ticker()

        # 잔고 구하기
        self.print_balance()

        # 콤보 박스 비활성화
        self.datasetWidget.combo_ticker.setEnabled(False)
        self.start = time.time()
        self.systemLog("타이머 시작")
        self.Timer(4)

    # 현재 잔고 구해서 로그에 출력
    def print_balance(self):
        self.systemLog("현재 티커")
        self.systemLog(f"{self.ticker}")
        # 원금 잔고
        self.prin_fiat = self.m.get_balance(str(self.tic_fiat))
        # 잔고가 없을 경우
        if self.prin_fiat == None:
            self.prin_fiat = 0
        self.systemLog("원화 잔고")
        self.systemLog(f"{self.prin_fiat}")
        # 코인 잔고
        self.bal_coin = self.m.get_balance(str(self.tic_coin))
        # 잔고가 없을 경우
        if self.bal_coin == None:
            self.bal_coin = 0
        self.systemLog("코인 잔고")
        self.systemLog(f"{self.bal_coin}")

    # 타이머
    def Timer(self, sec):
        timer = threading.Timer(1, self.Timer, args=[sec])
        timer.start()

        # 지정한 시간이 지나면 타이머 종료
        current = time.time()
        if (current - self.start) > sec:
            timer.cancel()
            # 콤보 박스 활성화
            self.datasetWidget.combo_ticker.setEnabled(True)
            self.systemLog("타이머 종료")

    # 모듈 설정
    def set_Module(self, module):
        if module == "Upbit":
            self.m = St_001_MM_U.OrderbookAlgorizm(self.systemlog, self.log)

            # 파일에서 키 값 읽기
            # file_path = resource_path("upbit.txt")
            with open("upbit.txt", "r") as f:
                key1 = f.readline().strip()
                key2 = f.readline().strip()

            # lineEdit에 키 값 넣기
            self.key1.setText(key1)
            self.key2.setText(key2)

            # 티커 자르기
            self.split_ticker()

        elif module == "Binance":
            self.m = St_001_MM_Bn.BinanceModule(self.systemlog, self.log)

            # 파일에서 키 값 읽기
            # file_path = resource_path("Binance.txt")
            with open("Binance.txt", "r") as f:
                key1 = f.readline().strip()
                key2 = f.readline().strip()

            # lineEdit에 키 값 넣기
            self.key1.setText(key1)
            self.key2.setText(key2)

            # 티커 자르기
            self.split_ticker()

        elif module == "Future":
            self.m = St_001_MM_Bn.BinanceModule(self.systemlog, self.log)

            # 파일에서 키 값 읽기
            # file_path = resource_path("Binance.txt")
            with open("Binance.txt", "r") as f:
                key1 = f.readline().strip()
                key2 = f.readline().strip()

            # lineEdit에 키 값 넣기
            self.key1.setText(key1)
            self.key2.setText(key2)

            # 티커 자르기
            self.split_ticker()

        # API 로그인
        self.m.login(self.key1.text(), self.key2.text())

    # 티커 자르는 함수
    def split_ticker(self):
        if self.module == "Upbit":
            # 티커 자르기
            split_ticker = self.ticker.split('-')

            # 티커 설정
            self.tic_fiat = split_ticker[0]
            self.tic_coin = split_ticker[1]
        elif self.module == "Binance" or self.module == "Future":
            # 티커 자르기
            split_ticker = self.ticker.split('/')

            # 티커 설정
            self.tic_fiat = split_ticker[1]
            self.tic_coin = split_ticker[0]

    # 데이터 저장
    def save_data(self, data):
        self.systemLog("데이터 저장")
        # file_path = resource_path('data.txt')
        with open('data.txt', 'w', encoding='UTF-8') as f:
            for d in data:
                f.write(f"{str(d)}\n")

    # 데이터 불러오기
    def load_data(self):
        self.systemLog("데이터 불러오기")
        # file_path = resource_path('data.txt')
        f = open('data.txt', 'r')
        data = []
        while True:
            line = f.readline().strip()
            if not line:
                break
            data.append(line)
        f.close()
        return data
            
    # 로그인
    def login(self):
        # 버튼 텍스트 상황으로 로그인 상황 파악
        if self.btn.text() == "login":
            if self.module == "Future":
                self.set_Msgbox("선물 거래는 아직 구현 중")
                return
            # 입력 데이터 확인
            if self.check_linedata(self.datasetWidget.line_prin.text()) == False:
                self.set_Msgbox("매매 금액 비율 1~100 사이의 숫자를 입력하세요")
                return
            if self.check_linedata(self.datasetWidget.line_ticker.text()) == False:
                if self.datasetWidget.line_ticker.text() != '0':
                    self.set_Msgbox("원화 비율 0~100 사이의 숫자를 입력하세요")
                    return
            if self.check_linedata(self.datasetWidget.line_loss.text()) == False:
                if self.datasetWidget.line_loss.text() != '0':
                    self.set_Msgbox("손절 기준치 0~100 사이의 숫자를 입력하세요")
                    return
            if self.check_linedata(self.datasetWidget.line_profit.text()) == False:
                if self.datasetWidget.line_profit.text() != '0':
                    self.set_Msgbox("익절 기준치 0~100 사이의 숫자를 입력하세요")
                    return
            hour = self.datasetWidget.spin_hour.value()
            min = self.datasetWidget.spin_min.value()
            sec = self.datasetWidget.spin_sec.value()
            if hour == 0 and min == 0 and sec == 0:
                self.set_Msgbox("대기 시간을 설정해주세요")
                return

            # 로그 내역 초기화
            self.del_systemlog(True)

            if self.module == "Future":
                self.systemLog("선물거래 선택")
                return
            else:
                # 미체결 주문이 있다면 전부 취소
                self.m.cancel_openorder_list(self.ticker)

                self.systemLog("매매 관련 데이터 가져오기")

                self.systemLog("대기 시간")
                timedata = [hour, min, sec]
                
                # 가격 범위 설정 값 가져오기(매수, 매도)
                range_bidmin = self.datasetWidget.spin_bidmin.value()
                range_bidmax = self.datasetWidget.spin_bidmax.value()
                range_bidnum = self.datasetWidget.spin_bidnum.value()

                range_askmin = self.datasetWidget.spin_askmin.value()
                range_askmax = self.datasetWidget.spin_askmax.value()
                range_asknum = self.datasetWidget.spin_asknum.value()
                
                # 최소값 > 최대값인 경우 실행하지 않음
                if range_bidmin > range_bidmax or range_askmin > range_askmax:
                    self.set_Msgbox("최소값은 최대값보다 작아야 합니다")
                    return

                # 각 범위 값을 리스트에 넣음
                self.systemLog("가격 Range")
                if range_bidnum != 0:
                    bid_rangelist = [range_bidmin, range_bidmax, range_bidnum]
                else:
                    bid_rangelist = []
                if range_asknum != 0:
                    ask_rangelist = [range_askmin, range_askmax, range_asknum]
                else:
                    ask_rangelist = []

                # 최소 가격 간격 값
                self.systemLog("최소 간격 갭")
                price_range = self.datasetWidget.spin_pricerange.value()         

                # 종료 플래그 초기화
                quit = False

                # 시장가 매매(초기 원금 설정) 여부 확인
                self.systemLog("시장가 매매로 잔고 세팅 여부")
                check_market = self.datasetWidget.check_market.isChecked()
                
                # 호가창에서 호가 테이블 정보 가져오기
                self.systemLog("호가 테이블 정보")
                asktable = self.orderbookWidget.askTable
                bidtable = self.orderbookWidget.bidTable
                orderbookdata = [asktable, bidtable]

                # 버튼 텍스트 설정 - 로그아웃
                self.btn.setText("logout")

                # 데이터 설정
                # 특정 %만큼 손실 시 종료할지 설정
                loss = int(self.datasetWidget.line_loss.text())
                # 특정 %만큼 이득 시 종료할지 설정
                profit = int(self.datasetWidget.line_profit.text())
                # 매매 종료 시 모든 코인을 매각할지 설정
                bid = self.datasetWidget.check_bid.isChecked()

                self.systemLog("손절, 익절 기준치와 종료 시 매각 여부")
                flag = [loss, profit, bid]

                self.systemLog("매매 설정 시작")

                # 코인 현재가
                price_coin = self.m.get_currentprice(self.ticker)

                # 모듈 변수 설정
                self.m.setting(bid_rangelist, ask_rangelist, price_range, quit, check_market, timedata)

                # 코인 원금
                prin_coin = self.bal_coin * price_coin
                # 총 자산(소수점 버림)
                principal = int(self.prin_fiat + prin_coin)
                self.systemLog("총 잔고")
                self.systemLog(f"{principal}")
                # 자산으로 데이터 생성
                data = self.divide_principal(principal)
                # 원화 비율을 설정한 경우. 바로 잔고 세팅 진행
                ret = self.m.set_principal(data)
                # 잔고 세팅 실패 시 종료
                if ret == False:
                    self.btn.setText("login")
                    self.log.append(f"원금 세팅 실패 / 로그아웃")
                    self.restart()
                    return

                # 로그에 로그인 여부와 현 자산 표시
                self.log.append(f"로그인 성공")
                fiat = self.m.get_balance(str(self.tic_fiat))
                # 잔고가 없을 경우
                if fiat == None:
                    fiat = 0
                coin = self.m.get_balance(str(self.tic_coin))
                # 잔고가 없을 경우
                if coin == None:
                    coin = 0
                currentprice = self.m.get_currentprice(self.ticker)
                # 코인 원금
                prin_coin = coin * currentprice
                # 총 자산(소수점 버림)
                principal = int(fiat + prin_coin)
                self.log.append(f"{self.tic_fiat} : {str(fiat)} / {self.tic_coin} : {str(coin)}(전체 재산 : {principal}(소수점 버림))")
            
            # 로그 객체
            log = []
            log.append(self.log)
            log.append(self.systemlog)
            # 자동매매 로직을 실행할 쓰레드 객체 생성
            self.w = Worker(orderbookdata, flag, self.m, log)

            # 자동매매 로직을 실행할 쓰레드 객체 실행
            # 넘겨주는 데이터는 업비트 객체, 원금 데이터, 호가 테이블 데이터, 종료 플래그데이터
            self.w.tradingMessageSent.connect(self.receiveMessage)
            self.w.exitlogin_Bi.connect(self.endlogin)
            self.w.exitlogin_Up.connect(self.endlogin)
            self.w.systemlog.connect(self.systemLog)
            self.w.dellog.connect(self.del_systemlog)
            self.w.start()
        else:
            # 자동매매 쓰레드 종료
            self.w.end()
            self.btn.setText("login")     

    # 로그 내역 삭제
    def del_systemlog(self, isMaindel):
        # 조건 만족 시 메인 로그도 삭제
        if isMaindel:
            print("메인 로그 포함 초기화")
            self.clear_log(self.log)
            # 로그 객체 데이터를 다시 모듈에 넘긴다.
            self.m.mainlog = self.log
        print("로그 초기화")
        self.clear_log(self.systemlog)
        # 로그 객체 데이터를 다시 모듈에 넘긴다.
        self.m.systemlog = self.systemlog

    # 로그 상태 확인
    def check_log(self):
        if self.systemlog.toPlainText() == '':
            return True
        else:
            return False

    # 잔고 세팅 오류 시 재시작하는 함수
    def restart(self):
        self.systemLog("재시작")
        self.login()

    # 주어진 총 자산으로 기본 원금 배분하는 함수
    def divide_principal(self, principal):
        self.systemLog("원금 배분 시작")
        # 총 자산 대비 투입 비율
        per_bal = int((self.datasetWidget.line_prin.text())) / 100
        # 투자할 금액
        bal = principal * per_bal
        # 원화 비율
        fiatrate = int(self.datasetWidget.line_ticker.text())
        # 원화 비율에 0을 입력한 경우, 호가창에 비율을 맞춰야 함
        if fiatrate != 0:
            per_fiat = int((self.datasetWidget.line_ticker.text())) / 100
            # 원화, 코인 원금
            fiat = bal * per_fiat
            coin = bal - fiat
        else:
            self.systemLog("호가 추종 설정이므로 배분을 진행하지 않음")
            self.m.fiatrate = True
            fiat = 0
            coin = 0

        # 티커, 투자금, 원화, 티커 원금 데이터
        data = [self.ticker, bal, fiat, coin]
        self.systemLog("티커, 투자금, 원화, 코인")
        self.systemLog(f"{data}")
        
        return data

    # 기준치, 비율에 1~100 사이의 숫자가 들어갔는지 검사하는 함수
    def check_linedata(self, linedata):
        if linedata.isdigit() == False:
            return False
        elif int(linedata) < 1 or int(linedata) > 100:
            return False
        else:
            return True       

    # 경고 메세지 박스 띄우기
    def set_Msgbox(self, msg):
        QMessageBox.warning(self, '경고', msg, QMessageBox.Ok)

    # 확인 메세지 박스 띄우기
    def set_checkMsgbox(self, msg):
        reply = QMessageBox.warning(self, '확인', msg, QMessageBox.Yes | QMessageBox.No)
        return reply

    # 시그널로 전송받은 메세지를 처리할 메서드
    def receiveMessage(self, msg):
        # 로그에 문자열 추가
        self.log.append(msg)

    # 시스템 로그에 문자열 추가
    def systemLog(self, msg):
        self.systemlog.append(msg)

    def endlogin(self, module):
        # 자동매매 쓰레드 종료
        self.btn.setText("login")
        time.sleep(1)
        self.log.append(f"로그아웃 성공 / 자동매매 종료")
        self.m = module
        self.w.quit()

        # 잔고 세팅 오류일 경우 재시작
        if self.m.balance_setting == False:
            self.restart()

    # 로그 내용 전부 삭제
    def clear_log(self, log):
        log.clear()

    # 프로세스 강제 종료
    def closeEvent(self, event):
        self.overviewWidget.closeEvent(event)
        self.chartWidget.closeEvent(event)
        self.orderbookWidget.closeEvent(event)

if __name__ == "__main__":
    app = QApplication([])
    m = MyWindow()
    m.show()
    app.exec_()