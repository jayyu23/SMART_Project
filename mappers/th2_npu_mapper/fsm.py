from mappers.th2_npu_mapper.operation_maker import OperationMaker


class FSM:
    """An abstract finite state machine to simulate the behaviour of NPU

    The instructions are categorized into 3 classes based on the Time Space
    complexity. 2 stands for O(N^2), 1 stands for O(N) and 0 stands for O(1)
    """

    def __init__(self):
        self.out_dim = None  # number of columns
        self.in_dim = None  # numer of rows, NPU iterates over row
        self.fsmn_relu_range = (-128, 127)  # 8-bit signed integer
        self.NUM_MAC_ARRAY = 8
        self.op_maker = OperationMaker()

    # Level-2
    def sgemm(self, in_addr, out_addr, his_addr, batch_mode, scale, bias, his_enable, weight_bit):
        """SGEMM and optionally ReLU"""
        print('RUNNING SGEMM')
        print(
            f'SGEMM: batch={batch_mode} scale={scale} bias={bias} write_his={his_enable} weight={weight_bit}bit')
        if his_enable:
            print(f'his@: {his_addr.int}')
        print(f'input @ {in_addr.uint}')
        print(f'output@ {out_addr.uint}')
        # NOTE: it's a demo roughly calculating MACs
        num_macs = self.in_dim * self.out_dim
        # 8x8 mac unit can be used as two 8x4 mac unit
        mac_per_cycle = self.NUM_MAC_ARRAY * 8 / weight_bit
        num_cycles = num_macs / mac_per_cycle
        num_psram_access = num_macs * weight_bit / 8
        print(f'cycle: {num_cycles}, psram: {num_psram_access} Bytes')
        self.op_maker.add_sgemm(self.in_dim, self.out_dim, weight_bit, self.NUM_MAC_ARRAY, his_enable=his_enable)

    def fsmn(self, in_addr, out_addr):
        """FSMN history element-wise production and summation"""
        print('FSMN')
        print(f'input @ {in_addr.uint}')
        print(f'output@ {out_addr.uint}')
        # NOTE: it's a demo roughly calculating MACs
        num_macs = self.out_dim * self.fsmn_filter_size
        # FSMN computes 8x8 only
        num_cycles = num_macs / self.NUM_MAC_ARRAY
        num_psram_access = num_macs
        print(f'cycle: {num_cycles}, psram: {num_psram_access} Bytes, layers: {self.fsmn_filter_size}')
        self.op_maker.add_fsmn(out_dim=self.out_dim, fsmn_filter_size=self.fsmn_filter_size)

    def tdnn(self, his_addr, output_addr, length, write_back=False, reset=False):
        """TDNN via SGEMM and accumulate"""
        print('TDNN accumulate:', f'reset={reset}', f'write={write_back}')
        print(f'length: {length}')
        print(f'tdnn_sum @ {his_addr.uint}')
        print(f'output@ {output_addr.uint}')

    # Level-1
    def clamp(self, in_addr, out_addr, length):
        """Clamp by min-max value"""
        print('CLAMP')
        print(f'length: {length}')
        print(f'input @ {in_addr.uint}')
        print(f'output@ {out_addr.uint}')

    def modulation(self, in_addr, out_addr, length):
        """BatchNorm / Element-wise affine"""
        print('MODULATION / BatchNorm')
        print(f'length: {length}')
        print(f'input @ {in_addr.uint}')
        print(f'output@ {out_addr.uint}')

    def copy(self, in_addr, out_addr, length, direction, reset=False):
        """Copy database between database SRAM and history SRAM"""
        if direction:
            if reset:
                direction_str = '0 -> his'
            else:
                direction_str = 'database -> his'
        else:
            if reset:
                direction_str = 'database <- 0'
            else:
                direction_str = 'database <- his'
        print('COPY', direction_str)
        print(f'length: {length}')
        print(f'input @ {in_addr.uint}')
        print(f'output@ {out_addr.uint}')
        self.op_maker.add_copy_data(direction_str, length)

    # Level-0

    def weight_sram_redirection(self, target_addr):
        """Redirect the weight SRAM pointer"""
        print('REDIRECT')
        print(f'weight @ {target_addr.uint}')

    # meta database management
    # SGEMM part
    # slot1: in_dim
    # slot2: out_dim
    def set_matrix_dim(self, in_dim: int = None, out_dim: int = None):
        """Update the global status register"""
        print('UPDATE')
        if in_dim is not None:
            self.in_dim = in_dim
        if out_dim is not None:
            self.out_dim = out_dim
        print(f'in={self.in_dim}, out={self.out_dim}')
        self.op_maker.add_update_gsr()

    # slot0
    def set_sgemm_relu(self, min: int, max: int):
        self.sgemm_relu_range = (min, max)
        print('UPDATE')
        print(f'Clamp range sgemm={self.sgemm_relu_range}')
        self.op_maker.add_update_gsr()

    # slot1
    def set_drop_bits(self, drop_bits: int, scale_drop_bits: int):
        self.drop_bits = drop_bits
        self.scale_drop_bits = scale_drop_bits
        print('UPDATE')
        print(f'Drop bits ({self.drop_bits}, scale={self.scale_drop_bits})')
        self.op_maker.add_update_gsr()

    # FSMN part
    # slot1
    def set_fsmn_relu(self, min: int, max: int):
        self.fsmn_relu_range = (min, max)
        print('UPDATE')
        print(f'Clamp range fsmn={self.fsmn_relu_range}')
        self.op_maker.add_update_gsr()

    # slot2
    def set_fsmn_drop_bits(self, drop_bits: int):
        self.fsmn_drop_bits = drop_bits
        print(f'DROP BITS fsmn={self.fsmn_drop_bits}')

    # slot2
    def set_fsmn_history(self, history_size: int, left_order: int):
        """Set the temporal parameter for FSMN

        FUCK this API plz.

        filter_size = sum(lo + ro + 1)
        history_size = sum(lo + ro)
        left_order = lo
        """
        self.fsmn_filter_size = history_size + 1
        self.fsmn_lo = left_order

    # TDNN part
    # slot0
    def set_tdnn_relu(self, min: int, max: int):
        self.tdnn_relu_range = (min, max)
        print('UPDATE')
        print(f'Clamp range tdnn={self.tdnn_relu_range}')
        self.op_maker.add_update_gsr()
