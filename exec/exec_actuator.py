from core.actuator import Actuator
import subprocess

class ExecActuator(Actuator):

    def __init__(self, connections, log, params):

        super().__init__(connections, log, params)

        self.command = params("Command")
        self.command_topic = params("Topic")
        self.result_topic = params("ResultTopic")

        self.log.info("Configuring Exec Actuator: Command Topic = {}, Result "
                      "Topic = {}, Command = {}"
                      .format(self.command_topic, self.result_topic, self.command))

    def on_message(self, client, userdata, msg):

        self.log("Receives command on {}: {}"
                 .format(self.command_topic, msg.payload))

        cmd_args = [arg for arg in self.command.split(' ')
                    if arg.find(';') == -1 and arg.find('|') == -1 and arg.find('//') == -1]

        [cmd_args.append(arg) for arg in msg.payload.split(' ')
         if arg != 'NA' and arg.find(';') == -1 and arg.find('|') == -1 and arg.find('//') == -1]

        self.log.info("Executing command withe the following arguments: {}"
                      .format(cmd_args))

        try:
            output = subprocess.check_output(cmd_args, shell=False,
                                             universal_newlines=True)
            self.log.info("Command results to be published to {}\n{}"
                          .format(self.result_topic, output))
            self._publish(output, self.result_topic)
        except subprocess.CallProcessError as e:
            self.log.error("Command returned and error code: {}\n{}"
                           .format(e.returncode, e.output))
            self._publish("ERROR", self.result_topic)
