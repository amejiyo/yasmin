# Copyright (C) 2023  Miguel Ángel González Santamarta

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from abc import ABCMeta, abstractmethod
from typing import List, Callable, Type
from std_srvs.srv import Trigger
from std_msgs.msg import String

from rclpy.node import Node
from rclpy.service import Service

from yasmin import State
from yasmin import Blackboard
from yasmin_ros.yasmin_node import YasminNode
from yasmin_ros.basic_outcomes import SUCCEED, ABORT, TIMEOUT, CANCEL, WAITING


class ServiceServer(State):

    _node: Node
    _srv_name: str
    _service_server: Service
    _srv_callback: Callable
    _create_request_handler: Callable
    _response_handler: Callable
    _timeout: float
    __abort_event: Callable = None

    def __init__(
        self,
        srv_name: str,
        execute_handler: Callable,
        srv_callback: Callable = None,
        srv_type: Type = Trigger,
        outcomes: List[str] = None,
        node: Node = None,
        timeout: float = None,
        pub_topic_name: str = None,
        abort_event: Callable = None
    ) -> None:
        
        self._srv_name = srv_name

        _outcomes = [SUCCEED, CANCEL, ABORT]

        self._timeout = timeout
        if self._timeout:
            _outcomes.append(TIMEOUT)
            
        if outcomes:
            _outcomes = _outcomes + outcomes

        if node is None:
            self._node = YasminNode.get_instance()
        else:
            self._node = node

        if srv_callback: self._srv_callback = srv_callback
        self._service_server = self._node.create_service(
            srv_type, srv_name, self._srv_callback)
        
        if pub_topic_name: 
            self.__pub_topic = self._node.create_publisher(String, pub_topic_name, 10)
        else: self.__pub_topic = None

        if abort_event:
            self.__abort_event = abort_event

        self._execute_handler = execute_handler

        if srv_callback: self._srv_callback = srv_callback

        self.__transition:bool = False  # trigger to change state
        super().__init__(_outcomes)
        print(self.__str__)

    def _srv_callback(self, request, response):
        """ state service callback """
        self.__transition = True
        return response

    def execute(self, blackboard: Blackboard) -> str:
        while True:
            if self._execute_handler: 
                outcome = self._execute_handler(blackboard)
            if self.__transition:
                outcome = SUCCEED
                self.__transition = False
            if self._is_canceled(): 
                if self.__abort_event: self.__abort_event()
                return ABORT
            if outcome != WAITING: break
        return outcome
    
    def _is_canceled(self):
        if self.is_canceled():
            self._canceled = False
            return True
        return False
    
    def publish_msg(self, msg: str):
        """
        Args:
            msg: message (string) to publish
        Raises:
            ros2 publish message to <pub_topic_name>
        """
        _msg = String()
        _msg.data = msg
        if self.__pub_topic: self.__pub_topic.publish(_msg)