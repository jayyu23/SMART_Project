from estimator.data_structures.architecture import yaml_arch_factory
from estimator.utils import read_yaml_file
"""
Converts an Arhitecture Object into an actual Hardware Model
"""

class MemoryModel:
    def __init__(self, size_bytes: int):
        self.max_size = size_bytes
        self.allocation_map = [(range(0, self.max_size), False)]

    def get_current_bytes(self):
        return sum([len(k) for k, v in self.allocation_map if v])

    def print_hex_allocations(self):
        for r, fill in self.allocation_map:
            print(f"<Addr {hex(r.start)} to {hex(r.stop)}>: Filled={fill}")

    def __max_filled_addr(self):
        fill_parts = [max(k) for k, p in self.allocation_map if p]
        out = max(fill_parts) if fill_parts else -1
        return out

    def __edit_range(self, addr_range: range, fill=True):
        print(addr_range)
        to_pop = []
        to_insert = []
        for i, (fill_part, fill_value) in enumerate(self.allocation_map):
            print(i, (fill_part, fill_value))
            if set(addr_range).issubset(set(fill_part)):
                # Then we partition this addr_range
                before, after = range(fill_part.start, addr_range.start), range(addr_range.stop, fill_part.stop)
                if after:
                    to_insert.append((i + 1, (after, fill_value)))
                to_insert.append((i, (addr_range, fill)))
                if before:
                    # print("allocation map", self.allocation_map)
                    to_insert.append((i, (before, fill_value)))
                to_pop.append((fill_part, fill_value))
        [self.allocation_map.insert(k, v) for k, v in to_insert]
        [self.allocation_map.remove(c) for c in to_pop]
        self.__streamline()

    def __streamline(self):
        last_value = None
        new_mapping = []
        for i, partition in enumerate(self.allocation_map):
            if i > 0 and partition[1] == last_value:
                prev = self.allocation_map[i - 1]
                # Merge
                new_mapping.remove(prev)
                new_mapping.append((range(prev[0].start, partition[0].stop), partition[1]))
            else:
                new_mapping.append(partition)
            last_value = partition[1]
        self.allocation_map = new_mapping

    def allocate_new(self, size_bytes: int):
        # Allocates unused free memory
        print("allocate new")
        first_unfilled = self.__max_filled_addr() + 1
        if first_unfilled + size_bytes > self.max_size:
            raise MemoryError(f"Entry exceeds max size: {self.max_size}")
        self.__edit_range(range(first_unfilled, first_unfilled + size_bytes))

    def write_to_addr(self, mem_loc: int, bytes_size: int):
        # Writes to these addresses
        self.__edit_range(range(mem_loc, mem_loc + bytes_size))

    def delete(self, mem_loc: int, bytes_size):
        self.__edit_range(range(mem_loc, mem_loc + bytes_size), False)

    def clear(self):
        self.__edit_range(range(0, self.max_size), False)


class HardwareModel:
    def __init__(self, architecture):
        self.name = architecture.name
        self.architecture = architecture
        self.memory_models = {}

        # Init the different SRAMs
        srams = architecture.get_component_class('sram')
        for name, obj in srams.items():
            self.memory_models[name] = MemoryModel(int(obj.comp_args['size']))
            print(name, self.memory_models[name].allocation_map)
            self.memory_models[name].allocate_new(32)
        print(self.memory_models)

if __name__ == "__main__":
    arch = yaml_arch_factory(read_yaml_file('project_io/estimator_input/architecture.yaml'))
    hw_m = HardwareModel(arch)