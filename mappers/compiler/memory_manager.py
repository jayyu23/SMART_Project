import math

"""
SMART Compiler Memory Management System
"""


def convert_to_bits(data: int, unit: str):
    """
    Static method to convert data of different units all into bits, so that there can be easier processing
    :param data: int amount of data of any data unit
    :param unit: unit of the data i.e. bit, byte, KB. Conversion assumes 1KB = 1024 Bytes NOT 1000 Bytes
    :return: int the data in bits
    """
    if unit == "bit" or unit == "bits":
        return data
    elif unit == "byte" or unit == "bytes":
        return data * 8
    elif unit == "KB":
        return data * 8 * 1024
    else:
        raise ValueError(f"Unknown unit {unit}. Currently supports 'bit', 'byte', 'KB'")


class MemoryBlock:
    """
    MemoryBlock represents a certain Address Range, and whether or not this Address Range is written. Some functionality
    based on Python range()
    """

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
        else:
            raise TypeError

    def __gt__(self, other):
        if isinstance(other, int):
            return self.start > other
        else:
            raise TypeError

    def __lt__(self, other):
        if isinstance(other, int):
            return self.stop <= other
        else:
            raise TypeError

    def __len__(self):
        return len(self.range_repr)

    def __repr__(self):
        return f"<MemoryBlock {hex(self.start)}-{hex(self.stop)}, written={self.written}>"

    def partition(self, partition_at):
        """
        Partitions the MemoryBlock into two smaller MemoryBlocks, 'left' + 'right' at a given address
        :param partition_at: The memory address where the MemoryBlock should be partitioned into two
        :return: Two MemoryBlocks, tuple(left_block, right_block)
        """
        assert partition_at in self, "Partition address not in MemoryBlock range!"
        left = MemoryBlock(self.start, partition_at, self.step, self.written)
        right = MemoryBlock(partition_at, self.stop, self.step, self.written)
        return left, right


class MemoryModel:
    """
    MemoryModel represents a single storage unit, eg. an SRAM. The contents within the SRAM are kept track of by using
    MemoryBlocks. MemoryModel.address_map is a list() of MemoryBlocks, each with info for an address range and whether
    the address range is written, sorted in ascending order (from Address 0 to max_address)
    """

    def __init__(self, name, size_bits: int, width_bits: int = 64, offset=0x0000):
        self.name = name
        self.width = width_bits
        self.size_bits = size_bits
        self.max_address = int(size_bits / width_bits)
        self.entire_block = MemoryBlock(0, self.max_address)
        self.address_map = [MemoryBlock(0, self.max_address)]

    def __repr__(self):
        return str(self.address_map)

    def __len__(self):
        """
        :return: len() returns the max amount of bits this storage unit can hold
        """
        return self.size_bits

    def get_current_bits(self):
        """
        How many bits have been written in the MemoryModel, i.e. how many bits it is holding right now
        :return: int detailing no. of bits
        """
        addresses = sum([len(k) for k in self.address_map if k.written])
        return addresses * self.width

    def get_max_filled_addr(self):
        """
        The max address that is written within the MemoryModel
        :return: int address (base 10) of the max written address in the MemoryModel
        """
        fill_parts = [max(k.range_repr) for k in self.address_map if k.written]
        out = max(fill_parts) if fill_parts else -1
        return out

    def __edit_range(self, address_block: MemoryBlock, written=None):
        """
        Key algorithm in managing the different MemoryBlocks within MemoryModel.address_map. Uses a Binary Search method
        (since address_map is sorted in ascending order) to find the index of the MemoryBlocks holding the start + stop
        of the target 'address_block', partitions those two blocks to get the start_left and stop_right MemoryBlocks,
        then piece together the new address_map
        :param address_block: The target MemoryBlock to be entered into the MemoryModel.address_map
        :param written: True indicates a 'write'. False indicates a 'delete'
        :return: None. Updates the MemoryModel.address_map
        """
        # Implement a Binary Search of MemoryBlock containing Address start and Address end
        if address_block not in self.entire_block:
            raise ValueError("Not enough memory available")
        address_block.written = written if written is not None else address_block.written

        start_left_i, start_right_i, start_target, found_start = 0, len(self.address_map), address_block.start, False
        stop_left_i, stop_right_i, stop_target, found_stop = 0, len(self.address_map), address_block.stop, False
        start_block_i, stop_block_i = None, None  # MemoryBlock index
        while not (found_start and found_stop):
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
        self.address_map = self.address_map[:start_block_i] + partition_start_left + [address_block] + \
                           partition_stop_right + self.address_map[stop_block_i + 1:]
        self.__streamline()

    def __streamline(self):
        """
        Use the most concise way possible to express the data within the address_map. If two adjacent MemoryBlocks
        are either both written=True or written=False, then they can be merged into a single bigger MemoryBlock
        :return: None. Updates MemoryModel.address_map
        """
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

    def get_num_address(self, size, units='bit'):
        """
        Return how many addresses needed to represent the bit-data. We cannot know this a priori because different
        widths will result in a different number of addresses needed to represent the data.
        :param size: int size of data
        :param units: str units of the data, i.e. 'bit', 'byte', 'KB'.
        Conversion assumes 1KB = 1024 Bytes NOT 1000 Bytes
        :return: int number of addresses needed to represent the bit-data
        """
        return math.ceil(convert_to_bits(size, units) / self.width)

    def get_num_bits(self, num_addresses):
        """
        Return number of bits stored in num_addresses number of addresses
        :param num_addresses: int number of addresses
        :return: int number of bits that num_addresses hold
        """
        return self.width * num_addresses

    def allocate_new(self, size, units='bit'):
        """
        Automatically allocates new (free) memory addresses for data. If no data available, will raise ValueError
        (in MemoryModel.__edit_range method)
        :param size: int size of data
        :param units: str units of the data, i.e. 'bit', 'byte', 'KB'.
        Conversion assumes 1KB = 1024 Bytes NOT 1000 Bytes
        :return: tuple(start_address, stop_address) of the MemoryBlock allocated
        """
        # Allocates unused free memory
        start_address = self.get_max_filled_addr() + 1
        address_num = self.get_num_address(size, units)
        stop_address = start_address + address_num
        self.__edit_range(MemoryBlock(start_address, stop_address), True)
        return start_address, stop_address

    def write_to_address_bits(self, start_address: int, size, units='bit'):
        """
        Write a certain amount of bit-data to a specific start_address
        :param start_address: int (base 10) address to be written to
        :param size: int bit-data size
        :param units: str units of the data, i.e. 'bit', 'byte', 'KB'.
        :return: tuple(start_address, stop_address) of the MemoryBlock allocated
        """
        # Writes to these addresses
        address_num = self.get_num_address(size, units)
        stop_address = start_address + address_num
        self.__edit_range(MemoryBlock(start_address, stop_address), True)
        return start_address, stop_address

    def write_address_range(self, start_address: int, stop_address: int):
        """
        Write data to certain specific addresses
        :param start_address: int (base 10) start address (inclusive)
        :param stop_address: int (base 10) stop address (non-inclusive)
        :return: int total number of bits that have been written
        """
        # Writes from start_address to stop_address (not including stop address)
        self.__edit_range(MemoryBlock(start_address, stop_address))
        written_bits = (stop_address - start_address) * self.width
        return written_bits

    def delete(self, start_address: int, size, units='bit'):
        """
        Delete a certain number of bit-data starting from a certain address
        :param start_address: int (base 10) start address to delete
        :param size: int bit-data size
        :param units: str units of the data, i.e. 'bit', 'byte', 'KB'.
        :return: tuple(start_address, stop_address) of the data deleted
        """
        address_num = self.get_num_address(size, units)
        stop_address = start_address + address_num
        self.__edit_range(MemoryBlock(start_address, stop_address), False)
        return start_address, stop_address

    def clear(self):
        """
        Clear the entire MemoryModel
        :return: None
        """
        self.__edit_range(MemoryBlock(0, self.max_address))


class MemoryManager:
    """
    MemoryManager represents the memory management system for an entire hardware Architecture.
    Currently hard codes three storage units by default: data_sram, his_sram, model_sram
    """

    def __init__(self, name="TH2_NPU_Compiler"):
        self.name = name
        self.architecture = None
        self.memory_models = {'his_sram': MemoryModel('his_sram', size_bits=convert_to_bits(64, 'KB'), width_bits=64),
                              'data_sram': MemoryModel('data_sram', size_bits=convert_to_bits(64, 'KB'), width_bits=64),
                              'model_sram': MemoryModel('model_sram', size_bits=convert_to_bits(256, 'KB'), width_bits= 64)}

    def load_from_architecture(self, architecture):
        # Init the different SRAMs From Architecture Legacy Code
        self.architecture = architecture
        srams = architecture.get_component_class('sram')
        for name, obj in srams.items():
            self.memory_models[name] = MemoryModel(name, int(convert_to_bits(obj.comp_args['size'], 'bytes')),
                                                   obj.comp_args['width'])

    def __repr__(self):
        return f"<MemoryManager for {self.name}: {self.memory_models}>"

    def get(self, memory_name):
        """
        Get the MemoryModel object according to the name of the storage unit
        :param memory_name: The name of the storage unit (eg. data_sram)
        :return: MemoryModel object corresponding to name
        """
        return self.memory_models[memory_name]
