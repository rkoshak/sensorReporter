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

""" Communicator that publishes and subscribes to openHAB's REST API.
    Classes:
        - openhab_rest: publishes state updates to openHAB Items.
"""
from threading import Thread, Timer
from typing import Callable, Optional, Union, Any, Dict
import json
import traceback
import requests
import sseclient
from core.connection import Connection, ConnState

class OpenhabREST(Connection):
    """ Publishes a state to a given openHAB Item. Expects there to be a URL
        parameter set to the base URL of the openHAB instance. Subscribes to the OH
        SSE feed for commands on the registered Items.
    """

    def __init__(self,
                 msg_processor:Callable[[str], None],
                 conn_cfg:Dict[str, Any]) -> None:
        """ Starts the SSE subscription and registers for commands on
            RefreshItem. Expects the following params:
            - "URL": base URL of the openHAB instance NOTE: does not support TLS.
            - "RefreshItem": Name of the openHAB Item that, when it receives a
                             command will cause sensor_reporter to publish
                             the most recent states of all the sensors.
            - msg_processor: message handler for command to the RefreshItem
        """
        super().__init__(msg_processor, conn_cfg)
        self.log.info("Initializing openHAB REST Connection...")

        self.openhab_url = conn_cfg["URL"]
        self.refresh_item = conn_cfg["RefreshItem"]
        self.registered[self.refresh_item] = msg_processor

        # Optional OpenHAB Version and optional API-Token for connections with authentication
        try:
            self.openhab_version = float(conn_cfg["openHAB-Version"])
        except KeyError:
            self.log.info("No openHAB-Version specified, falling back to version 2.0")
            self.openhab_version = 2.0
        if self.openhab_version >= 3.0:
            self.api_token = conn_cfg.get("API-Token", "")

            if not bool(self.api_token):
                self.log.info("No API-Token specified,"
                " connecting to openHAB without authentication")

        # Read certificate settings
        self.verify_cert:Union[bool, str] = True
        if conn_cfg.get("TLSinsecure", False):
            self.verify_cert = False
        else:
            cert = conn_cfg.get("CAcert", '')
            if cert:
                self.verify_cert = cert
        self.log.info("Attempting to connect to openHAB REST at %s,"
                      " TLS certificate %s",
                      self.openhab_url, self.verify_cert)

        self.reciever:Optional[OpenhabReciever] = None

        # Initiate openHAB connection by running check_connection for the first time
        self.close_connection = False   # Stops 'check_connection' on demand
        self.conn_check:Timer
        self.check_connection()

    def check_connection(self) -> None:
        """ Runs every 30 seconds to check if the openHAB REST-API
            is available. If yes and not connected initiate connection.
            If connected but the API is not reachable switch to offline mode.
        """
        header = None
        conn_error = False
        conn_success = False
        if self.openhab_version >= 3.0 and bool(self.api_token):
            header = {'Authorization': 'Bearer ' + self.api_token }

        try:
            response = requests.get(f'{self.openhab_url}/rest',
                                  headers=header, stream=False, verify=self.verify_cert)
            self.log.debug("Connection checker: got response code: %s for URL %s/rest",
                           response.status_code, self.openhab_url)
            response.raise_for_status()
            conn_success = True
        except requests.exceptions.Timeout:
            self.log.error("Connection checker: %s timed out", self.openhab_url)
            conn_error = True
        except requests.exceptions.ConnectionError as ex:
            # Occurs when openHAB server is down
            self.log.error("Connection checker: failed connecting to %s, response: %s",
                           self.openhab_url, ex)
            conn_error = True
        except requests.exceptions.HTTPError as ex:
            self.log.error("Received an unsuccessful response code %s", ex)
            conn_error = True

        if conn_success:
            if self.state in [ConnState.INIT, ConnState.OFFLINE]:
                self.log.info("Connected to openHAB %s", self.openhab_url)
                self.reciever = OpenhabReciever(self, header)
                super().conn_went_online()
        elif conn_error:
            if self.state == ConnState.ONLINE:
                self.log.info("Disconnected from openHAB %s", self.openhab_url)
                if self.reciever:
                    # Stop old instance
                    self.reciever.stop()
                super().conn_went_offline()

        if not self.close_connection:
            self.conn_check = Timer(30, self.check_connection)
            self.conn_check.start()

    def publish(self,
                message:str,
                comm_conn:Dict[str, Any],
                output_name:Optional[str] = None) -> None:
        """ Publishes the passed in message to the passed in destination as an update.

        Arguments:
        - message:     the message to process / publish, expected type <string>
        - comm_conn:   dictionary containing only the parameters for the called connection,
                       e. g. information where to publish
        - output_name: optional, the output channel to publish the message to,
                       defines the sub-directory in comm_conn to look for the return topic.
                       When defined the output_name must be present
                       in the sensor YAML configuration:
                       Connections:
                           <connection_name>:
                                <output_name>:
        """
        if self.reciever:
            self.reciever.start_watchdog()

        #if output_name is in the communication dict parse it's contents
        local_comm = comm_conn[output_name] if output_name in comm_conn else comm_conn
        destination = local_comm.get('Item')

        #if output_name (output) is not present in comm_conn, Item will be None
        if destination is None:
            return

        try:
            self.log.debug("Publishing message %s to %s", message, destination)
            # openHAB 2.x doesn't need the Content-Type header
            header = None
            if self.openhab_version >= 3.0:
                # define header for OH3 communication and authentication
                header = {'Content-Type': 'text/plain'}
                if bool(self.api_token):
                    header['Authorization'] = "Bearer " + self.api_token
            response = requests.put(f'{self.openhab_url}/rest/items/{destination}/state',
                                    headers=header, data=message,
                                    timeout=10, verify=self.verify_cert)
            if response.status_code == 401:
                # 401 = unauthorized, API-Key required
                self.log.error("Can't publish message,"
                               " received error unauthorized! Consider to set a 'API-Token'!")
            else:
                response.raise_for_status()
                if self.reciever:
                    self.reciever.activate_watchdog()
        except ConnectionError:
            self.log.error("Failed to connect to %s\n%s", self.openhab_url,
                           traceback.format_exc())
            super().conn_went_offline()
        except requests.exceptions.Timeout:
            self.log.error("Timed out connecting to %s", self.openhab_url)
        except requests.exceptions.ConnectionError as ex:
            # Handles exception "[Errno 111] Connection refused"
            # which is not caught by above "ConnectionError"
            self.log.error("Failed to connect to %s, response: %s", self.openhab_url, ex)
            super().conn_went_offline()
        except requests.exceptions.HTTPError as ex:
            self.log.error("Received an unsuccessful response code %s", ex)

    def disconnect(self) -> None:
        """ Stops the event processing loop."""
        self.log.info("Disconnecting from openHAB SSE")
        self.close_connection = True
        if self.reciever:
            self.reciever.stop()
        self.conn_check.cancel()

    def register(self,
                 comm_conn:Dict[str, Any],
                 handler:Optional[Callable[[str], None]]) -> None:
        """ Set up the passed in handler to be called for any message on the
            destination. Alternate implementation using 'Item' as Topic
        """
        #handler can be None if a sensor registers it's outputs
        if handler:
            self.log.info("Registering destination %s", comm_conn['Item'])
            self.registered[comm_conn['Item']] = handler

class OpenhabReciever():
    """ Subscribes to SSE events from openHAB and
        initiates a separate Task for receiving the events.
    """

    def __init__(self,
                 caller:OpenhabREST,
                 header:Optional[Dict[str, str]]) -> None:
        """  Parameter:
            - caller    : The class object from the calling OpenhabREST
            - header    : HTTP header which is send to openHAB when
                          subscribing to events
        """
        self.stop_thread = False
        self.client = self.subscribe_to_events(caller, header)
        self.caller = caller
        self.watchdog:Optional[Timer] = None
        self.watchdog_activ = False
        # In case of a connection error don't start the get_messages thread
        if self.client:
            self.thread = Thread(target=self._get_messages, args=(caller,))
            self.thread.start()

    @staticmethod
    def subscribe_to_events(caller:OpenhabREST,
                            header:Optional[Dict[str, str]]) -> Optional[sseclient.SSEClient]:
        """ Subscribe to SSE events and start processing the events
            if API-Token is provided and supported then include it in the request
            Parameter:
                - header    : HTTP header to send to openHAB
        """
        client:Optional[sseclient.SSEClient] = None
        try:
            stream = requests.get(f'{caller.openhab_url}/rest/events',
                                  headers=header, stream=True, verify=caller.verify_cert)
            # The type checker doesn't understand requests.response is compatible with
            # Generator[bytes, None, None] required by SSEClient
            client = sseclient.SSEClient(stream)   # type: ignore

        except requests.exceptions.Timeout:
            caller.log.error("Timed out connecting to %s", caller.openhab_url)
        except requests.exceptions.ConnectionError as ex:
            caller.log.error("Failed to connect to %s, response: %s", caller.openhab_url, ex)
        except requests.exceptions.HTTPError as ex:
            caller.log.error("Received and unsuccessful response code %s", ex)

        return client

    def _get_messages(self,
                      caller:OpenhabREST) -> None:
        """ Blocks until stop is set to True. Loops through all the events on the
            SSE subscription and if it's a command to a registered Item, call's that
            Item's handler.
        """
        if self.client is None:
            return
        for event in self.client.events():
            # reset reconnect watchdog
            if self.watchdog:
                self.watchdog.cancel()

            if self.stop_thread:
                self.client.close()
                caller.log.debug("Old openHab connection closed")
                return

            # See if this is an event we care about. Commands on registered Items.
            decoded = json.loads(event.data)
            if decoded["type"] == "ItemCommandEvent":
                # openHAB 2.x locates the items on a different url
                if caller.openhab_version < 3.0:
                    item = decoded["topic"].replace("smarthome/items/",
                                                    "").replace("/command", "")
                else:
                    item = decoded["topic"].replace("openhab/items/",
                                                    "").replace("/command", "")
                if item in caller.registered:
                    payload = json.loads(decoded["payload"])
                    msg = payload["value"]
                    caller.log.info("Received command from %s: %s", item, msg)
                    caller.registered[item](msg)
        caller.log.debug("Connection interrupted: old openHab connection closed")
        self.client.close()

    def _wd_timeout(self) -> None:
        """ Watchdog: check if subscription to openHAB SSE events
            is still active, if not resubscribe. Whenever OpenhabREST
            sends a message to openHAB we expect a response.
            If the response is not received within 2s we consider the
            connection expired.
        """
        if self.watchdog_activ:
            self.caller.log.info("connection EXPIRED, reconnecting")
            self.stop()
            # The events stream is broken, set state to INIT so check_Connection
            # will reinitialize stream
            self.caller.state = ConnState.INIT

    def start_watchdog(self) -> None:
        """ Start watchdog before msg gets sent to openhabREST
            if the watchdog gets activated and after 2s no msg from openHAB was
            received the connection gets reseted
        """
        if self.watchdog:
            self.watchdog.cancel()
        self.watchdog_activ = False
        self.watchdog = Timer(2, self._wd_timeout)
        self.watchdog.start()

    def activate_watchdog(self) -> None:
        """ Enable watchdog after msg was successful send (no exception due to connection error)
            avoids a reconnect attempt when the connection was unsuccessful
        """
        self.watchdog_activ = True

    def stop(self) -> None:
        """ Sets a flag to stop the _get_messages thread and to close the openHAB connection.
            Since the thread itself blocks until a message is received we won't wait for it
        """
        self.stop_thread = True
