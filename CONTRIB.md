# Coding Style

Do not use `implicit` coding style
```
test = None
if (test):
   print('test is None')
```

Do use the `explicit` coding style
```
test = None
if test is not None:
   print('test is None')
```