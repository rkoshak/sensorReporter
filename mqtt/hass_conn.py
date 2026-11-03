# mqtt/ha_discovery.py
"""Optional Home Assistant discovery bridge built on ha-mqtt-discoverable."""
import json
import re
from collections.abc import Callable
from time import sleep
from typing import Any, ClassVar, Optional

import paho.mqtt.client as mqtt

from mqtt.mqtt_conn import OFFLINE, ONLINE, REFRESH, MqttConnection

try:
    from ha_mqtt_discoverable import DeviceInfo
    from ha_mqtt_discoverable import sensors as hads
    HAVE_HAD = True
except ImportError:
    HAVE_HAD = False


class HassConnection(MqttConnection):
    """Emits HA discovery configs using MqttConnection's paho client.

    Only the discovery/config messages go through ha-mqtt-discoverable.
    State publication stays in MqttConnection so the generic Connection
    interface (shared with openHAB REST) is untouched.
    """

    TOPIC_FORMAT = "{}/{}"  # root_topic, destination

    COMPONENT_MAP: ClassVar = {
        "sensor": ("Sensor", "SensorInfo"),
        "binary_sensor": ("BinarySensor", "BinarySensorInfo"),
        "switch": ("Switch", "SwitchInfo"),
        "light": ("Light", "LightInfo"),
        "number": ("Number", "NumberInfo"),
        "select": ("Select", "SelectInfo"),
        "button": ("Button", "ButtonInfo"),
        "cover": ("Cover", "CoverInfo"),
    }

    def __init__(self, msg_processor, conn_cfg: dict[str, Any]):
        # Initialize MqttConnection base class (sets up self.client, etc.)
        self.discovery_enabled = bool(conn_cfg.get("HADiscovery", True)) and HAVE_HAD
        try:
            with open('.ha_entities.json', 'r') as f:
                self.published: dict[str, dict[str, str]] = json.load(f)  # topic -> payload

        except FileNotFoundError:
            self.published: dict[str, dict[str, str]] = {}

        except json.JSONDecodeError:
            self.published: dict[str, dict[str, str]] = {}

        self.availability = None  # set by MqttConnection once known

        # start mqtt client
        super().__init__(msg_processor, conn_cfg)
        self.log.debug("HAConnection initializing with config:\n%s", json.dumps(conn_cfg, indent=2))
        self.client_name = conn_cfg["Client"]
        self.node_id = re.sub(r"\W", "_", self.client_name)
        self.prefix = conn_cfg.get("HAPrefix", "homeassistant")

        self._seen: set = set()

        self.device_info = None
        if HAVE_HAD:
            name = conn_cfg["DeviceID"] or self.client_name
            ident = "{}_{}".format(
                name,
                conn_cfg["DeviceID"].replace(" ", "_").lower(),
            )
            self.device_info = DeviceInfo(name=name, identifiers=ident)

        if conn_cfg.get("HADiscovery", False) and not HAVE_HAD:
            self.log.warning("HADiscovery requested but ha-mqtt-discoverable is "
                        "not installed; run ./install_dependencies.sh hadiscovery")
        elif not self.discovery_enabled and self.published:
            self.log.info("HADiscovery disabled in config; removing previously published configs")
            self.withdraw_all()
        
        self.set_availability(
                self.TOPIC_FORMAT.format(self.root_topic, self.lwt),
                ONLINE, OFFLINE
            )

    def register(self,
                 comm_conn: dict[str, Any],
                 handler:Optional[Callable[[str], None]]) -> None:
        """ Registers a handler to be called on messages received on topic
            appended to the root_topic. Handler is expected to take one argument,
            the message.
        """
        #handler can be None if a sensor registers it's outputs
        super().register(comm_conn, handler)
        sensors_ha_cfg: list = []
        if "HADiscovery" in comm_conn:
            cfg = dict(comm_conn.get("HADiscovery"))                      # don't mutate the YAML dict
            cfg.setdefault("command_src", comm_conn.get("CommandSrc"))
            cfg.setdefault("state_dest", comm_conn.get("StateDest"))
            sensors_ha_cfg.append(cfg)
        else:
            # handle connections with multiple sensors
            for sensor, value in comm_conn.items():
                if "HADiscovery" in value:
                    cfg = dict(value.get("HADiscovery"))                      # don't mutate the YAML dict
                    cfg.setdefault("command_src", value.get("CommandSrc"))
                    cfg.setdefault("state_dest", value.get("StateDest"))
                    self.log.debug("cfg for sensor %s: %s", sensor, cfg)
                    sensors_ha_cfg.append(cfg)

        if self.discovery_enabled:
            for sensor_config in sensors_ha_cfg:
                self.annouce_entitie(sensor_config)


    def on_connect(self,
                   client: mqtt.Client,
                   userdata: Any,
                   flags: dict[str, int],
                   retcode: int) -> None:
        """ Called when the client connects to the broker, resubscribe to the
            sensorReporter topic.
            Gets automatically called from self.client after connection
            got fully established (on first connect and on reconnect)
        """
        refresh = self.TOPIC_FORMAT.format(self.root_topic, REFRESH)
        self.log.info(
            "Connected with client %s, userdata %s, flags %s, and "
            "result code %s. Subscribing to refresh command topic %s",
            client,
            userdata,
            flags,
            retcode,
            refresh,
        )

        self.connected = True

        # Publish the ONLINE message to the LWT
        self._publish_mqtt(ONLINE, self.lwt, True)
        # send messages which got collected while connection was offline
        super().conn_went_online()

        # Resubscribe on connection
        for reg in self.registered:
            self.log.info("on_connect: Resubscribing to %s", reg)
            self.client.subscribe(reg)

        # Plublish entities configuration
        self.republish_all()

        # causes sensors to republish their states
        self.msg_processor("MQTT connected")

    def disconnect(self) -> None:
        """ Closes the connection to the MQTT broker."""
        self.log.debug("HassConnection disconnecting from MQTT")
        self.withdraw_stale()
        with open(".ha_entities.json", "w") as f:
            json.dump(self.published, f)
        self._seen.clear()
        self.published.clear()
        super().disconnect()

    def set_availability(self, topic: str, online: str, offline: str) -> None:
        self.availability = {"availability_topic": topic,
                             "payload_available": online,
                             "payload_not_available": offline}

    def annouce_entitie(self, cfg: dict[str, Any]) -> None:
        if not self.discovery_enabled:
            self.log.debug("HADiscovery disabled; skipping announce for %s", cfg)
            return

        component = cfg.pop("component", "sensor")
        if component not in self.COMPONENT_MAP:
            self.log.error("Unsupported HADiscovery component: %s", component)
            return

        _, info_cls_name = self.COMPONENT_MAP[component]
        info_cls = getattr(hads, info_cls_name)

        name = cfg.pop("name", None)
        state_dest = cfg.pop("state_dest", None)
        command_src = cfg.pop("command_src", None)
        object_id = re.sub(
            r"\W", "_", str(state_dest or command_src)
        )
        unique_id = cfg.pop(
            "unique_id", 
            f"{self.client_name}_{object_id}"
        )
        kwargs = dict(cfg)                       # device_class, units, templates...
        kwargs["name"] = name or object_id       # required by every *Info class
        kwargs[""] = object_id
        kwargs["device"] = self.device_info
        if unique_id:
            kwargs["unique_id"] = unique_id
        if self.availability:
            kwargs.update(self.availability)
        if state_dest:
            kwargs["state_topic"] = self.TOPIC_FORMAT.format(
                self.root_topic, state_dest)
        if command_src:
            kwargs["command_topic"] = "{}/{}/set".format(
                self.root_topic, command_src)

        try:
            info = info_cls(**kwargs)
            payload = json.loads(
                info.model_dump_json(exclude_none=True, by_alias=True)
            )
            self.log.debug("HADiscovery payload for %s: %s", object_id, payload)
        except Exception as exc:
            self.log.error("Bad HADiscovery config for %s: %s", object_id, exc)
            return

        if state_dest:
            payload["state_topic"] = self.TOPIC_FORMAT.format(
                self.root_topic, state_dest)
            payload.pop("json_attributes_topic", None)
        if command_src:
            payload["command_topic"] = "{}/{}/set".format(
                self.root_topic, command_src)

        if self.availability:
            payload.update(self.availability)

        cfg_topic = "{}/{}/{}/{}/config".format(
            self.prefix, component, self.node_id, object_id)
        body = json.dumps(payload)

        self.client.publish(cfg_topic, body, qos=1, retain=True)
        self.log.debug("HADiscovery announced %s: %s", cfg_topic, body)
        self.published[cfg_topic] = body
        self._seen.add(cfg_topic)

    def withdraw_all(self) -> None:
        """Blank out retained configs before a config reload."""
        self.log.debug("Withdrawing all HADiscovery configs")
        for topic in self.published:
            self.client.publish(topic, "", qos=1, retain=True)
            self.log.debug("HADiscovery withdrawing config: %s", topic)
        self.published.clear()
        with open(".ha_entities.json", "w") as f:
            json.dump(self.published, f)

    def republish_all(self):
        if not self.discovery_enabled:
            return
        for topic, payload in self.published.items():
            self.client.publish(topic, payload, qos=1, retain=True)

    def withdraw_stale(self) -> None:
        """Call after all devices have re-registered."""
        self.log.debug("Withdrawing stale HADiscovery configs")
        for topic in list(self.published.keys()):
            if topic not in self._seen:
                self.client.publish(topic, "", qos=1, retain=True)
                self.log.debug(
                    "HADiscovery withdrawing stale configs: %s",
                    self.published[topic],
                )
                del self.published[topic]

    def publish_device_properties(self):
        """
        Used to delete sensors removed from yaml file.
        
        Could be more useful if sensors and actuators are passed as args.
        
        """
        # Send empty configs to topice removed from yml
        self.withdraw_stale()

        # Give HA time to process the config before state arrives
        sleep(.5 * len(self.published))
        super().publish_device_properties()
