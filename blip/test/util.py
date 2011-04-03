from pkgutil import get_data


def find_data(name):
	"""
	Retrieves the raw contents of a file in the test data directory.
	"""
	return get_data("blip.test", "testdata/{0}".format(name))


def find_blip(name):
	"""
	Retrieves the raw contents of a Blip patch from the test data directory.
	"""
	return find_data("{0}.blip".format(name))


def find_blipa(name):
	"""
	Retrieves the contents of an assembler file from the test data directory.
	"""
	rawdata = find_data("{0}.blipa".format(name))
	return rawdata.decode("utf-8")

