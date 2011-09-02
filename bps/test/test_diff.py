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
				([5,6,7,8], 4),
				([9,0],     8),
			], list(diff.iter_blocks(source, 4)))

		self.assertEqual([
				([1,2,3], 0),
				([4,5,6], 3),
				([7,8,9], 6),
				([0],     9),
			], list(diff.iter_blocks(source, 3)))


class TestMeasureOp(unittest.TestCase):

	def testExactlyMatchingBlocks(self):
		"""
		measure_op yields a matching block.
		"""
		result = diff.measure_op(
				0,
				b'aAbAa', 1,
				b'xxAx', 2,
				ops.SourceCopy,
			)

		self.assertEqual(
				[ops.SourceCopy(1, 1)],
				result,
			)

	def testExtendBlocksForward(self):
		"""
		measure_op extends matches forward as far as possible.
		"""
		result = diff.measure_op(
				0,
				b'xABCD', 1,
				b'xxABC', 2,
				ops.SourceCopy,
			)

		self.assertEqual(
				[ops.SourceCopy(3, 1)],
				result,
			)

	def testExtendBlocksBackward(self):
		"""
		measure_op extends blocks backward up to pendingTargetReadSize bytes.
		"""
		result = diff.measure_op(
				5,
				b'ABCDEFGHIJK', 7,
				#        ^
				b'xxABCDEFGHI', 9,
				#          ^
				ops.SourceCopy,
			)

		self.assertEqual(
				[ops.SourceCopy(7, 2)],
				result,
			)

	def testSourceRead(self):
		"""
		measure_op yields SourceRead ops when possible.
		"""
		result = diff.measure_op(
				0,
				# Because the match is at the same offset in the source and
				# target buffers, we can represent it with a SourceRead
				# operation.
				b'xABABC', 1,
				b'xABCD', 1,
				ops.SourceCopy,
			)

		self.assertEqual(
				[ops.SourceRead(2)],
				result,
			)

	def testTargetCopy(self):
		"""
		measure_op can also generate TargetCopy instructions.
		"""
		target = b'xAxABxABC'
		#                ^

		result = diff.measure_op(
				0,
				target, 3,
				target, 6,
				ops.TargetCopy,
			)

		self.assertEqual(
				[ops.TargetCopy(2, 3)],
				result,
			)

	def testPendingTargetRead(self):
		"""
		measure_op includes a TargetRead if there's pending bytes.
		"""
		source = b'xBBBBBBB'
		target = b'xAAABBBB'
		#              ^

		result = diff.measure_op(
				3,
				source, 4,
				target, 4,
				ops.SourceCopy,
			)

		self.assertEqual(
				[ops.TargetRead(b'AAA'), ops.SourceRead(4)],
				result,
			)


class TestDiffBytearrays(unittest.TestCase):
	# Since the diff algorithm is based on heuristics, changes to the code can
	# produce different delta encodings without necessarily causing a problem.
	# Therefore, we have to think of some tests that test corner-cases without
	# making assumptions about the actual delta encoding that will be
	# generated.

	def _runtest(self, source, target):
		# Compare source and target
		ops = diff.diff_bytearrays(source, target)

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
		ops = diff.diff_bytearrays(b'A', b'B', "metadata goes here")

		header = next(ops)

		self.assertEqual(header.metadata, "metadata goes here")

