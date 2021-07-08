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
        self.range_repr = range(start, stop, step)
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
            return self.stop < other

    def __len__(self):
        return len(self.range_repr)

    def __repr__(self):
        return f"<MemoryBlock {hex(self.start)}-{hex(self.stop)}, written={self.written}>"

    def partition(self, partition_at):
        left = MemoryBlock(self.start, partition_at, self.step, self.written)
        right = MemoryBlock(partition_at, self.stop, self.step, self.written)
        return left, right

    def merge(self, adjacent_block_left) -> list:
        print(self, adjacent_block_left)
        assert type(adjacent_block_left) == type(self), "Can only merge with another MemoryBlock"
        assert adjacent_block_left.stop == self.start, "MemoryBlocks not adjacent. Unable to merge"
        if self.written == adjacent_block_left.written:
            return [MemoryBlock(adjacent_block_left.start, self.stop, self.step, self.written)]
        else:
            return [adjacent_block_left, self]


class MemoryModel:
    def __init__(self, size_bits: int, width_bits: int = 64):
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

    def __max_filled_addr(self):
        fill_parts = [max(k.range_repr) for k in self.address_map if k.written]
        out = max(fill_parts) if fill_parts else -1
        return out

    def __edit_range(self, address_block: MemoryBlock, written=True):
        # Implement a Binary Search of Address start and Address end
        print(address_block, self.entire_block)
        assert address_block in self.entire_block, "Address Memory Block is invalid for memory model"
        address_block.written = written
        start_left_i, start_right_i, start_target, found_start = 0, len(self.address_map), address_block.start, False
        stop_left_i, stop_right_i, stop_target, found_stop = 0, len(self.address_map), address_block.stop, False
        start_block_i, stop_block_i = None, None # MemoryBlock index
        while not(found_start and found_stop):
            if not found_start:
                # Search MemoryBlock holding start
                start_middle = int((start_left_i + start_right_i) / 2)
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

        self.address_map = self.address_map[:start_left_i] + partition_start_left + [address_block] + partition_stop_right \
                           + self.address_map[start_right_i:]
        """
        to_pop = []
        to_insert = []
        for i, (fill_part, fill_value) in enumerate(self.address_map):
            print(i, (fill_part, fill_value))
            if set(addr_range).issubset(set(fill_part)):
                # Then we partition this addr_range
                before, after = range(fill_part.start, addr_range.start), range(addr_range.stop, fill_part.stop)
                if after:
                    to_insert.append((i + 1, (after, fill_value)))
                to_insert.append((i, (addr_range, fill)))
                if before:
                    # print("allocation map", self.address_map)
                    to_insert.append((i, (before, fill_value)))
                to_pop.append((fill_part, fill_value))
        [self.address_map.insert(k, v) for k, v in to_insert]
        [self.address_map.remove(c) for c in to_pop]
        """
        self.__streamline()

    def __streamline(self):
        if len(self.address_map) > 1:
            new_address_map = []
            for i in range(1, len(self.address_map)):
                new_address_map += self.address_map[i].merge(self.address_map[i - 1])
            self.address_map = new_address_map

        """
        last_value = None
        new_mapping = []
        for i, partition in enumerate(self.address_map):
            if i > 0 and partition[1] == last_value:
                prev = self.address_map[i - 1]
                # Merge
                new_mapping.remove(prev)
                new_mapping.append((range(prev[0].start, partition[0].stop), partition[1]))
            else:
                new_mapping.append(partition)
            last_value = partition[1]
        self.address_map = new_mapping
        """

    def __get_address_nums(self, size, units):
        return math.ceil(convert_to_bits(size, units) / self.width)

    def allocate_new(self, size, units='bit'):
        # Allocates unused free memory
        start_address = self.__max_filled_addr() + 1
        address_num = self.__get_address_nums(size, units)
        stop_address = start_address + address_num
        if stop_address >= self.max_address:
            raise MemoryError(f"Entry exceeds max address: {self.max_address - 1}")
        self.__edit_range(MemoryBlock(start_address, stop_address))

    def write_to_addr(self, start_address: int, size, units='bit'):
        # Writes to these addresses
        address_num = self.__get_address_nums(size, units)
        stop_address = start_address + address_num
        if stop_address >= self.max_address:
            raise MemoryError(f"Entry exceeds max address: {self.max_address - 1}")
        self.__edit_range(MemoryBlock(start_address, stop_address))

    def delete(self, start_address: int, size, units='bit'):
        address_num = self.__get_address_nums(size, units)
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
            self.memory_models[name] = MemoryModel(int(convert_to_bits(obj.comp_args['size'], 'bytes')))
            self.memory_models[name].allocate_new(32, 'byte')
        print(self.memory_models)


if __name__ == "__main__":
    arch = yaml_arch_factory(read_yaml_file('project_io/estimator_input/architecture.yaml'))
    hw_m = MemoryManager(arch)
