def test(*args):
    return list(args)

#print(test(1))
s="hello\x1ethere"
print(s)
print(s.split('\x1e'))
print(s.encode())