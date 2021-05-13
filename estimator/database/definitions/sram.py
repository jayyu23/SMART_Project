class Sram:
    def __init__(self):
        self.width = 32
        self.KBSize = 32
        self.energy_functions = (("read", self.rw_energy_function),
                                 ("write", self.rw_energy_function),
                                 ("idle", self.idle_energy_function))
        self.cycle_functions = ()
        self.area_functions = ()

    def rw_energy_function(self, width, KBsize):
        w32 = {8: 5, 32: 10, 256: 20}
        if width == 32:
            return w32[KBsize]

    def idle_energy_function(self, width, KBsize):
        return 0.001 * width * KBsize
