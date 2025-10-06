import getpass
class test:
    def __init__(self):
        self.val = 0

def modify(t : test) -> None:
    t.val = 2

class MessageFormat:
    SEP = '|'
    def __init__(self, name: str, format_list: list = []):
        self.name = name
        self.format_list = format_list
    
    def build(self, arg_list: list = []) -> str:
        if len(arg_list) != len(self.format_list):
            raise ValueError(f"Expected {len(self.format_list)} args, got {len(arg_list)}.")
        
        built = self.name
        
        for format_type, arg in zip(self.format_list, arg_list):
            if type(arg).__name__ != format_type.__name__:
                raise ValueError(f"Expected type {format_type.__name__}, got {type(arg).__name__}")
            if type(arg).__name__ == "str" and MessageFormat.SEP in arg:
                raise ValueError(f"string in arg_list contains {MessageFormat.SEP}, which is not acceptable")
            built += MessageFormat.SEP + str(arg)
            
        return built
    
    def parse(self, message: str) -> list:
        parts = message.split(sep=MessageFormat.SEP)
        if parts[0] != self.name:
            raise ValueError(f"Expected {self.name}, got {parts[0]}.")
        if len(parts) - 1 != len(self.format_list):
            raise ValueError(f"Expected number for parameters of {self.name} is {len(self.format_list)}, got {len(parts) - 1} parameters.")
        parsed = []
        for format_type, part in zip(self.format_list, parts[1:]):
            try:
                parsed.append(format_type(part))
            except Exception:
                raise ValueError(f"failed to parse {part} as {format_type.__name__}.")
        return parsed

MYFORMAT = MessageFormat("MYFORMAT", [str, int, float])
TESTING = MessageFormat("TESTING", [int, str])
PURE = MessageFormat("PURE")
#print(type("3.5").__name__)

message = MYFORMAT.build(["", 4, 2.035])
print(f"message: \"{message}\"")
msg_list = MYFORMAT.parse(message)
print(f"parsed msg_list: {msg_list}")

message = TESTING.build([5, ""])
print(f"message: \"{message}\"")
msg_list = TESTING.parse(message)
print(f"parsed msg_list: {msg_list}")

message = PURE.build()
print(f"message: \"{message}\"")
msg_list = PURE.parse(message)
print(f"parsed msg_list: {msg_list}")

lst = []
if lst == None:
    print("True")
else:
    print("False")

print(f"\"{"123 \n".strip()}\"")

a, b, c = [3, "a", str]
print(a)
print(b)
print(c)
d, = [2]
print(d)
print(list(map(int, ['3', '14', '7'])))
print([2, 2, 4].count(2))
a = 2
print(3 / a if a != 0 else 7)
#print(2 / a)
t = test()

#print(13 // 2)
#print(ord('b') - ord('`'))

#print(t.val)
#modify(t)
#print(t.val)
#password = getpass.getpass("Enter Password: ")
#print(f"You entered: {password}")
def in_arg(*args):
    print(args)

in_arg(tuple([2, 4, 5]))

def add(a, b):
    return a + b

def pass_a_function(func: callable) -> None:
    print("result:", func(3, 4))
