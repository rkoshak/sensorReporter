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

"""Communicator that publishes and subscribes to openHAB's REST API.
Classes:
    - openhab_rest: publishes state updates to openHAB Items.
"""
from threading import Thread, Timer
from configparser import NoOptionError
import json
import traceback
import requests
import sseclient
from core.connection import Connection

def connect_oh_rest(caller):
    """ Subscribe to SSE events and start processing the events
        if API-Token is provided and supported then include it in the request"""
    try:
        if caller.openhab_version >= 3.0 and bool(caller.api_token):
            header = {'Authorization': 'Bearer ' + caller.api_token }
            stream = requests.get("{}/rest/events".format(caller.openhab_url),
                                  headers=header, stream=True)

        else:
            stream = requests.get("{}/rest/events".format(caller.openhab_url),
                                  stream=True)
        caller.client = sseclient.SSEClient(stream)

    except requests.exceptions.Timeout:
        caller.log.error("Timed out connecting to %s", caller.openhab_url)
    except requests.exceptions.ConnectionError as ex:
        caller.log.error("Failed to connect to %s, response: %s", caller.openhab_url, ex)
    except requests.exceptions.HTTPError as ex:
        caller.log.error("Received and unsuccessful response code %s", ex)

    caller.reciever = OpenhabReciever(caller)

class OpenhabREST(Connection):
    """Publishes a state to a given openHAB Item. Expects there to be a URL
    parameter set to the base URL of the openHAB instance. Subscribes to the OH
    SSE feed for commands on the registered Items.
    """

    def __init__(self, msg_processor, params):
        """Starts the SSE subscription and registers for commands on
        RefreshItem. Expects the following params:
        - "URL": base URL of the openHAB instance NOTE: does not support TLS.
        - "RefreshItem": Name of the openHAB Item that, when it receives a
        command will cause sensor_reporter to publish the most recent states of
        all the sensors.
        - msg_processor: message handler for command to the RefreshItem
        """
        super().__init__(msg_processor, params)
        self.log.info("Initializing openHAB REST Connection...")

        self.openhab_url = params("URL")
        self.refresh_item = params("RefreshItem")
        self.registered[self.refresh_item] = msg_processor

        # optional OpenHAB Verison and optional API-Token for connections with authentication
        try:
            self.openhab_version = float(params("openHAB-Version"))
        except NoOptionError:
            self.log.info("No openHAB-Version specified, falling back to version 2.0")
            self.openhab_version = 2.0
        if self.openhab_version >= 3.0:
            try:
                self.api_token = params("API-Token")
            except NoOptionError:
                self.api_token = ""

            if not bool(self.api_token):
                self.log.info("No API-Token specified,"
                " connecting to openHAB without authentication")

        self.client = None
        self.reciever = None
        connect_oh_rest(self)



    def publish(self, message, destination, filter_echo=False):
        """Publishes the passed in message to the passed in destination as an update.

        Handle filter_echo=True the same way as usual publishing of messages
        since openHAB won't send an status update to all subcribers"""
        self.reciever.start_watchdog()
        try:
            self.log.debug("Publishing message %s to %s", message, destination)
            # openHAB 2.x doesn't need the Content-Type header
            if self.openhab_version < 3.0:
                response = requests.put("{}/rest/items/{}/state"
                                    .format(self.openhab_url, destination),
                                    data=message, timeout=10)
            else:
                # define header for OH3 communication and authentication
                header = {'Content-Type': 'text/plain'}
                if bool(self.api_token):
                    header['Authorization'] = "Bearer " + self.api_token

                response = requests.put("{}/rest/items/{}/state"
                                    .format(self.openhab_url, destination),
                                    headers=header, data=message, timeout=10)

            response.raise_for_status()
            self.reciever.activate_watchdog()
        except ConnectionError:
            self.log.error("Failed to connect to %s\n%s", self.openhab_url,
                           traceback.format_exc())
        except requests.exceptions.Timeout:
            self.log.error("Timed out connecting to %s", self.openhab_url)
        except requests.exceptions.ConnectionError as ex:
            #handes exception "[Errno 111] Connection refused"
            # which is not caught by above "ConnectionError"
            self.log.error("Failed to connect to %s, response: %s", self.openhab_url, ex)
        except requests.exceptions.HTTPError as ex:
            self.log.error("Received and unsuccessful response code %s", ex)

    def disconnect(self):
        """Stops the event processing loop."""
        self.log.info("Disconnecting from openHAB SSE")
        self.reciever.stop()

class OpenhabReciever():
    """Initiates a separate Task for recieving OH SSE.
    """

    def __init__(self, caller):
        self.stop_thread = False
        # copy reciever object to local class
        self.client = caller.client
        self.caller = caller
        self.watchdog = None
        self.watchdog_activ = False
        # in case of a connection error dont start the get_messages thread
        if self.client:
            self.thread = Thread(target=self._get_messages, args=(caller,))
            self.thread.start()

    def _get_messages(self, caller):
        """Blocks until stop is set to True. Loops through all the events on the
        SSE subscription and if it's a command to a registered Item, call's that
        Item's handler.
        """
        for event in self.client.events():
            # reset reconnect watchdog
            if self.watchdog:
                self.watchdog.cancel()

            if self.stop_thread:
                self.client.close()
                caller.log.debug("Old OpenHab connection closed")
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

    def _wd_timeout(self):
        """watchdog handler: will reconnect to openhab when invoced"""
        if self.watchdog_activ:
            self.caller.log.info("connection EXPIRED, reconnecting")
            self.stop()
            connect_oh_rest(self.caller)

    def start_watchdog(self):
        """start watchdog before msg gets sent to openhabREST
        if the watchdog gets activated and after 2s no msg from openHAB was
        received the connection gets reseted
        """
        if self.watchdog:
            self.watchdog.cancel()
        self.watchdog_activ = False
        self.watchdog = Timer(2, self._wd_timeout)
        self.watchdog.start()

    def activate_watchdog(self):
        """enable watchdog after msg was succesful send (no exeption due to connection error)
        avoids a reconnect atempt when the connection was unsuccessful
        """
        self.watchdog_activ = True

    def stop(self):
        """Sets a flag to stop the _get_messages thread and to close the openHAB connection.
        Since the thread itself blocks until a message is recieved we won't wait for it
        """
        self.stop_thread = True
