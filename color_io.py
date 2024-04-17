import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def input_print(p, default = ""):
	eprint("\033[93m" + p, end=':\033[0m ', flush=True)
	inp = input("")
	if inp:
		return inp
	else:
		if not default:
			return input_print(p, default)
		return default

def green_print(p):
    eprint("\033[92m" + p + "\033[0m")