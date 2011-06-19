#!/usr/bin/python3

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# the COPYING file included with this distribution or
# http://sam.zoy.org/wtfpl/COPYING for more details.

import unittest
from blip import diff
from blip import operations as ops
from blip.apply import apply_to_bytearrays
from blip.validate import check_stream
from blip.test import util

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


class TestMeasureSpan(unittest.TestCase):

	def testBasicOperation(self):
		"""
		measure_span returns the correct length for a matching span.
		"""
		#           vvvvvvvvv      expected matching span
		source = [0,1,2,3,4,5,6,7]
		target = [1,2,3,4,5,7,9,0]
		#         ^^^^^^^^^        expected matching span

		self.assertEqual(5, diff.measure_span(source, 1, target, 0, 4))

	def testShortSource(self):
		"""
		measure_span stops when it hits the end of the source sequence.
		"""
		source = [0,1,2,3,4,5,6,7]
		target = [3,4,5,6,7,8,9,0]

		self.assertEqual(5, diff.measure_span(source, 3, target, 0, 4))

	def testShortTarget(self):
		"""
		measure_span stops when it hits the end of the target sequence.
		"""
		source = [3,4,5,6,7,8,9,0]
		target = [0,1,2,3,4,5,6,7]

		self.assertEqual(5, diff.measure_span(source, 0, target, 3, 4))


class TestIterCandidateOps(unittest.TestCase):

	def testMissingBlock(self):
		"""
		iter_candidate_ops yields nothing if the block cannot be found.
		"""
		candidates = diff.iter_candidate_ops(b'A', {}, b'ABC', b'CAB', 1,
				ops.SourceCopy)

		self.assertEqual([], list(candidates))

	def testExactlyMatchingBlocks(self):
		"""
		iter_candidate_ops yields blocks that match, if there are any.
		"""
		candidates = diff.iter_candidate_ops(
				b'A',
				{ b'A': [1, 3] },
				b'aAbAa',
				b'xxAx', 2,
				ops.SourceCopy,
			)

		self.assertEqual(
				[ ops.SourceCopy(1, 1), ops.SourceCopy(1, 3), ],
				list(candidates),
			)

	def testExtendableBlocks(self):
		"""
		iter_candidate_ops extends blocks, where possible.
		"""
		candidates = diff.iter_candidate_ops(
				b'A',
				{ b'A': [1, 3] },
				# The match at offset 1 matches for 2 bytes, but the match at
				# offset 3 matches for 3 bytes.
				b'xABABC',
				b'xxABCD', 2,
				ops.SourceCopy,
			)

		self.assertEqual(
				[ ops.SourceCopy(2, 1), ops.SourceCopy(3, 3) ],
				list(candidates),
			)

	def testSourceRead(self):
		"""
		iter_candidate_ops yields SourceRead ops when possible.
		"""
		candidates = diff.iter_candidate_ops(
				b'A',
				{ b'A': [1, 3] },
				# Because the first match is at the same offset in the source
				# and target buffers, we can represent it with a SourceRead
				# operation.
				b'xABABC',
				b'xABCD', 1,
				ops.SourceCopy,
			)

		self.assertEqual(
				[ ops.SourceRead(2), ops.SourceCopy(3, 3) ],
				list(candidates),
			)

	def testTargetCopy(self):
		"""
		iter_candidate_ops can also generate TargetCopy instructions.
		"""
		target = b'xAxABxABC'
		#                ^
		targetWriteOffset = 6
		targetmap = { b'A': [1, 3] }

		candidates = diff.iter_candidate_ops(
				b'A', targetmap, target, target, targetWriteOffset,
				ops.TargetCopy,
			)

		self.assertEqual(
				[ ops.TargetCopy(1, 1), ops.TargetCopy(2, 3) ],
				list(candidates),
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

		# Make sure that diff_bytearrays is producing a valid Blip instruction
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

