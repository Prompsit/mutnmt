import pynvml

class PowerUtils(object):
    # Units are Watts
    references = {
        "c3po": { "power": 48.6, "name": "C3PO Droids" }, # source: https://www.wired.com/2012/05/how-big-is-c-3p0s-battery/,
        "lightbulb": { "power": 15, "name": "lightbulbs" } # source: the lightbulb of my room
    }

    @classmethod
    def get_mean_power(self):
        # Returns mean power used by all the GPUs
        # at the moment the function is called
        # Units are Watts
        power = 0
        pynvml.nvmlInit()
        for i in range(0, pynvml.nvmlDeviceGetCount()):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            power = power + (pynvml.nvmlDeviceGetPowerUsage(handle) / 1000)
        power = round(power / pynvml.nvmlDeviceGetCount())
        return power

    @classmethod
    def get_reference_text(value, reference=None):
        def generate_text(reference, value):
            ref_value = value / PowerUtils.references[reference]['power']
            return "{} {}".format(ref_value, PowerUtils.references[reference]['name'])

        if reference:
            if reference in PowerUtils.references:
                return generate_text(reference, value)
        else:
            return " or ".join([generate_text(reference, value) for reference in PowerUtils.references])
