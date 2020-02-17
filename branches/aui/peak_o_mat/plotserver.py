__author__ = 'kristukat'

import wx
from pubsub import pub

from peak_o_mat import spec

import pickle

import time
import numpy as np

#from multiprocessing.connection import Listener

import zmq
import zmq.backend.cython.error

from threading import Thread, Event

class Server(Thread):
    def __init__(self, controller):
        super(Server, self).__init__()
        self.controller = controller
        self._stopevent = Event()
        self._sleepperiod = 0.1

    # def run(self):
    #     address = ('localhost', 6000)     # family is deduced to be 'AF_INET'
    #     listener = Listener(address, authkey='secret password')
    #
    #     conn = listener.accept()
    #     while not self._stopevent.isSet():
    #
    #         message = conn.recv()
    #         try:
    #             data = pickle.loads(message)
    #         except KeyError as e:
    #             print e
    #         else:
    #             try:
    #                 assert data['data'].ndim == 2
    #             except AssertionError as e:
    #                 print "bad data"
    #             else:
    #                 print "ok"
    #                 wx.CallAfter(self.controller.do_something, data)
    #                 listener.close()
    #                 conn = listener.accept()
    #
    #         self._stopevent.wait(self._sleepperiod)
    #     print 'stopping'
    #     listener.close()

    def run(self):
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind("tcp://*:6789")

        while not self._stopevent.isSet():
            try:
                #check for a message, this will not block
                data = socket.recv_pyobj(flags=zmq.NOBLOCK)
            except zmq.Again as e:
                time.sleep(0.1)
                continue
            #try:
            #    data = pickle.loads(message)
            #except KeyError as e:
            #    socket.send_string("bad data")
            #    print e
            #else:
            try:
                assert data['data'].ndim == 2
            except AssertionError as e:
                socket.send_string("bad data")
            else:
                socket.send_string("ok")
                wx.CallAfter(self.controller.do_something, data)

            self._stopevent.wait(self._sleepperiod)

    def join(self, timeout=None):
        """ Stop the thread and wait for it to end. """
        self._stopevent.set( )
        super(Server, self).join(timeout)

class PlotServer:
    def __init__(self, view_id):
        self.instid = view_id

        pub.subscribe(self.stop, (self.instid, 'stop_all',))

    def start(self):
        try: # check if port is available
            context = zmq.Context()
            socket = context.socket(zmq.REP)
            socket.bind("tcp://*:6789")
        except zmq.ZMQError as e:
            print(e)
            return False
        else:
            del socket
            self.comm_server = Server(self)
            self.comm_server.start()

            return True

    def stop(self):

        try:
            self.comm_server.join()
        except:
            pass

    def do_something(self, data):
        x = data['data'][0,:]
        y = np.atleast_2d(data['data'][1:,:])
        for n,_y in enumerate(y):
            s = spec.Spec(x,_y,'{}_col{}'.format(data['name'],n))
            pub.sendMessage((self.instid, 'set.add'), spec=s)

