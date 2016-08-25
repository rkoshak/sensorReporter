"""
   Copyright 2015 Richard Koshak

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

 Script: signalProc.py
 Author: Rich Koshak
 Date:   October 22, 2015
 Purpose: Provide a mechanism whereby fucntions can be run and in the event of a
   term singal exit cleanly.

  Based on code published here:
  http://stackoverflow.com/questions/14123592/implementing-signal-handling-on-a-sleep-loop
"""

import signal
import time

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

class BlockingAction(object):
    """Class to wrap a blocking function and record that the function is active. Used in conjunction with
       SignalHandler to properly handle termination signals. """

    def __new__(cls, action):
        """Wraps the passed in function in a BlockingAction unless it already is."""

        if isinstance(action, BlockingAction):
            return action
        else:
            new_action = super(BlockingAction, cls).__new__(cls)
            new_action.action = action
            new_action.active = False
            return new_action

    def __call__(self, *args, **kwargs):
        """Marks the function as active, calls it, then marks it as inactive"""

        self.active = True
        result = self.action(*args, **kwargs)
        self.active = False
        return result


class SignalHandler(object):
    """Handles termination signals by waiting for any active BlockingAction to complete before calling
       the cleanup function"""

    def __new__(cls, sig, action):
        """Wrap the passed in function in this object unless it is already wrapped."""

        if isinstance(action, SignalHandler):
            handler = action
        else:
            handler = super(SignalHandler, cls).__new__(cls)
            handler.action = action
            handler.blocking_actions = []
        signal.signal(sig, handler)
        return handler

    def __call__(self, signum, frame):
        """Wait for any active BlockingAction completes before calling the cleanup function"""

        while any(a.active for a in self.blocking_actions):
            time.sleep(.01)
        return self.action()
    
    def blocks_on(self, action):
        """Adds the passed in function as a BlockingAction"""

        blocking_action = BlockingAction(action)
        self.blocking_actions.append(blocking_action)
        return blocking_action

def handles(signal):
    """Called when a signal occurs. It wraps the SignalHandler so the decorator only has to pass the function."""

    def get_handler(action):

        return SignalHandler(signal, action)

    return get_handler
