"""Disassembly the NPU descriptor to human readable instructions"""
from collections import defaultdict
from bitstring import BitArray
import click

from fsm import FSM


def _get_in_out_addr(desc):
    input_addr = desc(44, 32)
    output_addr = desc(60, 48)
    return input_addr, output_addr


class Descriptor:
    """A simple wrapper for NPU descriptor easier to access

    Hardware designer prefer this type of addressing logic,
    I don't know why.

    self(high, low) == self.bit_array[low, high+1].reverse()
    """

    def __init__(self, bit_array: BitArray):
        self.bit_array = bit_array

    def __call__(self, high: int, low: int = None):
        if low is None:  # Single bit
            return self.bit_array[high]
        assert high >= low
        value = self.bit_array[low:high + 1]
        value.reverse()
        return value


class Disassembler:
    def __init__(self):
        self.npu = FSM()

    def disassembly(self, desc):
        mapping = {
            '00': self.sgemm,
            '01': self.other,
            '10': self.clamp,
        }
        desc_type = desc(1, 0).bin
        return mapping[desc_type](desc)

    def clamp(self, desc):
        sram_fifo_clr = desc(63)
        data_length = desc(28, 16).uint
        in_addr, out_addr = _get_in_out_addr(desc)
        self.npu.clamp(in_addr, out_addr, data_length)

    def sgemm(self, desc):
        sram_fifo_clr = desc(63)
        his_addr = desc(28, 16)

        weight_bit = desc(10, 8)
        weight_bit_mapping = {
            '000': 8,
            '001': 4,
            '011': 1,
        }
        weight_bit = weight_bit_mapping[weight_bit.bin]

        his_enable = desc(7)
        batch_mode = desc(14)
        scale = desc(11)
        bias = desc(3)
        in_addr, out_addr = _get_in_out_addr(desc)
        self.npu.sgemm(in_addr, out_addr, his_addr, batch_mode,
                       scale, bias, his_enable, weight_bit)

    def other(self, desc):
        mapping = ({
            '001': self.fsmn,
            '111': self.update_status,
            '110': self.copy,
            '011': self.tdnn,
            '100': self.modulation,
            '101': self.weight_sram_redirection,
        })
        desc_type = desc(6, 4)
        return mapping[desc_type.bin](desc)

    def fsmn(self, desc):
        in_addr, out_addr = _get_in_out_addr(desc)
        self.npu.fsmn(in_addr, out_addr)

    def _update_part0(self, desc):
        descriptor_type = desc(3, 2).bin
        if descriptor_type == '00':
            # ReLU min-max is signed integer
            relu_min = desc(15, 8).int
            relu_max = desc(23, 16).int
            self.npu.set_sgemm_relu(min=relu_min, max=relu_max)
        elif descriptor_type == '01':
            # ReLU min-max is signed integer
            relu_min = desc(15, 8).int
            relu_max = desc(23, 16).int
            self.npu.set_tdnn_relu(min=relu_min, max=relu_max)
        elif descriptor_type == '10':  # sigmoid
            print('NotImplemented d0', descriptor_type)
        elif descriptor_type == '11':  # bypass
            pass

    def _update_part1(self, desc):
        descriptor_type = desc(27, 24).bin
        if descriptor_type == '0000':
            rows = desc(40, 28).uint
            self.npu.set_matrix_dim(in_dim=rows)
        elif descriptor_type == '0010':
            sgemm_drop_bits = desc(32, 28).uint
            sgemm_scale_drop_bits = desc(40, 36).uint
            self.npu.set_drop_bits(sgemm_drop_bits, sgemm_scale_drop_bits)
        elif descriptor_type == '0011':
            relu_min = desc(35, 28).int
            relu_max = desc(43, 36).int
            self.npu.set_fsmn_relu(relu_min, relu_max)
        elif descriptor_type == '1111':
            pass
        else:
            print('NotImplemented d1', descriptor_type)

    def _update_part2(self, desc):
        descriptor_type = desc(47, 44).bin
        if descriptor_type == '0000':
            columns = desc(60, 48).uint
            self.npu.set_matrix_dim(out_dim=columns)
        elif descriptor_type == '0001':
            fsmn_history_size = desc(53, 48).uint  # his_num
            fsmn_left_order = desc(61, 56).uint
            self.npu.set_fsmn_history(fsmn_history_size, fsmn_left_order)
        elif descriptor_type == '0101':
            fsmn_drop_bits = desc(52, 48).uint
            self.npu.set_fsmn_drop_bits(fsmn_drop_bits)
        elif descriptor_type == '1111':
            pass
        else:
            print('NotImplemented d2', descriptor_type)

    def update_status(self, desc):
        self._update_part0(desc)
        self._update_part1(desc)
        self._update_part2(desc)

    def copy(self, desc):
        clear = desc(12)
        direction = desc(8)
        length = desc(28, 16).uint
        in_addr, out_addr = _get_in_out_addr(desc)
        self.npu.copy(in_addr, out_addr, length, direction, clear)

    def tdnn(self, desc):
        output_addr = desc(60, 48)
        his_addr = desc(39, 32)
        reset = desc(8)
        write_back = desc(9)
        length = desc(28, 16).uint
        self.npu.tdnn(his_addr, output_addr, length, write_back, reset)

    def modulation(self, desc):
        length = desc(28, 16).uint
        in_addr, out_addr = _get_in_out_addr(desc)
        self.npu.modulation(in_addr, out_addr, length)

    def weight_sram_redirection(self, desc):
        target_addr = desc(51, 32)
        self.npu.weight_sram_redirection(target_addr)


@click.command()
@click.argument('binary-path', default='machine_code_input/vad_binary.txt')
def main(binary_path):
    descriptors = [BitArray(hex=line.strip()) for line in open(binary_path)]
    for desc in descriptors:
        desc.reverse()

    open('desc_out.txt', 'w').writelines(
        '\n'.join([desc.bin for desc in descriptors]))
    fsm = Disassembler()
    for idx, desc in enumerate(descriptors):
        print(f'=== Instruction {idx} ===')
        fsm.disassembly(Descriptor(desc))
    fsm.npu.op_maker.write_out()


if __name__ == '__main__':
    main()
