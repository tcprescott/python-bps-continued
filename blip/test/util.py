from pkgutil import get_data


def read_blp(name):
	"""
	Reads a Blip patch from the test data directory.
	"""
	return get_data("blip.test", "testdata/{0}.blp".format(name))


def read_blpa(name):
	"""
	Reads a Blip assembler file from the test data directory.
	"""
	rawdata = get_data("blip.test", "testdata/{0}.blpa".format(name))
	return rawdata.decode("utf-8")

