#!/usr/bin/python3

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

import unittest
from bps import diff
from bps import operations as ops
from bps.apply import apply_to_bytearrays
from bps.validate import check_stream
from bps.test import util

class TestIterBlocks(unittest.TestCase):

	def testEmpty(self):
		"""
		An empty sequence yields no blocks.
		"""
		res = list(diff.iter_blocks([], 4))
		self.assertEqual([], res)

	def testReturnValues(self):
		"""
		Each item contains a block of values and the source offset.
		"""
		source = [1,2,3,4,5,6,7,8,9,0]

		self.assertEqual(
				([1,2,3,4], 0),
				next(diff.iter_blocks(source, 4)),
			)

	def testBlockSize(self):
		"""
		The blocksize parameter controls the size of the blocks.
		"""
		source = [1,2,3,4,5,6,7,8,9,0]

		self.assertEqual([
				# Each item is a block and an offset.
				([1,2,3,4], 0),
				([2,3,4,5], 1),
				([3,4,5,6], 2),
				([4,5,6,7], 3),
				([5,6,7,8], 4),
				([6,7,8,9], 5),
				([7,8,9,0], 6),
				([8,9,0],   7),
				([9,0],     8),
				([0],       9),
			], list(diff.iter_blocks(source, 4)))

		self.assertEqual([
				([1,2,3], 0),
				([2,3,4], 1),
				([3,4,5], 2),
				([4,5,6], 3),
				([5,6,7], 4),
				([6,7,8], 5),
				([7,8,9], 6),
				([8,9,0], 7),
				([9,0],   8),
				([0],     9),
			], list(diff.iter_blocks(source, 3)))


class TestMeasureOp(unittest.TestCase):

	def testExactlyMatchingBlocks(self):
		"""
		measure_op yields a matching block.
		"""
		result = diff.measure_op(
				b'aAbAa', 1,
				b'xxAx', 2,
			)

		self.assertEqual(
				(0, 1),
				result,
			)

	def testExtendBlocksForward(self):
		"""
		measure_op extends matches forward as far as possible.
		"""
		# Measure up to the first distance.
		result = diff.measure_op(
				b'xABCDE', 1,
				b'xyABCx', 2,
			)

		self.assertEqual(
				(0, 3),
				result,
			)

		# Measure up to the end of either one of the strings.
		result = diff.measure_op(
				b'xABCD', 1,
				b'xyABC', 2,
			)

		self.assertEqual(
				(0, 3),
				result,
			)

	def testExtendBlocksBackward(self):
		"""
		measure_op extends blocks backward as far as possible.
		"""
		# Measure back to the first difference.
		result = diff.measure_op(
				b'yABCDEFGHIJ', 8,
				#         ^
				b'xxABCDEFGHI', 9,
				#          ^
			)

		self.assertEqual( (7, 2), result)

		# Measure back to the beginning of the string.
		result = diff.measure_op(
				b'ABCDEFGHIJK', 7,
				#        ^
				b'xxABCDEFGHI', 9,
				#          ^
			)

		self.assertEqual( (7, 2), result)

	def testNoMatch(self):
		"""
		measure_op returns no ops if the source and target don't match.

		This can happen for example if there's a hash collision.
		"""
		source = b'AAAAAA'
		target = b'BBBBBB'

		result = diff.measure_op(
				source, 4,
				target, 4,
			)

		self.assertEqual((0, 0), result)


class TestDiffBytearrays(unittest.TestCase):
	# Since the diff algorithm is based on heuristics, changes to the code can
	# produce different delta encodings without necessarily causing a problem.
	# Therefore, we have to think of some tests that test corner-cases without
	# making assumptions about the actual delta encoding that will be
	# generated.

	def _runtest(self, source, target):
		# Compare source and target
		ops = diff.diff_bytearrays(2, source, target)

		# Create a buffer to store the result of applying the patch.
		result = bytearray(len(target))

		# Make sure that diff_bytearrays is producing a valid BPS instruction
		# stream.
		clean_ops = check_stream(ops)

		# Apply the instructions to the source, producing the encoded result.
		apply_to_bytearrays(check_stream(ops), source, result)

		# The result should match the original target.
		self.assertEqual(target, result)

	def testSwap(self):
		"""
		diff_bytearrays produces a working diff for AB -> BA
		"""
		self._runtest(b'AB', b'BA')

	def testEmptySource(self):
		"""
		diff_bytearrays works with an empty source file.
		"""
		self._runtest(b'', b'AB')

	def testEmptyTarget(self):
		"""
		diff_bytearrays works with an empty target file.
		"""
		self._runtest(b'AB', b'')

	def testTrailingNULs(self):
		"""
		diff_bytearrays produces a valid patch even if target ends with NULs.
		"""
		self._runtest(b'A', b'A\x00')

	def testMetadataSupported(self):
		"""
		diff_bytearrays can store metadata if requested.
		"""
		ops = diff.diff_bytearrays(2, b'A', b'B', "metadata goes here")

		header = next(ops)

		self.assertEqual(header.metadata, "metadata goes here")

	def testVariableBlockSize(self):
		"""
		Blocksize affects the generated delta encoding.
		"""
		source = b'ABABAB'
		target = b'AAABBB'

		self.assertEqual(
				list(diff.diff_bytearrays(2, source, target)),
				[
					ops.Header(len(source), len(target)),
					ops.TargetRead(b'AA'),
					ops.SourceRead(2),
					ops.TargetRead(b'B'),
					ops.SourceRead(1),
					ops.SourceCRC32(0x76F34B4D),
					ops.TargetCRC32(0x1A7E625E),
				],
			)

		self.assertEqual(
				list(diff.diff_bytearrays(3, source, target)),
				[
					ops.Header(len(source), len(target)),
					ops.TargetRead(b'AAABB'),
					ops.SourceRead(1),
					ops.SourceCRC32(0x76F34B4D),
					ops.TargetCRC32(0x1A7E625E),
				],
			)

