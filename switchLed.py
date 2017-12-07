occupiedPin = None
unoccupiedPin = None

def init(params):
    global occupiedPin
    global unoccupiedPin
    
    pins = params('StateCallbackArgs').split(',')
    occupiedPin = pins[0]
    unoccupiedPin = pins[1]

def stateChange(state, params, actuators):
    global occupiedPin
    global unoccupiedPin
    
    print(state)
    
    if (state == 1):
        actuators[occupiedPin].on_direct_message("ON")
        actuators[unoccupiedPin].on_direct_message("OFF")
    else:
        actuators[occupiedPin].on_direct_message("OFF")
        actuators[unoccupiedPin].on_direct_message("ON")
