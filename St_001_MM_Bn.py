import ccxt
import time
from datetime import datetime, timedelta
import numpy as np

# 바이낸스 모듈
class BinanceModule:
    # 생성자 함수. 업비트 객체와 티커, 현금, 코인 원금 데이터
    def __init__(self, systemlog, mainlog):
        # 데이터 변수(원화 잔고, 코인 잔고)
        self.bal_fiat = 0
        self.bal_coin = 0
        # 종료 플래그
        self.quit = False
        # 원화 비율 플래그(False인 경우 지정한 값으로 설정)
        self.fiatrate = False
        # 원금 설정 시 시장가 매매 여부
        self.checkmarket = True
        # 가격 간격(매수, 매도)
        self.price_range = 0

        # 매수, 매도 가격 범위 설정값
        self.range_bid = []
        self.range_ask = []

        # 체결 대기 시간
        self.hour = 0
        self.min = 0
        self.sec = 1

        # 잔고 세팅 플래그
        self.balance_setting = True

        # 선물/현물 거래 플래그(디폴트는 현물)
        self.isfuture = False

        # 로그 설정
        self.systemlog = systemlog
        self.mainlog = mainlog

        # 바이낸스 일반 객체 생성
        self.binance = ccxt.binance()

        self.systemLog("모듈 객체 생성 완료")

    # 시스템 로그
    def systemLog(self, msg):
        self.systemlog.append(msg)

    # 변수 설정
    def setting(self, bid_rangelist, ask_rangelist, price_range, quit, check_market, timedata):
        self.systemLog("매매 관련 변수 설정")
        self.range_bid = bid_rangelist
        self.range_ask = ask_rangelist
        self.price_range = price_range
        self.quit = quit
        self.checkmarket = check_market
        self.hour = timedata[0]
        self.min = timedata[1]
        self.sec = timedata[2]

    # 로그인
    def login(self, key1, key2):
        # API 로그인
        self.systemLog("로그인 실행")
        # 선물/현물 객체 생성
        if self.isfuture:
            # 모듈 이름표
            self.module = "Future"
            # 옵션에 futrue를 지정하여 선물거래용 객체 생성
            self.bn = ccxt.binance(config={
                'apiKey' : key1,
                'secret' : key2,
                # 조회 제한 정보를 받아올 것인지
                'enableRateLimit' : True,
                'options' : {
                    'defaultType' : 'future'
                }
            })
        else:
            # 모듈 이름표
            self.module = "Binance"
            # 현물거래용 객체 생성
            self.bn = ccxt.binance({
                'apiKey' : key1,
                'secret' : key2
            })
        # 현재 잔고 중 원금으로 사용하지 않고 남긴 잔고량
        self.remainbal = 0
    
    # 원금 설정 함수
    def set_principal(self, data):
        self.systemLog("원금 데이터 설정 시작")
        # 각 데이터 저장(티커, 총 투자금, 원화 원금, 코인 원금)
        self.ticker = data[0]

        # 티커 자르기
        split_ticker = self.ticker.split('/')

        # 티커 설정
        self.tic_fiat = split_ticker[1]
        self.tic_coin = split_ticker[0]

        self.prin = data[1]
        fiat = data[2]
        coin = data[3]
        self.systemLog("티커, 투자금, 원화 원금, 코인 원금")
        self.systemLog(f"{data}")
        
        # 호가비율을 사용하는 경우 원금 설정을 지금 진행하지 않음
        if self.fiatrate:
            self.systemLog("호가 추종 설정이므로 원금 데이터 설정을 진행하지 않음")
            return True

        # 잔고 세팅
        ret = self.set_balance(coin)
        if ret == False:
            self.systemLog("잔고 세팅 실패")
            return False
        self.bal_fiat = fiat
        self.bal_coin = self.get_balance(self.tic_coin)
        # 잔고가 없을 경우
        if self.bal_coin == None:
            self.bal_coin = 0
        currentprice = self.get_currentprice(self.ticker)
        fiat = self.get_balance(self.tic_fiat)
        # 잔고가 없을 경우
        if fiat == None:
            fiat = 0
        self.systemLog("최종 코인 잔고")
        self.systemLog(f"{self.bal_coin}")
        # 원화 잔고가 투자금보다 큰 경우 남은 금액 모듈에 저장
        if fiat > self.bal_fiat:
            self.remainbal = fiat - self.bal_fiat
        else:
            self.remainbal = 0
        self.systemLog("미사용 원화 잔고")
        self.systemLog(f"{self.remainbal}")
        # 시작 투자금 내역 갱신
        self.prin = self.bal_fiat + (self.bal_coin * currentprice)
        self.prin_fiat = self.bal_fiat
        self.prin_coin = self.bal_coin
        self.systemLog(f"시작 투자금 : {self.prin}")
        # 주문 내역을 저장할 리스트
        self.order = []
        return True

    # 잔고를 세팅값으로 맞추는 함수
    def set_balance(self, coin):
        # 시장가 매매를 하지 않도록 설정했다면 바로 종료
        if not self.checkmarket:
            self.systemLog("잔고 세팅을 진행하지 않음")
            return True

        # 선물 거래인 경우 진행하지 않고 종료
        if self.isfuture:
            self.systemLog("잔고 세팅을 진행하지 않음")
            return True

        self.systemLog("잔고 세팅하기")
        # 현재 티커 잔고, 티커 원금 잔량 구하기
        currentprice = self.get_currentprice(self.ticker)
        self.systemLog(f"현재가 : {currentprice}")
        b = self.get_balance(self.tic_coin)
        if b == None:
            bal = 0
        else:
            bal = round(b, 8)
        startcoin = round(coin / currentprice, 8)
        self.systemLog(f"투자할 코인 갯수 : {startcoin}")

        order = []

        # 코인 잔금 세팅
        # 현재 코인 잔고가 설정한 초기 금액과 일치하도록 매매 진행
        if startcoin != bal:
            # 세팅값이 잔고보다 크면 매수
            if startcoin > bal:
                self.systemLog("매수로 잔고 맞추기")
                # 매수할 금액 구하기
                # 구매해야 하는 갯수
                volume = startcoin - bal
                # 금액
                price = currentprice * volume
                # 수수료 적용
                price = int(price * (1-0.001))
                volume = round(price / currentprice, 8)
                self.systemLog(f"매수할 금액 : {price}")
                self.systemLog(f"매수할 갯수 : {volume}")
                if price > 11:
                    # 매수
                    self.systemLog("시장가 매수")
                    ret = self.buy_market_order(self.ticker, volume)
                    order.append(ret['id'])
                    # 주문 체결 대기
                    check = self.wait_done(order)
                    if check == False:
                        return False
                    return True
                else:
                    self.systemLog("최소금액보다 작으므로 매매 진행하지 않음")
                    return True
            # 세팅값이 잔고보다 작으면 매도
            if startcoin < bal:
                self.systemLog("매도로 잔고 맞추기")
                # 매도할 개수 구하기
                volume = bal - startcoin
                p = volume * currentprice
                self.systemLog(f"매도할 금액 : {p}")
                if p > 11:
                    # 매도
                    self.systemLog("시장가 매도")
                    ret = self.sell_market_order(self.ticker, volume)
                    order.append(ret['id'])
                    # 주문 체결 대기
                    check = self.wait_done(order)
                    if check == False:
                        return False
                    return True
                else:
                    self.systemLog("최소금액보다 작으므로 매매 진행하지 않음")
                    return True
       
    # 종료
    def exit(self):
        self.systemLog("강제 종료")
        self.quit = True

    # 매매 실행 함수. 호가 데이터를 받는다.
    def excute_algorizm(self, data):
        self.systemLog("매매 시작")

        # 현물 거래
        if self.isfuture == False:
            self.systemLog("현물 거래")

            # 매도, 매수 데이터(데이터프레임.호가, 잔고 칼럼 존재)
            askdata = data[0]
            biddata = data[1]       

            # 데이터에서 호가만 꺼내 리스트로 생성
            askprice = self.get_collist(askdata, '호가')
            self.systemLog("매도 호가 리스트")
            self.systemLog(f"{askprice}")

            # 데이터에서 잔고만 꺼내서 리스트로 생성
            asklist = self.get_collist(askdata, '잔고')
            self.systemLog("매도 오더북 잔고 리스트")
            self.systemLog(f"{asklist}")

            bidprice = self.get_collist(biddata, '호가')
            self.systemLog("매수 호가 리스트")
            self.systemLog(f"{bidprice}")

            bidlist = self.get_collist(biddata, '잔고')
            self.systemLog("매수 오더북 잔고 리스트")
            self.systemLog(f"{bidlist}")

            # 원금 비율을 호가에 맞추는 경우 여기서 배분 진행
            if self.fiatrate:
                # 플래그 초기화
                self.balance_setting = True
                self.systemLog("호가에 맞춰 원금 세팅")
                self.fiatrate = False
                # 매도총액(매도호가 * 매도잔고)
                askvol = np.multiply(askprice, asklist)
                self.systemLog("호가 매도 총액 리스트")
                self.systemLog(f"{askvol}")
                # 매수총액(매수호가 * 매수잔고)
                bidvol = np.multiply(bidprice, bidlist)
                self.systemLog("호가 매수 총액 리스트")
                self.systemLog(f"{bidvol}")

                # 매도총액 합산, 매수총액 합산
                askvoltotal = sum(askvol)
                bidvoltotal = sum(bidvol)
                self.systemLog("매도총액 합산")
                self.systemLog(f"{askvoltotal}")
                self.systemLog("매수총액 합산")
                self.systemLog(f"{bidvoltotal}")
                # 원금 비율
                fiatrate = bidvoltotal / (askvoltotal + bidvoltotal)
                self.systemLog("원금 비율")
                self.systemLog(f"{fiatrate}")

                # 원금 재설정
                # 원금 잔고
                self.prin_fiat = self.get_balance(str(self.tic_fiat))
                # 잔고가 없을 경우
                if self.prin_fiat == None:
                    self.prin_fiat = 0
                self.systemLog("원화 잔고")
                self.systemLog(f"{self.prin_fiat}")
                # 코인 잔고
                self.prin_coin = self.get_balance(str(self.tic_coin))
                # 잔고가 없을 경우
                if self.prin_coin == None:
                    self.prin_coin = 0
                price = self.get_currentprice(str(self.ticker))
                coin = self.prin_coin * price

                self.prin = self.prin_fiat + coin

                fiat = self.prin_fiat

                # 원화, 코인 원금(잔고 세팅 하는 경우에만)
                if self.checkmarket == True:
                    fiat = self.prin * fiatrate
                    coin = self.prin - fiat
                # 티커, 투자금, 원화, 티커 원금 데이터
                data = [self.ticker, self.prin, fiat, coin]
                self.systemLog("티커, 투자금, 원화, 코인")
                self.systemLog(f"{data}")

                # 원화 비율을 설정한 경우. 바로 잔고 세팅 진행
                ret = self.set_principal(data)
                # 잔고 세팅 실패 시 종료
                if ret == False:
                    self.balance_setting = False
                    quit()
                self.fiatrate = True

            # 현재 자산 체크
            self.systemLog("원화, 코인 현재 잔고")
            self.systemLog(f"{self.bal_fiat}, {self.bal_coin}")

            # 가격 Range를 설정한 경우, 적용함
            self.systemLog("매도 가격 Range")
            self.systemLog(f"{self.range_ask}")
            self.systemLog("매수 가격 Range")
            self.systemLog(f"{self.range_bid}")
            if len(self.range_ask) != 0:
                self.systemLog("매도 가격 Range 적용")
                askrange = self.calculate_range(self.range_ask, 'ask')
                # 매도 원금 재분배
                askprincipal = self.bal_coin / self.range_ask[2]
                askprin = []
                for i in range(0, self.range_ask[2]):
                    askprin.append(askprincipal)
                askprice = askrange
                self.systemLog("재분배 매도 원금")
                self.systemLog(f"{askprin}")

            if len(self.range_bid) != 0:
                self.systemLog("매수 가격 Range 적용")
                bidrange = self.calculate_range(self.range_bid, 'bid')
                # 매수 원금 재분배
                bidprincipal = self.bal_fiat / self.range_bid[2]
                bidprin = []
                for i in range(0, self.range_bid[2]):
                    bidprin.append(bidprincipal)
                bidprice = bidrange 
                self.systemLog("재분배 매수 원금")
                self.systemLog(f"{bidprin}")

            if len(self.range_ask) == 0:
                # 잔고 비율 구하기
                askrate = self.get_sizerate(asklist)
                self.systemLog("매도 잔고 비율")
                self.systemLog(f"{askrate}")

                # 잔고 비율을 바탕으로 원금 배분하기(매도)
                askprin = self.divide_pricipal(askrate, self.bal_coin)
                self.systemLog("매도 원금")
                self.systemLog(f"{askprin}")

            if len(self.range_bid) == 0:
                bidrate = self.get_sizerate(bidlist)
                self.systemLog("매수 잔고 비율")
                self.systemLog(f"{bidrate}")

                bidprin = self.divide_pricipal(bidrate, self.bal_fiat)
                self.systemLog("매수 원금")
                self.systemLog(f"{bidprin}")

            # 종료 시그널 들어오면 종료
            if self.quit:
                quit()

            # 추정 현재가 = (매수 최고가 + 매도 최저가) / 2
            current = (max(bidprice) + min(askprice)) / 2

            # 매매 전 최소 가격 간격에 따른 지정 가격 갭 설정
            if self.price_range != 0 and (len(self.range_bid) == 0 or len(self.range_ask) == 0):
                self.systemLog("지정 가격 갭 설정")
                self.systemLog("추정 현재가")
                self.systemLog(f"{current}")
                # 지정 가격 갭 = 추정 현재가 * 지정 퍼센트 변수
                pricerange = current * (self.price_range / 100)
                self.systemLog("지정 가격 갭")
                self.systemLog(f"{pricerange}")
            else:
                self.systemLog("지정 가격 갭 없음")
                pricerange = current * 0.0012

            for i in range(0, len(bidprin)):
                # 매수 주문
                if bidprin[i] > 11:
                    self.systemLog("매수할 금액")
                    self.systemLog(f"{bidprin[i]}")
                    self.systemLog("주문가")
                    self.systemLog(f"{bidprice[i]}")
                    self.systemLog("최소 간격 계산치")
                    self.systemLog(f"{current - pricerange}")
                    # 주문가 < 추정현재가 - 지정 가격 갭일 때만 주문
                    if bidprice[i] < current - pricerange:
                        self.systemLog("매수 주문")
                        self.trade_bid(bidprin[i], bidprice[i])
                    else:
                        self.systemLog("최소 간격에 맞지 않으므로 주문 불가")
                else:
                    self.systemLog("최소 금액보다 적으므로 매수 불가")
                
                # API 제한 대비
                time.sleep(0.2)

                # 종료 시그널 들어오면 모든 주문 취소하고 종료
                if self.quit:
                    if len(self.order) > 0:
                        self.cancel_allorder(self.order)
                    quit()

                # 매도 주문
                if askprin[i] * askprice[i] > 11:
                    self.systemLog("매도할 금액")
                    self.systemLog(f"{askprin[i] * askprice[i]}")
                    self.systemLog("주문가")
                    self.systemLog(f"{askprice[i]}")
                    self.systemLog("최소 간격 계산치")
                    self.systemLog(f"{current + pricerange}")
                    # 주문가 > 추정현재가 + 지정 가격 갭일 때만 주문
                    if askprice[i] > current + pricerange:
                        self.systemLog("매도 주문")
                        self.trade_ask(askprin[i], askprice[i])
                    else:
                        self.systemLog("최소 간격에 맞지 않으므로 주문 불가")
                else:
                    self.systemLog("최소 금액보다 적으므로 매도 불가")

                # API 제한 대비
                time.sleep(0.2)

                # 종료 시그널 들어오면 모든 주문 취소하고 종료
                if self.quit:
                    if len(self.order) > 0:
                        self.cancel_allorder(self.order)
                    quit()
                        
            # 주문 정보 반환
            return self.order

    # 가격 Range에 따른 매매가 계산
    def calculate_range(self, rangelist, flag):
        self.systemLog("Range 계산")
        min = rangelist[0]
        max = rangelist[1]
        num = rangelist[2]
        current = self.get_currentprice(self.ticker)
        if flag == 'ask':
            if min != 0:
                minprice = current + (current * (min / 100))
            else:
                minprice = current
            maxprice = current + (current * (max / 100))
        else:
            if min != 0:
                maxprice = current - (current * (min / 100))
            else:
                maxprice = current
            minprice = current - (current * (max / 100))
        self.systemLog("최대가")
        self.systemLog(f"{maxprice}")
        self.systemLog("최소가")
        self.systemLog(f"{minprice}")
        pricelist = []
        ran = (maxprice - minprice) / (num - 1)
        # 최대, 최소가를 가지고 갯수만큼 분배한다.
        for i in range(0, num):
            p = round((minprice + (ran * i)), 8)
            pricelist.append(p)
        self.systemLog("매매 가격 리스트")
        self.systemLog(f"{pricelist}")
        return pricelist

    # 데이터에서 칼럼 리스트 생성하는 함수
    def get_collist(self, data, col):
        self.systemLog("칼럼 리스트 생성")
        list = []
        length = len(data)
        for i in range(0, length):
            bal = float(data[col][i])
            list.append(bal)
        
        return list
            
    # 매수 함수
    def trade_bid(self, prin, price):
        self.systemLog("매수 시작")
        # 배분한 원금(정산금액), 현재 호가
        # 매수할 갯수 구하기
        # 바이낸스 거래수수료는 0.1%
        unit = (prin - (prin * 0.001)) / price
        # 매수 진행 (매수할 티커, 주문 수량, 주문 가격)
        try:
            order = self.buy_limitorder(self.ticker, price, unit)
            uuid = order['id']
            self.order.append(uuid)
            self.systemLog("매수 성공. 주문번호")
            self.systemLog(f"{uuid}")
        except:
            self.systemLog("매수 오류")

    # 매도 함수
    def trade_ask(self, prin, price):
        self.systemLog("매도 시작")
        # 배분한 잔고(매도 수량), 현재 호가
        # 매도 진행 (매도할 티커, 매도 수량, 매도 가격)
        try:
            order = self.sell_limitorder(self.ticker, price, prin)
            uuid = order['id']
            self.order.append(uuid)
            self.systemLog("매도 성공. 주문번호")
            self.systemLog(f"{uuid}")
        except:
            self.systemLog("매도 오류")

    # 데이터를 바탕으로 각 리스트 잔고 비율 구하는 함수
    def get_sizerate(self, list):
        # 데이터는 가져온 호가창 데이터들 중 잔고만 따로 리스트를 만들어 넘긴 것
        # 잔고 데이터를 통해 새롭게 비율로 이루어진 리스트를 생성해 반환한다.
        self.systemLog("잔고 비율 구하기")
        s = sum(list)
        rate = []
        for d in list:
            rate.append(round((d / s) , 5))
        return rate

    # 원금을 잔고 비율만큼 배분하는 함수
    def divide_pricipal(self, rate, principal):
        self.systemLog("원금 배분 시작")
        # 원금을 각 잔고 비율만큼 배분
        self.systemLog("원금")
        self.systemLog(f"{principal}")
        price = []
        for r in rate:
            price.append(round(r * principal, 5))

        # 배분한 값의 합이 원금보다 크면 그만큼 차감
        self.systemLog("배분한 원금 합산")
        self.systemLog(f"{sum(price)}")
        if sum(price) > principal:
            for i in range(len(price)):
                price[i] = round(price[i] - ((sum(price) - principal) / len(price)), 5)
        return price

    # 현재 잔고 구하는 함수
    def get_balance(self, ticker):
        # 선물 잔고 조회
        if self.isfuture:
            b = self.bn.fetch_balance(params={"type":"future"})
            balance = b[ticker]['free']
        # 현물 잔고 조회
        else:
            b = self.bn.fetch_balance()
            balance = b[ticker]['free']
        # 티커
        return balance

    # 주문 취소하는 함수
    def cancel_order(self, uuid):
        self.systemLog("주문 취소")
        try:
            self.bn.cancel_order(uuid, self.ticker)
        except:
            pass

    # 모든 주문이 체결되기를 기다리는 함수
    def wait_done(self, order):
        self.systemLog("체결 대기 시작")
        # 현재 시간 저장
        now = datetime.now()
        # 대기 종료 시간
        end = now + timedelta(hours=self.hour, minutes=self.min, seconds=self.sec)
        self.systemLog("시작 시간")
        self.systemLog(f"{now}")
        self.systemLog("대기 종료 시간")
        self.systemLog(f"{end}")

        # 모든 주문이 체결될 때까지 루프
        waitorder = True
        donenum = 0
        self.systemLog(f"현재 주문 갯수 : {len(order)}")
        if len(order) == 0:
            self.systemLog("주문 내역 없음. 대기 종료")
            return True
        while waitorder:
            try:
                # 주문 체결 확인
                for i in range(0, len(order)):
                    # 미체결된 주문일 경우에만 조회
                    if order[i] != 'done':
                        # 주문 조회
                        self.systemLog("주문 조회")
                        ret = self.bn.fetch_order(order[i], self.ticker)
                        # 주문이 체결되었다면
                        if ret['status'] == "closed":
                            donenum += 1
                            price = float(ret['price'])
                            amount = float(ret['amount'])
                            volume = price * amount
                            self.mainlog.append("주문 체결 또는 취소됨")
                            self.mainlog.append(f"주문 : {ret['side']} / 체결가 : {price} / 체결량 : {amount} / 체결금액 : {volume}")
                            if ret['side'] == "buy":
                                with open('buyresult.txt', 'a', encoding='UTF-8') as f:
                                    f.write(f"체결가 : {price} / 체결량 : {amount} / 체결금액 : {volume}\n")
                                    f.close()
                            elif ret['side'] == "sell":
                                with open('sellresult.txt', 'a', encoding='UTF-8') as f:
                                    f.write(f"체결가 : {price} / 체결량 : {amount} / 체결금액 : {volume}\n")
                                    f.close()
                            self.set_tradeData(ret['side'], volume)
                            self.systemLog(f"{i}번째 주문 체결 또는 취소됨")
                            self.systemLog(f"주문 {donenum}개 처리 완료")
                            order[i] = "done"
                            # 모든 주문이 체결되었는지 확인
                            if donenum == len(order):
                                self.systemLog("모든 주문 처리 완료")
                                waitorder = False
                                return True
                            continue
                        self.systemLog(f"{i}번째 주문 미체결")
                        time.sleep(0.2)

                        # 종료 시그널 들어오면 종료
                        if self.quit:
                            self.systemLog("강제 종료. 모든 주문 취소")
                            waitorder = False
                            self.cancel_allorder(order)
                            break
                if self.quit:
                    break
                # 현재 시간 확인
                current = datetime.now()
                self.systemLog("종료 시간")
                self.systemLog(f"{end}")
                self.systemLog("현재 시간")
                self.systemLog(f"{current}")
                # 종료 시간이 지났다면 주문 전부 취소하고 대기 종료
                if end < current:
                    self.systemLog("체결 대기 종료. 주문 전부 취소")
                    self.cancel_allorder(order)
                    time.sleep(1)
                    waitorder = False
                    return True
                time.sleep(0.5)
            except:
                pass
    
    # 매매 금액 누적하기
    def set_tradeData(self, side, vol):
        # 매매 누적 합산 데이터 가져오기
        f = open('tradetotal.txt', 'r')
        tradetotal = []
        while True:
            line = f.readline().strip()
            if not line:
                break
            tradetotal.append(line)
        f.close()
        if len(tradetotal) == 0:
            tradetotal[0] = 0
            tradetotal[1] = 0
        if side == "buy":
            tradetotal[0] = float(tradetotal[0]) + vol
        elif side == "sell":
            tradetotal[1] = float(tradetotal[1]) + vol
        with open('tradetotal.txt', 'w', encoding='UTF-8') as f:
            for d in tradetotal:
                f.write(f"{str(d)}\n")

    # 미체결 주문 취소
    def cancel_allorder(self, order):
        self.systemLog("미체결 주문 전부 취소")
        self.systemLog(f"현재 주문 갯수 : {len(order)}")
        for i in range(0, len(order)):
            if order[i] != "done":
                self.systemLog("주문 조회")
                ret = self.bn.fetch_order(order[i], self.ticker)
                if ret['status'] != "closed":
                    # 주문 취소
                    self.bn.cancel_order(order[i], self.ticker)
                    self.systemLog(f"{i}번째 주문 취소 성공")
                    time.sleep(0.5)
        order = []
        self.systemLog("모든 주문 취소 완료")

    # 미체결 주문 확인하고 있다면 전부 취소
    def cancel_openorder_list(self, ticker):
        self.systemLog("미체결 주문 확인")
        open_orders = self.bn.fetch_open_orders(symbol=ticker)

        self.ticker = ticker

        # 미체결 주문이 있는 경우에만 진행
        if len(open_orders) != 0:
            self.systemLog("미체결 주문 있음. id 반환")
            # 주문 id 리스트 생성
            order = []
            for i in range(0, len(open_orders)):
                id = open_orders[i]['id']
                order.append(id)            
            self.cancel_allorder(order)
        self.systemLog("미체결 주문 없음")

    # 현재가 구하는 함수(티커 입력받음)
    def get_currentprice(self, ticker):
        self.systemLog(f"{ticker}의 현재가 구하기")
        current = self.binance.fetch_ticker(ticker)
        return current['close']

    # 시장가 매도
    def sell_market_order(self, ticker, vol):
        self.systemLog("시장가 매도")
        # 매도
        ret = self.bn.create_market_sell_order(ticker, vol)
        return ret

    # 시장가 매수
    def buy_market_order(self, ticker, vol):
        self.systemLog("시장가 매수")
        # 매수 진행
        ret = self.bn.create_market_buy_order(ticker, vol)
        return ret

    # 지정가 매수
    def buy_limitorder(self, ticker, price, vol):
        self.systemLog("지정가 매수")
        # 매수 진행
        ret = self.bn.create_limit_buy_order(ticker, vol, price)
        return ret

    # 지정가 매도
    def sell_limitorder(self, ticker, price, vol):
        self.systemLog("지정가 매도")
        # 매도 진행
        ret = self.bn.create_limit_sell_order(ticker, vol, price)
        return ret

    # 손, 익절 판단 함수. data는 손, 익절 기준치
    def check_end(self, data):
        self.systemLog("손, 익절 여부 확인")
        # 데이터 정리
        loss = data[0]
        profit = data[1]
        current = data[2]
        bid = data[3]
        order = []
        re = True
        # 종료 플래그
        self.quit = False
        # 재산이 손절기준보다 떨어지거나 익절기준보다 높아지면 스레드 종료
        if (loss != 0 and loss > current) or (profit != 0 and profit < current):
            self.systemLog("손절 혹은 익절 기준 만족")
            # 종료 시 매도 여부 확인
            if bid:
                self.systemLog("남은 코인 전부 매도")
                # 코인을 전부 시장가 매도
                # 잔고
                vol = self.get_balance(self.ticker[:3])
                # 현재가
                price_coin = self.get_currentprice(self.ticker)
                # 코인 금액
                p = vol * price_coin
                self.systemLog(f"매도할 금액 : {p}")
                if p > 5000:
                    while re:
                        # 매도
                        self.systemLog("시장가 매도")
                        ret = self.sell_market_order(self.ticker, vol)
                        order.append(ret['id'])
                        # 주문 체결 대기
                        check = self.wait_done(order)
                        if check:
                            re = False
                            break
                        order = []
                        time.sleep(0.5)
                else:
                    self.systemLog("최소금액보다 작으므로 매매 진행하지 않음")
                # 원금 재설정
                self.bal_coin = self.get_balance(self.tic_coin)
                self.bal_fiat = self.get_balance(self.tic_fiat)
                self.systemLog("코인 처리 완료")
                self.systemLog(f"현재 잔고 : {[self.bal_fiat, self.bal_coin]}")

            return True
        else:
            # 원금 재설정
            self.systemLog("매매 변수 초기화 후 재실행")
            coin = self.get_balance(self.tic_coin)
            fiat = self.get_balance(self.tic_fiat)
            if self.fiatrate:
                self.bal_fiat = fiat
            else:
                self.bal_fiat = fiat - self.remainbal
            self.bal_coin = coin
            self.order = []

            return False

    # 총 자산 구하기
    def get_allbalance(self):
        self.systemLog("현재 총 잔고 구하기")
        # 원금 잔고
        prin_fiat = self.get_balance(self.tic_fiat)
        # 잔고가 없을 경우
        if prin_fiat == None:
            prin_fiat = 0
        # 코인 잔고
        bal_coin = self.get_balance(self.tic_coin)
        # 잔고가 없을 경우
        if bal_coin == None:
            bal_coin = 0
        # 현재가
        price_coin = self.get_currentprice(self.ticker)
        # 코인 원금
        prin_coin = bal_coin * price_coin
        # 총 자산
        current = prin_fiat + prin_coin - self.remainbal
        self.systemLog("현재 잔액(미사용 금액 제외)")
        self.systemLog(f"{current}")
        ballist = [prin_fiat, bal_coin]
        self.systemLog(f"실제 잔고 : {ballist}")
        ballist = [prin_fiat, bal_coin, current]

        return ballist

    # 로그 내역 삭제
    def del_systemlog(self, isMaindel):
        print("로그 초기화")
        # 조건 만족 시 메인 로그도 삭제
        if isMaindel:
            print("메인 로그 포함 초기화")
            self.mainlog.clear()
        self.systemlog.clear()

if __name__ == "__main__":
    data = []
    for i in range(1, 10):
        data.append(i)

    m = BinanceModule()
    result = m.get_sizerate(data)
    print(result)