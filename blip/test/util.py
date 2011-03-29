from pkgutil import get_data


def find_blip(name):
	"""
	Retrieves the raw contents of a Blip patch from the test data directory.
	"""
	return get_data("blip.test", "testdata/{0}.blip".format(name))


def find_blipa(name):
	"""
	Retrieves the contents of an assembler file from the test data directory.
	"""
	rawdata = get_data("blip.test", "testdata/{0}.blipa".format(name))
	return rawdata.decode("utf-8")

