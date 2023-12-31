import time
import numpy as np
import serial
from command import interface, ser
from struct import pack, unpack

DEBUG = True
data_storage = ''

# Set the COM port and baud rate

# Open the serial connection

def log_debug(data):
    extras = ''
    print("-------------------",data)
    try:
        msgs = data.split('{')
        print(msgs)
        msgs = "\n".join([msg.split('}')[0] for msg in msgs if msg])
        with open('debug.log', 'a') as f:
                f.write(msgs + '\n^^^^^^^^^^^^^^^^^^^^\n')
    except:
        try:
            with open('errors.log', 'a') as f:
                f.write(data + '\n')
        except:
            pass
    if extras:
        return extras

# Functions 
def send_message(message):
    ser.write(message)

def receive_response(stop = b'\x00'):
    response = ser.read_until(stop)  # Reading until \0
    with open('aaaaaaa.log', 'a') as f:
        f.write(response.decode('utf-8') + '\n')
    return response[:-1]

# deprecated
def receive_data():
    try:
        data = receive_response()
        data = unpack("hhhhhh", data)
        #print(f'Received: {data}')
    except:
        #print(f'Error en leer mensaje [{data.decode("utf-8")}]')
        raise Exception()
    return data

def receive_data_print():
    global data_storage
    try:
        data = receive_response(b'>').decode('utf-8')
        if '{' in data:
            data = log_debug(data)
            
        if not data:
            return 
        data = data.split('<')[1].split('>')[0].split('|')
        #print(f'Received: {data}')
    except:
        data_storage += data
        if DEBUG: log_debug(data)
        # print(f'Error en leer mensaje [{data}]')
        raise Exception()

    return data

def convert_value_data(l, type = int):
    l = [type(i) for i in l]
    return np.array(l)

def convert_complex_data(l):
    # [ftax, ftay, ..., ftgy, ftgz] = l
    for i, dim  in enumerate(l):
        # 'val1-val2-...-valn' = dim
        dim = dim.split(';')
        for j, val in enumerate(dim):
            # 'real,imag' = val
            real, imag = val.split(',')
            dim[j] = complex(float(real), float(imag))
        l[i] = dim

    return l


def mult_n_round(num, factor, digs):
    return round(num*factor, digs)

def interpret_data(data):
    acc_x, acc_y, acc_z, gyr_x, gyr_y, gyr_z = data
    sensor = ['Accelerometer', 'Accelerometer', 'Gyroscope']
    units = ['m/s^2', 'g', 'rad/s']
    factors = [78.4532/32768, 8.000/32768, 34.90659/32768]
    values = [[acc_x, acc_y, acc_z], [acc_x, acc_y, acc_z], [gyr_x, gyr_y, gyr_z]]
    
    #print(f"|    Sensor   |{'X':<9}|{'Y':<9}|{'Z':<9}|{'units':^6}|")
    #print( "|-------------|---------|---------|---------|---------|")
    for sens, vals, fact, unit in zip(sensor, values, factors, units):
        x, y, z = vals
        x = mult_n_round(x, fact, 7)
        y = mult_n_round(y, fact, 7)
        z = mult_n_round(z, fact, 7)
        #print(f'|{sens:^13}|{x:^10}|{y:^10}|{z:^10}|{unit:^6}|')
    
    
  
def send_end_message():
    end_message = pack('4s', 'END\0'.encode())
    ser.write(end_message)

def retrieve_storage():
    global data_storage
    if not data_storage:
        return None
    if '<' not in data:
        data_storage = ''
        print("\n\n\n STORAGE CLEARED \n\n\n")
    if '>' not in data:
        print("\n\n STORAGE NOT READY \n\n")
        return None
    split = data_storage.split('<')[1].split('>')
    data = split[0].split('|')
    data_storage = split[1]
    print("             ", data)
    return data



def monitor():
    if not interface():
        return False
    # Send "BEGIN" message
    message = pack('6s','BEGIN\0'.encode())
    ser.write(message)

    # Read data from the serial port, waiting for the data
    # counter = 0
    desync = 0
    while True:
        if ser.in_waiting > 0:
            try:
                message = receive_data_print()
                if message is None:
                    message = retrieve_storage()
                    if message is None:
                        desync += 1
                        continue
                if message == ['RESET']:
                    print(message)
                    break
                vals, rms_vals, fts, peaks = message

                # separate values as string lists
                vals = vals.split('\t')
                rms_vals = rms_vals.split('\t')
                fts = fts.split('\t')
                peaks = peaks.split('&')

                # convert acc & gyr values to int
                vals = convert_value_data(vals, int)
                # convert rms values to float
                rms_vals = convert_value_data(rms_vals, float)
                # parse out ft values
                fts = convert_complex_data(fts)
                #convert peaks values to float in m/s²
                peaks_accx = convert_value_data(peaks[0].split('\t'),float)*(78.4532/32768)
                peaks_accy = convert_value_data(peaks[1].split('\t'),float)*(78.4532/32768)
                peaks_accz = convert_value_data(peaks[2].split('\t'),float)*(78.4532/32768)
                peaks_gyrx = convert_value_data(peaks[3].split('\t'),float)*(34.90659/32768)
                peaks_gyry = convert_value_data(peaks[4].split('\t'),float)*(34.90659/32768)
                peaks_gyrz = convert_value_data(peaks[5].split('\t'),float)*(34.90659/32768)

                interpret_data(vals)
                print("RMS:", rms_vals)
                print("acc_x Peaks:", peaks_accx,"m/s²")
                print("acc_y Peaks:", peaks_accy,"m/s²")
                print("acc_z Peaks:", peaks_accz,"m/s²")
                print("gyr_x Peaks:", peaks_gyrx,"rad/s")
                print("gyr_y Peaks:", peaks_gyry,"rad/s")
                print("gyr_z Peaks:", peaks_gyrz,"rad/s")
                print("FTS:", fts)
            except serial.SerialTimeoutException:
                break
            except Exception as e:
                desync += 1
                if desync == 100:
                    break
                continue

            # else: 
            #     counter += 1
            #     #print(counter)
            # finally:
            #     if counter == 10000:
            #         #print('Lecturas listas!')
            #         break
        # else: # 0 bytes a leer
        #     desync += 1
        #     if desync == 100:
        #         break
    return True

on = True
while on:
    on = monitor()

ser.close()
        