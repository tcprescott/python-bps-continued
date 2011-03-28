from pkgutil import get_data


def find_blp(name):
	"""
	Retrieves the raw contents of a Blip patch from the test data directory.
	"""
	return get_data("blip.test", "testdata/{0}.blp".format(name))


def find_blpa(name):
	"""
	Retrieves the contents of an assembler file from the test data directory.
	"""
	rawdata = get_data("blip.test", "testdata/{0}.blpa".format(name))
	return rawdata.decode("utf-8")

