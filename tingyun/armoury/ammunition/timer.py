"""this module implement the time tracer for tracker
"""

import time
import logging


console = logging.getLogger(__name__)


class Timer(object):
    """
    """
    node = None

    def __init__(self, tracker):
        self.tracker = tracker
        self.children = []
        self.start_time = 0
        self.end_time = 0
        self.duration = 0
        self.exclusive = 0
        
    def __enter__(self):
        """
        """
        if not self.tracker:
            console.debug("tracker is %s.return now.", self.tracker)
            return self

        # check the base node is set or not
        parent_node = self.tracker.current_node()
        if not parent_node or parent_node.terminal_node():
            self.tracker = None
            return parent_node

        self.start_time = time.time()
        self.tracker.push_node(self)
        
        return self
        
    def __exit__(self, exc, value, tb):
        """
        """
        if not self.tracker:
            return self.tracker

        self.end_time = time.time()
        if self.end_time < self.start_time:
            self.end_time = self.start_time
            console.warn("end time is less than start time.")

        self.duration = int((self.end_time - self.start_time) * 1000)
        self.exclusive += self.duration
        
        # pop the self and return parent node
        parent_node = self.tracker.pop_node(self)

        self.finalize_data()
        current_node = self.create_node()
        
        if current_node:
            self.tracker.process_database_node(current_node)
            parent_node.process_child(current_node)
            
        self.tracker = None
        
    def create_node(self):
        if self.node:
            return self.node(**dict((k, self.__dict__[k]) for k in self.node._fields))

        return self

    def finalize_data(self):
        pass
    
    def process_child(self, node):
        self.children.append(node)
        self.exclusive -= node.duration
        
    def terminal_node(self):
        return False
