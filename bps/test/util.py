
# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

from pkgutil import get_data


def find_data(name):
	"""
	Retrieves the raw contents of a file in the test data directory.
	"""
	return get_data("bps.test", "testdata/{0}".format(name))


def find_bps(name):
	"""
	Retrieves the raw contents of a BPS patch from the test data directory.
	"""
	return find_data("{0}.bps".format(name))


def find_bpsa(name):
	"""
	Retrieves the contents of an assembler file from the test data directory.
	"""
	rawdata = find_data("{0}.bpsa".format(name))
	return rawdata.decode("utf-8")

