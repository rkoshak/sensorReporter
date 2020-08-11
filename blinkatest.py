import time
import board
import adafruit_dht

print("Hello blinka!")

dht = adafruit_dht.DHT22(board.D4)

while True:
    try:
        temperature = dht.temperature
        humidity = dht.humidity
        if temperature and humidity:
            print("Temp: {} *C \t Humidity: {}%".format(temperature, humidity))
        else:
            print("None reading returned: temp = {} humi = {}".format(temperature, humidity))
    except RuntimeError as e:
        print("Reading from DHT failure: %s", e.args)

    time.sleep(1)

print("done!")
