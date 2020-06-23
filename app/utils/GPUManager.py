import redis
import pynvml

class GPUManager(object):
    redis_conn = redis.Redis()

    def scan_devices(reset=False):
        pynvml.nvmlInit()
        devices = pynvml.nvmlDeviceGetCount()

        for device_id in range(0, devices):
            if reset or not GPUManager.redis_conn.hexists("gpu_slot", device_id):
                GPUManager.free_device(device_id)

        return devices

    def get_available_device(mark_as_used = True):
        devices = GPUManager.scan_devices()
        for device_id in range(devices):
            if int(GPUManager.redis_conn.hget("gpu_slot", device_id)) == 0:
                if mark_as_used: GPUManager.use_device(device_id)
                return device_id

        return None

    def wait_for_available_device(max_iter=None):
        i = 0

        gpu_id = GPUManager.get_available_device()
        while gpu_id is None and (max_iter is None or i < max_iter):
            time.sleep(1)
            gpu_id = GPUManager.get_available_device()
            i += 1

        return gpu_id

    def use_device(device_id):
        GPUManager.redis_conn.hset("gpu_slot", device_id, 1)

    def free_device(device_id):
        GPUManager.redis_conn.hset("gpu_slot", device_id, 0)
