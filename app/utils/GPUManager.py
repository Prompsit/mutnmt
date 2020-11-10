import redis
import pynvml
import time

class GPUManager(object):
    redis_conn = redis.Redis()

    @staticmethod
    def scan_devices(reset=False, is_admin=False):
        pynvml.nvmlInit()
        devices = pynvml.nvmlDeviceGetCount()
        start = 0

        if devices > 1:
            if is_admin: devices = 1
            else: start = 1

        for device_id in range(start, devices):
            if reset or not GPUManager.redis_conn.hexists("gpu_slot", device_id):
                GPUManager.free_device(device_id)

        return devices

    @staticmethod
    def get_available_device(mark_as_used=True, is_admin=False):
        devices = GPUManager.scan_devices(is_admin=is_admin)
        for device_id in range(devices):
            if int(GPUManager.redis_conn.hget("gpu_slot", device_id)) == 0:
                if mark_as_used: GPUManager.use_device(device_id)
                return device_id

        return None

    @staticmethod
    def wait_for_available_device(max_iter=None, is_admin=False):
        i = 0

        gpu_id = GPUManager.get_available_device(is_admin=is_admin)
        while gpu_id is None and (max_iter is None or i < max_iter):
            time.sleep(1)
            gpu_id = GPUManager.get_available_device()
            i += 1

        return gpu_id

    @staticmethod
    def use_device(device_id):
        GPUManager.redis_conn.hset("gpu_slot", device_id, 1)

    @staticmethod
    def free_device(device_id):
        GPUManager.redis_conn.hset("gpu_slot", device_id, 0)
