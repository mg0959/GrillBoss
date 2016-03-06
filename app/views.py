__author__ = 'Grant Martin'
from app import app, Arduino, socketio
from flask import render_template, session, request, current_app
from flask.ext.socketio import emit, disconnect
from config import MAX_WEB_UPDATE_TIME
import celery_tasks
import datetime, uuid

@app.route('/')
@app.route('/index')
@app.route('/gb')
def index():
    return render_template("index.html")

@socketio.on('get arduinoStatus', namespace='/data')
def arduinoStatus():
    emit('statusData', makeStatusDict(), broadcast=True)
    task = celery_tasks.say_hey.delay()


@socketio.on('disconnect request', namespace='/data')
def disconnect_request():
    print 'Disconnecting client'
    emit('disconnected response', {'data': 'Disconnected'})
    disconnect()


@socketio.on('connect', namespace='/data')
def socket_connect():
    socketId = str(uuid.uuid4())
    current_app.clients.append(socketId)
    session['socketId'] = socketId
    print "Client Connected. Active sockets:", len(app.clients)
    #Arduino.start_socket_interval_readings(1)
    emit('connected response', {'socketId': socketId})
    emit('new leader', {'leader':app.clients[0]})


@socketio.on('disconnect', namespace='/data')
def socket_disconnect():
    current_app.clients.remove(session['socketId'])
    #if len(app.clients) < 1: Arduino.stop_socket_interval_readings()
    #else: emit('new leader', {'leader':app.clients[0]})
    print 'Client disconnected. Active Sockets:', len(app.clients)

@socketio.on_error(namespace='/data')
def data_error_handler(e):
    print('An error has occurred: ' + str(e))

def makeStatusDict():
        statusDict = {"time":Arduino.lastUpdate.strftime("%Y-%m-%d %H:%M:%S"),
              "FB1_Ag1":Arduino.firebox1.woodAuger.status,
              "FB1_HE1":Arduino.firebox1.heatingElement.status,
              "FB2_Ag1":Arduino.firebox2.woodAuger.status,
              "FB2_HE1":Arduino.firebox2.heatingElement.status,
              "CS1_HE_top":Arduino.coldSmoker.heatingElementTop.status,
              "CS1_HE_bot":Arduino.coldSmoker.heatingElementBottom.status,
              "CS1_AP":Arduino.coldSmoker.airPump.status}
        for i in range(8):
            statusDict["T"+str(i+1)] = Arduino.thermometers[i].temp

        return statusDict