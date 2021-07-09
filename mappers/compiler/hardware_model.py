import math

from estimator.data_structures.architecture import yaml_arch_factory
from estimator.utils import read_yaml_file

"""
Memory Management System created from an Architecture Object
"""


def convert_to_bits(data: int, unit: str):
    if unit == "bit" or unit == "bits":
        return data
    elif unit == "byte" or unit == "bytes":
        return data * 8
    elif unit == "KB":
        return data * 8 * 1024


class MemoryBlock:
    def __init__(self, start, stop, step=1, written=False):
        self.range_repr = range(start, stop, step)  # Since we can't inherit range object
        self.start = start
        self.stop = stop
        self.step = step
        self.written = written

    def __contains__(self, item):
        if isinstance(item, int):
            return self.start <= item < self.stop
        elif isinstance(item, MemoryBlock):
            return item.start >= self.start and item.stop < self.stop

    def __gt__(self, other):
        if isinstance(other, int):
            return self.start > other

    def __lt__(self, other):
        if isinstance(other, int):
            return self.stop <= other

    def __len__(self):
        return len(self.range_repr)

    def __repr__(self):
        return f"<MemoryBlock {hex(self.start)}-{hex(self.stop)}, written={self.written}>"

    def partition(self, partition_at):
        left = MemoryBlock(self.start, partition_at, self.step, self.written)
        right = MemoryBlock(partition_at, self.stop, self.step, self.written)
        return left, right


class MemoryModel:
    def __init__(self, name, size_bits: int, width_bits: int = 64):
        self.name = name
        self.width = width_bits
        self.size_bits = size_bits
        self.max_address = int(size_bits / width_bits)
        self.entire_block = MemoryBlock(0, self.max_address)
        self.address_map = [MemoryBlock(0, self.max_address)]

    def __repr__(self):
        return str(self.address_map)

    def __len__(self):
        return self.size_bits

    def get_current_bits(self):
        addresses = sum([len(k.range_repr) for k in self.address_map if k.written])
        return addresses * self.width

    def get_max_filled_addr(self):
        fill_parts = [max(k.range_repr) for k in self.address_map if k.written]
        out = max(fill_parts) if fill_parts else -1
        return out

    def __edit_range(self, address_block: MemoryBlock, written=True):
        # Implement a Binary Search of MemoryBlock containing Address start and Address end
        assert address_block in self.entire_block, "Address Memory Block is invalid for memory model"
        address_block.written = written

        start_left_i, start_right_i, start_target, found_start = 0, len(self.address_map), address_block.start, False
        stop_left_i, stop_right_i, stop_target, found_stop = 0, len(self.address_map), address_block.stop, False
        start_block_i, stop_block_i = None, None  # MemoryBlock index
        while not (found_start and found_stop):
            if not found_start:
                # Search MemoryBlock holding start
                start_middle = int((start_left_i + start_right_i) / 2)
                # print('im stuck', hex(start_target), self.address_map, start_middle)
                if start_target in self.address_map[start_middle]:
                    start_block_i = start_middle
                    found_start = True
                elif start_target > self.address_map[start_middle]:
                    start_left_i = start_middle + 1
                elif start_target < self.address_map[start_middle]:
                    start_right_i = start_middle - 1
            if not found_stop:
                # Search MemoryBlock holding stop
                stop_middle = int((stop_left_i + stop_right_i) / 2)
                if stop_target in self.address_map[stop_middle]:
                    stop_block_i = stop_middle
                    found_stop = True
                elif start_target > self.address_map[stop_middle]:
                    stop_left_i = stop_middle + 1
                elif start_target < self.address_map[stop_middle]:
                    stop_right_i = stop_middle - 1
        # Now reconstruct the address_map
        partition_start_left = self.address_map[start_block_i].partition(start_target)[0]
        partition_start_left = [partition_start_left] if len(partition_start_left) > 0 else []
        partition_stop_right = self.address_map[stop_block_i].partition(stop_target)[1]
        partition_stop_right = [partition_stop_right] if len(partition_stop_right) > 0 else []
        self.address_map = self.address_map[:start_block_i] + partition_start_left + [address_block] + \
                           partition_stop_right + self.address_map[stop_block_i + 1:]
        self.__streamline()

    def __streamline(self):
        if len(self.address_map) > 1:
            new_address_map = [self.address_map[0]]
            for i in range(1, len(self.address_map)):
                current_block = self.address_map[i]
                previous_block = new_address_map[-1]
                # Determine if merge
                if current_block.written == previous_block.written:
                    new_address_map[-1] = MemoryBlock(previous_block.start, current_block.stop,
                                                      written=current_block.written)
                else:
                    new_address_map.append(current_block)
            self.address_map = new_address_map

    def get_address_num(self, size, units):
        """
        Return how many addresses needed to represent the bit-data
        :param size:
        :param units:
        :return:
        """
        return math.ceil(convert_to_bits(size, units) / self.width)

    def get_bits_num(self, num_addresses):
        return self.width * num_addresses

    def allocate_new(self, size, units='bit'):
        # Allocates unused free memory
        start_address = self.get_max_filled_addr() + 1
        address_num = self.get_address_num(size, units)
        stop_address = start_address + address_num
        self.__edit_range(MemoryBlock(start_address, stop_address), True)
        return start_address, stop_address

    def write_to_addr_bits(self, start_address: int, size, units='bit'):
        # Writes to these addresses
        address_num = self.get_address_num(size, units)
        stop_address = start_address + address_num
        self.__edit_range(MemoryBlock(start_address, stop_address), True)
        return start_address, stop_address

    def write_address_range(self, start_address: int, stop_address: int):
        # Writes from start_address to stop_address (not including stop address)
        self.__edit_range(MemoryBlock(start_address, stop_address))
        written_bits = (stop_address - start_address) * self.width
        return written_bits

    def delete(self, start_address: int, size, units='bit'):
        address_num = self.get_address_num(size, units)
        stop_address = start_address + address_num
        self.__edit_range(MemoryBlock(start_address, stop_address), False)

    def clear(self):
        self.__edit_range(MemoryBlock(0, self.max_address))


class MemoryManager:
    def __init__(self, architecture):
        self.name = architecture.name
        self.architecture = architecture
        self.memory_models = {}

        # Init the different SRAMs
        srams = architecture.get_component_class('sram')
        for name, obj in srams.items():
            self.memory_models[name] = MemoryModel(name, int(convert_to_bits(obj.comp_args['size'], 'bytes')),
                                                             obj.comp_args['width'])
            # self.memory_models[name].allocate_new(4, 'KB')
        # print(self)

    def __repr__(self):
        return f"<MemoryManager for {self.name}: {self.memory_models}>"

    def get(self, memory_name):
        return self.memory_models[memory_name]


if __name__ == "__main__":
    arch = yaml_arch_factory(read_yaml_file('project_io/estimator_input/architecture.yaml'))
    hw_m = MemoryManager(arch)
