from app.utils import utils

import pynvml

class PowerUtils(object):
    # Units are Wh
    references = {
        "lightbulb": { "power": 15, "name": "CFL light bulbs" },
        "c3po": { "power": 48.6, "name": "C3PO Droids" } # source: https://www.wired.com/2012/05/how-big-is-c-3p0s-battery/,
    }

    @classmethod
    def get_mean_power(cls, engine_id=None):
        # Returns mean power used by all the GPUs
        # at the moment the function is called
        # Units are Watts
        power = 0
        pynvml.nvmlInit()

        if engine_id:
            handle = pynvml.nvmlDeviceGetHandleByIndex(engine_id)
            power = (pynvml.nvmlDeviceGetPowerUsage(handle) / 1000)
        else:
            for i in range(0, pynvml.nvmlDeviceGetCount()):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                power = power + (pynvml.nvmlDeviceGetPowerUsage(handle) / 1000)
            power = round(power / pynvml.nvmlDeviceGetCount())

        return power

    @classmethod
    def get_reference_text(cls, value, elapsed, reference=None):
        def generate_text(reference, value):
            ref_value = value / PowerUtils.references[reference]['power']
            ref_value = ref_value * (elapsed / 3600)
            ref_value = utils.parse_number(ref_value, round_number=2)
            return "{} {}".format(ref_value, PowerUtils.references[reference]['name'])

        if reference:
            if reference in PowerUtils.references:
                return generate_text(reference, value)
        else:
            texts = [generate_text(reference, value) for reference in PowerUtils.references]
            return texts