import inspect
"""Shows how it is possible to convert class function into string to store into database"""
class Laptop:
    def __init__(self, name, processor, hdd, ram, cost):
        self.name = name
        self.processor = processor
        self.hdd = hdd
        self.ram = ram
        self.cost = cost
    def myFunc(self, a, b):
        if a == "64":
            return 55
        elif b == "32":
            return 999
        else:
            return 30

laptop1 = Laptop('a', 'b', 'c', 'd', 'e')
src = [c.replace("\t", "", 2).replace(" "*4,"", 2) for c in inspect.getsourcelines(laptop1.myFunc)[0][1:]]
print(src)
print("".join(src))
