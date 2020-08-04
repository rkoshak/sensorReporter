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
import logging
import requests
import traceback
from core.connection import Connection

log = logging.getLogger(__name__.split(".")[1])

class OpenhabREST(Connection):
    """Publishes a state to a given openHAB Item. Expects there to be a URL
    parameter set to the base URL of the openHAB instance.
    """

    def __init__(self, msg_processor, params):
        super().__init__(msg_processor, params, log)
        log.info("Initializing openHAB REST Connection...")

        self.openhab_url = params("URL")

        # TODO implement a websocket subscription

    def publish(self, state, item):
        """Publishes the passed in state to the passed in Item."""
        try:
            log.debug("Publishing message %s to %s", state, item)
            response = requests.put("{}/rest/items/{}/state"
                                    .format(self.openhab_url, item),
                                    data=state, timeout=10)
            response.raise_for_status()
        except ConnectionError:
            log.error("Failed to connect to %s\n%s", self.openhab_url,
                      traceback.format_exc())
        except requests.exceptions.Timeout:
            log.error("Timed out connecting to %s")
        except requests.exceptions.HTTPError as ex:
            log.error("Received and unsuccessful response code %s", ex)
