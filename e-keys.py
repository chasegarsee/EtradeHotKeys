#!/usr/bin/env python
import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
from PyQt4 import QtGui
from PyQt4.QtCore import QTimer, QRegExp
import sys
import math
import json
from pprint import pprint
#import hkeys
#import ahkeys
#import ashkeystab as ash
import ashkeys5 as ash
#import ashkeys6
import etradepy

from etrade_settings import TRADESIZE

class EtradeApp(QtGui.QMainWindow, ash.Ui_MainWindow):
    def __init__(self, parent=None):
        super(EtradeApp, self).__init__(parent)
        self.setupUi(self)

        self.setWindowTitle(trading_account_name)

        self.cleartimer = QTimer()
        self.cleartimer.setSingleShot(True)
        self.cleartimer.timeout.connect(lambda : self.statusBar.showMessage( "" ) )
        self.Arm.stateChanged.connect(self.arm)

        qreq = QRegExp(r'frame.\d')
        frames = self.findChildren(QtGui.QFrame, qreq)
        for frame in frames:
            self.connectSignals( frame )


    def connectSignals( self, frame ):
        suffix     = frame.objectName()[-1]
        getattr( self, 'qty_'+suffix ).setText('0')   # Not a connect, but since we're dealing with this frame anyway...
        ticker     = getattr( self, 'T_'+suffix )
        header     = getattr( self, 'ticker_'+suffix )
        try: multiplier = getattr( self, 'multiplier_'+suffix )
        except AttributeError: pass
        quantity   = getattr( self, 'qty_'+suffix )
        try: price = getattr( self, 'price_'+suffix )
        except AttributeError: pass
        try: loss  = getattr( self, 'loss_'+suffix )
        except AttributeError: pass
        try: stop  = getattr( self, 'stop_'+suffix )
        except AttributeError: pass
        try: order  = getattr( self, 'order_'+suffix )
        except AttributeError: pass
        #
        quantity.textChanged.connect(lambda: self.showLongShort( quantity.objectName()[-1]))
        ticker.textChanged.connect(lambda: self.setTicker( ticker.text(), header, multiplier))
        #---- LONG --------------------------------------------------------------------------------
        try:
            buy = getattr( self, 'Buy_'+suffix )
            buy.clicked.connect( lambda: self.buy( ticker, quantity ) )
        except AttributeError:
            pass
        try:
            sell = getattr( self, 'Sell_'+suffix )
            sell.clicked.connect( lambda: self.sell( ticker, quantity ) )
        except AttributeError:
            pass
        try:
            limit = getattr( self, 'SLimit_'+suffix )
            limit.clicked.connect( lambda: self.slimit( ticker, quantity, price ) )
        except AttributeError:
            pass
        try:
            stoploss = getattr( self, 'SLoss_'+suffix )
            stoploss.clicked.connect( lambda: self.stoploss( ticker, quantity, loss ) )
        except AttributeError:
            pass
        try:
            b1x = getattr( self, 'B1K_'+suffix )
            b1x.clicked.connect(lambda: self.accumulate(ticker, multiplier.text(), quantity))
        except AttributeError:
            pass
        try:
            b2x = getattr( self, 'B2K_'+suffix )
            b2x.clicked.connect(lambda: self.accumulate(ticker, int(multiplier.text())*2, quantity))
        except AttributeError:
            pass
        try:
            sAll = getattr( self, 'SAll_'+suffix )
            sAll.clicked.connect(lambda: self.accumulate(ticker, -int(quantity.text()), quantity))
        except AttributeError:
            pass
        try:
            sHalf = getattr( self, 'SHalf_'+suffix )
            sHalf.clicked.connect(lambda: self.accumulate(ticker, -int(quantity.text())/2, quantity))
        except AttributeError:
            pass
        #---- SHORT -------------------------------------------------------------------------------
        try:
            ss1x = getattr( self, 'SH1x_'+suffix )
            ss1x.clicked.connect(lambda: self.accumulate(ticker, multiplier.text(), quantity, type='SHORT'))
        except AttributeError:
            pass
        try:
            ss2x = getattr( self, 'SH2x_'+suffix )
            ss2x.clicked.connect(lambda: self.accumulate(ticker, int(multiplier.text())*2, quantity, type='SHORT'))
        except AttributeError:
            pass
        try:
            bcA = getattr( self, 'BCa_'+suffix )
            bcA.clicked.connect(lambda: self.accumulate(ticker, int(quantity.text()), quantity, type='SHORT'))
        except AttributeError:
            pass
        try:
            bcHalf = getattr( self, 'BCh_'+suffix )
            bcHalf.clicked.connect(lambda: self.accumulate(ticker, int(quantity.text())/2, quantity, type='SHORT'))
        except AttributeError:
            pass
        try:
            order = getattr( self, 'order_'+suffix )
            bcx = getattr( self, 'Cx_'+suffix )
            bcx.setEnabled( True )
            bcx.clicked.connect(lambda: self.cancel( order, stop ))
        except AttributeError:
            pass
        try:
            order = getattr( self, 'order_'+suffix )
            bch = getattr( self, 'Chg_'+suffix )
            bch.setEnabled( True )
            bch.clicked.connect(lambda: self.change( order, ticker, quantity, stop ))
        except AttributeError:
            pass


    def cancel( self,  order, stop ):
        cx = etradepy.cancelOrder( trading_account, order.text() )
        pprint( cx )
        order.setText( '' )
        stop.setText( '' )


    def change( self, order, ticker, quantity, stop ):
        qty = int(quantity.text())
        if qty < 0:
            qty = -qty
            action = 'BUY_TO_COVER'
        else:
            action = 'SELL'

        ch = etradepy.placeEquityOrderChangeNow(
                trading_account,
                order.text(),
                ticker.text(),
                qty,
                action,
                stop.text()
            )
        pprint( ch )
        response = ch['placeChangeEquityOrderResponse']['equityOrderResponse']
        order.setText( str(response['orderNum']) )


    def setTicker( self, ticker, tickerLabel, multiplier ):
        """ Use ticker text to look up the price of the stock,
            set the ticker label text
            and set the multiplier input to the number of shares required to meet "TRADESIZE" setting
        """
        ticker = ticker.upper()
        #
        # UGLY - only looks up price when you add a space to the end of the ticker symbol
        #
        if len(ticker) and ticker[-1] == ' ':
            ticker = ticker[:-1]
            quote = etradepy.getQuote( ticker )
            try:
                price = quote['quoteResponse']['quoteData']['all']['lastTrade']
                quantity = TRADESIZE / price
                quantity = int(math.ceil(quantity / 10.0)) * 10
                multiplier.setText( str(quantity) )
            except KeyError:
                self.statusBar.showMessage( quote['quoteResponse']['quoteData']['errorMessage'] )
                pprint( quote )
        tickerLabel.setText( ticker )


    def accumulate(self, ticker, qty, counter, type='LONG'):
        if type == 'LONG':
            if qty < 0:
                result = self.sell(ticker, -qty)
            else:
                result = self.buy(ticker, qty)
        else:
            if qty < 0:
                result = self.buy_to_cover(ticker, -qty)
            else:
                result = self.sell_short(ticker, qty)
        if result:
            acc = int(counter.text())
            if acc == 0:
                print "START TIMER"
                # found 5 seconds didn't give time for short sales to complete
                timeout = 3500 if type == 'LONG' else 8000;
                qtimer.start(timeout)
            print acc
            print qty
            if type == 'LONG':
                counter.setText(str(acc + int(qty)))
            else:
                counter.setText(str(acc - int(qty)))
            suffix = counter.objectName()[-1]
            self.showLongShort( suffix )



    def buy_to_cover(self, ticker, qty):
        self.statusBar.showMessage( "Pending..." )
        try:
            qty = qty.text()
        except AttributeError:
            pass
        return self.report( etradepy.buyToCoverNow( trading_account, ticker.text(), qty ) )

    def sell_short(self, ticker, qty):
        try:
            qty = qty.text()
        except AttributeError:
            pass
        self.status_msg( "Pending..." )
        return self.report( etradepy.sellShortNow( trading_account, ticker.text(), qty ) )

    def buy(self, ticker, qty):
        self.statusBar.showMessage( "Pending..." )
        try:
            qty = qty.text()
        except AttributeError:
            pass
        return self.report( etradepy.buyNow( trading_account, ticker.text(), qty ) )

    def sell(self, ticker, qty):
        try:
            qty = qty.text()
        except AttributeError:
            pass
        self.status_msg( "Pending..." )
        return self.report( etradepy.sellNow( trading_account, ticker.text(), qty ) )

    def slimit(self, ticker, qty, price):
        self.status_msg( "Pending..." )
        return self.report( etradepy.sellLimitNow( trading_account, ticker.text(), qty.text(),price.text() ) )

    def stoploss(self, ticker, qty, trailing):
        self.status_msg( "Pending..." )
        return self.report( etradepy.sellStopNow( trading_account, ticker.text(), qty.text(),trailing.text() ) )

    def report(self, response):
        pprint( response )
        if 'Error' in response:
            print type(response)
            self.status_msg( response['Error']['message'] )
            msg = QMessageBox()
            msg.setIcon( QMessageBox.Error )
            msg.setText( "Order Placement Error")
            return False
        else:
            self.status_msg( response['PlaceEquityOrderResponse']['EquityOrderResponse']['messageList']['msgDesc'] )
            return True

    def status_msg( self, message ):
        self.statusBar.showMessage( message )
        self.cleartimer.start(9000)


    # TODO - attributes are grouped by basic and advanced control sets, could make finer granularity to allow them to be mixed
    def arm(self, int):
        state = self.Arm.isChecked()
        w = self.centralwidget
        p = w.palette()
        if state:
            p.setColor(w.backgroundRole(),QtGui.QColor(255,148,60))
        else:
            p.setColor(w.backgroundRole(),QtGui.QColor(73, 143, 255))
        w.setPalette(p)

        qreq = QRegExp(r'frame.\d')
        frames = self.findChildren(QtGui.QFrame, qreq)
        for frame in frames:
            suffix = frame.objectName()[-1]
            try:
                #
                w = getattr( self, 'Buy_'+suffix )
                w.setEnabled(state)
                w = getattr( self, 'Sell_'+suffix )
                w.setEnabled(state)
                w = getattr( self, 'SLimit_'+suffix )
                w.setEnabled(state)
                w = getattr( self, 'SLoss_'+suffix )
                w.setEnabled(state)
            except AttributeError:
                w = getattr( self, 'B1K_'+suffix )
                w.setEnabled(state)
                w = getattr( self, 'B2K_'+suffix )
                w.setEnabled(state)
                w = getattr( self, 'SAll_'+suffix )
                w.setEnabled(state)
                w = getattr( self, 'SHalf_'+suffix )
                w.setEnabled(state)
            try:
                w = getattr( self, 'SH1x_'+suffix )
                w.setEnabled(state)
                w = getattr( self, 'SH2x_'+suffix )
                w.setEnabled(state)
                w = getattr( self, 'BCa_'+suffix )
                w.setEnabled(state)
                w = getattr( self, 'BCh_'+suffix )
                w.setEnabled(state)
            except AttributeError:
                pass


    def showLongShort( self, suffix ):
        """ This function is called after every transaction, and ensures that
            LONG buttons are hidden if you are in a SHORT position, and vice versa

            ALSO called when the qty is changed directly by the user - only update
            the key states if the panel is "live" - Arm is checked
        """
        if self.Arm.isChecked():
            qty = getattr( self, 'qty_'+suffix )
            quantity = int( qty.text() )
            try:
                w = getattr( self, 'B1K_'+suffix )
                w.setEnabled(True)
                w = getattr( self, 'B2K_'+suffix )
                w.setEnabled(True)
                w = getattr( self, 'SAll_'+suffix )
                w.setEnabled(True)
                w = getattr( self, 'SHalf_'+suffix )
                w.setEnabled(True)
                w = getattr( self, 'SH1x_'+suffix )
                w.setEnabled(True)
                w = getattr( self, 'SH2x_'+suffix )
                w.setEnabled(True)
                w = getattr( self, 'BCa_'+suffix )
                w.setEnabled(True)
                w = getattr( self, 'BCh_'+suffix )
                w.setEnabled(True)
                if quantity > 0:
                    w = getattr( self, 'SH1x_'+suffix )
                    w.setEnabled(False)
                    w = getattr( self, 'SH2x_'+suffix )
                    w.setEnabled(False)
                    w = getattr( self, 'BCa_'+suffix )
                    w.setEnabled(False)
                    w = getattr( self, 'BCh_'+suffix )
                    w.setEnabled(False)
                if quantity < 0:
                    w = getattr( self, 'B1K_'+suffix )
                    w.setEnabled(False)
                    w = getattr( self, 'B2K_'+suffix )
                    w.setEnabled(False)
                    w = getattr( self, 'SAll_'+suffix )
                    w.setEnabled(False)
                    w = getattr( self, 'SHalf_'+suffix )
                    w.setEnabled(False)

            except AttributeError:
                pass


    def saveState( self ):
        data = {}
        qreq = QRegExp(r'frame.\d')
        frames = self.findChildren(QtGui.QFrame, qreq)
        for frame in frames:
            suffix = frame.objectName()[-1]
            try:
                w = getattr( self, 'T_'+suffix )
                data['t'+suffix] = w.text()
                w = getattr( self, 'qty_'+suffix )
                data['q'+suffix] = w.text()
                w = getattr( self, 'multiplier_'+suffix )
                data['m'+suffix] = w.text()
            except AttributeError:
                pass

            with open('state.txt', 'w') as outfile:
                json.dump( data, outfile )


    def restoreState( self ):
        try:
            with open('state.txt','r') as infile:
                data = json.load( infile )
        except IOError:
            return

        qreq = QRegExp(r'frame.\d')
        frames = self.findChildren(QtGui.QFrame, qreq)
        for frame in frames:
            suffix = frame.objectName()[-1]
            try:
                w = getattr( self, 'T_'+suffix )
                w.setText( data['t'+suffix] )
                w = getattr( self, 'qty_'+suffix )
                w.setText( data['q'+suffix] )
                w = getattr( self, 'multiplier_'+suffix )
                w.setText( data['m'+suffix] )
            except (AttributeError, KeyError) as e:
                pass

    def recordStopLossOrder( self ):
        resp = etradepy.placeStopLossOrder()
        response = resp['PlaceEquityOrderResponse']['EquityOrderResponse']
        # find frame  associated with this symbol
        #   fill in stop loss order details,
        #       save EquityOrderRequest with order number from
        #       EquityOrderResponse
        qreq = QRegExp(r'frame.\d')
        frames = self.findChildren(QtGui.QFrame, qreq)
        for frame in frames:
            suffix = frame.objectName()[-1]
            label = getattr( self, 'ticker_'+suffix )
            print( response['symbol'] )
            if label.text() == response['symbol']:
                print( label.text() )
                order = getattr( self, 'order_'+suffix )
                order.setText( str(response['orderNum']) )
                stop = getattr( self, 'stop_'+suffix )
                stop.setText( str(response['stopPrice']) )

def main():
    global trading_account
    global trading_account_name
    global qtimer

    # start connection to etrade
    etradepy.login()
    accounts =  etradepy.listAccounts()
    trading_account = accounts['json.accountListResponse']['response'][0]['accountId']
    trading_account_name = accounts['json.accountListResponse']['response'][0]['accountDesc']

    app = QtGui.QApplication(sys.argv)
    form = EtradeApp()
    form.show()
    form.statusBar.showMessage( accounts['json.accountListResponse']['response'][0]['accountDesc'])
    form.restoreState()
    #
    # This is a kludge to automatically place a stop loss order after placing a buy or a sell_short
    # Ideally we'd get a response from the server after the initial order executes, but instead
    # we set a short delay on qtimer in the placeEquityOrder function
    #
    qtimer = QTimer()
    qtimer.setSingleShot(True)
    qtimer.timeout.connect(form.recordStopLossOrder)

    app.aboutToQuit.connect(form.saveState)
    app.exec_()

if __name__ == '__main__':
    main()

