#!/usr/bin/python3

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

import unittest
from io import BytesIO
from blip import operations as ops
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
				ops.Header(3, 3),
				ops.SourceRead(1),
				ops.SourceRead(1),
				ops.SourceRead(1),
				ops.SourceCRC32(0x66A031A7),
				ops.TargetCRC32(0x66A031A7),
			]

		expected = [
				ops.Header(3, 3),
				ops.SourceRead(3),
				ops.SourceCRC32(0x66A031A7),
				ops.TargetCRC32(0x66A031A7),
			]

		actual = list(test_optimize(original))

		self.assertSequenceEqual(expected, actual)

	def testMergeTargetReads(self):
		"""
		Consecutive TargetReads are merged.
		"""
		original = [
				ops.Header(0, 3),
				ops.TargetRead(b'A'),
				ops.TargetRead(b'A'),
				ops.TargetRead(b'A'),
				ops.SourceCRC32(0x00000000),
				ops.TargetCRC32(0x66A031A7),
			]

		expected = [
				ops.Header(0, 3),
				ops.TargetRead(b'AAA'),
				ops.SourceCRC32(0x00000000),
				ops.TargetCRC32(0x66A031A7),
			]

		actual = list(test_optimize(original))

		self.assertSequenceEqual(expected, actual)

	def testMergeContiguousSourceCopys(self):
		"""
		A SourceCopy is merged if its offset is zero.
		"""
		original = [
				ops.Header(3, 4),
				# Make sure the SourceCopy offset never matches the
				# targetWriteOffset, so that our SourceCopys won't be converted
				# to SourceReads.
				ops.TargetRead(b'A'),
				ops.SourceCopy(1, 0),
				# This SourceCopy resumes where the previous one left off, so
				# it can be merged with the previous one.
				ops.SourceCopy(1, 1),
				# This SourceCopy copies data from somewhere else in the file,
				# so it can't be merged.
				ops.SourceCopy(1, 0),
				ops.SourceCRC32(0x66A031A7),
				ops.TargetCRC32(0x66A031A7),
			]

		expected = [
				ops.Header(3, 4),
				ops.TargetRead(b'A'),
				ops.SourceCopy(2, 0),
				ops.SourceCopy(1, 0),
				ops.SourceCRC32(0x66A031A7),
				ops.TargetCRC32(0x66A031A7),
			]

		actual = list(test_optimize(original))

		self.assertSequenceEqual(expected, actual)

	def testMergeContiguousTargetCopys(self):
		"""
		A TargetCopy is merged if its offset is zero.
		"""
		original = [
				ops.Header(0, 4),
				ops.TargetRead(b'A'),
				ops.TargetCopy(1, 0),
				# This TargetCopy resumes where the previous one left off, so
				# it can be merged with the previous one.
				ops.TargetCopy(1, 1),
				# This TargetCopy copies data from somewhere else in the file,
				# so it can't be merged.
				ops.TargetCopy(1, 0),
				ops.SourceCRC32(0x00000000),
				ops.TargetCRC32(0x66A031A7),
			]

		expected = [
				ops.Header(0, 4),
				ops.TargetRead(b'A'),
				ops.TargetCopy(2, 0),
				ops.TargetCopy(1, 0),
				ops.SourceCRC32(0x00000000),
				ops.TargetCRC32(0x66A031A7),
			]

		actual = list(test_optimize(original))

		self.assertSequenceEqual(expected, actual)

	def testConvertSourceCopyToSourceRead(self):
		"""
		A SourceCopy at the targetWriteOffset can be a SourceRead.
		"""
		original = [
				ops.Header(3, 3),
				# This SourceCopy can be coverted to a SourceRead, because it's
				# reading at the targetWriteOffset.
				ops.SourceCopy(1, 0),
				# This SourceCopy can't be converted, since it's reading from
				# a different offset.
				ops.SourceCopy(1, 0),
				# This one can be converted.
				ops.SourceCopy(1, 2),
				ops.SourceCRC32(0x66A031A7),
				ops.TargetCRC32(0x66A031A7),
			]

		expected = [
				ops.Header(3, 3),
				ops.SourceRead(1),
				ops.SourceCopy(1, 0),
				ops.SourceRead(1),
				ops.SourceCRC32(0x66A031A7),
				ops.TargetCRC32(0x66A031A7),
			]

		actual = list(test_optimize(original))

		self.assertSequenceEqual(expected, actual)


if __name__ == "__main__":
	unittest.main()
