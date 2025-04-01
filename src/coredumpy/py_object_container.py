# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/coredumpy/blob/master/NOTICE.txt

import queue
import time

from .config import config
from .type_support import TypeSupportManager, NotReady
from .py_object_proxy import PyObjectProxy, _unknown


class PyObjectContainer:
    def __init__(self):
        self._objects = {}
        self._objects_holder = {}
        self._proxies = {}

    def clear(self):
        self._objects.clear()
        self._objects_holder.clear()
        self._proxies.clear()

    def add_objects(self, objs, depth=None):
        TypeSupportManager.load_lazy_supports()
        with config.dump_context():
            objects = {}
            curr_recursion_depth = 0
            pending_objects = list(objs)
            if depth is None:
                depth = config.default_recursion_depth
            start_time = time.perf_counter()
            while curr_recursion_depth < depth and pending_objects:
                next_objects = {}
                for o in pending_objects:
                    data, new_objects = TypeSupportManager.dump(o)
                    objects[str(id(o))] = data
                    # To avoid repeated object ids, we keep a reference to all
                    # objects in the container
                    self._objects_holder[str(id(o))] = o
                    if new_objects:
                        for new_obj in new_objects:
                            if str(id(new_obj)) not in objects:
                                next_objects[str(id(new_obj))] = new_obj
                curr_recursion_depth += 1
                pending_objects = list(next_objects.values())
                if time.perf_counter() - start_time > config.dump_timeout:
                    break
            self._objects.update(objects)
        return [self._objects[str(id(obj))] for obj in objs]

    def add_object(self, obj, depth=None):
        return self.add_objects([obj], depth)[0]

    def load_objects(self, objects):
        TypeSupportManager.load_lazy_supports()
        self._objects = objects.copy()
        unresolved_queue = queue.Queue()
        not_ready_objects = set()
        for key in self._objects:
            unresolved_queue.put(key)

        while not unresolved_queue.empty():
            obj_id = unresolved_queue.get()
            data = self._objects.get(obj_id)
            if data is None:
                proxy = _unknown
            else:
                if obj_id in self._proxies:
                    if obj_id in not_ready_objects:
                        dependency = TypeSupportManager.reload(self._proxies[obj_id], data, self._proxies)
                        if dependency:
                            for dep_id in dependency:
                                unresolved_queue.put(dep_id)
                            unresolved_queue.put(obj_id)
                        else:
                            not_ready_objects.remove(obj_id)
                    continue
                else:
                    proxy, dependency = TypeSupportManager.load(data, self._proxies)
                    if isinstance(proxy, PyObjectProxy):
                        proxy.link_container(self)
                        proxy._coredumpy_id = obj_id
                    if dependency:
                        not_ready_objects.add(obj_id)
                        for dep_id in dependency:
                            unresolved_queue.put(dep_id)
                        unresolved_queue.put(obj_id)
                    else:
                        if obj_id in not_ready_objects:
                            not_ready_objects.remove(obj_id)

            if proxy is not NotReady:
                self._proxies[obj_id] = proxy
        # We could have imported some new libs while loading the objects,
        # so we need to load lazy supports again to make sure we have all the
        # encoders listed
        TypeSupportManager.load_lazy_supports()

    def get_object(self, obj_id):
        return self._proxies.get(obj_id, _unknown)

    def get_objects(self):
        return self._objects
