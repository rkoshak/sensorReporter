# Copyright 2020 Richard Koshak
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This module includes the local logic core class.

Classes: LogicCore, LogicOr
"""
from abc import abstractmethod
import yaml
from core.actuator import Actuator
from core.utils import parse_values, is_toggle_cmd, verify_connections_layout

OUT_DEST = "Output"
IN_ENABLE_SRC = "Enable"
IN_INPUT = "Input"

LOCAL_CONN_STATE_TOPIC = "StateDest"
LOCAL_CONN_EQUAL_ATTRIB = "eq"

class LogicCore(Actuator):
    """Class from which all local logic capabilities must inherit. Is assumes there
    is a "InputSrc" param and automatically registers to subscribe to that topic
    with all of the passed in connections. A default implementation is provided
    for all but the process_message method which must be overridden.
    """
    def __init__(self, connections, dev_cfg):
        """Initializes the Actuator by storing the passed in arguments as data
        members and registers to subscribe to params("InputSrc").

        Arguments:
        - connections: List of the connections
        - dev_cfg: dictionary
            "Values":     optional,  Alternative values to publish instead of OFF / ON
        """
        super().__init__(connections, dev_cfg)

        self.enabled = True
        self.values = parse_values(dev_cfg, ["ON", "OFF"])


        self.known_inputs = []
        #grab inputs and register them one by one
        for (conn, subdict) in self.comm.items():
            #grab EnableSrc subdictionary and register
            if IN_ENABLE_SRC in subdict:
                self.connections[conn].register(subdict[IN_ENABLE_SRC], self.on_message)
            #grab InputSrc and register them one by one
            if IN_INPUT in subdict:
                for (param_name, src_list) in subdict[IN_INPUT].items():
                    # make sure we got the list containing the InputSrc
                    if isinstance(src_list, list):
                        for src in src_list:
                            def create_msg_handler(conn_src= conn + '_' + src,
                                                    l_conn = conn, l_param_name = param_name,
                                                    l_src = src):
                                self.known_inputs.append(conn_src)
                                def msg_handler(msg):
                                    if self.enabled:
                                        self.process_message(msg, conn_src)
                                    else:
                                        self.log.info("Actuator is disabled, ignoring command!")
                                self.connections[l_conn].register( {l_param_name : l_src },
                                                                   msg_handler)
                            create_msg_handler()

    def _register(self, comm, handler):
        """override register of parent so it does nothing
        """

    @abstractmethod
    def process_message(self, msg, src):
        """Abstract method that will get called when a any 'InputSrc' sends a message
        Implementers should execute the action the Actuator performs.

        Arguments:
            - msg : the message from the 'InputSrc'
            - src : the name of the calling 'InputSrc'
        """

    def on_message(self, msg):
        """Enable or Disable local logic depending on the send msg
        """
        self.enabled = (msg == "ON")
        self.log.info("%s received %s command for logic actuator",
                      self.name, "enable" if self.enabled else "disable")

    def _publish(self, message, comm, trigger=False):
        """Protected method that will publish the passed in message to the
        passed in destination to all the passed in connections.

        Parameter filter_echo is intended to activate a filter for looped back messages
        """
        for conn in comm.keys():
            #only publish to local connections (attrib eq)
            if hasattr(self.connections[conn], LOCAL_CONN_EQUAL_ATTRIB):
                self.connections[conn].publish(message, comm[conn], trigger)

class LogicOr (LogicCore):
    """Logical OR gate, can receive from multiple sensors
    and will trigger all configured receivers
    """
    def __init__(self, connections, dev_cfg):
        """Initializes the Actuator by storing the passed in arguments as data
        members and registers 'InputSrc' and 'EnableSrc' with the given connections

        Arguments:
        - connections: List of the connections
        - dev_cfg: lambda that returns value for the passed in key
            "Values":     Alternative values to publish instead of OFF / ON
            "Level : debug level
        """
        super().__init__(connections, dev_cfg)

        self.log.info("Configuring LogicOr %s", self.name)
        self.log.debug("%s has following configured connections: \n%s",
                       self.name, yaml.dump(self.comm))
        verify_connections_layout(self.comm, self.log, self.name,
                                  [IN_INPUT, IN_ENABLE_SRC, OUT_DEST])

        self.src_is_on = {}
        #split output list to subdicts if it's a local connection (attrib eq)
        count_outputs = 1
        for (conn, subdict) in self.comm.items():
            #check if it is a local connection
            if hasattr(self.connections[conn], LOCAL_CONN_EQUAL_ATTRIB):
                if OUT_DEST in subdict:
                    #assume the params 'StateDest' is present,
                    # since we checked it is a local connection
                    for out in subdict[OUT_DEST][LOCAL_CONN_STATE_TOPIC]:
                        self.comm[conn][OUT_DEST + str(count_outputs)] = {}
                        self.comm[conn][OUT_DEST + str(count_outputs)][LOCAL_CONN_STATE_TOPIC] = out
                        count_outputs += 1
        self.count_outs = count_outputs
        #delet old items
        for (conn, subdict) in self.comm.items():
            if hasattr(self.connections[conn], LOCAL_CONN_EQUAL_ATTRIB):
                if OUT_DEST in subdict:
                    del self.comm[conn][OUT_DEST]

        self.src_is_on = {}
        for src in self.known_inputs:
            self.src_is_on[src] = False
        self.output_activ = False
        self.last_output_state = False

    def process_message(self, msg, src):
        """Will switch the registered 'OutputDest' corresponding
        to the input message from the calling 'InputSrc'

        Arguments:
            - msg : the message from the 'InputSrc'
            - src : the name of the calling 'InputSrc'
        """
        self.last_output_state = self.output_activ

        if is_toggle_cmd(msg):
            self.output_activ = not self.output_activ
        else:
            self.src_is_on[src] = (msg == "ON")

            # if all InputSrc are OFF -> False
            # else -> True
            self.output_activ = bool(sum(self.src_is_on.values()))

        output = self.values[0] if self.output_activ else self.values[1]
        if self.last_output_state != self.output_activ:
            self.log.info("%s received command %s, from %s, forwarding command '%s'",
                           self.name, msg, src, output)

            for dest_num in range(1, self.count_outs):
                self._publish(output, self.comm, OUT_DEST + str(dest_num))
        else:
            self.log.info("%s received command %s, from %s, output %s doesn't change,"
                          " ignoring command!", self.name, msg, src, output)
