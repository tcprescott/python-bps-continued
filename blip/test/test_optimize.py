#!/usr/bin/python3

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

import unittest
from io import BytesIO
from blip import constants as C
from blip.io import read_blip
from blip.test.util import find_blip
from blip.validate import check_stream
from blip.optimize import optimize


def test_optimize(iterable):
	"""
	Check that the input to and output from optimize is sensible.
	"""
	for item in check_stream(optimize(check_stream(iterable))):
		yield item


class TestOptimize(unittest.TestCase):

	def testEmptyPatch(self):
		"""
		The simplest possible patch can be processed correctly.
		"""
		original = list(read_blip(BytesIO(find_blip("empty"))))
		result = list(test_optimize(original))

		self.assertSequenceEqual(original, result)

	def testMergeSourceReads(self):
		"""
		Consecutive SourceReads are merged.
		"""
		original = [
				(C.BLIP_MAGIC, 3, 3, ""),
				(C.SOURCEREAD, 1),
				(C.SOURCEREAD, 1),
				(C.SOURCEREAD, 1),
				(C.SOURCECRC32, 0x66A031A7),
				(C.TARGETCRC32, 0x66A031A7),
			]

		expected = [
				(C.BLIP_MAGIC, 3, 3, ""),
				(C.SOURCEREAD, 3),
				(C.SOURCECRC32, 0x66A031A7),
				(C.TARGETCRC32, 0x66A031A7),
			]

		actual = list(test_optimize(original))

		self.assertSequenceEqual(expected, actual)

	def testMergeTargetReads(self):
		"""
		Consecutive TargetReads are merged.
		"""
		original = [
				(C.BLIP_MAGIC, 0, 3, ""),
				(C.TARGETREAD, b'A'),
				(C.TARGETREAD, b'A'),
				(C.TARGETREAD, b'A'),
				(C.SOURCECRC32, 0x00000000),
				(C.TARGETCRC32, 0x66A031A7),
			]

		expected = [
				(C.BLIP_MAGIC, 0, 3, ""),
				(C.TARGETREAD, b'AAA'),
				(C.SOURCECRC32, 0x00000000),
				(C.TARGETCRC32, 0x66A031A7),
			]

		actual = list(test_optimize(original))

		self.assertSequenceEqual(expected, actual)

	def testMergeContiguousSourceCopys(self):
		"""
		A SourceCopy is merged if its offset is zero.
		"""
		original = [
				(C.BLIP_MAGIC, 3, 3, ""),
				(C.SOURCECOPY, 1, 0),
				# This SourceCopy resumes where the previous one left off, so
				# it can be merged with the previous one.
				(C.SOURCECOPY, 1, 1),
				# This SourceCopy copies data from somewhere else in the file,
				# so it can't be merged.
				(C.SOURCECOPY, 1, 0),
				(C.SOURCECRC32, 0x66A031A7),
				(C.TARGETCRC32, 0x66A031A7),
			]

		expected = [
				(C.BLIP_MAGIC, 3, 3, ""),
				(C.SOURCECOPY, 2, 0),
				(C.SOURCECOPY, 1, 0),
				(C.SOURCECRC32, 0x66A031A7),
				(C.TARGETCRC32, 0x66A031A7),
			]

		actual = list(test_optimize(original))

		self.assertSequenceEqual(expected, actual)

	def testMergeContiguousTargetCopys(self):
		"""
		A TargetCopy is merged if its offset is zero.
		"""
		original = [
				(C.BLIP_MAGIC, 0, 4, ""),
				(C.TARGETREAD, b'A'),
				(C.TARGETCOPY, 1, 0),
				# This TargetCopy resumes where the previous one left off, so
				# it can be merged with the previous one.
				(C.TARGETCOPY, 1, 1),
				# This TargetCopy copies data from somewhere else in the file,
				# so it can't be merged.
				(C.TARGETCOPY, 1, 0),
				(C.SOURCECRC32, 0x00000000),
				(C.TARGETCRC32, 0x66A031A7),
			]

		expected = [
				(C.BLIP_MAGIC, 0, 4, ""),
				(C.TARGETREAD, b'A'),
				(C.TARGETCOPY, 2, 0),
				(C.TARGETCOPY, 1, 0),
				(C.SOURCECRC32, 0x00000000),
				(C.TARGETCRC32, 0x66A031A7),
			]

		actual = list(test_optimize(original))

		self.assertSequenceEqual(expected, actual)


if __name__ == "__main__":
	unittest.main()
